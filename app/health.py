"""Runtime health endpoints shared by every deployment mode."""

from __future__ import annotations

from sqlalchemy import text
from starlette.responses import JSONResponse

from app.config import settings
from app.db.engine import engine


async def healthz(_request=None):
    return JSONResponse(
        {"status": "ok", "product": settings.APP_NAME, "mode": settings.DEPLOY_MODE}
    )


async def readyz(_request=None):
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            {"status": "not_ready", "product": settings.APP_NAME}, status_code=503
        )
    return JSONResponse({"status": "ready", "product": settings.APP_NAME})
