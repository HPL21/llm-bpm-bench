from datetime import datetime

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/", summary="API Status")
async def api_root():
    """
    General API status and info.
    """
    return {
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "time": datetime.now(),
        "docs_url": "/docs",
    }


@router.get("/health", summary="Health Check")
async def health_check():
    """
    Simple health check for container orchestrators (like Docker/K8s).
    """
    return {"status": "ok"}
