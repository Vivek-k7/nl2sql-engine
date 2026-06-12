from fastapi import APIRouter, WebSocket
from app.core.graph import graph
from pydantic import BaseModel

class QueryRequest(BaseModel):
    question: str

router = APIRouter()

@router.post("/query")
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

@router.websocket("/ws/query")
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
    
    final_state = {}
    
    async for chunk in graph.astream(initial_state):
        await websocket.send_json(chunk)
        final_state.update(chunk)

    result = final_state.get("execute", {}).get("result", {})
    
    if result.get("success"):
        await websocket.send_json({
            "status": "success",
            "sql": final_state.get("sql_gen", {}).get("sql"),
            "data": result.get("data"),
            "attempts": final_state.get("sql_gen", {}).get("attempts")
        })
    else:
        await websocket.send_json({
            "status": "failed",
            "message": "Max retries reached. Could not generate a valid query.",
            "error_history": initial_state["error_history"]
        })
    
    await websocket.close()