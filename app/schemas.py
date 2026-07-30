from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ── Restaurants ──────────────────────────────────────────────────────────
class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    about: str = ""
    phone_number: str = ""
    available: bool = True
    city: str = ""
    country: str = ""
    zipcode: str = ""
    logo: Optional[str] = None
    back_image: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None


class RestaurantDetail(RestaurantOut):
    products: list[ProductOut] = []
    hours: list[RestaurantHoursOut] = []


# ── Restaurant Hours ─────────────────────────────────────────────────────
class RestaurantHoursOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    week_day: int
    from_hour: Optional[datetime.time] = None
    to_hour: Optional[datetime.time] = None
    work: bool = False


class RestaurantHoursUpdate(BaseModel):
    week_day: int
    from_hour: Optional[str] = None
    to_hour: Optional[str] = None
    work: bool = False


# ── Products ─────────────────────────────────────────────────────────────
class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    name: str
    description: str = ""
    image: Optional[str] = None
    current_price: Decimal
    old_price: Decimal
    quantity: int
    meals: bool = False
    pastries: bool = False
    drinks: bool = False
    bread: bool = False
    groceries: bool = False
    vegetarian: bool = False
    vegan: bool = False
    lactose_free: bool = False
    gluten_free: bool = False
    allergen: str = ""


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    image: Optional[str] = None
    current_price: Decimal
    old_price: Decimal
    quantity: int = 1
    meals: bool = False
    pastries: bool = False
    drinks: bool = False
    bread: bool = False
    groceries: bool = False
    vegetarian: bool = False
    vegan: bool = False
    lactose_free: bool = False
    gluten_free: bool = False
    allergen: str = ""


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    current_price: Optional[Decimal] = None
    old_price: Optional[Decimal] = None
    quantity: Optional[int] = None
    meals: Optional[bool] = None
    pastries: Optional[bool] = None
    drinks: Optional[bool] = None
    bread: Optional[bool] = None
    groceries: Optional[bool] = None
    vegetarian: Optional[bool] = None
    vegan: Optional[bool] = None
    lactose_free: Optional[bool] = None
    gluten_free: Optional[bool] = None
    allergen: Optional[str] = None


# ── Orders ───────────────────────────────────────────────────────────────
class OrderProductIn(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    restaurant_id: int
    products: list[OrderProductIn]
    pickup_time: Optional[str] = None
    customer_message: Optional[str] = None


class OrderProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    quantity: int
    old_price: Decimal
    current_price: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    restaurant_id: Optional[int] = None
    number_order: Optional[int] = None
    amount: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    status: str = "new"
    date: Optional[datetime.datetime] = None
    pickup_time: Optional[str] = None
    customer_message: Optional[str] = None
    products: list[OrderProductOut] = []


class OrderStatusUpdate(BaseModel):
    status: str  # accepted | refused | done


# ── Cart ─────────────────────────────────────────────────────────────────
class CartData(BaseModel):
    data: list[Any]


class CartItem(BaseModel):
    restaurant_id: int
    product_id: int
    quantity: int


class CartUpdate(BaseModel):
    items: list[CartItem]


# ── Favorites ────────────────────────────────────────────────────────────
class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_id: int
    restaurant: RestaurantOut


class FavoriteAdd(BaseModel):
    restaurant_id: int


# ── Info ─────────────────────────────────────────────────────────────────
class ContactUsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    phone: str


class UserAgreementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    commission: int


class PrivacyPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


# Rebuild forward refs now that all models exist
RestaurantDetail.model_rebuild()
