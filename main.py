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


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):

    user = "vndjandgjvbilb"
    pwd = "baa627f8fad9e103962d75b6b282cbac9fa9898188f5f4560fd2fbe138b28859"
    server = "ec2-107-22-189-136.compute-1.amazonaws.com"
    port = "5432"
    db = "dbrp0st7k5ml0l"        
    con = psycopg2.connect("host=" + server + " port=" + port + " dbname=" + db + " user=" + user + " password=" + pwd)
    cursor = con.cursor()
    #cursor.execute("SELECT a1 FROM sample;")
    #results = cursor.fetchone()

    # メッセージを分割
    umsg = event.message.text.split()

    if 'あいさつ' in event.message.text:
        content = "jijijij"
    
    # 支払金額のDB登録
    elif '登録' in umsg[0]:

        name = umsg[1].replace('こー', 'koji').replace('こうじ', 'koji').replace('まー', 'mari').replace('まり', 'mari').replace('まーちゃん', 'mari')
        money = umsg[2]
        nowtime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        
        sql1 ="insert into wallet (opstime,payer,money) values ('"+nowtime+"','"+name+"',"+money+");"
        cursor.execute(sql1)

        content = "金額の登録が完了したよ！"      
 

    elif '集計' in event.message.text:
        aaa = event.message.text.split()
        bbb = aaa[1].replace('月', '')
        
        bun = ""
        
        # 指定した月の集計を取得
        sql1 ="select sum(money)::integer from wallet where date_part('month',opstime) = "+ bbb + " and payer = 'koji';"
        cursor.execute(sql1)
        r1 = cursor.fetchone()
    
        bun = str(aaa[1]) + " 集計だお！\n\nこーじろー：" + str(r1[0]) + "\nまーじろー："
        
        sql2 ="select sum(money)::integer from wallet where date_part('month',opstime) = "+ bbb + " and payer = 'mari';"
        cursor.execute(sql2)
        r2 = cursor.fetchone()
        
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
        # content = 'ごめんなさい、あまり喋れません'
        sss = event.message.text.split()
        content = sss[0]

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=content)
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
