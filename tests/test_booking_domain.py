import datetime
import hashlib
import hmac
import inspect
import time
from pathlib import Path

import pytest
from fastcore.xml import to_xml

from app.api.deps import get_current_user
from app.api.main import create_api_app
from app.auth.access import can_configure_products
from app.db.base import Base
from app.db.platform_models import PRODUCT_MODULES
from app.integrations.payments import (
    CheckoutRequest,
    PaymentUnavailable,
    StripeGateway,
    verify_stripe_signature,
)
from app.services.booking import (
    BookingError,
    ensure_capacity,
    nights_between,
    validate_time_range,
)
from app.ui.main import create_ui_app
from app.ui.pages.platform import comparison_page, features_page, landing_page


def test_all_configurable_product_modules_are_registered():
    assert PRODUCT_MODULES == (
        "restaurant",
        "hotel",
        "clinic",
        "events",
        "recreation",
    )
    assert {
        "fastbooking.tenants",
        "fastbooking.tenant_modules",
        "fastbooking.bookings",
        "fastbooking.hotel_night_inventory",
        "fastbooking.scheduled_events",
        "fastbooking.ticket_types",
        "fastbooking.recreation_programmes",
        "fastbooking.programme_enrolments",
        "fastbooking.membership_plans",
        "fastbooking.customer_memberships",
        "fastbooking.attendance_records",
        "fastbooking.payment_transactions",
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
    assert "/v1/public/{tenant_slug}/bookings/recreation/facilities" in paths
    assert "/v1/public/{tenant_slug}/bookings/recreation/programmes" in paths
    assert "/v1/public/{tenant_slug}/memberships" in paths
    assert "/v1/tenants/{tenant_slug}/attendance" in paths
    assert "/v1/tenants/{tenant_slug}/payments/onsite" in paths
    assert "/v1/tenants/{tenant_slug}/reports/financial" in paths
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


def test_recreation_capacity_rejects_over_allocation():
    ensure_capacity(capacity=4, reserved=2, quantity=2)
    with pytest.raises(BookingError, match="capacity"):
        ensure_capacity(capacity=4, reserved=3, quantity=2)


def test_stripe_signature_requires_valid_recent_raw_payload():
    payload = b'{"type":"checkout.session.completed"}'
    timestamp = int(time.time())
    secret = "whsec_test"
    digest = hmac.new(
        secret.encode(),
        str(timestamp).encode() + b"." + payload,
        hashlib.sha256,
    ).hexdigest()
    assert verify_stripe_signature(
        payload, f"t={timestamp},v1={digest}", secret
    )
    assert not verify_stripe_signature(
        payload + b" ", f"t={timestamp},v1={digest}", secret
    )


def test_landing_page_leads_with_recreation_and_fastcrm():
    html = to_xml(landing_page())
    assert "Every facility, programme and member" in html
    assert "Swimming lessons &amp; programmes" in html
    assert "Aquatics &amp; lane allocation" in html
    assert "FastCRM" in html
    assert 'src="/static/product-demo.gif"' in html
    assert 'href="/auth/google"' in html
    assert "14-day" not in html
    assert 'href="/features"' in html
    assert 'href="/compare"' in html


def test_recreation_walkthrough_gif_is_packaged():
    gif = Path("static/product-demo.gif")
    assert gif.stat().st_size > 100_000
    assert gif.read_bytes()[:6] in {b"GIF87a", b"GIF89a"}


def test_features_and_comparison_are_public_and_source_linked():
    features_html = to_xml(features_page())
    comparison_html = to_xml(comparison_page())
    assert "Swimming lessons" in features_html
    assert "Admin-only product-module configuration" in features_html
    for vendor in (
        "Xplor Recreation",
        "PerfectMind",
        "ACTIVE Network",
        "Jonas Leisure",
        "Legend",
        "Envibe",
    ):
        assert vendor in comparison_html
    assert comparison_html.count("https://") >= 7


def test_customer_journeys_and_marketing_routes_are_registered():
    paths = {getattr(route, "path", "") for route in create_ui_app().routes}
    assert {
        "/features",
        "/compare",
        "/access-pending",
        "/app",
        "/book/{tenant_slug}",
        "/book/{tenant_slug}/{module}",
    }.issubset(paths)


def test_admin_is_the_only_product_configuration_role():
    assert can_configure_products("admin")
    assert not can_configure_products("staff")
    assert not can_configure_products("viewer")
    assert not can_configure_products("owner")
    assert "request" in inspect.signature(get_current_user).parameters


def test_trials_are_not_part_of_the_runtime_schema():
    assert "fastbooking.trial_entitlements" not in Base.metadata.tables
    tenant_status = next(
        constraint
        for constraint in Base.metadata.tables["fastbooking.tenants"].constraints
        if constraint.name == "ck_tenants_status"
    )
    assert "trial" not in str(tenant_status.sqltext)


def test_customer_journey_images_are_packaged():
    for name in (
        "table-reservation.jpg",
        "hotel-booking.jpg",
        "clinic-booking.jpg",
        "event-booking.jpg",
        "facility-booking.jpg",
        "aquatics-booking.jpg",
    ):
        image = Path("static/images") / name
        assert image.stat().st_size > 20_000
        assert image.read_bytes()[:3] == b"\xff\xd8\xff"
