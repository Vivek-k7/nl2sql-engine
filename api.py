from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from graph import graph

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

@app.post("/query")
async def query(request: QueryRequest):
    initial_state = {
        "question": request.question,
        "tables": [],
        "schema_context": "",
        "sql": "",
        "result": {},
        "error_history": [],
        "attempts": 0
    }
    
    result = await graph.ainvoke(initial_state)
    
    return {
        "question": request.question,
        "sql": result["sql"],
        "data": result["result"]["data"] if result["result"].get("success") else None,
        "error": None if result["result"].get("success") else result["error_history"][-1]["error"],
        "attempts": result["attempts"]
    }

@app.websocket("/ws/query")
async def query_ws(websocket: WebSocket):
    await websocket.accept()
    
    data = await websocket.receive_json()
    question = data['question']

    initial_state = {
        "question": question,
        "tables": [],
        "schema_context": "",
        "sql": "",
        "result": {},
        "error_history": [],
        "attempts": 0
    }
    
    async for chunk in graph.astream(initial_state):
        await websocket.send_json(chunk)

    await websocket.close()