# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import sys
import datetime
from dateutil.relativedelta import relativedelta
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    PostbackEvent,
    TextMessage,
    TextSendMessage,
    TemplateSendMessage,
    PostbackTemplateAction,
    StickerSendMessage,
    MessageAction,
    ConfirmTemplate,
)
from app.database_connection import get_connection
from app.models.wallet import AggregateWallet, insert_wallet
from app.models.payer import StorePayer


app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)

if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(PostbackEvent)
def on_postback(event):
    postback_data = event.postback.data.split(":")
    StorePayer.pname_id = postback_data[1]
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text=postback_data[0] + "の支払額はいくらですか？")
    )


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    # DBコネクション作成
    conn = get_connection()
    # 支払者クラスのインスタンス作成＋支払者名取得
    payer = StorePayer(conn)
    # 受信メッセージを分割
    umsg = event.message.text.split()

    match umsg[0]:
        case "集計":
            year_labels = (
                str((datetime.date.today() - relativedelta(months=1)).year) + "年",
                str((datetime.datetime.now()).year) + "年",
            )
            month_labels = (
                str((datetime.date.today() - relativedelta(months=1)).month) + "月",
                str((datetime.date.today()).month) + "月",
            )
            confirm_template_message = TemplateSendMessage(
                alt_text="何月の集計ですか？",
                template=ConfirmTemplate(
                    text="何月の集計ですか？",
                    actions=[
                        MessageAction(
                            label=month_labels[0],
                            text=year_labels[0] + " " + month_labels[0],
                        ),
                        MessageAction(
                            label=month_labels[1],
                            text=year_labels[1] + " " + month_labels[1],
                        )
                    ]
                )
            )
            line_bot_api.reply_message(event.reply_token, confirm_template_message)
        case x if "年" in x:
            agr_wal = AggregateWallet(umsg, conn)
            # 集計処理実行
            agr_money = agr_wal.no_assign_year()
            msg_month = str(umsg[0]) + " " + str(umsg[1])
            # メッセージ作成
            content = (
                msg_month
                + "分 集計しました！\n\n"
                + payer.getname(1)
                + "："
                + str(agr_money[0])
                + "\n"
                + payer.getname(2)
                + "："
                + str(agr_money[1])
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=content))
        case "登録":
            message_template = TemplateSendMessage(
                alt_text="支払者は誰ですか？",
                template=ConfirmTemplate(
                    text="支払者は誰ですか？",
                    actions=[
                        PostbackTemplateAction(
                            label=payer.getname(1), data=payer.getname(1) + ":1"
                        ),
                        PostbackTemplateAction(
                            label=payer.getname(2), data=payer.getname(2) + ":2"
                        ),
                    ],
                ),
            )
            line_bot_api.reply_message(event.reply_token, message_template)
        case x if(x.isnumeric()) and (StorePayer.pname_id is not None):
            # 時間取得
            nowtime = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            # 集計クラスのインスタンス作成
            agr_wal = AggregateWallet(umsg[0], conn)
            # 支払金額登録処理+集計処理実行
            agr_money = insert_wallet(umsg, nowtime, StorePayer.pname_id, conn, agr_wal)
            content = (
                "金額の登録が完了したよ！\n\n【現在までの集計】\n"
                + "{0:%m}".format(datetime.datetime.strptime(nowtime, "%Y/%m/%d %H:%M:%S"))
                + "月分\n"
                + payer.getname(1)
                + "："
                + str(agr_money[0])
                + "\n"
                + payer.getname(2)
                + "："
                + str(agr_money[1])
            )
            StorePayer.pname_id = None
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=content))
        case _:
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text="ちょっと何言ってるか分からない。"),
                    StickerSendMessage(package_id=1, sticker_id=113),
                ],
            )

    # DBの切断
    conn.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
