from langchain_ollama import ChatOllama
import os
from dotenv import load_dotenv
load_dotenv()

MODEL = os.getenv("MODEL")
llm = ChatOllama(
        model=MODEL,
    )

SYSTEM_PROMPT = """
You are a database routing assistant. Given a natural language question, return only the names of the tables needed to answer it.

Available tables:
- customers: customer personal and location info
- orders: core order records and status
- order_items: individual products within each order
- order_payments: payment details per order
- order_reviews: customer review scores and comments
- products: product catalog and dimensions
- sellers: seller info and location
- geolocation: zip code to lat/lng mapping
- product_category_name_translation: Portuguese to English category names

Rules:
- Return only a comma-separated list of table names, nothing else
- No explanation, no punctuation other than commas
- Only return tables that are strictly necessary to answer the question

"""

def intent_detector(query: str) -> list:

    prompt = SYSTEM_PROMPT + f"\nQuery: {query}"

    response = llm.invoke(prompt)
    
    tables = response.content.strip().split(",")
    tables = [t.strip() for t in tables]
    return tables
