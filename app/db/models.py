from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Sequence,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db.base import Base

SCHEMA = settings.DB_SCHEMA

order_number_seq = Sequence("order_number_seq", schema=SCHEMA)


# ── Users ────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    username: Mapped[str] = mapped_column(String(300), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(50), default="user")  # user | restaurant
    phone_number: Mapped[str] = mapped_column(String(30), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    registered: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    restaurant: Mapped[Optional[Restaurant]] = relationship(back_populates="user", uselist=False)
    orders: Mapped[list[Order]] = relationship(back_populates="user")
    cart: Mapped[Optional[UserCart]] = relationship(back_populates="user", uselist=False)
    favorites: Mapped[list[UserFavoriteRestaurant]] = relationship(back_populates="user")


# ── Restaurants ──────────────────────────────────────────────────────────
class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey(f"{SCHEMA}.users.id"))
    name: Mapped[str] = mapped_column(String(200), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), default=None)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), default=None)
    about: Mapped[str] = mapped_column(Text, default="")
    phone_number: Mapped[str] = mapped_column(String(30), default="")
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    city: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    zipcode: Mapped[str] = mapped_column(String(30), default="")
    logo: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    back_image: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    email: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    site: Mapped[Optional[str]] = mapped_column(String(500), default=None)

    # relationships
    user: Mapped[Optional[User]] = relationship(back_populates="restaurant")
    hours: Mapped[list[RestaurantHours]] = relationship(back_populates="restaurant")
    products: Mapped[list[Product]] = relationship(back_populates="restaurant")
    orders: Mapped[list[Order]] = relationship(back_populates="restaurant")
    favorites: Mapped[list[UserFavoriteRestaurant]] = relationship(back_populates="restaurant")


# ── Restaurant Hours ─────────────────────────────────────────────────────
class RestaurantHours(Base):
    __tablename__ = "restaurant_hours"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.restaurants.id"))
    week_day: Mapped[int] = mapped_column(SmallInteger)  # 0=Mon … 6=Sun
    from_hour: Mapped[Optional[datetime.time]] = mapped_column(Time, default=None)
    to_hour: Mapped[Optional[datetime.time]] = mapped_column(Time, default=None)
    work: Mapped[bool] = mapped_column(Boolean, default=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="hours")


# ── Products ─────────────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.restaurants.id"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    # categories
    meals: Mapped[bool] = mapped_column(Boolean, default=False)
    pastries: Mapped[bool] = mapped_column(Boolean, default=False)
    drinks: Mapped[bool] = mapped_column(Boolean, default=False)
    bread: Mapped[bool] = mapped_column(Boolean, default=False)
    groceries: Mapped[bool] = mapped_column(Boolean, default=False)
    # dietary
    vegetarian: Mapped[bool] = mapped_column(Boolean, default=False)
    vegan: Mapped[bool] = mapped_column(Boolean, default=False)
    lactose_free: Mapped[bool] = mapped_column(Boolean, default=False)
    gluten_free: Mapped[bool] = mapped_column(Boolean, default=False)
    allergen: Mapped[str] = mapped_column(Text, default="")

    restaurant: Mapped[Restaurant] = relationship(back_populates="products")

    @property
    def discount_pct(self) -> float:
        if self.current_price and self.old_price and self.old_price > 0:
            return round(float((1 - self.current_price / self.old_price) * 100))
        return 0


# ── Orders ───────────────────────────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.users.id"))
    restaurant_id: Mapped[Optional[int]] = mapped_column(ForeignKey(f"{SCHEMA}.restaurants.id"))
    number_order: Mapped[Optional[int]] = mapped_column(
        Integer, order_number_seq, server_default=order_number_seq.next_value(), unique=True
    )
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    final_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), default="new")
    date: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    to_hour: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    commission: Mapped[Optional[int]] = mapped_column(SmallInteger)
    pickup_time: Mapped[Optional[str]] = mapped_column(String(200))
    customer_message: Mapped[Optional[str]] = mapped_column(String(200))

    user: Mapped[User] = relationship(back_populates="orders")
    restaurant: Mapped[Optional[Restaurant]] = relationship(back_populates="orders")
    products: Mapped[list[OrderProduct]] = relationship(back_populates="order")


# ── Order Products ───────────────────────────────────────────────────────
class OrderProduct(Base):
    __tablename__ = "order_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.orders.id"))
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(f"{SCHEMA}.products.id"), default=None
    )
    product_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="products")


# ── Codes ────────────────────────────────────────────────────────────────
class Code(Base):
    __tablename__ = "codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(10), unique=True)
    start_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    discount: Mapped[int] = mapped_column(Integer, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    free_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    quantity: Mapped[Optional[int]] = mapped_column(SmallInteger, default=1)
    used_by: Mapped[str] = mapped_column(Text, default="")


# ── User Cart ────────────────────────────────────────────────────────────
class UserCart(Base):
    __tablename__ = "user_carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.users.id"), unique=True)
    data: Mapped[Any] = mapped_column(JSON, default=list)

    user: Mapped[User] = relationship(back_populates="cart")


# ── User Favorite Restaurants ────────────────────────────────────────────
class UserFavoriteRestaurant(Base):
    __tablename__ = "user_favorite_restaurants"
    __table_args__ = (
        UniqueConstraint("user_id", "restaurant_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.restaurants.id"))

    user: Mapped[User] = relationship(back_populates="favorites")
    restaurant: Mapped[Restaurant] = relationship(back_populates="favorites")


# ── Contact Us ───────────────────────────────────────────────────────────
class ContactUs(Base):
    __tablename__ = "contact_us"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")


# ── User Agreements ──────────────────────────────────────────────────────
class UserAgreement(Base):
    __tablename__ = "user_agreements"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, default="")
    commission: Mapped[int] = mapped_column(SmallInteger, default=0)


# ── Privacy Policy ───────────────────────────────────────────────────────
class PrivacyPolicy(Base):
    __tablename__ = "privacy_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, default="")
