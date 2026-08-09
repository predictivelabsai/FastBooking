from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.access import ADMIN_ROLE
from app.db.engine import async_session_factory
from app.db.models import User
from app.db.platform_models import Membership, Tenant


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    """Resolve an active user from the signed browser session."""
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=401, detail="Sign in required")
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Session is no longer valid")
    return user


async def get_current_tenant(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve the selected tenant and verify that the user belongs to it."""
    tenant_slug = request.session.get("tenant_slug")
    if not isinstance(tenant_slug, str):
        raise HTTPException(status_code=403, detail="No tenant access is assigned")
    tenant = (
        await db.execute(
            select(Tenant)
            .join(Membership, Membership.tenant_id == Tenant.id)
            .where(
                Tenant.slug == tenant_slug,
                Membership.user_id == user.id,
                Tenant.status == "active",
            )
        )
    ).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=403, detail="Tenant access denied")
    return tenant


async def get_current_restaurant_user(
    user: User = Depends(get_current_user),
) -> User:
    """Compatibility dependency for signed-in operational users."""
    return user


async def get_current_admin_user(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require the sole product-configuration role for the selected tenant."""
    tenant_slug = request.session.get("tenant_slug")
    membership = (
        await db.execute(
            select(Membership)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .where(
                Tenant.slug == tenant_slug,
                Membership.user_id == user.id,
                Membership.role == ADMIN_ROLE,
                Tenant.status == "active",
            )
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
