from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "FastBooking"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 5023
    PUBLIC_URL: str = "http://localhost:5023"
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/fastbooking"
    )
    DEPLOY_MODE: Literal["monolith", "api", "ui"] = "monolith"
    API_BASE_URL: str = "http://localhost:5023"
    DB_SCHEMA: str = "fastbooking"
    SESSION_SECRET: str = "development-only-change-me"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    GOOGLE_ALLOWED_DOMAINS: str = ""
    GOOGLE_ALLOWED_EMAILS: str = ""
    POSTMARK_API_TOKEN: str = ""
    FROM_EMAIL: str = "info@fastsme.com"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    TRIAL_DAYS: int = 14


settings = Settings()
