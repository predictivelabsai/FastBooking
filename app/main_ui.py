"""UI-only entrypoint — connects to API via HttpClient."""

from __future__ import annotations

import uvicorn

from app.config import settings

# Force ui mode
settings.DEPLOY_MODE = "ui"

from app.ui.main import create_ui_app

app = create_ui_app()

if __name__ == "__main__":
    uvicorn.run("app.main_ui:app", host="0.0.0.0", port=8001, reload=True)
