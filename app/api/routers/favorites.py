from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.db.models import Restaurant, User, UserFavoriteRestaurant
from app.schemas import FavoriteAdd, FavoriteOut

router = APIRouter()


@router.get("/", response_model=list[FavoriteOut])
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(UserFavoriteRestaurant)
        .where(UserFavoriteRestaurant.user_id == user.id)
        .options(selectinload(UserFavoriteRestaurant.restaurant))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", status_code=201)
async def add_favorite(
    body: FavoriteAdd,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # check duplicate
    stmt = select(UserFavoriteRestaurant).where(
        UserFavoriteRestaurant.user_id == user.id,
        UserFavoriteRestaurant.restaurant_id == body.restaurant_id,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already a favorite")

    restaurant = await db.get(Restaurant, body.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    fav = UserFavoriteRestaurant(
        tenant_id=restaurant.tenant_id,
        user_id=user.id,
        restaurant_id=body.restaurant_id,
    )
    db.add(fav)
    await db.commit()
    return {"status": "added"}


@router.delete("/{restaurant_id}")
async def remove_favorite(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(UserFavoriteRestaurant).where(
        UserFavoriteRestaurant.user_id == user.id,
        UserFavoriteRestaurant.restaurant_id == restaurant_id,
    )
    result = await db.execute(stmt)
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.delete(fav)
    await db.commit()
    return {"status": "removed"}
