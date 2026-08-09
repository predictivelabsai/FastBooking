"""Postmark delivery worker for persisted notification outbox rows."""

from __future__ import annotations

import datetime

import httpx
from sqlalchemy import select

from app.config import settings
from app.db.engine import async_session_factory
from app.db.platform_models import NotificationOutbox


async def deliver_pending(limit: int = 50) -> int:
    if not settings.POSTMARK_API_TOKEN:
        return 0
    now = datetime.datetime.now(datetime.UTC)
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(NotificationOutbox)
                .where(
                    NotificationOutbox.status == "pending",
                    NotificationOutbox.send_after <= now,
                )
                .order_by(NotificationOutbox.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).scalars()
        delivered = 0
        async with httpx.AsyncClient(timeout=20) as client:
            for item in rows:
                reference = item.payload.get("reference", "")
                subjects = {
                    "booking_confirmation": f"Booking confirmed · {reference}",
                    "booking_waitlisted": f"Added to waitlist · {reference}",
                    "booking_reminder": f"Booking reminder · {reference}",
                    "booking_cancelled": f"Booking cancelled · {reference}",
                    "membership_created": f"Membership created · {reference}",
                }
                messages = {
                    "booking_confirmation": (
                        f"Your booking {reference} with "
                        f"{item.payload.get('tenant', 'the business')} is confirmed. "
                        f"Manage it at {settings.PUBLIC_URL}/manage/"
                        f"{item.payload.get('manage_token', '')}"
                    ),
                    "booking_reminder": (
                        f"Reminder: your booking {reference} is tomorrow. "
                        f"Manage it at {settings.PUBLIC_URL}/manage/"
                        f"{item.payload.get('manage_token', '')}"
                    ),
                    "booking_waitlisted": (
                        f"You are on the waitlist for {reference} with "
                        f"{item.payload.get('tenant', 'the facility')}. We will "
                        "contact you when a place becomes available."
                    ),
                    "booking_cancelled": f"Your booking {reference} has been cancelled.",
                    "membership_created": (
                        f"Your {item.payload.get('plan', 'membership')} request "
                        f"{reference} with {item.payload.get('tenant', 'the facility')} "
                        "has been created."
                    ),
                }
                response = await client.post(
                    "https://api.postmarkapp.com/email",
                    headers={
                        "X-Postmark-Server-Token": settings.POSTMARK_API_TOKEN,
                        "Accept": "application/json",
                    },
                    json={
                        "From": settings.FROM_EMAIL,
                        "To": item.recipient,
                        "Subject": subjects.get(item.template, f"Booking · {reference}"),
                        "TextBody": messages.get(item.template, f"Booking {reference}"),
                        "MessageStream": "outbound",
                    },
                )
                item.attempts += 1
                if response.is_success:
                    item.status = "sent"
                    item.last_error = ""
                    delivered += 1
                else:
                    item.last_error = f"Postmark returned HTTP {response.status_code}"
                    if item.attempts >= 5:
                        item.status = "failed"
        await db.commit()
        return delivered
