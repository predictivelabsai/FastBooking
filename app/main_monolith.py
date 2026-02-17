"""Monolith entrypoint — mounts FastAPI at /api and FastHTML at /."""

from __future__ import annotations

import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount

from app.api.main import create_api_app
from app.db.base import Base
from app.db.engine import engine
from app.config import settings
from app.ui.main import create_ui_app


async def create_schema():
    """Create the DB schema and tables on startup."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)


api_app = create_api_app()
ui_app = create_ui_app()

app = Starlette(
    routes=[
        Mount("/api", app=api_app),
        Mount("/", app=ui_app),
    ],
)


@app.on_event("startup")
async def startup():
    await create_schema()


if __name__ == "__main__":
    uvicorn.run("app.main_monolith:app", host="0.0.0.0", port=8000, reload=True)
