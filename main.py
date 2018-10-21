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
from datetime import datetime

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
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
    user = "vndjandgjvbilb"
    pwd = "baa627f8fad9e103962d75b6b282cbac9fa9898188f5f4560fd2fbe138b28859"
    server = "ec2-107-22-189-136.compute-1.amazonaws.com"
    port = "5432"
    db = "dbrp0st7k5ml0l"        
    con = psycopg2.connect("host=" + server + " port=" + port + " dbname=" + db + " user=" + user + " password=" + pwd)
    return psycopg2.connect(con)

# 支払額登録関数
def inst_wallet(usr, money, nowtime, cur):

    sql ="BEGIN;insert into wallet (opstime,payer,money) values ('"+nowtime+"','"+usr+"',"+money+");COMMIT;"
    cur.execute(sql)


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):

    """
    user = "vndjandgjvbilb"
    pwd = "baa627f8fad9e103962d75b6b282cbac9fa9898188f5f4560fd2fbe138b28859"
    server = "ec2-107-22-189-136.compute-1.amazonaws.com"
    port = "5432"
    db = "dbrp0st7k5ml0l"        
    con = psycopg2.connect("host=" + server + " port=" + port + " dbname=" + db + " user=" + user + " password=" + pwd)
    """
    # DBコネクション作成
    conn = get_connection()
    # DBカーソル作成
    cur = conn.cursor()

    # 受信メッセージを分割
    umsg = event.message.text.split()

    # 支払金額のDB登録
    if '登録' in umsg[0]:

        usr = umsg[1].replace('こーじ', 'koji').replace('こー', 'koji').replace('まり', 'mari').replace('まー', 'mari')
        money = umsg[2]
        nowtime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        
        # 支払金額登録
        inst_wallet(usr,money,nowtime,cur)
        
        content = "金額の登録が完了したよ！"      
 

    elif '集計' in event.message.text:
        aaa = event.message.text.split()
        bbb = aaa[1].replace('月', '')
        
        bun = ""
        
        # 指定した月の集計を取得
        sql1 ="select sum(money)::integer from wallet where date_part('month',opstime) = "+ bbb + " and payer = 'koji';"
        cur.execute(sql1)
        r1 = cur.fetchone()
    
        bun = str(aaa[1]) + " 集計だお！\n\nこーじろー：" + str(r1[0]) + "\nまーじろー："
        
        sql2 ="select sum(money)::integer from wallet where date_part('month',opstime) = "+ bbb + " and payer = 'mari';"
        cur.execute(sql2)
        r2 = cur.fetchone()
        
        bun = bun + str(r2[0])
        
        if r1 > r2:
            bun = bun + "\n\nこーじろーの方がよーはろとる！"
        elif r1 < r2:
            bun = bun + "\n\nまーじろーの方がよーはろとる！"
        else:
            bun = bun + "\n\n仲良く同じ額やで！"
        
        content = bun
        
    elif 'まー' in event.message.text:
        content = "きんたまさぶろー"
    else:
        content = '？？？？規定にしたがって下さいよ！まったく！！'
    
    # DB切断
    cur.close()
    conn.close()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=content)
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
