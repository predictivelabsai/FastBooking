from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.db.models import Order, OrderProduct, Product, User
from app.schemas import OrderCreate, OrderOut

router = APIRouter()


@router.post("/", response_model=OrderOut, status_code=201)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # resolve products and compute amount
    total = Decimal("0")
    order_products: list[OrderProduct] = []
    restaurant_id: int | None = None
    tenant_id: int | None = None
    for item in body.products:
        result = await db.execute(select(Product).where(Product.id == item.product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not found")
        if product.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient quantity for {product.name}",
            )
        if restaurant_id is None:
            restaurant_id = product.restaurant_id
            tenant_id = product.tenant_id
        if product.restaurant_id != body.restaurant_id or product.restaurant_id != restaurant_id:
            raise HTTPException(status_code=400, detail="Order items must belong to one restaurant")
        line_total = product.current_price * item.quantity
        total += line_total
        order_products.append(
            OrderProduct(
                product_id=product.id,
                product_name=product.name,
                quantity=item.quantity,
                old_price=product.old_price,
                current_price=product.current_price,
            )
        )

    order = Order(
        tenant_id=tenant_id,
        user_id=user.id,
        restaurant_id=body.restaurant_id,
        amount=total,
        final_price=total,
        status="new",
        pickup_time=body.pickup_time,
        customer_message=body.customer_message,
    )
    db.add(order)
    await db.flush()

    for op in order_products:
        op.order_id = order.id
        db.add(op)

    await db.commit()
    await db.refresh(order)

    # reload with products
    stmt = (
        select(Order).where(Order.id == order.id).options(selectinload(Order.products))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("/history", response_model=list[OrderOut])
async def order_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.products))
        .order_by(Order.date.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(selectinload(Order.products))
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
