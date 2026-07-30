"""FastHTML UI app factory."""

from __future__ import annotations

from fasthtml.common import fast_app
from sqlalchemy import select

from app.config import settings
from app.db.engine import async_session_factory
from app.db.models import User
from app.ui.client import DbClient, HttpClient
from app.ui.pages import admin, cart, home, orders, platform, restaurant
from app.ui.seo import register_seo_routes


def create_ui_app():
    app, rt = fast_app(
        pico=False,
        secret_key=settings.SESSION_SECRET,
        hdrs=(
            # TailwindCSS CDN + HTMX already injected via layout shell
        ),
    )

    # pick client based on deploy mode
    if settings.DEPLOY_MODE == "ui":
        client = HttpClient(settings.API_BASE_URL)
    else:
        client = DbClient()

    # stub user helpers
    async def get_user_id() -> int:
        async with async_session_factory() as db:
            result = await db.execute(
                select(User).where(User.is_active.is_(True), User.role == "user").limit(1)
            )
            user = result.scalar_one_or_none()
            if user:
                return user.id
            result = await db.execute(select(User).limit(1))
            return result.scalar_one().id

    async def get_admin_user_id() -> int:
        async with async_session_factory() as db:
            result = await db.execute(
                select(User)
                .where(User.is_active.is_(True), User.role == "restaurant")
                .limit(1)
            )
            user = result.scalar_one_or_none()
            if user:
                return user.id
            result = await db.execute(select(User).limit(1))
            return result.scalar_one().id

    # register page routes
    register_seo_routes(app)
    platform.register_routes(app)
    home.register_routes(app, client)
    restaurant.register_routes(app, client)
    cart.register_routes(app, client, get_user_id)
    orders.register_routes(app, client, get_user_id)
    admin.register_routes(app, client, get_admin_user_id)

    return app
