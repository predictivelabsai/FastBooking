"""DataClient abstraction — DbClient (direct DB) vs HttpClient (REST calls)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.engine import async_session_factory
from app.db.models import (
    Order,
    OrderProduct,
    Product,
    Restaurant,
    User,
    UserCart,
    UserFavoriteRestaurant,
)


@runtime_checkable
class DataClient(Protocol):
    async def list_restaurants(self, q: str = "") -> list[dict]:
        ...

    async def get_restaurant(self, restaurant_id: int) -> dict | None:
        ...

    async def get_product(self, product_id: int) -> dict | None:
        ...

    async def get_cart(self, user_id: int) -> list[dict]:
        ...

    async def update_cart(self, user_id: int, items: list[dict]) -> list[dict]:
        ...

    async def clear_cart(self, user_id: int) -> list[dict]:
        ...

    async def create_order(self, user_id: int, data: dict) -> dict:
        ...

    async def list_orders(self, user_id: int) -> list[dict]:
        ...

    async def get_order(self, user_id: int, order_id: int) -> dict | None:
        ...

    async def list_favorites(self, user_id: int) -> list[dict]:
        ...

    async def add_favorite(self, user_id: int, restaurant_id: int) -> None:
        ...

    async def remove_favorite(self, user_id: int, restaurant_id: int) -> None:
        ...

    # admin
    async def admin_list_products(self, user_id: int) -> list[dict]:
        ...

    async def admin_create_product(self, user_id: int, data: dict) -> dict:
        ...

    async def admin_update_product(self, user_id: int, product_id: int, data: dict) -> dict:
        ...

    async def admin_delete_product(self, user_id: int, product_id: int) -> None:
        ...

    async def admin_list_orders(self, user_id: int) -> list[dict]:
        ...

    async def admin_update_order_status(self, user_id: int, order_id: int, status: str) -> dict:
        ...

    async def admin_get_restaurant(self, user_id: int) -> dict | None:
        ...

    async def admin_toggle_availability(self, user_id: int) -> dict:
        ...


# ── Helpers ──────────────────────────────────────────────────────────────
def _restaurant_to_dict(r: Restaurant) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "address": r.address,
        "latitude": float(r.latitude) if r.latitude else None,
        "longitude": float(r.longitude) if r.longitude else None,
        "about": r.about,
        "phone_number": r.phone_number,
        "available": r.available,
        "city": r.city,
        "country": r.country,
        "zipcode": r.zipcode,
        "logo": r.logo,
        "back_image": r.back_image,
    }


def _product_to_dict(p: Product) -> dict:
    return {
        "id": p.id,
        "restaurant_id": p.restaurant_id,
        "name": p.name,
        "description": p.description,
        "image": p.image,
        "current_price": str(p.current_price),
        "old_price": str(p.old_price),
        "quantity": p.quantity,
        "meals": p.meals,
        "pastries": p.pastries,
        "drinks": p.drinks,
        "bread": p.bread,
        "groceries": p.groceries,
        "vegetarian": p.vegetarian,
        "vegan": p.vegan,
        "lactose_free": p.lactose_free,
        "gluten_free": p.gluten_free,
        "allergen": p.allergen,
        "discount_pct": p.discount_pct,
    }


def _order_to_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "user_id": o.user_id,
        "restaurant_id": o.restaurant_id,
        "number_order": o.number_order,
        "amount": str(o.amount) if o.amount else "0",
        "final_price": str(o.final_price) if o.final_price else "0",
        "status": o.status,
        "date": o.date.isoformat() if o.date else None,
        "pickup_time": o.pickup_time,
        "customer_message": o.customer_message,
        "products": [
            {
                "id": op.id,
                "product_name": op.product_name,
                "quantity": op.quantity,
                "old_price": str(op.old_price),
                "current_price": str(op.current_price),
            }
            for op in o.products
        ],
    }


# ── DbClient ────────────────────────────────────────────────────────────
class DbClient:
    """Direct-to-DB implementation — used in monolith mode."""

    async def list_restaurants(self, q: str = "") -> list[dict]:
        async with async_session_factory() as db:
            stmt = select(Restaurant).order_by(Restaurant.name)
            if q:
                stmt = stmt.where(Restaurant.name.ilike(f"%{q}%"))
            result = await db.execute(stmt)
            return [_restaurant_to_dict(r) for r in result.scalars().all()]

    async def get_restaurant(self, restaurant_id: int) -> dict | None:
        async with async_session_factory() as db:
            stmt = (
                select(Restaurant)
                .where(Restaurant.id == restaurant_id)
                .options(selectinload(Restaurant.products), selectinload(Restaurant.hours))
            )
            result = await db.execute(stmt)
            r = result.scalar_one_or_none()
            if not r:
                return None
            d = _restaurant_to_dict(r)
            d["products"] = [_product_to_dict(p) for p in r.products]
            d["hours"] = [
                {
                    "id": h.id,
                    "week_day": h.week_day,
                    "from_hour": str(h.from_hour) if h.from_hour else None,
                    "to_hour": str(h.to_hour) if h.to_hour else None,
                    "work": h.work,
                }
                for h in r.hours
            ]
            return d

    async def get_product(self, product_id: int) -> dict | None:
        async with async_session_factory() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            p = result.scalar_one_or_none()
            return _product_to_dict(p) if p else None

    async def get_cart(self, user_id: int) -> list[dict]:
        async with async_session_factory() as db:
            result = await db.execute(select(UserCart).where(UserCart.user_id == user_id))
            cart = result.scalar_one_or_none()
            return cart.data if cart and cart.data else []

    async def update_cart(self, user_id: int, items: list[dict]) -> list[dict]:
        async with async_session_factory() as db:
            result = await db.execute(select(UserCart).where(UserCart.user_id == user_id))
            cart = result.scalar_one_or_none()
            if cart:
                cart.data = items
            else:
                cart = UserCart(user_id=user_id, data=items)
                db.add(cart)
            await db.commit()
            return items

    async def clear_cart(self, user_id: int) -> list[dict]:
        async with async_session_factory() as db:
            result = await db.execute(select(UserCart).where(UserCart.user_id == user_id))
            cart = result.scalar_one_or_none()
            if cart:
                cart.data = []
                await db.commit()
            return []

    async def create_order(self, user_id: int, data: dict) -> dict:
        from decimal import Decimal

        async with async_session_factory() as db:
            total = Decimal("0")
            order_products = []
            for item in data["products"]:
                result = await db.execute(
                    select(Product).where(Product.id == item["product_id"])
                )
                p = result.scalar_one_or_none()
                if not p:
                    continue
                line = p.current_price * item["quantity"]
                total += line
                order_products.append(
                    OrderProduct(
                        product_id=p.id,
                        product_name=p.name,
                        quantity=item["quantity"],
                        old_price=p.old_price,
                        current_price=p.current_price,
                    )
                )

            order = Order(
                user_id=user_id,
                restaurant_id=data["restaurant_id"],
                amount=total,
                final_price=total,
                status="new",
                pickup_time=data.get("pickup_time"),
                customer_message=data.get("customer_message"),
            )
            db.add(order)
            await db.flush()
            for op in order_products:
                op.order_id = order.id
                db.add(op)
            await db.commit()
            await db.refresh(order)
            stmt = (
                select(Order).where(Order.id == order.id).options(selectinload(Order.products))
            )
            result = await db.execute(stmt)
            return _order_to_dict(result.scalar_one())

    async def list_orders(self, user_id: int) -> list[dict]:
        async with async_session_factory() as db:
            stmt = (
                select(Order)
                .where(Order.user_id == user_id)
                .options(selectinload(Order.products))
                .order_by(Order.date.desc())
            )
            result = await db.execute(stmt)
            return [_order_to_dict(o) for o in result.scalars().all()]

    async def get_order(self, user_id: int, order_id: int) -> dict | None:
        async with async_session_factory() as db:
            stmt = (
                select(Order)
                .where(Order.id == order_id, Order.user_id == user_id)
                .options(selectinload(Order.products))
            )
            result = await db.execute(stmt)
            o = result.scalar_one_or_none()
            return _order_to_dict(o) if o else None

    async def list_favorites(self, user_id: int) -> list[dict]:
        async with async_session_factory() as db:
            stmt = (
                select(UserFavoriteRestaurant)
                .where(UserFavoriteRestaurant.user_id == user_id)
                .options(selectinload(UserFavoriteRestaurant.restaurant))
            )
            result = await db.execute(stmt)
            return [
                {
                    "id": f.id,
                    "restaurant_id": f.restaurant_id,
                    "restaurant": _restaurant_to_dict(f.restaurant),
                }
                for f in result.scalars().all()
            ]

    async def add_favorite(self, user_id: int, restaurant_id: int) -> None:
        async with async_session_factory() as db:
            fav = UserFavoriteRestaurant(user_id=user_id, restaurant_id=restaurant_id)
            db.add(fav)
            await db.commit()

    async def remove_favorite(self, user_id: int, restaurant_id: int) -> None:
        async with async_session_factory() as db:
            stmt = select(UserFavoriteRestaurant).where(
                UserFavoriteRestaurant.user_id == user_id,
                UserFavoriteRestaurant.restaurant_id == restaurant_id,
            )
            result = await db.execute(stmt)
            fav = result.scalar_one_or_none()
            if fav:
                await db.delete(fav)
                await db.commit()

    # ── Admin methods ────────────────────────────────────────────────────
    async def _get_restaurant_for_user(self, db: AsyncSession, user_id: int) -> Restaurant | None:
        stmt = select(Restaurant).where(Restaurant.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def admin_list_products(self, user_id: int) -> list[dict]:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            if not rest:
                return []
            result = await db.execute(
                select(Product).where(Product.restaurant_id == rest.id)
            )
            return [_product_to_dict(p) for p in result.scalars().all()]

    async def admin_create_product(self, user_id: int, data: dict) -> dict:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            if not rest:
                return {}
            product = Product(restaurant_id=rest.id, **data)
            db.add(product)
            await db.commit()
            await db.refresh(product)
            return _product_to_dict(product)

    async def admin_update_product(self, user_id: int, product_id: int, data: dict) -> dict:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            if not rest:
                return {}
            result = await db.execute(
                select(Product).where(Product.id == product_id, Product.restaurant_id == rest.id)
            )
            p = result.scalar_one_or_none()
            if not p:
                return {}
            for k, v in data.items():
                if v is not None:
                    setattr(p, k, v)
            await db.commit()
            await db.refresh(p)
            return _product_to_dict(p)

    async def admin_delete_product(self, user_id: int, product_id: int) -> None:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            if not rest:
                return
            result = await db.execute(
                select(Product).where(Product.id == product_id, Product.restaurant_id == rest.id)
            )
            p = result.scalar_one_or_none()
            if p:
                await db.delete(p)
                await db.commit()

    async def admin_list_orders(self, user_id: int) -> list[dict]:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            if not rest:
                return []
            stmt = (
                select(Order)
                .where(Order.restaurant_id == rest.id)
                .options(selectinload(Order.products))
                .order_by(Order.date.desc())
            )
            result = await db.execute(stmt)
            return [_order_to_dict(o) for o in result.scalars().all()]

    async def admin_update_order_status(
        self, user_id: int, order_id: int, status: str
    ) -> dict:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            if not rest:
                return {}
            stmt = (
                select(Order)
                .where(Order.id == order_id, Order.restaurant_id == rest.id)
                .options(selectinload(Order.products))
            )
            result = await db.execute(stmt)
            o = result.scalar_one_or_none()
            if not o:
                return {}
            o.status = status
            await db.commit()
            await db.refresh(o)
            return _order_to_dict(o)

    async def admin_get_restaurant(self, user_id: int) -> dict | None:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            return _restaurant_to_dict(rest) if rest else None

    async def admin_toggle_availability(self, user_id: int) -> dict:
        async with async_session_factory() as db:
            rest = await self._get_restaurant_for_user(db, user_id)
            if not rest:
                return {"available": False}
            rest.available = not rest.available
            await db.commit()
            return {"available": rest.available}


# ── HttpClient ───────────────────────────────────────────────────────────
class HttpClient:
    """REST-based implementation — used when UI runs separately from API."""

    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    async def list_restaurants(self, q: str = "") -> list[dict]:
        async with httpx.AsyncClient() as c:
            params = {"q": q} if q else {}
            r = await c.get(self._url("/api/v0/restaurants/search"), params=params)
            r.raise_for_status()
            return r.json()

    async def get_restaurant(self, restaurant_id: int) -> dict | None:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url(f"/api/v0/restaurants/{restaurant_id}"))
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def get_product(self, product_id: int) -> dict | None:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url(f"/api/v0/products/{product_id}"))
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def get_cart(self, user_id: int) -> list[dict]:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url("/api/v0/cart/"))
            r.raise_for_status()
            return r.json().get("data", [])

    async def update_cart(self, user_id: int, items: list[dict]) -> list[dict]:
        async with httpx.AsyncClient() as c:
            r = await c.post(self._url("/api/v0/cart/"), json={"items": items})
            r.raise_for_status()
            return r.json().get("data", [])

    async def clear_cart(self, user_id: int) -> list[dict]:
        async with httpx.AsyncClient() as c:
            r = await c.delete(self._url("/api/v0/cart/"))
            r.raise_for_status()
            return []

    async def create_order(self, user_id: int, data: dict) -> dict:
        async with httpx.AsyncClient() as c:
            r = await c.post(self._url("/api/v0/orders/"), json=data)
            r.raise_for_status()
            return r.json()

    async def list_orders(self, user_id: int) -> list[dict]:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url("/api/v0/orders/history"))
            r.raise_for_status()
            return r.json()

    async def get_order(self, user_id: int, order_id: int) -> dict | None:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url(f"/api/v0/orders/{order_id}"))
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    async def list_favorites(self, user_id: int) -> list[dict]:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url("/api/v0/favorites/"))
            r.raise_for_status()
            return r.json()

    async def add_favorite(self, user_id: int, restaurant_id: int) -> None:
        async with httpx.AsyncClient() as c:
            await c.post(
                self._url("/api/v0/favorites/"), json={"restaurant_id": restaurant_id}
            )

    async def remove_favorite(self, user_id: int, restaurant_id: int) -> None:
        async with httpx.AsyncClient() as c:
            await c.delete(self._url(f"/api/v0/favorites/{restaurant_id}"))

    async def admin_list_products(self, user_id: int) -> list[dict]:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url("/api/v0/admin/products/"))
            r.raise_for_status()
            return r.json()

    async def admin_create_product(self, user_id: int, data: dict) -> dict:
        async with httpx.AsyncClient() as c:
            r = await c.post(self._url("/api/v0/admin/products/"), json=data)
            r.raise_for_status()
            return r.json()

    async def admin_update_product(self, user_id: int, product_id: int, data: dict) -> dict:
        async with httpx.AsyncClient() as c:
            r = await c.put(self._url(f"/api/v0/admin/products/{product_id}"), json=data)
            r.raise_for_status()
            return r.json()

    async def admin_delete_product(self, user_id: int, product_id: int) -> None:
        async with httpx.AsyncClient() as c:
            await c.delete(self._url(f"/api/v0/admin/products/{product_id}"))

    async def admin_list_orders(self, user_id: int) -> list[dict]:
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url("/api/v0/admin/orders/"))
            r.raise_for_status()
            return r.json()

    async def admin_update_order_status(
        self, user_id: int, order_id: int, status: str
    ) -> dict:
        async with httpx.AsyncClient() as c:
            r = await c.put(
                self._url(f"/api/v0/admin/orders/{order_id}/status"),
                json={"status": status},
            )
            r.raise_for_status()
            return r.json()

    async def admin_get_restaurant(self, user_id: int) -> dict | None:
        # In HTTP mode, admin endpoints use auth header to identify restaurant
        async with httpx.AsyncClient() as c:
            r = await c.get(self._url("/api/v0/restaurants/"))
            r.raise_for_status()
            data = r.json()
            return data[0] if data else None

    async def admin_toggle_availability(self, user_id: int) -> dict:
        async with httpx.AsyncClient() as c:
            r = await c.put(self._url("/api/v0/admin/availability"))
            r.raise_for_status()
            return r.json()
