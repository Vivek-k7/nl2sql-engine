from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from intent import intent_detector
from schema import get_schema_context
from llm import generate_sql
from db import execute_sql

MAX_RETRIES = 3

class AgentState(TypedDict):
    question: str
    tables: list[str]
    schema_context: str
    sql: str
    result: dict
    error_history: Annotated[list[dict], add]
    attempts: int


def intent_node(state: AgentState):
    result = intent_detector(state['question'])
    return {'tables': result}

def schema_node(state: AgentState):
    result = get_schema_context(state['tables'])
    return {'schema_context': result}

def sql_gen_node(state: AgentState):
    result = generate_sql(state['question'], state['schema_context'], state['error_history'])
    new_attempts = state['attempts'] + 1
    return {'sql': result, 'attempts': new_attempts}

def execute_node(state: AgentState):
    result = execute_sql(state['sql'])
    if result["success"]:
        return {'result': result}
    else:
        return {'error_history': [{
            "sql": state['sql'],
            "error": result["error"]
        }]}
    
def should_retry(state: AgentState) -> str:
    if state.get("result") and state["result"]["success"]:
        return "end"
    if state["attempts"] >= MAX_RETRIES:
        return "end"
    return "sql_gen"

builder = StateGraph(AgentState)

builder.add_node("intent", intent_node)
builder.add_node("schema", schema_node)
builder.add_node("sql_gen", sql_gen_node)
builder.add_node("execute", execute_node)

builder.set_entry_point("intent")

builder.add_edge("intent", "schema")
builder.add_edge("schema", "sql_gen")
builder.add_edge("sql_gen", "execute")

builder.add_conditional_edges(
    "execute",
    should_retry,
    {
        "sql_gen": "sql_gen",
        "end": END
    }
)

graph = builder.compile()

if __name__ == "__main__":
    initial_state = {
        "question": "How many orders were delivered successfully?",
        "tables": [],
        "schema_context": "",
        "sql": "",
        "result": {},
        "error_history": [],
        "attempts": 0
    }
    
    result = graph.invoke(initial_state)
    print(f"SQL: {result['sql']}")
    print(f"Result: {result['result']}")