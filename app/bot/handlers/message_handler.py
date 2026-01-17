import os
import datetime
from dateutil.relativedelta import relativedelta
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    TemplateSendMessage,
    StickerSendMessage,
    MessageAction,
    ConfirmTemplate,
)
from app.utils.database import get_connection
from app.services import backup
from app.bot.line_bot import line_bot_api, handler
from app.services.transaction_service import TransactionService


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    # DBコネクション作成
    conn = get_connection()

    try:
        # 受信メッセージを分割
        umsg = event.message.text.split()

        match umsg[0]:
            case "集計":
                last_month = (
                    str((datetime.date.today() - relativedelta(months=1)).month) + "月"
                )
                this_month = str((datetime.date.today()).month) + "月"
                last_year_month = f"{(datetime.date.today() - relativedelta(months=1)).year}年 {last_month}"
                this_year_month = f"{(datetime.datetime.now()).year}年 {this_month}"

                confirm_template_message = TemplateSendMessage(
                    alt_text="何月の集計ですか？",
                    template=ConfirmTemplate(
                        text="何月の集計ですか？",
                        actions=[
                            MessageAction(
                                label=last_month,
                                text=last_year_month,
                            ),
                            MessageAction(
                                label=this_month,
                                text=this_year_month,
                            ),
                        ],
                    ),
                )
                line_bot_api.reply_message(event.reply_token, confirm_template_message)
            case x if "年" in x:
                # 集計処理実行
                ts = TransactionService(conn)

                agr_money = ts.get_monthly_total(umsg[0:2])
                msg_month = str(umsg[0]) + " " + str(umsg[1])

                # メッセージ作成
                content = "\n".join(
                    [msg_month + "分 集計しました！", "合計：" + str(agr_money)]
                )

                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=content)
                )
            case "登録":
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="支払額はいくらですか？")
                )
            case x if x.isnumeric():
                # 支払金額登録処理実行
                ts = TransactionService(conn)

                user_id = event.source.user_id

                result = ts.register_payment(user_id, umsg)
                # メッセージ作成
                content = (
                    "金額の登録が完了しました！\n\n【現在までの集計】\n"
                    + str(result[0])
                    + "月分："
                    + str(result[1])
                )

                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=content)
                )
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

                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=message)
                )
            case _:
                line_bot_api.reply_message(
                    event.reply_token,
                    [
                        TextSendMessage(text="ちょっと何言ってるか分からない。"),
                        StickerSendMessage(package_id=1, sticker_id=113),
                    ],
                )
    finally:
        conn.close()
