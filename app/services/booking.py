"""Transaction-safe booking strategies for all FastBooking product modules."""

from __future__ import annotations

import datetime
import hashlib
import os
import secrets
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.platform_models import (
    Booking,
    BookingAllocation,
    ClinicConnector,
    Guest,
    HotelNightInventory,
    HotelRoomType,
    Location,
    NotificationOutbox,
    Offering,
    Resource,
    ScheduledEvent,
    Tenant,
    TenantModule,
    TicketType,
    TrialEntitlement,
    UsageEvent,
)

ACTIVE_BOOKING_STATUSES = ("pending", "confirmed")


class BookingError(ValueError):
    """A safe, user-facing booking validation or availability error."""


@dataclass(frozen=True)
class BookingResult:
    booking: Booking
    manage_token: str


def nights_between(
    check_in: datetime.date, check_out: datetime.date
) -> list[datetime.date]:
    """Return occupied hotel nights for a half-open stay range."""
    if check_out <= check_in:
        raise BookingError("Check-out must be after check-in")
    return [
        check_in + datetime.timedelta(days=offset)
        for offset in range((check_out - check_in).days)
    ]


def validate_time_range(
    starts_at: datetime.datetime, ends_at: datetime.datetime
) -> None:
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        raise BookingError("Booking times must include a timezone")
    if ends_at <= starts_at:
        raise BookingError("Booking end must be after its start")


def _reference() -> str:
    return f"FB-{secrets.token_hex(4).upper()}"


def _manage_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


async def _tenant_context(
    db: AsyncSession, tenant_slug: str, module: str, location_slug: str
) -> tuple[Tenant, Location]:
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalar_one_or_none()
    if not tenant or tenant.status in {"suspended", "closed"}:
        raise BookingError("Booking business is unavailable")
    trial = (
        await db.execute(
            select(TrialEntitlement).where(TrialEntitlement.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()
    now = datetime.datetime.now(datetime.timezone.utc)
    if (
        tenant.status == "trial"
        and trial
        and trial.ends_at < now
        and not trial.manually_activated
    ):
        raise BookingError("This workspace trial has ended")

    result = await db.execute(
        select(TenantModule).where(
            TenantModule.tenant_id == tenant.id,
            TenantModule.module == module,
            TenantModule.enabled.is_(True),
        )
    )
    if not result.scalar_one_or_none():
        raise BookingError(f"{module.title()} bookings are not enabled")

    result = await db.execute(
        select(Location).where(
            Location.tenant_id == tenant.id,
            Location.slug == location_slug,
            Location.active.is_(True),
        )
    )
    location = result.scalar_one_or_none()
    if not location:
        raise BookingError("Booking location not found")
    return tenant, location


async def _guest(
    db: AsyncSession,
    tenant_id: int,
    *,
    name: str,
    email: str,
    phone: str = "",
) -> Guest:
    guest = Guest(
        tenant_id=tenant_id,
        name=name.strip()[:160],
        email=email.strip().lower()[:320],
        phone=phone.strip()[:40],
    )
    if not guest.name or "@" not in guest.email:
        raise BookingError("A valid guest name and email are required")
    db.add(guest)
    await db.flush()
    return guest


async def _base_booking(
    db: AsyncSession,
    *,
    tenant: Tenant,
    location: Location,
    guest: Guest,
    module: str,
    starts_at: datetime.datetime,
    ends_at: datetime.datetime,
    offering_id: int | None = None,
    quantity: int = 1,
    party_size: int | None = None,
    subtotal: Decimal = Decimal("0"),
    total: Decimal = Decimal("0"),
    notes: str = "",
    idempotency_key: str | None = None,
    external_provider: str | None = None,
    external_id: str | None = None,
    booking_metadata: dict[str, Any] | None = None,
) -> BookingResult:
    validate_time_range(starts_at, ends_at)
    token, token_hash = _manage_token()
    booking = Booking(
        tenant_id=tenant.id,
        location_id=location.id,
        guest_id=guest.id,
        offering_id=offering_id,
        module=module,
        public_reference=_reference(),
        idempotency_key=idempotency_key,
        status="confirmed",
        starts_at=starts_at,
        ends_at=ends_at,
        quantity=quantity,
        party_size=party_size,
        currency=tenant.currency,
        subtotal=subtotal,
        total=total,
        manage_token_hash=token_hash,
        external_provider=external_provider,
        external_id=external_id,
        notes=notes[:2000],
        booking_metadata=booking_metadata or {},
    )
    db.add(booking)
    await db.flush()
    db.add(
        UsageEvent(
            tenant_id=tenant.id,
            kind="booking",
            source_type=module,
            source_id=str(booking.id),
        )
    )
    if guest.email:
        db.add(
            NotificationOutbox(
                tenant_id=tenant.id,
                booking_id=booking.id,
                template="booking_confirmation",
                recipient=guest.email,
                payload={
                    "reference": booking.public_reference,
                    "tenant": tenant.name,
                    "module": module,
                    "manage_token": token,
                },
                send_after=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        reminder_at = starts_at - datetime.timedelta(hours=24)
        if reminder_at > datetime.datetime.now(datetime.timezone.utc):
            db.add(
                NotificationOutbox(
                    tenant_id=tenant.id,
                    booking_id=booking.id,
                    template="booking_reminder",
                    recipient=guest.email,
                    payload={
                        "reference": booking.public_reference,
                        "tenant": tenant.name,
                        "module": module,
                        "manage_token": token,
                    },
                    send_after=reminder_at,
                )
            )
    return BookingResult(booking=booking, manage_token=token)


async def cancel_booking(db: AsyncSession, manage_token: str) -> Booking:
    """Cancel a booking and restore counted inventory under row locks."""
    token_hash = hashlib.sha256(manage_token.encode()).hexdigest()
    booking = (
        await db.execute(
            select(Booking)
            .where(Booking.manage_token_hash == token_hash)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not booking:
        raise BookingError("Booking management link is invalid")
    if booking.status == "cancelled":
        return booking
    if booking.status not in ACTIVE_BOOKING_STATUSES:
        raise BookingError("This booking can no longer be cancelled")

    if booking.module == "hotel":
        room_type_id = int(booking.booking_metadata["room_type_id"])
        nights = nights_between(
            datetime.date.fromisoformat(booking.booking_metadata["check_in"]),
            datetime.date.fromisoformat(booking.booking_metadata["check_out"]),
        )
        inventory = (
            await db.execute(
                select(HotelNightInventory)
                .where(
                    HotelNightInventory.tenant_id == booking.tenant_id,
                    HotelNightInventory.room_type_id == room_type_id,
                    HotelNightInventory.night.in_(nights),
                )
                .with_for_update()
            )
        ).scalars()
        for row in inventory:
            row.reserved = max(0, row.reserved - booking.quantity)
    elif booking.module == "events":
        ticket_type_id = int(booking.booking_metadata["ticket_type_id"])
        ticket = (
            await db.execute(
                select(TicketType)
                .where(
                    TicketType.id == ticket_type_id,
                    TicketType.tenant_id == booking.tenant_id,
                )
                .with_for_update()
            )
        ).scalar_one()
        ticket.reserved = max(0, ticket.reserved - booking.quantity)
    elif booking.module == "clinic" and booking.external_id:
        connector = (
            await db.execute(
                select(ClinicConnector).where(
                    ClinicConnector.tenant_id == booking.tenant_id,
                    ClinicConnector.location_id == booking.location_id,
                    ClinicConnector.enabled.is_(True),
                )
            )
        ).scalar_one_or_none()
        if not connector:
            raise BookingError("Clinic integration is unavailable")
        secret = os.getenv(connector.secret_env_name, "")
        if not secret:
            raise BookingError("Clinic integration is not configured")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{connector.base_url.rstrip('/')}/api/v1/external/appointments/"
                f"{booking.external_id}/cancel",
                headers={"Authorization": f"Bearer {secret}"},
            )
        if response.status_code >= 400:
            raise BookingError("Clinic cancellation could not be completed")

    booking.status = "cancelled"
    db.add(
        UsageEvent(
            tenant_id=booking.tenant_id,
            kind="booking_cancelled",
            source_type=booking.module,
            source_id=str(booking.id),
        )
    )
    guest = await db.get(Guest, booking.guest_id)
    if guest and guest.email:
        db.add(
            NotificationOutbox(
                tenant_id=booking.tenant_id,
                booking_id=booking.id,
                template="booking_cancelled",
                recipient=guest.email,
                payload={"reference": booking.public_reference},
                send_after=datetime.datetime.now(datetime.timezone.utc),
            )
        )
    return booking


async def create_restaurant_reservation(
    db: AsyncSession,
    *,
    tenant_slug: str,
    location_slug: str,
    guest_name: str,
    guest_email: str,
    guest_phone: str = "",
    starts_at: datetime.datetime,
    party_size: int,
    duration_minutes: int = 90,
    notes: str = "",
    idempotency_key: str | None = None,
) -> BookingResult:
    if party_size < 1:
        raise BookingError("Party size must be at least one")
    tenant, location = await _tenant_context(
        db, tenant_slug, "restaurant", location_slug
    )
    ends_at = starts_at + datetime.timedelta(minutes=duration_minutes)
    validate_time_range(starts_at, ends_at)

    result = await db.execute(
        select(Resource)
        .where(
            Resource.tenant_id == tenant.id,
            Resource.location_id == location.id,
            Resource.module == "restaurant",
            Resource.resource_type == "table",
            Resource.active.is_(True),
            Resource.capacity >= party_size,
        )
        .order_by(Resource.capacity, Resource.id)
        .with_for_update(skip_locked=True)
    )
    candidates = result.scalars().all()
    selected: Resource | None = None
    for resource in candidates:
        conflict = await db.execute(
            select(BookingAllocation.id)
            .join(Booking, Booking.id == BookingAllocation.booking_id)
            .where(
                BookingAllocation.resource_id == resource.id,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
                BookingAllocation.starts_at < ends_at,
                BookingAllocation.ends_at > starts_at,
            )
            .limit(1)
        )
        if conflict.scalar_one_or_none() is None:
            selected = resource
            break
    if not selected:
        raise BookingError("No table is available for that party and time")

    guest = await _guest(
        db,
        tenant.id,
        name=guest_name,
        email=guest_email,
        phone=guest_phone,
    )
    created = await _base_booking(
        db,
        tenant=tenant,
        location=location,
        guest=guest,
        module="restaurant",
        starts_at=starts_at,
        ends_at=ends_at,
        party_size=party_size,
        notes=notes,
        idempotency_key=idempotency_key,
        booking_metadata={"fulfillment": "dine_in"},
    )
    db.add(
        BookingAllocation(
            tenant_id=tenant.id,
            booking_id=created.booking.id,
            resource_id=selected.id,
            starts_at=starts_at,
            ends_at=ends_at,
            quantity=1,
        )
    )
    return created


async def create_hotel_booking(
    db: AsyncSession,
    *,
    tenant_slug: str,
    location_slug: str,
    room_type_id: int,
    guest_name: str,
    guest_email: str,
    guest_phone: str = "",
    check_in: datetime.date,
    check_out: datetime.date,
    rooms: int = 1,
    notes: str = "",
    idempotency_key: str | None = None,
) -> BookingResult:
    if rooms < 1:
        raise BookingError("At least one room is required")
    tenant, location = await _tenant_context(db, tenant_slug, "hotel", location_slug)
    result = await db.execute(
        select(HotelRoomType)
        .where(
            HotelRoomType.id == room_type_id,
            HotelRoomType.tenant_id == tenant.id,
            HotelRoomType.location_id == location.id,
            HotelRoomType.active.is_(True),
        )
        .with_for_update()
    )
    room_type = result.scalar_one_or_none()
    if not room_type:
        raise BookingError("Room type not found")

    nights = nights_between(check_in, check_out)
    result = await db.execute(
        select(HotelNightInventory)
        .where(
            HotelNightInventory.tenant_id == tenant.id,
            HotelNightInventory.room_type_id == room_type.id,
            HotelNightInventory.night.in_(nights),
        )
        .order_by(HotelNightInventory.night)
        .with_for_update()
    )
    inventory = {row.night: row for row in result.scalars().all()}
    total = Decimal("0")
    for night in nights:
        row = inventory.get(night)
        capacity = row.capacity if row else room_type.units
        reserved = row.reserved if row else 0
        if (row and row.closed) or reserved + rooms > capacity:
            raise BookingError(f"Room type is unavailable on {night.isoformat()}")
        rate = row.rate if row else room_type.nightly_rate
        total += rate * rooms
        if row:
            row.reserved += rooms
        else:
            new_row = HotelNightInventory(
                tenant_id=tenant.id,
                room_type_id=room_type.id,
                night=night,
                capacity=room_type.units,
                reserved=rooms,
                rate=room_type.nightly_rate,
            )
            db.add(new_row)

    timezone = datetime.timezone.utc
    starts_at = datetime.datetime.combine(check_in, datetime.time(15), timezone)
    ends_at = datetime.datetime.combine(check_out, datetime.time(11), timezone)
    guest = await _guest(
        db,
        tenant.id,
        name=guest_name,
        email=guest_email,
        phone=guest_phone,
    )
    return await _base_booking(
        db,
        tenant=tenant,
        location=location,
        guest=guest,
        module="hotel",
        offering_id=room_type.offering_id,
        starts_at=starts_at,
        ends_at=ends_at,
        quantity=rooms,
        subtotal=total,
        total=total,
        notes=notes,
        idempotency_key=idempotency_key,
        booking_metadata={
            "room_type_id": room_type.id,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
        },
    )


async def create_event_booking(
    db: AsyncSession,
    *,
    tenant_slug: str,
    location_slug: str,
    ticket_type_id: int,
    guest_name: str,
    guest_email: str,
    guest_phone: str = "",
    quantity: int = 1,
    notes: str = "",
    idempotency_key: str | None = None,
) -> BookingResult:
    tenant, location = await _tenant_context(db, tenant_slug, "events", location_slug)
    result = await db.execute(
        select(TicketType, ScheduledEvent)
        .join(ScheduledEvent, ScheduledEvent.id == TicketType.event_id)
        .where(
            TicketType.id == ticket_type_id,
            TicketType.tenant_id == tenant.id,
            ScheduledEvent.location_id == location.id,
            TicketType.active.is_(True),
        )
        .with_for_update()
    )
    row = result.one_or_none()
    if not row:
        raise BookingError("Ticket type not found")
    ticket, event = row
    now = datetime.datetime.now(datetime.timezone.utc)
    if event.status != "published":
        raise BookingError("Event is not on sale")
    if event.sales_open_at and now < event.sales_open_at:
        raise BookingError("Ticket sales have not opened")
    if event.sales_close_at and now >= event.sales_close_at:
        raise BookingError("Ticket sales have closed")
    if quantity < 1 or quantity > ticket.max_per_booking:
        raise BookingError(f"Choose between 1 and {ticket.max_per_booking} tickets")
    if ticket.reserved + quantity > ticket.capacity:
        raise BookingError("Not enough tickets remain")
    ticket.reserved += quantity
    total = ticket.price * quantity
    guest = await _guest(
        db,
        tenant.id,
        name=guest_name,
        email=guest_email,
        phone=guest_phone,
    )
    return await _base_booking(
        db,
        tenant=tenant,
        location=location,
        guest=guest,
        module="events",
        offering_id=event.offering_id,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        quantity=quantity,
        subtotal=total,
        total=total,
        notes=notes,
        idempotency_key=idempotency_key,
        booking_metadata={
            "event_id": event.id,
            "ticket_type_id": ticket.id,
            "ticket_type": ticket.name,
        },
    )


async def _fastclinic_reserve(
    connector: ClinicConnector,
    *,
    practitioner_external_id: str,
    service_external_id: str,
    starts_at: datetime.datetime,
    guest_name: str,
    guest_email: str,
    guest_phone: str,
    notes: str,
    idempotency_key: str,
) -> dict[str, Any]:
    secret = os.getenv(connector.secret_env_name, "")
    if not secret:
        raise BookingError("Clinic integration is not configured")
    headers = {
        "Authorization": f"Bearer {secret}",
        "Idempotency-Key": idempotency_key,
    }
    payload = {
        "practitioner_id": practitioner_external_id,
        "service_id": service_external_id,
        "starts_at": starts_at.isoformat(),
        "guest": {
            "name": guest_name,
            "email": guest_email,
            "phone": guest_phone,
        },
        "notes": notes,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{connector.base_url.rstrip('/')}/api/v1/external/appointments",
            json=payload,
            headers=headers,
        )
    if response.status_code == 409:
        raise BookingError("That clinic time is no longer available")
    if response.status_code >= 400:
        raise BookingError("Clinic booking could not be completed")
    return response.json()


async def create_clinic_booking(
    db: AsyncSession,
    *,
    tenant_slug: str,
    location_slug: str,
    offering_id: int,
    practitioner_resource_id: int,
    guest_name: str,
    guest_email: str,
    guest_phone: str = "",
    starts_at: datetime.datetime,
    notes: str = "",
    idempotency_key: str | None = None,
) -> BookingResult:
    tenant, location = await _tenant_context(db, tenant_slug, "clinic", location_slug)
    result = await db.execute(
        select(Offering).where(
            Offering.id == offering_id,
            Offering.tenant_id == tenant.id,
            Offering.location_id == location.id,
            Offering.module == "clinic",
            Offering.active.is_(True),
        )
    )
    offering = result.scalar_one_or_none()
    result = await db.execute(
        select(Resource).where(
            Resource.id == practitioner_resource_id,
            Resource.tenant_id == tenant.id,
            Resource.location_id == location.id,
            Resource.module == "clinic",
            Resource.resource_type == "practitioner",
            Resource.active.is_(True),
        )
    )
    practitioner = result.scalar_one_or_none()
    result = await db.execute(
        select(ClinicConnector).where(
            ClinicConnector.tenant_id == tenant.id,
            ClinicConnector.location_id == location.id,
            ClinicConnector.enabled.is_(True),
        )
    )
    connector = result.scalar_one_or_none()
    if not offering or not practitioner or not connector:
        raise BookingError("Clinic booking configuration is incomplete")
    if not offering.duration_minutes:
        raise BookingError("Clinic service duration is not configured")
    if not offering.settings_json.get("external_id") or not practitioner.external_id:
        raise BookingError("Clinic service mapping is incomplete")

    key = idempotency_key or secrets.token_urlsafe(18)
    remote = await _fastclinic_reserve(
        connector,
        practitioner_external_id=practitioner.external_id,
        service_external_id=str(offering.settings_json["external_id"]),
        starts_at=starts_at,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        notes=notes,
        idempotency_key=key,
    )
    ends_at = datetime.datetime.fromisoformat(remote["ends_at"])
    guest = await _guest(
        db,
        tenant.id,
        name=guest_name,
        email=guest_email,
        phone=guest_phone,
    )
    return await _base_booking(
        db,
        tenant=tenant,
        location=location,
        guest=guest,
        module="clinic",
        offering_id=offering.id,
        starts_at=starts_at,
        ends_at=ends_at,
        notes=notes,
        idempotency_key=key,
        external_provider="fastclinic",
        external_id=str(remote["id"]),
        booking_metadata={"practitioner_resource_id": practitioner.id},
    )
