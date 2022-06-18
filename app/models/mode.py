def update_mode(conn, mode):
    cur = conn.cursor()

    sql = f"""
    BEGIN;
    update orion_mode set mode = {mode};
    COMMIT;
    """
    cur.execute(sql)

    cur.close()


def get_mode(conn):
    cur = conn.cursor()

    sql = """
    select mode from orion_mode
    ;
    """
    cur.execute(sql)

    result = cur.fetchone()

    cur.close()

    return result
