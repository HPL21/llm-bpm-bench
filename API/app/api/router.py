from fastapi import APIRouter

from app.api import cases, files, suites, system, websocket, llm, llm_models, benchmarks

api_router = APIRouter()

api_router.include_router(system.router, tags=["System"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(files.router, prefix="/files", tags=["Files"])
api_router.include_router(suites.router, prefix="/suites", tags=["Test Suites"])
api_router.include_router(cases.router, prefix="/cases", tags=["Test Cases"])
api_router.include_router(llm.router, prefix="/llm", tags=["LLM"])
api_router.include_router(llm_models.router, prefix="/llm-models", tags=["LLM Models"])
api_router.include_router(benchmarks.router, prefix="/benchmarks", tags=["Benchmarks"])
