"""API-only entrypoint — serves at /api/v0/..."""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from app.api.main import create_api_app
from app.config import settings
from app.db.base import Base
from app.db.engine import engine
from app.health import healthz, readyz


async def create_schema():
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(_app):
    if settings.ENVIRONMENT != "production":
        await create_schema()
    try:
        yield
    finally:
        await engine.dispose()


api_app = create_api_app()

app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/healthz", healthz),
        Route("/readyz", readyz),
        Mount("/api", app=api_app),
    ],
)


if __name__ == "__main__":
    uvicorn.run(
        "app.main_api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
