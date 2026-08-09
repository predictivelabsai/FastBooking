"""Tenant configuration, catalogue, and public booking API."""

from __future__ import annotations

import datetime
import hashlib
import json
import secrets
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_db
from app.auth.access import ADMIN_ROLE
from app.config import settings
from app.db.models import User
from app.db.platform_models import (
    PRODUCT_MODULES,
    AttendanceRecord,
    Booking,
    CustomerMembership,
    Guest,
    HotelRoomType,
    Location,
    Membership,
    MembershipPlan,
    Offering,
    PaymentTransaction,
    ProgrammeEnrolment,
    RecreationProgramme,
    Resource,
    ScheduledEvent,
    Tenant,
    TenantModule,
    TicketType,
)
from app.integrations.payments import (
    CheckoutRequest,
    PaymentUnavailable,
    StripeGateway,
    verify_stripe_signature,
)
from app.platform_schemas import (
    AttendanceIn,
    BookingCheckoutIn,
    BookingOut,
    CheckoutOut,
    ClinicBookingIn,
    EventBookingIn,
    FacilityBookingIn,
    HotelBookingIn,
    MembershipOut,
    MembershipPurchaseIn,
    OnsitePaymentIn,
    ProgrammeEnrolmentIn,
    RestaurantReservationIn,
    TenantModuleOut,
    TenantModuleUpdate,
)
from app.services.booking import (
    BookingError,
    BookingResult,
    cancel_booking,
    create_clinic_booking,
    create_event_booking,
    create_facility_booking,
    create_hotel_booking,
    create_restaurant_reservation,
    enrol_in_programme,
    purchase_membership,
)

router = APIRouter()


def _booking_out(created: BookingResult) -> BookingOut:
    booking = created.booking
    return BookingOut(
        id=booking.id,
        public_reference=booking.public_reference,
        module=booking.module,
        status=booking.status,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        quantity=booking.quantity,
        party_size=booking.party_size,
        currency=booking.currency,
        total=booking.total,
        manage_token=created.manage_token,
    )


async def _tenant(db: AsyncSession, tenant_slug: str) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


async def _require_admin(
    db: AsyncSession, tenant: Tenant, user: User
) -> Membership:
    result = await db.execute(
        select(Membership).where(
            Membership.tenant_id == tenant.id,
            Membership.user_id == user.id,
            Membership.role == ADMIN_ROLE,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    return membership


@router.get("/tenants/{tenant_slug}/modules", response_model=list[TenantModuleOut])
async def list_modules(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    tenant = await _tenant(db, tenant_slug)
    await _require_admin(db, tenant, user)
    result = await db.execute(
        select(TenantModule)
        .where(TenantModule.tenant_id == tenant.id)
        .order_by(TenantModule.module)
    )
    return result.scalars().all()


@router.put(
    "/tenants/{tenant_slug}/modules/{module}", response_model=TenantModuleOut
)
async def configure_module(
    tenant_slug: str,
    module: str,
    body: TenantModuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    if module not in PRODUCT_MODULES:
        raise HTTPException(status_code=400, detail="Unknown product module")
    tenant = await _tenant(db, tenant_slug)
    await _require_admin(db, tenant, user)
    result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant.id, TenantModule.module == module
        )
    )
    configured = result.scalar_one_or_none()
    if configured:
        configured.enabled = body.enabled
        configured.settings_json = body.settings
    else:
        configured = TenantModule(
            tenant_id=tenant.id,
            module=module,
            enabled=body.enabled,
            settings_json=body.settings,
        )
        db.add(configured)
    await db.commit()
    await db.refresh(configured)
    return configured


@router.get("/public/{tenant_slug}/catalogue")
async def public_catalogue(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, tenant_slug)
    modules_result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant.id, TenantModule.enabled.is_(True)
        )
    )
    locations_result = await db.execute(
        select(Location).where(
            Location.tenant_id == tenant.id, Location.active.is_(True)
        )
    )
    offerings_result = await db.execute(
        select(Offering).where(
            Offering.tenant_id == tenant.id, Offering.active.is_(True)
        )
    )
    resources_result = await db.execute(
        select(Resource).where(
            Resource.tenant_id == tenant.id, Resource.active.is_(True)
        )
    )
    programmes_result = await db.execute(
        select(RecreationProgramme).where(
            RecreationProgramme.tenant_id == tenant.id,
            RecreationProgramme.status == "published",
        )
    )
    membership_plans_result = await db.execute(
        select(MembershipPlan).where(
            MembershipPlan.tenant_id == tenant.id,
            MembershipPlan.active.is_(True),
        )
    )
    room_types_result = await db.execute(
        select(HotelRoomType).where(
            HotelRoomType.tenant_id == tenant.id, HotelRoomType.active.is_(True)
        )
    )
    events_result = await db.execute(
        select(ScheduledEvent).where(
            ScheduledEvent.tenant_id == tenant.id,
            ScheduledEvent.status == "published",
        )
    )
    events = events_result.scalars().all()
    tickets = []
    if events:
        tickets_result = await db.execute(
            select(TicketType).where(
                TicketType.event_id.in_([event.id for event in events]),
                TicketType.active.is_(True),
            )
        )
        tickets = tickets_result.scalars().all()
    return {
        "tenant": {
            "slug": tenant.slug,
            "name": tenant.name,
            "timezone": tenant.timezone,
            "currency": tenant.currency,
            "accent_color": tenant.accent_color,
            "logo_url": tenant.logo_url,
        },
        "modules": [
            {
                "module": item.module,
                "settings": item.settings_json,
            }
            for item in modules_result.scalars().all()
        ],
        "locations": [
            {
                "id": item.id,
                "slug": item.slug,
                "name": item.name,
                "address": item.address,
                "city": item.city,
                "country": item.country,
                "timezone": item.timezone,
            }
            for item in locations_result.scalars().all()
        ],
        "offerings": [
            {
                "id": item.id,
                "location_id": item.location_id,
                "module": item.module,
                "slug": item.slug,
                "name": item.name,
                "description": item.description,
                "duration_minutes": item.duration_minutes,
                "capacity": item.capacity,
                "price": str(item.price),
            }
            for item in offerings_result.scalars().all()
        ],
        "resources": [
            {
                "id": item.id,
                "location_id": item.location_id,
                "module": item.module,
                "name": item.name,
                "resource_type": item.resource_type,
                "capacity": item.capacity,
            }
            for item in resources_result.scalars().all()
            if item.module != "clinic" or item.resource_type == "practitioner"
        ],
        "recreation_programmes": [
            {
                "id": item.id,
                "location_id": item.location_id,
                "offering_id": item.offering_id,
                "resource_id": item.resource_id,
                "code": item.code,
                "name": item.name,
                "category": item.category,
                "starts_at": item.starts_at,
                "ends_at": item.ends_at,
                "remaining": max(0, item.capacity - item.enrolled),
                "waitlist_enabled": item.waitlist_enabled,
                "schedule": item.schedule_json,
            }
            for item in programmes_result.scalars().all()
        ],
        "membership_plans": [
            {
                "id": item.id,
                "location_id": item.location_id,
                "code": item.code,
                "name": item.name,
                "description": item.description,
                "billing_interval": item.billing_interval,
                "price": str(item.price),
                "duration_days": item.duration_days,
                "included_visits": item.included_visits,
                "access_rules": item.access_rules,
            }
            for item in membership_plans_result.scalars().all()
        ],
        "hotel_room_types": [
            {
                "id": item.id,
                "location_id": item.location_id,
                "name": item.name,
                "occupancy": item.occupancy,
                "units": item.units,
                "nightly_rate": str(item.nightly_rate),
            }
            for item in room_types_result.scalars().all()
        ],
        "events": [
            {
                "id": item.id,
                "location_id": item.location_id,
                "slug": item.slug,
                "name": item.name,
                "starts_at": item.starts_at,
                "ends_at": item.ends_at,
            }
            for item in events
        ],
        "ticket_types": [
            {
                "id": item.id,
                "event_id": item.event_id,
                "name": item.name,
                "price": str(item.price),
                "remaining": item.capacity - item.reserved,
                "max_per_booking": item.max_per_booking,
            }
            for item in tickets
        ],
    }


async def _complete(db: AsyncSession, operation) -> BookingOut:
    try:
        created = await operation
        await db.commit()
        await db.refresh(created.booking)
        return _booking_out(created)
    except BookingError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/public/bookings/manage/{manage_token}/cancel")
async def cancel_public_booking(
    manage_token: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        booking = await cancel_booking(db, manage_token)
        await db.commit()
        return {
            "public_reference": booking.public_reference,
            "status": booking.status,
        }
    except BookingError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/public/{tenant_slug}/bookings/restaurant",
    response_model=BookingOut,
    status_code=201,
)
async def reserve_restaurant(
    tenant_slug: str,
    body: RestaurantReservationIn,
    db: AsyncSession = Depends(get_db),
):
    return await _complete(
        db,
        create_restaurant_reservation(
            db,
            tenant_slug=tenant_slug,
            location_slug=body.location_slug,
            starts_at=body.starts_at,
            party_size=body.party_size,
            duration_minutes=body.duration_minutes,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
            guest_name=body.guest.name,
            guest_email=body.guest.email,
            guest_phone=body.guest.phone,
        ),
    )


@router.post(
    "/public/{tenant_slug}/bookings/hotel",
    response_model=BookingOut,
    status_code=201,
)
async def reserve_hotel(
    tenant_slug: str,
    body: HotelBookingIn,
    db: AsyncSession = Depends(get_db),
):
    return await _complete(
        db,
        create_hotel_booking(
            db,
            tenant_slug=tenant_slug,
            location_slug=body.location_slug,
            room_type_id=body.room_type_id,
            check_in=body.check_in,
            check_out=body.check_out,
            rooms=body.rooms,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
            guest_name=body.guest.name,
            guest_email=body.guest.email,
            guest_phone=body.guest.phone,
        ),
    )


@router.post(
    "/public/{tenant_slug}/bookings/events",
    response_model=BookingOut,
    status_code=201,
)
async def reserve_event(
    tenant_slug: str,
    body: EventBookingIn,
    db: AsyncSession = Depends(get_db),
):
    return await _complete(
        db,
        create_event_booking(
            db,
            tenant_slug=tenant_slug,
            location_slug=body.location_slug,
            ticket_type_id=body.ticket_type_id,
            quantity=body.quantity,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
            guest_name=body.guest.name,
            guest_email=body.guest.email,
            guest_phone=body.guest.phone,
        ),
    )


@router.post(
    "/public/{tenant_slug}/bookings/clinic",
    response_model=BookingOut,
    status_code=201,
)
async def reserve_clinic(
    tenant_slug: str,
    body: ClinicBookingIn,
    db: AsyncSession = Depends(get_db),
):
    return await _complete(
        db,
        create_clinic_booking(
            db,
            tenant_slug=tenant_slug,
            location_slug=body.location_slug,
            offering_id=body.offering_id,
            practitioner_resource_id=body.practitioner_resource_id,
            starts_at=body.starts_at,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
            guest_name=body.guest.name,
            guest_email=body.guest.email,
            guest_phone=body.guest.phone,
        ),
    )


@router.post(
    "/public/{tenant_slug}/bookings/recreation/facilities",
    response_model=BookingOut,
    status_code=201,
)
async def reserve_recreation_facility(
    tenant_slug: str,
    body: FacilityBookingIn,
    db: AsyncSession = Depends(get_db),
):
    return await _complete(
        db,
        create_facility_booking(
            db,
            tenant_slug=tenant_slug,
            location_slug=body.location_slug,
            resource_id=body.resource_id,
            offering_id=body.offering_id,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            quantity=body.quantity,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
            guest_name=body.guest.name,
            guest_email=body.guest.email,
            guest_phone=body.guest.phone,
        ),
    )


@router.post(
    "/public/{tenant_slug}/bookings/recreation/programmes",
    response_model=BookingOut,
    status_code=201,
)
async def reserve_recreation_programme(
    tenant_slug: str,
    body: ProgrammeEnrolmentIn,
    db: AsyncSession = Depends(get_db),
):
    return await _complete(
        db,
        enrol_in_programme(
            db,
            tenant_slug=tenant_slug,
            location_slug=body.location_slug,
            programme_id=body.programme_id,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
            guest_name=body.guest.name,
            guest_email=body.guest.email,
            guest_phone=body.guest.phone,
        ),
    )


@router.post(
    "/public/{tenant_slug}/memberships",
    response_model=MembershipOut,
    status_code=201,
)
async def buy_membership(
    tenant_slug: str,
    body: MembershipPurchaseIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        created = await purchase_membership(
            db,
            tenant_slug=tenant_slug,
            location_slug=body.location_slug,
            plan_id=body.plan_id,
            starts_on=body.starts_on,
            auto_renew=body.auto_renew,
            guest_name=body.guest.name,
            guest_email=body.guest.email,
            guest_phone=body.guest.phone,
        )
        tenant = await _tenant(db, tenant_slug)
        checkout_url = None
        payment_status = "not_required"
        if created.plan.price > 0:
            gateway = StripeGateway()
            payment_status = "pay_at_facility"
            if gateway.configured:
                checkout = await gateway.create_checkout(
                    CheckoutRequest(
                        tenant_id=tenant.id,
                        reference=created.membership.reference,
                        amount=created.plan.price,
                        currency=tenant.currency,
                        return_url=(
                            f"{settings.PUBLIC_URL.rstrip('/')}/book/{tenant.slug}"
                            "?payment=return"
                        ),
                    )
                )
                payment = PaymentTransaction(
                    tenant_id=tenant.id,
                    guest_id=created.membership.guest_id,
                    membership_id=created.membership.id,
                    provider=checkout.provider,
                    external_id=checkout.external_id,
                    status="pending",
                    amount=created.plan.price,
                    currency=tenant.currency,
                    metadata_json={"checkout_url": checkout.checkout_url},
                )
                db.add(payment)
                checkout_url = checkout.checkout_url
                payment_status = "pending"
        await db.commit()
        await db.refresh(created.membership)
        return MembershipOut(
            id=created.membership.id,
            reference=created.membership.reference,
            plan_id=created.membership.plan_id,
            status=created.membership.status,
            starts_on=created.membership.starts_on,
            ends_on=created.membership.ends_on,
            visits_remaining=created.membership.visits_remaining,
            currency=tenant.currency,
            amount_due=created.plan.price,
            payment_status=payment_status,
            checkout_url=checkout_url,
        )
    except BookingError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PaymentUnavailable as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/public/bookings/checkout", response_model=CheckoutOut)
async def checkout_booking(
    body: BookingCheckoutIn,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(body.manage_token.encode()).hexdigest()
    booking = (
        await db.execute(
            select(Booking).where(Booking.manage_token_hash == token_hash)
        )
    ).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in {"pending", "confirmed"} or booking.total <= 0:
        raise HTTPException(status_code=409, detail="Booking does not require payment")
    existing = (
        await db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.booking_id == booking.id,
                PaymentTransaction.status == "pending",
            )
        )
    ).scalars().first()
    if existing and existing.metadata_json.get("checkout_url"):
        return CheckoutOut(
            payment_id=existing.id,
            provider=existing.provider,
            status=existing.status,
            checkout_url=existing.metadata_json["checkout_url"],
        )
    gateway = StripeGateway()
    try:
        checkout = await gateway.create_checkout(
            CheckoutRequest(
                tenant_id=booking.tenant_id,
                reference=booking.public_reference,
                amount=booking.total,
                currency=booking.currency,
                return_url=(
                    f"{settings.PUBLIC_URL.rstrip('/')}/manage/{body.manage_token}"
                    "?payment=return"
                ),
            )
        )
    except PaymentUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    payment = PaymentTransaction(
        tenant_id=booking.tenant_id,
        guest_id=booking.guest_id,
        booking_id=booking.id,
        provider=checkout.provider,
        external_id=checkout.external_id,
        status="pending",
        amount=booking.total,
        currency=booking.currency,
        metadata_json={"checkout_url": checkout.checkout_url},
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return CheckoutOut(
        payment_id=payment.id,
        provider=payment.provider,
        status=payment.status,
        checkout_url=checkout.checkout_url,
    )


@router.post("/payments/stripe/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    if not verify_stripe_signature(
        payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    try:
        event = json.loads(payload)
        event_type = event["type"]
        session = event["data"]["object"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe event") from exc
    payment = (
        await db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.provider == "stripe",
                PaymentTransaction.external_id == str(session.get("id", "")),
            )
        )
    ).scalar_one_or_none()
    if payment:
        paid_event = event_type == "checkout.session.async_payment_succeeded" or (
            event_type == "checkout.session.completed"
            and session.get("payment_status") in {"paid", "no_payment_required"}
        )
        if paid_event:
            payment.status = "paid"
            payment.payment_method = "online"
            if payment.membership_id:
                membership = await db.get(CustomerMembership, payment.membership_id)
                if membership and membership.status == "pending":
                    membership.status = "active"
        elif event_type in {
            "checkout.session.expired",
            "checkout.session.async_payment_failed",
        }:
            payment.status = "failed"
        await db.commit()
    return {"received": True}


@router.post("/tenants/{tenant_slug}/attendance", status_code=201)
async def record_attendance(
    tenant_slug: str,
    body: AttendanceIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    tenant = await _tenant(db, tenant_slug)
    await _require_admin(db, tenant, user)
    location = await db.get(Location, body.location_id)
    guest = await db.get(Guest, body.guest_id)
    if not location or location.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Location not found")
    if not guest or guest.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Customer not found")
    membership = None
    if body.membership_id:
        membership = await db.get(CustomerMembership, body.membership_id)
        today = datetime.date.today()
        if (
            not membership
            or membership.tenant_id != tenant.id
            or membership.guest_id != guest.id
            or membership.status != "active"
            or membership.starts_on > today
            or (membership.ends_on and membership.ends_on < today)
        ):
            raise HTTPException(status_code=409, detail="Membership is not valid")
        if (
            body.status in {"checked_in", "attended"}
            and membership.visits_remaining is not None
        ):
            if membership.visits_remaining < 1:
                raise HTTPException(status_code=409, detail="No membership visits remain")
            membership.visits_remaining -= 1
    if body.programme_id:
        programme = await db.get(RecreationProgramme, body.programme_id)
        if (
            not programme
            or programme.tenant_id != tenant.id
            or programme.location_id != location.id
        ):
            raise HTTPException(status_code=409, detail="Programme is invalid")
    enrolment = None
    if body.enrolment_id:
        enrolment = await db.get(ProgrammeEnrolment, body.enrolment_id)
        if (
            not enrolment
            or enrolment.tenant_id != tenant.id
            or enrolment.guest_id != guest.id
            or enrolment.programme_id != body.programme_id
        ):
            raise HTTPException(status_code=409, detail="Programme enrolment is invalid")
        if body.status in {"checked_in", "attended"}:
            enrolment.attended_sessions += 1
    attendance = AttendanceRecord(
        tenant_id=tenant.id,
        location_id=location.id,
        guest_id=guest.id,
        programme_id=body.programme_id,
        enrolment_id=body.enrolment_id,
        membership_id=body.membership_id,
        status=body.status,
        source=body.source,
        notes=body.notes,
    )
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)
    return {"id": attendance.id, "status": attendance.status}


@router.post("/tenants/{tenant_slug}/payments/onsite", status_code=201)
async def record_onsite_payment(
    tenant_slug: str,
    body: OnsitePaymentIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    tenant = await _tenant(db, tenant_slug)
    await _require_admin(db, tenant, user)
    if (body.booking_id is None) == (body.membership_id is None):
        raise HTTPException(
            status_code=422,
            detail="Provide either booking_id or membership_id",
        )
    booking = await db.get(Booking, body.booking_id) if body.booking_id else None
    membership = (
        await db.get(CustomerMembership, body.membership_id)
        if body.membership_id
        else None
    )
    if booking and booking.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if membership and membership.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Membership not found")
    if body.booking_id and not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if body.membership_id and not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    if body.refunded_amount > body.amount:
        raise HTTPException(
            status_code=422,
            detail="Refunded amount cannot exceed payment amount",
        )
    status = "refunded" if body.refunded_amount == body.amount else "paid"
    payment = PaymentTransaction(
        tenant_id=tenant.id,
        guest_id=booking.guest_id if booking else membership.guest_id,
        booking_id=booking.id if booking else None,
        membership_id=membership.id if membership else None,
        provider="onsite",
        external_id=f"onsite-{secrets.token_hex(12)}",
        status=status,
        amount=body.amount,
        refunded_amount=body.refunded_amount,
        currency=tenant.currency,
        payment_method=body.payment_method,
    )
    if membership and membership.status == "pending":
        membership.status = "active"
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return {
        "id": payment.id,
        "status": payment.status,
        "amount": str(payment.amount),
        "refunded_amount": str(payment.refunded_amount),
        "currency": payment.currency,
        "payment_method": payment.payment_method,
    }


@router.get("/tenants/{tenant_slug}/reports/financial")
async def financial_report(
    tenant_slug: str,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    tenant = await _tenant(db, tenant_slug)
    await _require_admin(db, tenant, user)
    if date_from and date_to and date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to must be on or after date_from")
    start = datetime.datetime.combine(
        date_from or datetime.date.today().replace(day=1),
        datetime.time.min,
        datetime.timezone.utc,
    )
    end = datetime.datetime.combine(
        (date_to or datetime.date.today()) + datetime.timedelta(days=1),
        datetime.time.min,
        datetime.timezone.utc,
    )
    payments = (
        await db.execute(
            select(
                PaymentTransaction.status,
                func.count(PaymentTransaction.id),
                func.coalesce(func.sum(PaymentTransaction.amount), 0),
                func.coalesce(func.sum(PaymentTransaction.refunded_amount), 0),
            )
            .where(
                PaymentTransaction.tenant_id == tenant.id,
                PaymentTransaction.occurred_at >= start,
                PaymentTransaction.occurred_at < end,
            )
            .group_by(PaymentTransaction.status)
        )
    ).all()
    bookings = (
        await db.execute(
            select(func.count(Booking.id), func.coalesce(func.sum(Booking.total), 0))
            .where(
                Booking.tenant_id == tenant.id,
                Booking.created_at >= start,
                Booking.created_at < end,
                Booking.status.not_in(("cancelled", "failed")),
            )
        )
    ).one()
    attendance_count = (
        await db.execute(
            select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.tenant_id == tenant.id,
                AttendanceRecord.occurred_at >= start,
                AttendanceRecord.occurred_at < end,
                AttendanceRecord.status.in_(("checked_in", "attended")),
            )
        )
    ).scalar_one()
    return {
        "currency": tenant.currency,
        "period": {"from": start.date(), "to": (end - datetime.timedelta(days=1)).date()},
        "bookings": {"count": bookings[0], "gross_value": str(bookings[1])},
        "payments": [
            {
                "status": status,
                "count": count,
                "gross": str(gross),
                "refunded": str(refunded),
                "net": str(Decimal(gross) - Decimal(refunded)),
            }
            for status, count, gross, refunded in payments
        ],
        "visits": attendance_count,
    }
    AttendanceRecord,
    Booking,
    CustomerMembership,
    Guest,
    PaymentTransaction,
    ProgrammeEnrolment,
    RecreationProgramme,
    FacilityBookingIn,
    MembershipOut,
    MembershipPurchaseIn,
    ProgrammeEnrolmentIn,
    create_facility_booking,
