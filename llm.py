from langchain_ollama import ChatOllama
import os
from dotenv import load_dotenv
load_dotenv()

MODEL = os.getenv("MODEL")
llm = ChatOllama(
        model=MODEL,
    )

def generate_sql(user_question: str, schema_context: str, error_history: list = []) -> str:

    SCHEMA_CONTEXT = schema_context
    error_context = ""
    
    if error_history:
        error_context = "\n\n--- PREVIOUS FAILED ATTEMPTS ---\n"
        for i, entry in enumerate(error_history):
            error_context += f"\nAttempt {i + 1}:\nSQL: {entry['sql']}\nError: {entry['error']}\n"
        error_context += "\nFix the errors above and generate a corrected SQL query."
    
    prompt = f"{SCHEMA_CONTEXT}{error_context}\n\nQuestion: {user_question}\n\nSQL:"

    response = llm.invoke(prompt)
    
    return response.content


if __name__ == "__main__":
    question = "How many orders were delivered successfully?"
    print(f"Question: {question}")
    print(f"Generated SQL:\n")
    sql = generate_sql(question)
    print(sql)