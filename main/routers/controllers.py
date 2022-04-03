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
import uvicorn
from fastapi import FastAPI, Request, HTTPException
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
from main.db import get_connection
from fastapi import APIRouter

router = APIRouter()

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


@router.post("/callback")
async def callback(request: Request):
    signature = request.headers['X-Line-Signature']

    body = await request.body()

    handler.handle(body.decode("utf-8"), signature)

    # handle webhook body
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="chatbot handle body error.")

    # LINEサーバへHTTP応答を返す
    return "ok"


# 支払額登録関数
def insert_wallet(umsg, nowtime, user_id, conn, agr_wal):
    # カーソル作成
    cur = conn.cursor()
    # 金額合計
    total = 0
    for n in umsg[0: len(umsg)]:
        total = total + int(n)
    # 登録処理実行
    cur.execute(
        "BEGIN;insert into wallet (opstime,payer_id,money) values ('"
        + nowtime
        + "',"
        + str(user_id)
        + ","
        + str(total)
        + ");COMMIT;"
    )
    # 集計関数呼び出し
    agr_money = agr_wal.no_assign_year_insert()
    # カーソル切断
    cur.close()
    # 金額を返す
    return agr_money


# 集計クラス
class AggregateWallet:
    def __init__(self, set_umsg, set_conn):
        self.umsg = set_umsg
        self.conn = set_conn
        self.now_year = str(datetime.datetime.now().year)
        self.now_month = str(datetime.datetime.now().month)

    def no_assign_year_insert(self):
        # カーソル作成
        cur = self.conn.cursor()
        # 集計処理実行
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + self.now_month
            + " and date_part('year',opstime) = "
            + self.now_year
            + " and payer_id = 1;"
        )
        r1 = cur.fetchone()
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + self.now_month
            + " and date_part('year',opstime) = "
            + self.now_year
            + " and payer_id = 2;"
        )
        r2 = cur.fetchone()
        # カーソル切断
        cur.close()
        # 金額、差額を返す
        return r1[0], r2[0], 10000 - r1[0], 10000 - r2[0]

    def no_assign_year(self):
        # カーソル作成
        cur = self.conn.cursor()
        # 年、月を削除
        month = self.umsg[1].replace("月", "")
        year = self.umsg[0].replace("年", "")
        # 集計処理実行
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month
            + " and date_part('year',opstime) = "
            + year
            + " and payer_id = 1;"
        )
        r1 = cur.fetchone()
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month
            + " and date_part('year',opstime) = "
            + year
            + " and payer_id = 2;"
        )
        r2 = cur.fetchone()
        # カーソル切断
        cur.close()
        # 金額、差額を返す
        return r1[0], r2[0], 10000 - r1[0], 10000 - r2[0]

    def assign_year(self):
        # カーソル作成
        cur = self.conn.cursor()
        # 年、月を削除
        month = self.umsg[2].replace("月", "")
        year = self.umsg[1].replace("年", "")
        # 集計処理実行
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month
            + " and date_part('year',opstime) = "
            + year
            + " and payer_id = 1;"
        )
        r1 = cur.fetchone()
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month
            + " and date_part('year',opstime) = "
            + year
            + " and payer_id = 2;"
        )
        r2 = cur.fetchone()
        # カーソル切断
        cur.close()
        # 金額、差額を返す
        return r1[0], r2[0], 10000 - r1[0], 10000 - r2[0]


# 支払者クラス
class StorePayer:
    # クラス変数にて支払者IDを保存
    pname_id = None

    def __init__(self, set_conn):
        self.conn = set_conn

    def getname(self, user_id):
        # カーソル作成
        cur = self.conn.cursor()
        cur.execute("select name from payer where id = " + str(user_id) + ";")
        r1 = cur.fetchone()
        # カーソル切断
        cur.close()
        return r1[0]


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

    # 集計処理
    if "集計" in umsg[0]:
        # 月取得
        now_month = str((datetime.date.today()).month) + "月"
        now_year = str((datetime.datetime.now()).year) + "年"
        now_month2 = (
            str((datetime.date.today() - relativedelta(months=1)).month) + "月"
        )
        now_year2 = (
            str((datetime.date.today() - relativedelta(months=1)).year) + "年"
        )
        confirm_template_message = TemplateSendMessage(
            alt_text="何月の集計ですか？",
            template=ConfirmTemplate(
                text="何月の集計ですか？",
                actions=[
                    MessageAction(
                        label=now_month2, text=now_year2 + " " + now_month2
                    ),
                    MessageAction(label=now_month, text=now_year + " " + now_month),
                ],
            ),
        )

        line_bot_api.reply_message(event.reply_token, confirm_template_message)
    elif "年" in umsg[0]:
        # 集計クラスのインスタンス作成
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
            + " (差額："
            + str(agr_money[2])
            + ")\n"
            + payer.getname(2)
            + "："
            + str(agr_money[1])
            + " (差額："
            + str(agr_money[3])
            + ")"
        )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=content))

    elif (umsg[0].isnumeric()) and (StorePayer.pname_id is not None):
        # 時間取得
        nowtime = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        # 集計クラスのインスタンス作成
        agr_wal = AggregateWallet(umsg[0], conn)
        # 支払金額登録処理+集計処理実行
        agr_money = insert_wallet(umsg, nowtime, StorePayer.pname_id, conn, agr_wal)
        content = (
            "金額の登録が完了したよ！\n\n【現在までの集計】\n"
            + "{0:%m}".format(
                datetime.datetime.strptime(nowtime, "%Y/%m/%d %H:%M:%S")
            )
            + "月分\n"
            + payer.getname(1)
            + "："
            + str(agr_money[0])
            + " (差額："
            + str(agr_money[2])
            + ")\n"
            + payer.getname(2)
            + "："
            + str(agr_money[1])
            + " (差額："
            + str(agr_money[3])
            + ")"
        )
        StorePayer.pname_id = None
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=content))

    elif "起動" in umsg[0]:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="生きてます！")
        )

    elif "登録" in umsg[0]:
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

    else:
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text="ちょっと何言ってるか分からない。"),
                StickerSendMessage(package_id=1, sticker_id=113),
            ],
        )

    # DBの切断
    conn.close()
