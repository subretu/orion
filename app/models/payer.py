# 支払者クラス
class StorePayer:
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
