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
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import ( # 使用するモデル(イベント, メッセージ, アクションなど)を列挙
    FollowEvent, UnfollowEvent, MessageEvent, PostbackEvent,
    TextMessage, TextSendMessage, TemplateSendMessage,
    ButtonsTemplate, CarouselTemplate, CarouselColumn,
    PostbackTemplateAction, StickerSendMessage,
    MessageAction, ConfirmTemplate, PostbackAction
)

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
    con = psycopg2.connect("host=" + server + " port=" + port + " dbname=" + db + " user=" + user + " password=" + pwd)
    return con

# 支払額登録関数
def inst_wallet(umsg, nowtime, conn):
    # カーソル作成
    cur = conn.cursor()
    # 登録名に置き換え
    usr = umsg[1].replace('こーじ', 'koji').replace('こー', 'koji').replace('まり', 'mari').replace('まー', 'mari')
    # 金額合計
    total = 0
    for n in umsg[2:len(umsg)]:
        total = total + int(n)
    # 登録処理実行
    cur.execute("BEGIN;insert into wallet (opstime,payer,money) values ('"+nowtime+"','"+usr+"',"+str(total)+");COMMIT;")
    now_month = '{0:%m}'.format(datetime.datetime.strptime(nowtime, '%Y/%m/%d %H:%M:%S'))
    # 集計関数呼び出し
    agr_money = agr_wallet(now_month+"月", conn)
    # カーソル切断
    cur.close()
    # 金額を返す
    return agr_money

# 集計関数
def agr_wallet(umsg, conn):
    # カーソル作成
    cur = conn.cursor()
    # 月を削除
    month = umsg.replace('月', '')
    # 集計処理実行
    cur.execute("select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "+ month + " and payer = 'koji';")
    r1 = cur.fetchone()    
    cur.execute("select coalesce(sum(money),0)::integer from wallet where date_part('month',opstime) = "+ month + " and payer = 'mari';")
    r2 = cur.fetchone()
    # カーソル切断
    cur.close()
    # 金額、差額を返す
    return r1[0], r2[0], 10000-r1[0], 10000-r2[0]

@handler.add(MessageEvent, message=TextMessage)
def message_text(event):

    # DBコネクション作成
    conn = get_connection()
    # 受信メッセージを分割
    umsg = event.message.text.split()

    if len(umsg) > 1:

        # 支払金額のDB登録＋集計処理
        if '登録' in umsg[0]:
            # 時間取得
            nowtime = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            # 支払金額登録処理+集計処理実行
            agr_money = inst_wallet(umsg,nowtime,conn)
            content = "金額の登録が完了したよ！\n\n【現在までの集計】\n"+'{0:%m}'.format(datetime.datetime.strptime(nowtime, '%Y/%m/%d %H:%M:%S'))+"月分\nこー：" + str(agr_money[0]) + " (差額：" + str(agr_money[2]) + ")\nまー：" + str(agr_money[1])+ " (差額：" + str(agr_money[3]) + ")"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
        # 集計処理
        elif '集計' in umsg[0]:
            # 集計処理実行
            agr_money = agr_wallet(umsg[1], conn)
            # メッセージ作成
            content = str(umsg[1]) + "分 集計しました！\n\nこー：" + str(agr_money[0]) + " (差額：" + str(agr_money[2]) + ")\nまー：" + str(agr_money[1])+ " (差額：" + str(agr_money[3]) + ")"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
        else:
            content = 'ちょっと何言ってるか分からない。'

            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(text=content),
                StickerSendMessage(package_id=1, sticker_id=113)]
            )

    elif len(umsg) == 1:

        # 集計処理
        if '集計' in umsg[0]:
            # 月取得
            #sengetu = datetime.date.today() - relativedelta(months=1)
            now_month = str((datetime.date.today()).month)+"月"
            now_month2 = str(datetime.date.today() - relativedelta(months=1))+"月"
            #now_month3 = str((datetime.date.today()-datetime.timedelta(days=28)).month)+"月"
            confirm_template_message = TemplateSendMessage(
                alt_text='月別集計',
                template=ConfirmTemplate(
                    text='何月の集計ですか？',
                    actions=[
                        MessageAction(
                            label=now_month2,
                            text=now_month2
                        ),                    
                        MessageAction(
                            label=now_month,
                            text=now_month
                        )
                    ]
                )
            )

            line_bot_api.reply_message(
                    event.reply_token,
                    confirm_template_message
            )
        elif '月' in umsg[0]:
            # 集計処理実行
            agr_money = agr_wallet(umsg[0], conn)
            # メッセージ作成
            content = str(umsg[0]) + "分 集計しました！\n\nこー：" + str(agr_money[0]) + " (差額：" + str(agr_money[2]) + ")\nまー：" + str(agr_money[1])+ " (差額：" + str(agr_money[3]) + ")"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
        elif '起動' in umsg[0]:
            content = '生きてます！'
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
        else:
            content = 'ちょっと何言ってるか分からない。'
            
            line_bot_api.reply_message(
                event.reply_token,
                [TextSendMessage(text=content),
                StickerSendMessage(package_id=1, sticker_id=113)]
            )

    # DB切断
    conn.close()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
