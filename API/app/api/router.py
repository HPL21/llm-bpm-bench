from fastapi import APIRouter

from app.api import cases, files, suites, system, websocket

api_router = APIRouter()

api_router.include_router(system.router, tags=["System"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(suites.router, prefix="/suites", tags=["Test Suites"])
api_router.include_router(cases.router, prefix="/cases", tags=["Test Cases"])
