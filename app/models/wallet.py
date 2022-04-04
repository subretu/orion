import datetime


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


# 支払額登録関数
def insert_wallet(umsg, nowtime, user_id, conn, agr_wal):
    # カーソル作成
    cur = conn.cursor()
    # 金額合計
    total = 0
    for n in umsg[0 : len(umsg)]:
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
