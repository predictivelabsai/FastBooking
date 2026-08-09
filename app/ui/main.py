"""FastHTML UI app factory."""

from __future__ import annotations

from fasthtml.common import fast_app

from app.config import settings
from app.ui.pages import platform
from app.ui.seo import register_seo_routes


def create_ui_app():
    app, rt = fast_app(
        pico=False,
        secret_key=settings.SESSION_SECRET,
        sess_https_only=settings.ENVIRONMENT == "production",
        hdrs=(
            # TailwindCSS CDN + HTMX already injected via layout shell
        ),
    )

    register_seo_routes(app)
    platform.register_routes(app)

    return app
