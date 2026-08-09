from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin_user, get_db
from app.db.models import (
    Order,
    Product,
    Restaurant,
    RestaurantHours,
    User,
)
from app.schemas import (
    OrderOut,
    OrderStatusUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    RestaurantHoursOut,
    RestaurantHoursUpdate,
)

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────
async def _get_restaurant(user: User, db: AsyncSession) -> Restaurant:
    stmt = select(Restaurant).where(Restaurant.user_id == user.id)
    result = await db.execute(stmt)
    rest = result.scalar_one_or_none()
    if not rest:
        raise HTTPException(status_code=403, detail="No restaurant linked to user")
    return rest


# ── Products ─────────────────────────────────────────────────────────────
@router.get("/products/", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    stmt = select(Product).where(Product.restaurant_id == rest.id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/products/", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    product = Product(
        tenant_id=rest.tenant_id, restaurant_id=rest.id, **body.model_dump()
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.restaurant_id == rest.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.restaurant_id == rest.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)
    await db.commit()


# ── Orders ───────────────────────────────────────────────────────────────
@router.get("/orders/", response_model=list[OrderOut])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    stmt = (
        select(Order)
        .where(Order.restaurant_id == rest.id)
        .options(selectinload(Order.products))
        .order_by(Order.date.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.put("/orders/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.restaurant_id == rest.id)
        .options(selectinload(Order.products))
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if body.status not in ("accepted", "refused", "done"):
        raise HTTPException(status_code=400, detail="Invalid status")

    order.status = body.status
    await db.commit()
    await db.refresh(order)
    return order


# ── Hours ────────────────────────────────────────────────────────────────
@router.get("/hours/", response_model=list[RestaurantHoursOut])
async def get_hours(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    stmt = (
        select(RestaurantHours)
        .where(RestaurantHours.restaurant_id == rest.id)
        .order_by(RestaurantHours.week_day)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.put("/hours/", response_model=list[RestaurantHoursOut])
async def update_hours(
    body: list[RestaurantHoursUpdate],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    stmt = (
        select(RestaurantHours)
        .where(RestaurantHours.restaurant_id == rest.id)
        .order_by(RestaurantHours.week_day)
    )
    result = await db.execute(stmt)
    hours = {h.week_day: h for h in result.scalars().all()}

    for item in body:
        h = hours.get(item.week_day)
        if h:
            h.from_hour = item.from_hour
            h.to_hour = item.to_hour
            h.work = item.work
        else:
            new_h = RestaurantHours(
                restaurant_id=rest.id,
                week_day=item.week_day,
                from_hour=item.from_hour,
                to_hour=item.to_hour,
                work=item.work,
            )
            db.add(new_h)

    await db.commit()
    result = await db.execute(
        select(RestaurantHours)
        .where(RestaurantHours.restaurant_id == rest.id)
        .order_by(RestaurantHours.week_day)
    )
    return result.scalars().all()


# ── Availability ─────────────────────────────────────────────────────────
@router.put("/availability")
async def toggle_availability(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin_user),
):
    rest = await _get_restaurant(user, db)
    rest.available = not rest.available
    await db.commit()
    return {"available": rest.available}
