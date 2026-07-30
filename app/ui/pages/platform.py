"""FastBooking landing, tenant onboarding, and module configuration."""

from __future__ import annotations

import datetime
import hashlib
import re
import secrets

from fasthtml.common import *
from sqlalchemy import select
from starlette.responses import JSONResponse, RedirectResponse

from app.auth import google
from app.config import settings
from app.db.engine import async_session_factory
from app.db.models import User
from app.db.platform_models import (
    PRODUCT_MODULES,
    Booking,
    Location,
    Membership,
    Tenant,
    TenantModule,
    TrialEntitlement,
)
from app.services.booking import BookingError, cancel_booking

MODULE_LABELS = {
    "restaurant": ("Restaurants", "Food ordering, dine-in pre-orders, and tables"),
    "hotel": ("Hotels", "Room-type inventory and overnight stays"),
    "clinic": ("Private clinics", "FastClinic-connected appointments"),
    "events": ("Events", "Concerts, ticket types, and capacity"),
}
CSS = """
:root{--accent:#0f766e;--tint:#f0fdfa;--ink:#102a2a;--muted:#667575;--line:#dce8e5}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font-family:Inter,system-ui,sans-serif}
.nav{height:68px;display:flex;align-items:center;justify-content:space-between;max-width:1160px;margin:auto;padding:0 24px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;color:var(--ink);text-decoration:none}.mark{width:32px;height:32px;border-radius:10px;background:var(--accent);display:grid;place-items:center;color:#fff}
.button{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:999px;padding:11px 18px;text-decoration:none;font-weight:700;font-size:14px;background:var(--accent);color:#fff;cursor:pointer}.outline{background:#fff;color:var(--ink);border:1px solid var(--line)}
.hero{max-width:1160px;margin:auto;padding:100px 24px 78px}.kicker{color:var(--accent);font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.16em}.hero h1{font-size:clamp(42px,7vw,76px);line-height:1.03;letter-spacing:-.055em;max-width:900px;margin:22px 0}.lede{font-size:20px;line-height:1.65;color:var(--muted);max-width:760px}
.band{background:var(--tint);border-block:1px solid #d3e9e3}.grid{max-width:1160px;margin:auto;padding:64px 24px;display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.card{background:#fff;border:1px solid #d3e9e3;border-radius:20px;padding:24px}.card h2{font-size:19px;margin:18px 0 8px}.card p{color:var(--muted);line-height:1.55}.num{font-size:12px;color:var(--accent);font-weight:800}
.shell{max-width:1080px;margin:50px auto;padding:0 24px}.head{display:flex;justify-content:space-between;align-items:center;gap:20px}.modules{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:28px}.module{border:1px solid var(--line);border-radius:18px;padding:22px}.module.enabled{border-color:var(--accent);background:var(--tint)}.notice{max-width:1160px;margin:16px auto 0;padding:12px 24px;color:#92400e}.footer{max-width:1160px;margin:auto;padding:38px 24px;color:var(--muted);display:flex;justify-content:space-between;font-size:13px}
@media(max-width:780px){.grid,.modules{grid-template-columns:1fr}.hero{padding-top:70px}.footer{flex-direction:column;gap:12px}}
"""


def _head(title: str):
    return Head(
        Title(title),
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(
            name="description",
            content="Configurable bookings for restaurants, hotels, private clinics, and events.",
        ),
        Link(
            rel="icon",
            href=(
                "data:image/svg+xml,"
                "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
                "<rect width='32' height='32' rx='8' fill='%230f766e'/>"
                "<path d='M10 7h13v5h-7v3h6v5h-6v6h-6z' fill='white'/></svg>"
            ),
        ),
        Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
        ),
        Style(CSS),
    )


def landing_page(message: str = ""):
    cards = [
        Article(
            Span(f"0{index}", cls="num"),
            H2(label),
            P(description),
            cls="card",
        )
        for index, (label, description) in enumerate(MODULE_LABELS.values(), 1)
    ]
    return Html(
        _head("FastBooking · Configurable bookings for service businesses"),
        Body(
            Nav(
                A(Span("F", cls="mark"), "FastBooking", href="/", cls="brand"),
                Div(
                    A("Developers", href="/developers"),
                    " ",
                    A("Sign In", href="/auth/google", cls="button outline"),
                ),
                cls="nav",
            ),
            P(message, cls="notice") if message else None,
            Main(
                Section(
                    Span("Multi-tenant booking and commerce", cls="kicker"),
                    H1("One booking platform. Configured for your business."),
                    P(
                        "Take food orders and table reservations, sell hotel stays and event tickets, or connect public appointments directly to FastClinic.",
                        cls="lede",
                    ),
                    A("Start a 14-day trial", href="/auth/google", cls="button"),
                    cls="hero",
                ),
                Section(Div(*cards, cls="grid"), cls="band"),
            ),
            Footer(
                Span("FastBooking is part of the open-source FastSME suite."),
                A("Explore FastSME", href="https://fastsme.com/products"),
                cls="footer",
            ),
        ),
    )


def _slug(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:50]
    return f"{base or 'workspace'}-{secrets.token_hex(2)}"


async def _provision(identity: dict[str, str]) -> tuple[int, str]:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == identity["email"]))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=identity["email"],
                username=identity["name"],
                role="tenant_admin",
                is_active=True,
            )
            db.add(user)
            await db.flush()
        result = await db.execute(
            select(Membership, Tenant)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .where(Membership.user_id == user.id)
            .order_by(Membership.id)
        )
        existing = result.first()
        if existing:
            _, tenant = existing
            return user.id, tenant.slug

        tenant = Tenant(
            slug=_slug(identity["name"]),
            name=f"{identity['name']}'s workspace",
            status="trial",
        )
        db.add(tenant)
        await db.flush()
        db.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner"))
        for module in PRODUCT_MODULES:
            db.add(TenantModule(tenant_id=tenant.id, module=module, enabled=False))
        now = datetime.datetime.now(datetime.UTC)
        db.add(
            TrialEntitlement(
                tenant_id=tenant.id,
                starts_at=now,
                ends_at=now + datetime.timedelta(days=settings.TRIAL_DAYS),
                booking_limit=100,
                order_limit=100,
                enforcement="soft",
            )
        )
        db.add(
            Location(
                tenant_id=tenant.id,
                slug="main",
                name="Main location",
                timezone=tenant.timezone,
            )
        )
        await db.commit()
        return user.id, tenant.slug


def register_routes(app):
    @app.get("/developers")
    async def developers():
        return Html(
            _head("FastBooking API · Developers"),
            Body(
                Main(
                    A("FastBooking", href="/", cls="brand"),
                    Span("Developers", cls="kicker"),
                    H1("Build on tenant-scoped booking APIs."),
                    P(
                        "Configure product modules, read public tenant catalogues, "
                        "and create conflict-checked restaurant, hotel, clinic, and "
                        "event bookings."
                    ),
                    Ul(
                        Li(Code("GET /api/v1/public/{tenant}/catalogue")),
                        Li(Code("POST /api/v1/public/{tenant}/bookings/restaurant")),
                        Li(Code("POST /api/v1/public/{tenant}/bookings/hotel")),
                        Li(Code("POST /api/v1/public/{tenant}/bookings/clinic")),
                        Li(Code("POST /api/v1/public/{tenant}/bookings/events")),
                    ),
                    A("Open interactive API docs", href="/api/docs", cls="button"),
                    P(A("Download OpenAPI JSON", href="/swagger.json")),
                    cls="shell",
                )
            ),
        )

    @app.get("/swagger.json")
    async def swagger():
        from app.api.main import create_api_app

        return JSONResponse(create_api_app().openapi())

    @app.get("/")
    async def landing(request, session):
        if session.get("user_id"):
            return RedirectResponse("/app", status_code=303)
        messages = {
            "unconfigured": "Google sign-in is not configured for this deployment.",
            "failed": "Google sign-in failed. Please try again.",
            "unauthorised": "That Google account is not authorised.",
        }
        return landing_page(messages.get(request.query_params.get("auth", ""), ""))

    @app.get("/auth/google")
    async def google_start(request, session):
        if not google.enabled():
            return RedirectResponse("/?auth=unconfigured", status_code=303)
        state = google.new_state()
        session["google_oauth_state"] = state
        return RedirectResponse(google.authorize_url(request, state), status_code=303)

    @app.get("/auth/google/callback")
    async def google_callback(
        request, session, code: str = "", state: str = "", error: str = ""
    ):
        expected = session.pop("google_oauth_state", None)
        if error or not code or not secrets.compare_digest(state, expected or ""):
            return RedirectResponse("/?auth=failed", status_code=303)
        identity = await google.exchange(request, code)
        if not identity:
            return RedirectResponse("/?auth=unauthorised", status_code=303)
        user_id, tenant_slug = await _provision(identity)
        session["user_id"], session["tenant_slug"] = user_id, tenant_slug
        return RedirectResponse("/app", status_code=303)

    @app.get("/logout")
    async def logout(session):
        session.clear()
        return RedirectResponse("/", status_code=303)

    @app.get("/app")
    async def workspace(session):
        tenant_slug = session.get("tenant_slug")
        if not tenant_slug:
            return RedirectResponse("/", status_code=303)
        async with async_session_factory() as db:
            tenant = (
                await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
            ).scalar_one()
            modules = (
                await db.execute(
                    select(TenantModule)
                    .where(TenantModule.tenant_id == tenant.id)
                    .order_by(TenantModule.module)
                )
            ).scalars()
            cards = [
                Article(
                    H2(MODULE_LABELS[item.module][0]),
                    P(MODULE_LABELS[item.module][1]),
                    P("Enabled" if item.enabled else "Not enabled"),
                    Form(
                        Button(
                            "Disable" if item.enabled else "Enable",
                            cls="button",
                            type="submit",
                        ),
                        method="post",
                        action=f"/app/modules/{item.module}/toggle",
                    ),
                    cls=f"module {'enabled' if item.enabled else ''}",
                )
                for item in modules
            ]
        return Html(
            _head(f"{tenant.name} · FastBooking"),
            Body(
                Main(
                    Div(
                        Div(H1(tenant.name), P("Choose the products this tenant uses.")),
                        Div(
                            A("Public page", href=f"/book/{tenant.slug}"),
                            " · ",
                            A("Sign out", href="/logout"),
                        ),
                        cls="head",
                    ),
                    Div(*cards, cls="modules"),
                    cls="shell",
                )
            ),
        )

    @app.post("/app/modules/{module}/toggle")
    async def toggle_module(module: str, session):
        if module not in PRODUCT_MODULES or not session.get("user_id"):
            return RedirectResponse("/", status_code=303)
        async with async_session_factory() as db:
            configured = (
                await db.execute(
                    select(TenantModule)
                    .join(Tenant, Tenant.id == TenantModule.tenant_id)
                    .join(Membership, Membership.tenant_id == Tenant.id)
                    .where(
                        Tenant.slug == session.get("tenant_slug"),
                        Membership.user_id == session["user_id"],
                        Membership.role.in_(("owner", "admin")),
                        TenantModule.module == module,
                    )
                )
            ).scalar_one_or_none()
            if configured:
                configured.enabled = not configured.enabled
                await db.commit()
        return RedirectResponse("/app", status_code=303)

    @app.get("/book/{tenant_slug}")
    async def public_tenant(tenant_slug: str):
        async with async_session_factory() as db:
            tenant = (
                await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
            ).scalar_one_or_none()
            if not tenant:
                return landing_page("Booking page not found.")
            modules = (
                await db.execute(
                    select(TenantModule).where(
                        TenantModule.tenant_id == tenant.id,
                        TenantModule.enabled.is_(True),
                    )
                )
            ).scalars()
            cards = [
                Article(
                    H2(MODULE_LABELS[item.module][0]),
                    P(MODULE_LABELS[item.module][1]),
                    A(
                        "View availability",
                        href=f"/api/v1/public/{tenant.slug}/catalogue",
                    ),
                    cls="module enabled",
                )
                for item in modules
            ]
        return Html(
            _head(f"Book with {tenant.name}"),
            Body(
                Main(
                    A("FastBooking", href="/", cls="brand"),
                    H1(tenant.name),
                    P("Choose a service to continue."),
                    Div(*cards, cls="modules")
                    if cards
                    else P("Online booking is not enabled yet."),
                    cls="shell",
                )
            ),
        )

    @app.get("/manage/{manage_token}")
    async def manage_booking(manage_token: str):
        token_hash = hashlib.sha256(manage_token.encode()).hexdigest()
        async with async_session_factory() as db:
            booking = (
                await db.execute(
                    select(Booking).where(Booking.manage_token_hash == token_hash)
                )
            ).scalar_one_or_none()
            if not booking:
                return landing_page("Booking management link is invalid.")
            tenant = await db.get(Tenant, booking.tenant_id)
        return Html(
            _head(f"Manage {booking.public_reference}"),
            Body(
                Main(
                    A("FastBooking", href="/", cls="brand"),
                    H1(f"Booking {booking.public_reference}"),
                    P(f"Status: {booking.status.title()}"),
                    P(
                        f"{booking.starts_at:%d %b %Y %H:%M} – "
                        f"{booking.ends_at:%d %b %Y %H:%M}"
                    ),
                    Form(
                        Button("Cancel booking", cls="button", type="submit"),
                        method="post",
                        action=f"/manage/{manage_token}/cancel",
                    )
                    if booking.status in {"pending", "confirmed"}
                    else None,
                    P(
                        "To choose a new time, cancel this booking and make a new "
                        "conflict-checked reservation."
                    ),
                    A("Return to booking page", href=f"/book/{tenant.slug}"),
                    cls="shell",
                )
            ),
        )

    @app.post("/manage/{manage_token}/cancel")
    async def cancel_managed_booking(manage_token: str):
        async with async_session_factory() as db:
            try:
                await cancel_booking(db, manage_token)
                await db.commit()
            except BookingError:
                await db.rollback()
        return RedirectResponse(f"/manage/{manage_token}", status_code=303)
