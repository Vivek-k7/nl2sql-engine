from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

llm = ChatGroq(
    model=MODEL,
    temperature=0,
)

def get_relationships_from_db():
    """Query the database for actual foreign key relationships."""
    import psycopg2
    
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    
    query = """
    SELECT
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    """
    
    with conn.cursor() as cursor:
        cursor.execute(query)
        relationships = [(row[0], row[2]) for row in cursor.fetchall()]
    
    conn.close()
    return relationships

RELATIONSHIPS = get_relationships_from_db()

def build_relationship_graph():
    graph = {}
    all_tables = {t for pair in RELATIONSHIPS for t in pair}
    
    for table in all_tables:
        graph[table] = []
    
    for t1, t2 in RELATIONSHIPS:
        graph[t1].append(t2)
        graph[t2].append(t1)
    
    return graph

def find_bridge_tables(selected_tables: list[str]) -> set[str]:
    if len(selected_tables) <= 1:
        return set(selected_tables)
    
    graph = build_relationship_graph()
    
    explicitly_selected = set(selected_tables)

    def bfs_path(start, end):
        if start == end:
            return [start]
        
        queue = [(start, [start])]
        seen = {start}
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in graph.get(current, []):
                if (neighbor == "zip_location" and neighbor not in explicitly_selected):
                    continue

                if neighbor == end:
                    return path + [neighbor]
                
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []
    
    bridge_tables = set(selected_tables)
    
    for i, t1 in enumerate(selected_tables):
        for t2 in selected_tables[i+1:]:
            path = bfs_path(t1, t2)
            if path:
                bridge_tables.update(path)
    
    return bridge_tables

VALID_TABLES = {
    "customers", "orders", "order_items", "order_payments",
    "order_reviews", "products", "sellers",
    "product_category_name_translation", "zip_location"
}

def clean_table_list(raw_tables: list[str]) -> list[str]:
    """Filter out anything that isn't an exact match to a known table name."""
    cleaned = []
    for t in raw_tables:
        t = t.strip()
        if t in VALID_TABLES:
            cleaned.append(t)
    return cleaned

def intent_detector(query: str) -> list[str]:
    prompt = """You select the main information-bearing tables needed to answer an e-commerce analytics question.

Select a table only when it directly contains:
- a value that must be returned;
- a metric that must be calculated; or
- a field needed for filtering, grouping, or ordering.

Do not select a table merely because it connects other tables. Foreign-key bridge tables are discovered automatically after your selection.

Available tables:
- customers: customer identity, unique customer identity, city, state, and zip-code prefix
- orders: order status and purchase, approval, shipping, and delivery timestamps; select it when order-level status or dates are directly needed
- order_items: individual purchased items, item price, freight value, product, and seller; use it for item counts, products sold, item-price revenue, freight, or seller-product transactions
- order_payments: payment amount, payment type, and installments
- order_reviews: review score, comments, and review timestamps
- products: product category and physical product attributes
- sellers: seller identity, city, state, and zip-code prefix
- product_category_name_translation: English product-category names
- zip_location: city and state lookup by zip-code prefix; select it only for an explicit zip-based lookup or normalization

Selection boundaries:
- Select customers whenever customer identity or customer city/state is returned, grouped, filtered, or compared.
- Select sellers whenever seller identity or seller city/state is returned, grouped, filtered, or compared.
- Select order_reviews only when the question asks about reviews, ratings, scores, or review comments.
- Select products only when the question asks about a product, category, or product attribute.
- An English category requires both products and product_category_name_translation.
- Item counts, items sold, item price, freight, and item-price revenue require order_items.
- Spending based on payments, payment methods, or installments requires order_payments.
- Select orders directly only for order status or order timestamps; otherwise let the graph add it as a bridge.
- Select zip_location only when the question explicitly asks for a zip-code lookup or normalization.
- Before answering, verify that every selected table provides requested information and that every requested entity and metric has a selected table.

Question: {query}

Return only a comma-separated list of main table names. Do not explain your answer.

Tables:"""

    response = llm.invoke(prompt.format(query=query))
    raw_tables = response.content.strip().split(",")
    main_tables = clean_table_list(raw_tables)
    
    # The LLM chooses information-bearing endpoints; the FK graph supplies
    # every table needed to connect them.
    all_tables = list(find_bridge_tables(main_tables))
    
    return sorted(all_tables)

if __name__ == "__main__":
    test_questions = [
        "What is the most sold product category in English by number of order items?",
        "Find the seller state that generated the most item price revenue.",
        "List the top 3 unique customers who spent the most money overall.",
        "What is the English category name with the highest average review score, considering only categories with at least 10 reviews?",
        "Which customer city and state pair has the highest number of 1-star reviews?",
        "Find the total item price revenue generated when the seller and customer are in the same city and state.",
    ]
    
    for question in test_questions:
        tables = intent_detector(question)
        print(f"Q: {question}")
        print(f"Tables: {tables}\n")
