from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.models.base import Base
from app.models.file_asset import FileAsset  # noqa: F401 (Import needed for registry)
from app.models.test_suite import TestSuite  # noqa: F401
from app.models.test_case import TestCase  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: code to run on startup and shutdown.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)
