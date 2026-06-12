import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

RELATIONSHIPS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("order_payments", "order_id", "orders", "order_id"),
    ("order_reviews", "order_id", "orders", "order_id"),
    (
        "products",
        "product_category_name",
        "product_category_name_translation",
        "product_category_name",
    ),
    (
        "customers",
        "customer_zip_code_prefix",
        "geolocation",
        "geolocation_zip_code_prefix",
    ),
    (
        "sellers",
        "seller_zip_code_prefix",
        "geolocation",
        "geolocation_zip_code_prefix",
    ),
]


def get_relationship_context(tables: list[str]) -> str:
    selected_tables = set(tables)
    matching_relationships = []

    for left_table, left_col, right_table, right_col in RELATIONSHIPS:
        if left_table in selected_tables and right_table in selected_tables:
            matching_relationships.append(
                f"- {left_table}.{left_col} = {right_table}.{right_col}"
            )

    if not matching_relationships:
        return ""

    return (
        "--- DATABASE RELATIONSHIPS ---\n"
        "Use these join relationships when joining the selected tables:\n\n"
        + "\n".join(matching_relationships)
        + "\n\n"
    )


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

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (tables,))
            rows = cursor.fetchall()

    TYPE_MAP = {
        "character varying": "VARCHAR",
        "double precision": "FLOAT",
        "timestamp without time zone": "TIMESTAMP",
        "integer": "INT",
        "bigint": "BIGINT",
        "boolean": "BOOL",
        "text": "TEXT",
    }

    schema = {}
    for table, column, dtype in rows:
        mapped_type = TYPE_MAP.get(dtype, dtype)
        schema.setdefault(table, []).append({
            "column": column,
            "type": mapped_type
        })

    SCHEMA_CONTEXT = """You are an expert PostgreSQL assistant for an ecommerce analytics database.

Given a natural language question, generate one valid PostgreSQL query that answers it.

Use only the tables and columns listed in the schema below. Do not invent tables, columns, or values.

--- SCHEMA ---

"""

    for table_name, columns in schema.items():
        SCHEMA_CONTEXT += f"TABLE {table_name} (\n"
        for col in columns:
            SCHEMA_CONTEXT += f"    {col['column']} {col['type']}\n"
        SCHEMA_CONTEXT += ")\n\n"

    SCHEMA_CONTEXT += get_relationship_context(list(schema.keys()))

    SCHEMA_CONTEXT += """--- BUSINESS NOTES ---
- A successfully delivered order usually means orders.order_status = 'delivered'
- Revenue is usually calculated from order_items.price, or order_payments.payment_value if the question is about payments
- Product category names in products.product_category_name are in Portuguese
- Use product_category_name_translation.product_category_name_english when the user asks for category names in English
- Review ratings are stored in order_reviews.review_score
- Customer location is stored in customers.customer_city and customers.customer_state
- Seller location is stored in sellers.seller_city and sellers.seller_state
- Order purchase time is stored in orders.order_purchase_timestamp
- Delivery completion time is stored in orders.order_delivered_customer_date

--- SQL RULES ---
- Return only the SQL query
- Do not include explanations, markdown, comments, or backticks
- Generate exactly one SQL statement
- Generate only a read-only SELECT query
- WITH common table expressions are allowed only if the final statement is a SELECT
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, GRANT, or REVOKE
- Always use explicit JOIN ... ON syntax
- Never use implicit comma joins
- Qualify column names with table names or aliases when more than one table is used
- Use clear table aliases for multi-table queries
- Add LIMIT 100 for detail/listing queries
- Do not add LIMIT for aggregate queries that return one small summary result
- Use COUNT(*) for counting rows unless a specific column needs distinct counting
- Use COUNT(DISTINCT column) when the question asks for unique entities
- Use ORDER BY when asking for top, highest, lowest, most, least, best, or worst
"""
    print(SCHEMA_CONTEXT)
    return SCHEMA_CONTEXT
