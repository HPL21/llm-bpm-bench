import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/status")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Asynchronous WebSocket endpoint.
    Sends server time and status every second to the connected client.
    """
    await websocket.accept()
    try:
        while True:
            data = {
                "status": "online",
                "timestamp": datetime.now().isoformat(),
                "service": "LLM Benchmarker API",
            }
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Client disconnected")
