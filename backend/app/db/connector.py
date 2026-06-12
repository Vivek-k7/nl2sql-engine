import json
import os
import re
from decimal import Decimal

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

MAX_ROWS = 100
STATEMENT_TIMEOUT_MS = 5000


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def clean_sql(sql: str) -> str:
    sql = sql.strip()

    if sql.startswith("```"):
        sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
        sql = re.sub(r"```$", "", sql).strip()

    return sql


def validate_sql(sql: str) -> tuple[bool, str]:
    if not sql:
        return False, "empty SQL"

    normalized = sql.strip().rstrip(";").strip()

    if ";" in normalized:
        return False, "multiple SQL statements are not allowed"

    first_word_match = re.match(r"^\s*(\w+)", normalized, flags=re.IGNORECASE)
    first_word = first_word_match.group(1).lower() if first_word_match else ""

    if first_word not in {"select", "with"}:
        return False, "only SELECT queries are allowed"

    return True, ""


def enforce_limit(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()

    if re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
        return sql

    return f"SELECT * FROM ({sql}) AS nl2sql_query LIMIT {MAX_ROWS}"


def execute_sql(sql: str):
    sql = clean_sql(sql)
    is_valid, reason = validate_sql(sql)

    if not is_valid:
        return {"success": False, "error": f"Unsafe SQL rejected: {reason}"}

    safe_sql = enforce_limit(sql)

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            conn.set_session(readonly=True)

            with conn.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = %s", (STATEMENT_TIMEOUT_MS,))
                cursor.execute(safe_sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in rows]

        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def result_to_json(result: dict) -> str:
    return json.dumps(result, indent=2, cls=DecimalEncoder)
