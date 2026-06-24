import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.websockets import WebSocketState

from app.core.graph import graph

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


def build_initial_state(question: str) -> dict:
    return {
        "question": question,
        "tables": [],
        "schema_context": "",
        "sql": "",
        "result": {},
        "error_history": [],
        "attempts": 0,
    }


def validate_question(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please enter a question")

    return question.strip()


def format_query_response(question: str, state: dict) -> dict:
    result = state.get("result") or {}
    error_history = state.get("error_history") or []
    success = bool(result.get("success"))

    if not error_history:
        last_error = None
    else: 
        last_error = error_history[-1].get("error", "Unknown error")

    return {
        "question": question,
        "success": success,
        "sql": state.get("sql"),
        "data": result.get("data") if success else None,
        "error": None if success else last_error,
        "attempts": state.get("attempts", 0),
    }


def merge_stream_chunk(current_state: dict, chunk: dict) -> None:
    for node_update in chunk.values():
        if isinstance(node_update, dict):
            current_state.update(node_update)


async def close_websocket(websocket: WebSocket) -> None:
    if websocket.client_state == WebSocketState.CONNECTED:
        await websocket.close()


@router.post("/query")
async def query(request: QueryRequest):
    try:
        question = validate_question(request.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    initial_state = build_initial_state(question)

    try:
        result = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.exception("Graph execution failed.")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e

    return format_query_response(question, result)


@router.websocket("/ws/query")
async def query_ws(websocket: WebSocket):
    await websocket.accept()

    try:
        data = await websocket.receive_json()
        question = validate_question(data.get("question"))
        current_state = build_initial_state(question)

        await websocket.send_json({
            "type": "accepted",
            "question": question,
        })

        async for chunk in graph.astream(current_state):
            merge_stream_chunk(current_state, chunk)
            await websocket.send_json({
                "type": "progress",
                "chunk": chunk,
            })

        response = format_query_response(question, current_state)
        response["type"] = "final"
        response["status"] = "success" if response["success"] else "failed"
        await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("Client disconnected during graph execution.")

    except ValueError as e:
        await websocket.send_json({
            "type": "error",
            "status": "failed",
            "message": str(e),
        })

    except Exception as e:
        logger.exception("WebSocket query failed.")
        await websocket.send_json({
            "type": "error",
            "status": "failed",
            "message": f"An unexpected error occurred: {str(e)}",
        })

    finally:
        await close_websocket(websocket)