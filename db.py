import psycopg2
import json
from decimal import Decimal
import os
from dotenv import load_dotenv
load_dotenv()

postgres_pass = os.getenv("POSTGRES_PASSWORD")

DB_CONFIG = {
    "host": "localhost",
    "database": "nl2sql_ecommerce",
    "user": "postgres",
    "password": postgres_pass
}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def execute_sql(sql: str):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        conn.close()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def result_to_json(result: dict) -> str:
    return json.dumps(result, indent=2, cls=DecimalEncoder)