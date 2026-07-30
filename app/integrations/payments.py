"""Stripe-shaped payment boundary; capture is intentionally disabled in MVP."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.config import settings


class PaymentUnavailable(RuntimeError):
    pass


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
    """Provider stub preserving the future API without charging customers."""

    @property
    def configured(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY)

    async def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        raise PaymentUnavailable(
            "Stripe checkout is not enabled; bookings remain pay-later in the MVP"
        )
