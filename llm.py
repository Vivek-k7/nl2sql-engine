import requests
from schema import get_schema_context

ALL_TABLES = [
    "customers", "sellers", "products", "product_category_name_translation",
    "orders", "order_items", "order_payments", "order_reviews", "geolocation"
]

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:latest"

def generate_sql(user_question: str, error_history: list = []) -> str:
    SCHEMA_CONTEXT = get_schema_context(ALL_TABLES)
    error_context = ""
    
    if error_history:
        error_context = "\n\n--- PREVIOUS FAILED ATTEMPTS ---\n"
        for i, entry in enumerate(error_history):
            error_context += f"\nAttempt {i + 1}:\nSQL: {entry['sql']}\nError: {entry['error']}\n"
        error_context += "\nFix the errors above and generate a corrected SQL query."
    
    prompt = f"{SCHEMA_CONTEXT}{error_context}\n\nQuestion: {user_question}\n\nSQL:"
    
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })
    
    response.raise_for_status()
    return response.json()["response"].strip()


if __name__ == "__main__":
    question = "How many orders were delivered successfully?"
    print(f"Question: {question}")
    print(f"Generated SQL:\n")
    sql = generate_sql(question)
    print(sql)