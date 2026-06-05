from llm import generate_sql
from db import execute_sql, result_to_json
import json

MAX_RETRIES = 5

def run(question: str):
    print(f"Question: {question}\n")
    
    error_history = []
    sql = generate_sql(question)
    
    for attempt in range(MAX_RETRIES):
        print(f"Attempt {attempt + 1}")
        print(f"Generated SQL:\n{sql}\n")
        
        result = execute_sql(sql)
        
        if result["success"]:
            print(f"\nResult:\n{result_to_json(result)}")
            return
        
        print(f"DB Error: {result['error']}\n")
        error_history.append({
            "sql": sql,
            "error": result["error"]
        })
        
        if attempt < MAX_RETRIES - 1:
            print("Retrying with error context...\n")
            sql = generate_sql(question, error_history)
    
    print("Max retries reached. Could not generate a valid query.")


if __name__ == "__main__":
    run("How many orders had more than one payment installment?")