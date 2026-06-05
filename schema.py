import psycopg2
import json
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

def get_schema_context(tables: list[str]) -> str:
    sql = """
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = ANY(%s)
        AND table_schema = 'public'
        ORDER BY table_name, ordinal_position;
        """

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(sql, (tables,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    schema = {}
    for table, column, dtype in rows:
        schema.setdefault(table, []).append({
            "column": column,
            "type": dtype
        })

    SCHEMA_CONTEXT = """You are an expert SQL assistant. Given a natural language question, generate a valid PostgreSQL query.

Use only the tables and columns defined below. Do not hallucinate columns or tables.

--- SCHEMA ---

"""

    for table_name, columns in schema.items():
        SCHEMA_CONTEXT += f"TABLE {table_name} (\n"
        for col in columns:
            SCHEMA_CONTEXT += f"    {col['column']} {col['type']}\n"
        SCHEMA_CONTEXT += ")\n\n"

    SCHEMA_CONTEXT += """--- RULES ---
- Always use explicit JOIN ... ON syntax, never implicit joins
- Always qualify column names with table names when joining
- Return only the SQL query, no explanation, no markdown, no backticks
"""

    return SCHEMA_CONTEXT