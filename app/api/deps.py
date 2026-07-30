from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import async_session_factory
from app.db.models import User
from app.db.platform_models import Tenant


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Stub: returns the first active user (demo mode).

    Replace with JWT / session auth later.
    """
    result = await db.execute(
        select(User).where(User.is_active.is_(True), User.role == "user").limit(1)
    )
    user = result.scalar_one_or_none()
    if user is None:
        # fallback: return first user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one()
    return user


async def get_current_tenant(db: AsyncSession = Depends(get_db)) -> Tenant:
    """Resolve the demo tenant until session-backed tenant selection is enabled."""
    result = await db.execute(select(Tenant).order_by(Tenant.id).limit(1))
    return result.scalar_one()


async def get_current_restaurant_user(db: AsyncSession = Depends(get_db)) -> User:
    """Stub: returns the first restaurant-role user (demo mode)."""
    result = await db.execute(
        select(User).where(User.is_active.is_(True), User.role == "restaurant").limit(1)
    )
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one()
    return user
