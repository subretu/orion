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
import psycopg2
from argparse import ArgumentParser
import datetime
from dateutil.relativedelta import relativedelta
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (  # 使用するモデル(イベント, メッセージ, アクションなど)を列挙
    FollowEvent, UnfollowEvent, MessageEvent, PostbackEvent, TextMessage,
    TextSendMessage, TemplateSendMessage, ButtonsTemplate, CarouselTemplate,
    CarouselColumn, PostbackTemplateAction, StickerSendMessage, MessageAction,
    ConfirmTemplate, PostbackAction)

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
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


# DB接続用関数
def get_connection():
    user = os.getenv('POSTGRES_USER', None)
    pwd = os.getenv('POSTGRES_PASS', None)
    server = os.getenv('POSTGRES_HOST', None)
    port = "5432"
    db = os.getenv('POSTGRES_DB', None)
    con = psycopg2.connect("host=" + server + " port=" + port + " dbname=" +
                           db + " user=" + user + " password=" + pwd)
    return con

# 支払額登録関数
def insert_wallet(umsg, nowtime, usr, conn, agr_wal):
    # カーソル作成
    cur = conn.cursor()
    # 金額合計
    total = 0
    for n in umsg[0:len(umsg)]:
        total = total + int(n)
    # 登録処理実行
    cur.execute("BEGIN;insert into wallet (opstime,payer,money) values ('" +
                nowtime + "','" + usr + "'," + str(total) + ");COMMIT;")
    # 集計関数呼び出し
    agr_money = agr_wal.no_assign_year()
    # カーソル切断
    cur.close()
    # 金額を返す
    return agr_money

# 集計クラス
class Aggregate_wallet():

    def __init__(self, set_umsg, set_conn):
        self.umsg = set_umsg
        self.conn = set_conn

    def no_assign_year(self):
        # カーソル作成
        cur = self.conn.cursor()
        # 月を削除
        month = self.umsg.replace('月', '')
        # 集計処理実行
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month + " and payer = 'koji';")
        r1 = cur.fetchone()
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month + " and payer = 'mari';")
        r2 = cur.fetchone()
        # カーソル切断
        cur.close()
        # 金額、差額を返す
        return r1[0], r2[0], 10000 - r1[0], 10000 - r2[0]

    def assign_year(self):
        # カーソル作成
        cur = self.conn.cursor()
        # 年、月を削除
        month = self.umsg[2].replace('月', '')
        year = self.umsg[1].replace('年', '')
        # 集計処理実行
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month + " and date_part('year',opstime) = " + year + " and payer = 'koji';")
        r1 = cur.fetchone()
        cur.execute(
            "select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "
            + month + " and date_part('year',opstime) = " + year + " and payer = 'mari';")
        r2 = cur.fetchone()
        # カーソル切断
        cur.close()
        # 金額、差額を返す
        return r1[0], r2[0], 10000 - r1[0], 10000 - r2[0]


@handler.add(PostbackEvent)
def on_postback(event):
    postback_msg = event.postback.data

    if postback_msg == 'payer=1':
        StorePayer.pname = "koji"
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text='こうじさんの支払額はいくらですか？'))
    elif postback_msg == 'payer=2':
        StorePayer.pname = "mari"
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text='まりさんの支払額はいくらですか？'))


# 支払者名保存クラス
class StorePayer():
    pname = None


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):

    # DBコネクション作成
    conn = get_connection()
    # 受信メッセージを分割
    umsg = event.message.text.split()

    if len(umsg) > 1:

        # 集計クラスのインスタンス作成
        agr_wal = Aggregate_wallet(umsg, conn)

        # 集計処理
        if '集計' in umsg[0]:

            if len(umsg) == 2:
                # 集計処理実行
                agr_money = agr_wal.no_assign_year()
                msg_month = str(umsg[1])
            else:
                # 集計処理実行
                agr_money = agr_wal.assign_year()
                msg_month = str(umsg[1]) + " " + str(umsg[2])

            # メッセージ作成
            content = msg_month + "分 集計しました！\n\nこー：" + str(
                agr_money[0]) + " (差額：" + str(agr_money[2]) + ")\nまー：" + str(
                    agr_money[1]) + " (差額：" + str(agr_money[3]) + ")"

            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage(text=content))

        else:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text='ちょっと何言ってるか分からない。'),
                StickerSendMessage(package_id=1, sticker_id=113)
            ])

    elif len(umsg) == 1:

        # 集計処理
        if '集計' in umsg[0]:
            # 月取得
            now_month = str((datetime.date.today()).month) + "月"
            now_month2 = str(
                (datetime.date.today() - relativedelta(months=1)).month) + "月"
            confirm_template_message = TemplateSendMessage(
                alt_text='何月の集計ですか？',
                template=ConfirmTemplate(text='何月の集計ですか？',
                                         actions=[
                                             MessageAction(label=now_month2,
                                                           text=now_month2),
                                             MessageAction(label=now_month,
                                                           text=now_month)
                                         ]))

            line_bot_api.reply_message(event.reply_token,
                                       confirm_template_message)
        elif '月' in umsg[0]:
            # 集計クラスのインスタンス作成
            agr_wal = Aggregate_wallet(umsg[0], conn)
            # 集計処理実行
            agr_money = agr_wal.no_assign_year()
            # メッセージ作成
            content = str(umsg[0]) + "分 集計しました！\n\nこー：" + str(
                agr_money[0]) + " (差額：" + str(agr_money[2]) + ")\nまー：" + str(
                    agr_money[1]) + " (差額：" + str(agr_money[3]) + ")"

            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage(text=content))

        elif (umsg[0].isnumeric()) and (StorePayer.pname is not None):
            # 時間取得
            nowtime = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            # 集計クラスのインスタンス作成
            agr_wal = Aggregate_wallet(umsg[0], conn)
            # 支払金額登録処理+集計処理実行
            agr_money = insert_wallet(umsg, nowtime, StorePayer.pname, conn, agr_wal)
            content = "金額の登録が完了したよ！\n\n【現在までの集計】\n" + '{0:%m}'.format(
                datetime.datetime.strptime(nowtime, '%Y/%m/%d %H:%M:%S')
            ) + "月分\nこー：" + str(agr_money[0]) + " (差額：" + str(
                agr_money[2]) + ")\nまー：" + str(agr_money[1]) + " (差額：" + str(
                    agr_money[3]) + ")"
            StorePayer.pname = None
            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage(text=content))

        elif '起動' in umsg[0]:
            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage(text='生きてます！'))

        elif '登録' in umsg[0]:
            message_template = TemplateSendMessage(
                alt_text='支払者は誰ですか？',
                template=ConfirmTemplate(
                    text='支払者は誰ですか？',
                    actions=[
                        PostbackTemplateAction(label='こうじ', data='payer=1'),
                        PostbackTemplateAction(label='まり', data='payer=2')
                    ]))
            line_bot_api.reply_message(event.reply_token, message_template)

        else:
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text='ちょっと何言ってるか分からない。'),
                StickerSendMessage(package_id=1, sticker_id=113)
            ])

    # DBの切断
    conn.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
