import requests


def backup_to_notion(notion_api_url, notion_api_key, notion_database_id, conn):
    headers = {
        "accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Authorization": f"Bearer {notion_api_key}",
    }

    total_amount_text = calculate_total_amount(conn)

    json_data = {
        "parent": {
            "type": "database_id",
            "database_id": notion_database_id,
        },
        "properties": {
            "title": {"title": [{"text": {"content": "バックアップ"}}]},
        },
        "children": [
            {
                "object": "block",
                "paragraph": {"rich_text": [{"text": {"content": total_amount_text}}]},
            },
        ],
    }

    response = requests.post(notion_api_url, json=json_data, headers=headers)

    return response.status_code == 200


def calculate_total_amount(conn):
    total_amount_text = ""

    with conn:
        with conn.cursor() as cursor:
            sql = """
            select
                to_char(opstime, 'yyyy-mm') as year_month
                ,sum(money) as total_amount
            from
                wallet
            group by
                year_month
            order by
                year_month
            ;
            """
            cursor.execute(sql)
            result = cursor.fetchall()

        for data in result:
            total_amount_text = "\n".join(f"{data[0]} {data[1]}" for data in result)

    conn.close()

    return total_amount_text
