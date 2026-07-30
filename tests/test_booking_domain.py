import datetime

import pytest

from app.api.main import create_api_app
from app.db.base import Base
from app.db.platform_models import PRODUCT_MODULES
from app.integrations.payments import (
    CheckoutRequest,
    PaymentUnavailable,
    StripeGateway,
)
from app.services.booking import BookingError, nights_between, validate_time_range


def test_all_configurable_product_modules_are_registered():
    assert PRODUCT_MODULES == ("restaurant", "hotel", "clinic", "events")
    assert {
        "fastbooking.tenants",
        "fastbooking.tenant_modules",
        "fastbooking.bookings",
        "fastbooking.hotel_night_inventory",
        "fastbooking.scheduled_events",
        "fastbooking.ticket_types",
    }.issubset(Base.metadata.tables)


def test_hotel_stay_uses_half_open_night_range():
    assert nights_between(
        datetime.date(2026, 8, 10), datetime.date(2026, 8, 13)
    ) == [
        datetime.date(2026, 8, 10),
        datetime.date(2026, 8, 11),
        datetime.date(2026, 8, 12),
    ]


def test_hotel_stay_rejects_empty_range():
    with pytest.raises(BookingError, match="Check-out"):
        nights_between(datetime.date(2026, 8, 10), datetime.date(2026, 8, 10))


def test_booking_times_require_timezone_and_positive_duration():
    start = datetime.datetime(2026, 8, 10, 10, tzinfo=datetime.UTC)
    validate_time_range(start, start + datetime.timedelta(minutes=30))
    with pytest.raises(BookingError, match="timezone"):
        validate_time_range(start.replace(tzinfo=None), start.replace(tzinfo=None))
    with pytest.raises(BookingError, match="after"):
        validate_time_range(start, start)


def test_openapi_exposes_each_public_booking_strategy():
    paths = create_api_app().openapi()["paths"]
    assert "/v1/public/{tenant_slug}/bookings/restaurant" in paths
    assert "/v1/public/{tenant_slug}/bookings/hotel" in paths
    assert "/v1/public/{tenant_slug}/bookings/clinic" in paths
    assert "/v1/public/{tenant_slug}/bookings/events" in paths
    assert "/v1/public/bookings/manage/{manage_token}/cancel" in paths


@pytest.mark.asyncio
async def test_stripe_stub_never_captures_payment():
    request = CheckoutRequest(
        tenant_id=1,
        reference="FB-TEST",
        amount=__import__("decimal").Decimal("10.00"),
        currency="EUR",
        return_url="https://booking.fastsme.com/return",
    )
    with pytest.raises(PaymentUnavailable, match="not enabled"):
        await StripeGateway().create_checkout(request)
