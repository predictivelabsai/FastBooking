"""API contracts for the tenant platform and public booking journeys."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GuestInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(default="", max_length=40)


class RestaurantReservationIn(BaseModel):
    location_slug: str
    guest: GuestInput
    starts_at: datetime.datetime
    party_size: int = Field(ge=1, le=50)
    duration_minutes: int = Field(default=90, ge=15, le=480)
    notes: str = Field(default="", max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=120)


class HotelBookingIn(BaseModel):
    location_slug: str
    room_type_id: int
    guest: GuestInput
    check_in: datetime.date
    check_out: datetime.date
    rooms: int = Field(default=1, ge=1, le=20)
    notes: str = Field(default="", max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=120)


class EventBookingIn(BaseModel):
    location_slug: str
    ticket_type_id: int
    guest: GuestInput
    quantity: int = Field(default=1, ge=1, le=50)
    notes: str = Field(default="", max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=120)


class ClinicBookingIn(BaseModel):
    location_slug: str
    offering_id: int
    practitioner_resource_id: int
    guest: GuestInput
    starts_at: datetime.datetime
    notes: str = Field(default="", max_length=2000)
    idempotency_key: str | None = Field(default=None, max_length=120)


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_reference: str
    module: str
    status: str
    starts_at: datetime.datetime
    ends_at: datetime.datetime
    quantity: int
    party_size: int | None
    currency: str
    total: Decimal
    manage_token: str


class TenantModuleUpdate(BaseModel):
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class TenantModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    module: str
    enabled: bool
    settings_json: dict[str, Any]
