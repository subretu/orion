import datetime
from typing import List, Tuple


class TransactionService:
    def __init__(self, conn, umsg):
        self.conn = conn
        self.umsg = umsg
        self.now_year = str(datetime.datetime.now().year)
        self.now_month = str(datetime.datetime.now().month)
        self.now_timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    @staticmethod
    def _parse_year_month(parts: List[str]) -> Tuple[int, int]:
        year = int(parts[0].replace("年", ""))
        month = int(parts[1].replace("月", ""))
        return year, month

    def aggregate_money(self, parts: List[str]) -> int:
        with self.conn.cursor() as cursor:
            # 年、月を削除
            year, month = self._parse_year_month(parts)

            # 集計処理実行
            sql = f"""
                    select
                        coalesce(sum(amount),0)::integer as total_amount
                    from
                        transactions
                    where
                        date_part('year', occurred_at) = {year}
                        and
                        date_part('month', occurred_at)  = {month}
                    ;
            """
            cursor.execute(sql)
            result = cursor.fetchone()
        return result[0] if result is not None else 0

    def register_payment(self, tokens: List[str]) -> Tuple[int, int]:
        total = sum(int(t) for t in tokens if t.isnumeric())
        now = datetime.datetime.now()
        with self.conn.cursor() as cursor:
            sql = f"""
                begin;
                insert into transactions (occurred_at, amount) values ('{self.now_timestamp}', {total});
                commit;
            """
            cursor.execute(sql)

        with self.conn.cursor() as cursor:
            sql = f"""
                    select
                        coalesce(sum(amount),0)::integer as total_amount
                    from
                        transactions
                    where
                        date_part('year', occurred_at) = {self.now_year}
                        and
                        date_part('month', occurred_at)  = {self.now_month}
                    ;
            """
            cursor.execute(sql)
            result = cursor.fetchone()

        return now.month, (result[0] if result is not None else 0)
