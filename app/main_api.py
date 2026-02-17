"""API-only entrypoint — serves at /api/v0/..."""

from __future__ import annotations

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount

from app.api.main import create_api_app
from app.db.base import Base
from app.db.engine import engine
from app.config import settings

api_app = create_api_app()

app = Starlette(
    routes=[
        Mount("/api", app=api_app),
    ],
)


@app.on_event("startup")
async def startup():
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    uvicorn.run("app.main_api:app", host="0.0.0.0", port=8000, reload=True)
