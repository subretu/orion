import datetime


# 財布クラス
class Wallet:
    def __init__(self, set_umsg, set_conn):
        self.umsg = set_umsg
        self.conn = set_conn
        self.now_year = str(datetime.datetime.now().year)
        self.now_month = str(datetime.datetime.now().month)
        self.now_timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def aggregate_money_after_insert(self):
        # カーソル作成
        cur = self.conn.cursor()
        # 集計処理実行
        sql = f"""
                select
                    coalesce(sum(money),0)::integer as total_money
                from
                    wallet
                where
                    date_part('year', opstime) = {self.now_year}
                    and
                    date_part('month', opstime)  = {self.now_month}
                group by
                    date_part('month', opstime),date_part('year', opstime)
                ;
        """
        cur.execute(sql)
        result = cur.fetchone()

        # カーソル切断
        cur.close()

        return result[0]

    def aggregate_money(self):
        # カーソル作成
        cur = self.conn.cursor()
        # 年、月を削除
        month = self.umsg[1].replace("月", "")
        year = self.umsg[0].replace("年", "")
        # 集計処理実行
        sql = f"""
                select
                    coalesce(sum(money),0)::integer as total_money
                from
                    wallet
                where
                    date_part('year', opstime) = {year}
                    and
                    date_part('month', opstime)  = {month}
                group by
                    date_part('month', opstime),date_part('year', opstime)
                ;
        """
        cur.execute(sql)
        result = cur.fetchone()

        # カーソル切断
        cur.close()

        return result[0]

    # 支払額登録関数
    def insert_wallet(self, msg, user_id):
        # カーソル作成
        cur = self.conn.cursor()
        # 金額合計
        total = 0
        for n in msg[0 : len(msg)]:
            total = total + int(n)
        # 登録処理実行
        cur.execute(
            "begin;insert into wallet (opstime, money) values ('"
            + self.now_timestamp
            + ","
            + str(total)
            + ");commit;"
        )
        # 集計関数呼び出し
        agr_money = self.aggregate_money_after_insert()
        # カーソル切断
        cur.close()
        # 金額を返す
        return self.now_month, agr_money
