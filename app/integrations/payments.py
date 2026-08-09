"""Hosted Stripe Checkout boundary for card payments."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import httpx

from app.config import settings


class PaymentUnavailable(RuntimeError):
    pass


def verify_stripe_signature(
    payload: bytes, signature_header: str, secret: str, *, tolerance: int = 300
) -> bool:
    """Verify Stripe's signed raw request body and reject stale deliveries."""
    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        key, separator, value = item.partition("=")
        if separator:
            parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts["t"][0])
    except (KeyError, ValueError, IndexError):
        return False
    if abs(int(time.time()) - timestamp) > tolerance:
        return False
    signed = str(timestamp).encode() + b"." + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(
        hmac.compare_digest(expected, candidate) for candidate in parts.get("v1", [])
    )


@dataclass(frozen=True)
class CheckoutRequest:
    tenant_id: int
    reference: str
    amount: Decimal
    currency: str
    return_url: str


@dataclass(frozen=True)
class CheckoutSession:
    provider: str
    external_id: str
    checkout_url: str


class PaymentGateway(Protocol):
    async def create_checkout(self, request: CheckoutRequest) -> CheckoutSession: ...


class StripeGateway:
    """Create hosted Checkout sessions without handling card data locally."""

    @property
    def configured(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY)

    async def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        if not self.configured:
            raise PaymentUnavailable(
                "Stripe checkout is not enabled; payment can be taken at the facility"
            )
        amount_minor = int((request.amount * 100).quantize(Decimal("1")))
        if amount_minor < 1:
            raise PaymentUnavailable("Checkout amount must be greater than zero")
        data = {
            "mode": "payment",
            "success_url": request.return_url,
            "cancel_url": request.return_url,
            "client_reference_id": request.reference,
            "metadata[fastbooking_reference]": request.reference,
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": request.currency.lower(),
            "line_items[0][price_data][unit_amount]": str(amount_minor),
            "line_items[0][price_data][product_data][name]": (
                f"FastBooking {request.reference}"
            ),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                data=data,
                headers={"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}"},
            )
        if response.status_code >= 400:
            raise PaymentUnavailable("The payment provider could not start checkout")
        payload = response.json()
        if not payload.get("id") or not payload.get("url"):
            raise PaymentUnavailable("The payment provider returned an invalid session")
        return CheckoutSession(
            provider="stripe",
            external_id=str(payload["id"]),
            checkout_url=str(payload["url"]),
        )
