"""Minimal server-side Google OpenID Connect flow."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx

from app.config import settings


def enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def new_state() -> str:
    return secrets.token_urlsafe(32)


def callback_uri(request) -> str:
    if settings.GOOGLE_REDIRECT_URI:
        return settings.GOOGLE_REDIRECT_URI
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    )
    return f"{proto}://{host}/auth/google/callback"


def authorize_url(request, state: str) -> str:
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": callback_uri(request),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
    )


async def exchange(request, code: str) -> dict[str, str] | None:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": callback_uri(request),
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token = token_response.json()
            info_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {token['access_token']}"},
            )
            info_response.raise_for_status()
            info = info_response.json()
    except (httpx.HTTPError, KeyError, ValueError):
        return None

    email = (info.get("email") or "").strip().lower()
    if not email or info.get("email_verified") is False:
        return None
    domains = {
        item.strip().lower()
        for item in settings.GOOGLE_ALLOWED_DOMAINS.split(",")
        if item.strip()
    }
    emails = {
        item.strip().lower()
        for item in settings.GOOGLE_ALLOWED_EMAILS.split(",")
        if item.strip()
    }
    if domains or emails:
        if email not in emails and email.rsplit("@", 1)[-1] not in domains:
            return None
    return {"email": email, "name": info.get("name") or email}
