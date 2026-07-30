"""Tenant configuration, catalogue, and public booking API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_restaurant_user, get_db
from app.db.models import User
from app.db.platform_models import (
    PRODUCT_MODULES,
    HotelRoomType,
    Location,
    Membership,
    Offering,
    Resource,
    ScheduledEvent,
    Tenant,
    TenantModule,
    TicketType,
)
from app.platform_schemas import (
    BookingOut,
    ClinicBookingIn,
    EventBookingIn,
    HotelBookingIn,
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
    create_hotel_booking,
    create_restaurant_reservation,
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
            Membership.role.in_(("owner", "admin")),
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
    user: User = Depends(get_current_restaurant_user),
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
    user: User = Depends(get_current_restaurant_user),
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
