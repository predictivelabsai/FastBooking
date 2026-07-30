"""Tenant, booking, inventory, and SaaS models shared by every product module."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db.base import Base

SCHEMA = settings.DB_SCHEMA
PRODUCT_MODULES = ("restaurant", "hotel", "clinic", "events")


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('trial', 'active', 'suspended', 'closed')",
            name="ck_tenants_status",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="trial")
    timezone: Mapped[str] = mapped_column(String(80), default="Europe/Tallinn")
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    locale: Mapped[str] = mapped_column(String(20), default="en")
    accent_color: Mapped[str] = mapped_column(String(20), default="#0f766e")
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantModule(Base):
    """Admin-controlled product switches and module-level configuration."""

    __tablename__ = "tenant_modules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module", name="uq_tenant_modules_module"),
        CheckConstraint(
            "module IN ('restaurant', 'hotel', 'clinic', 'events')",
            name="ck_tenant_modules_module",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    module: Mapped[str] = mapped_column(String(30))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'staff', 'viewer')",
            name="ck_memberships_role",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), default="staff")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_locations_tenant_slug"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(255), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    timezone: Mapped[str] = mapped_column(String(80), default="Europe/Tallinn")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Guest(Base):
    __tablename__ = "guests"
    __table_args__ = (
        Index("ix_guests_tenant_email", "tenant_id", "email"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Offering(Base):
    """A sellable service, stay, dining experience, or ticketed experience."""

    __tablename__ = "offerings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_offerings_tenant_slug"),
        CheckConstraint(
            "module IN ('restaurant', 'hotel', 'clinic', 'events')",
            name="ck_offerings_module",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{SCHEMA}.locations.id", ondelete="CASCADE"), index=True
    )
    module: Mapped[str] = mapped_column(String(30), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    capacity: Mapped[Optional[int]] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Resource(Base):
    """A table, room, practitioner, venue section, or other allocatable unit."""

    __tablename__ = "resources"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "location_id", "slug", name="uq_resources_tenant_location_slug"
        ),
        CheckConstraint(
            "module IN ('restaurant', 'hotel', 'clinic', 'events')",
            name="ck_resources_module",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.locations.id", ondelete="CASCADE"), index=True
    )
    module: Mapped[str] = mapped_column(String(30), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    resource_type: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    external_id: Mapped[Optional[str]] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"
    __table_args__ = (
        CheckConstraint("week_day BETWEEN 0 AND 6", name="ck_availability_week_day"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.locations.id", ondelete="CASCADE"), index=True
    )
    offering_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{SCHEMA}.offerings.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{SCHEMA}.resources.id", ondelete="CASCADE"), index=True
    )
    week_day: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime.time] = mapped_column(Time)
    ends_at: Mapped[datetime.time] = mapped_column(Time)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=0)
    minimum_notice_minutes: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "public_reference", name="uq_bookings_tenant_reference"
        ),
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_bookings_tenant_idempotency"
        ),
        CheckConstraint(
            "module IN ('restaurant', 'hotel', 'clinic', 'events')",
            name="ck_bookings_module",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'completed', 'failed')",
            name="ck_bookings_status",
        ),
        Index("ix_bookings_tenant_time", "tenant_id", "starts_at", "ends_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.locations.id", ondelete="CASCADE"), index=True
    )
    guest_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.guests.id", ondelete="RESTRICT"), index=True
    )
    offering_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{SCHEMA}.offerings.id", ondelete="RESTRICT"), index=True
    )
    module: Mapped[str] = mapped_column(String(30), index=True)
    public_reference: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    starts_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    party_size: Mapped[Optional[int]] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    manage_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    external_provider: Mapped[Optional[str]] = mapped_column(String(50))
    external_id: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    booking_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BookingAllocation(Base):
    __tablename__ = "booking_allocations"
    __table_args__ = (
        Index(
            "ix_booking_allocations_resource_time",
            "resource_id",
            "starts_at",
            "ends_at",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    booking_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.bookings.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{SCHEMA}.resources.id", ondelete="RESTRICT"), index=True
    )
    starts_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    allocation_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class HotelRoomType(Base):
    __tablename__ = "hotel_room_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "location_id", "code", name="uq_room_types_code"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.locations.id", ondelete="CASCADE"), index=True
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.offerings.id", ondelete="CASCADE"), unique=True
    )
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    occupancy: Mapped[int] = mapped_column(Integer, default=2)
    units: Mapped[int] = mapped_column(Integer, default=1)
    nightly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class HotelNightInventory(Base):
    __tablename__ = "hotel_night_inventory"
    __table_args__ = (
        UniqueConstraint("room_type_id", "night", name="uq_room_inventory_night"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    room_type_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.hotel_room_types.id", ondelete="CASCADE"), index=True
    )
    night: Mapped[datetime.date] = mapped_column(Date, index=True)
    capacity: Mapped[int] = mapped_column(Integer)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    closed: Mapped[bool] = mapped_column(Boolean, default=False)


class ClinicConnector(Base):
    __tablename__ = "clinic_connectors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "location_id", name="uq_clinic_connector_location"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.locations.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="fastclinic")
    base_url: Mapped[str] = mapped_column(String(500))
    secret_env_name: Mapped[str] = mapped_column(String(120))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ScheduledEvent(Base):
    __tablename__ = "scheduled_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_scheduled_events_slug"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.locations.id", ondelete="CASCADE"), index=True
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.offerings.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(220))
    starts_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    ends_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    sales_open_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    sales_close_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    status: Mapped[str] = mapped_column(String(30), default="draft")


class TicketType(Base):
    __tablename__ = "ticket_types"
    __table_args__ = (
        UniqueConstraint("event_id", "code", name="uq_ticket_types_event_code"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.scheduled_events.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(160))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    capacity: Mapped[int] = mapped_column(Integer)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    max_per_booking: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TrialEntitlement(Base):
    __tablename__ = "trial_entitlements"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_trial_entitlements_tenant"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    plan_code: Mapped[str] = mapped_column(String(50), default="trial")
    starts_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    booking_limit: Mapped[Optional[int]] = mapped_column(Integer)
    order_limit: Mapped[Optional[int]] = mapped_column(Integer)
    enforcement: Mapped[str] = mapped_column(String(20), default="soft")
    manually_activated: Mapped[bool] = mapped_column(Boolean, default=False)


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        Index("ix_usage_events_tenant_kind_time", "tenant_id", "kind", "occurred_at"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    source_type: Mapped[str] = mapped_column(String(50), default="")
    source_id: Mapped[Optional[str]] = mapped_column(String(100))
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        Index("ix_notification_outbox_status_schedule", "status", "send_after"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey(f"{SCHEMA}.tenants.id", ondelete="CASCADE"), index=True
    )
    booking_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{SCHEMA}.bookings.id", ondelete="CASCADE"), index=True
    )
    template: Mapped[str] = mapped_column(String(80))
    recipient: Mapped[str] = mapped_column(String(320))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    send_after: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
