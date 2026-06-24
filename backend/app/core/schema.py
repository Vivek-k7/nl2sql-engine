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
        "zip_location",
        "zip_code_prefix",
    ),
    (
        "sellers",
        "seller_zip_code_prefix",
        "zip_location",
        "zip_code_prefix",
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

    TABLE_GRAINS = {
        "customers": (
            "one row per customer_id; customer_unique_id identifies the "
            "same real customer across multiple customer records"
        ),
        "orders": "one row per order_id",
        "order_items": (
            "one row per item position in an order, identified by "
            "(order_id, order_item_id)"
        ),
        "order_payments": (
            "one row per payment transaction or payment sequence for an order"
        ),
        "order_reviews": "one row per review record, identified by review_id",
        "products": "one row per product_id",
        "sellers": "one row per seller_id",
        "product_category_name_translation": (
            "one row per Portuguese product category name"
        ),
        "zip_location": "one row per zip_code_prefix",
    }

    SCHEMA_CONTEXT += "--- TABLE GRAINS ---\n"
    SCHEMA_CONTEXT += (
        "Use table grain to determine what each row represents and how "
        "entities should be counted:\n\n"
    )
    for table_name in schema:
        if table_name in TABLE_GRAINS:
            SCHEMA_CONTEXT += f"- {table_name}: {TABLE_GRAINS[table_name]}\n"
    SCHEMA_CONTEXT += "\n"

    BUSINESS_NOTES = {
        "customers": (
            "customer_unique_id is the real customer identity; customer "
            "location uses customer_city and customer_state"
        ),
        "orders": (
            "delivered orders have order_status = 'delivered'; purchase and "
            "delivery times are stored in the order timestamp columns"
        ),
        "order_items": "item-price revenue uses price; shipping cost uses freight_value",
        "order_payments": "payment spending uses payment_value",
        "order_reviews": "review ratings use review_score",
        "products": "product_category_name is in Portuguese",
        "sellers": "seller location uses seller_city and seller_state",
        "product_category_name_translation": (
            "English category names use product_category_name_english"
        ),
    }

    selected_notes = [
        f"- {BUSINESS_NOTES[table_name]}"
        for table_name in schema
        if table_name in BUSINESS_NOTES
    ]
    if selected_notes:
        SCHEMA_CONTEXT += "--- RELEVANT BUSINESS NOTES ---\n"
        SCHEMA_CONTEXT += "\n".join(selected_notes) + "\n\n"

    SCHEMA_CONTEXT += """--- QUERY PLANNING ---
Reason internally before writing SQL:
1. Dimensions: entity, category, location, or time values requested in the result.
2. Measures: counts, sums, averages, minima, or maxima requested or used for ranking.
3. Filters: conditions stated in the question.
4. Ranking: the measure, direction, and requested number of rows.

--- SQL RULES ---
- Return exactly one read-only PostgreSQL SELECT query and no other text.
- Use only listed tables, columns, and DATABASE RELATIONSHIPS; never invent a join.
- Put every requested dimension in SELECT and, for aggregate queries, GROUP BY.
- Put every requested measure in SELECT, including the aggregate used to rank groups.
- Count at the requested entity's TABLE GRAIN. Use COUNT(*) when one row equals one entity; use COUNT(DISTINCT key) only for unique entities or join duplication.
- Use the business identity described in TABLE GRAINS when the question asks for a unique real-world entity.
- Use ORDER BY on the ranking measure. Singular highest/lowest/most/least/best/worst means LIMIT 1; top/bottom N means LIMIT N.
- Use explicit JOIN ... ON clauses and clear, non-keyword aliases.
- Add LIMIT 100 only to unbounded detail listings, never to aggregate or ranked queries.
"""
    return SCHEMA_CONTEXT
