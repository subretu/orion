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
    StickerSendMessage,
    MessageAction,
    ConfirmTemplate,
)
from app.utils.database import get_connection
from app.models.wallet import Wallet
from app.models import backup


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


@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(PostbackEvent)
def on_postback(event):
    postback_data = event.postback.data.split(":")
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text=postback_data[0] + "の支払額はいくらですか？")
    )


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    # DBコネクション作成
    conn = get_connection()
    # 受信メッセージを分割
    umsg = event.message.text.split()

    wallet = Wallet(umsg, conn)

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
                        ),
                    ],
                ),
            )
            line_bot_api.reply_message(event.reply_token, confirm_template_message)
        case x if "年" in x:
            # 集計処理実行
            agr_money = wallet.aggregate_money()
            msg_month = str(umsg[0]) + " " + str(umsg[1])

            # メッセージ作成
            content = "\n".join([msg_month + "分 集計しました！", "合計：" + str(agr_money)])

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=content))
        case "登録":
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="支払額はいくらですか？")
            )
        case x if (x.isnumeric()):
            # 支払金額登録処理実行
            result = wallet.insert_wallet(umsg)
            # メッセージ作成
            content = (
                "金額の登録が完了しました！\n\n【現在までの集計】\n" + str(result[0]) + "月分：" + str(result[1])
            )

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=content))
        case "バックアップ":
            notion_api_url = os.getenv("NOTION_API_URL", None)
            notion_api_key = os.getenv("NOTION_API_KEY", None)
            notion_database_id = os.getenv("NOTION_DATABASE_ID", None)

            if backup.backup_to_notion(
                notion_api_url, notion_api_key, notion_database_id, conn
            ):
                message = " バックアップが成功しました。"
            else:
                message = " バックアップが失敗しました。"

            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message))
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
