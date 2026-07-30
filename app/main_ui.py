"""UI-only entrypoint — connects to API via HttpClient."""

from __future__ import annotations

import uvicorn

from app.config import settings

# Force ui mode
settings.DEPLOY_MODE = "ui"

from app.ui.main import create_ui_app

app = create_ui_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main_ui:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
