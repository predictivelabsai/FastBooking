from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User, UserCart
from app.schemas import CartData, CartUpdate

router = APIRouter()


@router.get("/", response_model=CartData)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(UserCart).where(UserCart.user_id == user.id))
    cart = result.scalar_one_or_none()
    if not cart:
        return CartData(data=[])
    return CartData(data=cart.data or [])


@router.post("/", response_model=CartData)
async def update_cart(
    body: CartUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(UserCart).where(UserCart.user_id == user.id))
    cart = result.scalar_one_or_none()

    items = [item.model_dump() for item in body.items]
    if cart:
        cart.data = items
    else:
        cart = UserCart(user_id=user.id, data=items)
        db.add(cart)

    await db.commit()
    return CartData(data=cart.data)


@router.delete("/", response_model=CartData)
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(UserCart).where(UserCart.user_id == user.id))
    cart = result.scalar_one_or_none()
    if cart:
        cart.data = []
        await db.commit()
    return CartData(data=[])
