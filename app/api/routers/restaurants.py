from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.db.models import Restaurant
from app.schemas import RestaurantDetail, RestaurantOut

router = APIRouter()


@router.get("/", response_model=list[RestaurantOut])
async def list_restaurants(
    city: str | None = None,
    available: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Restaurant)
    if city:
        stmt = stmt.where(Restaurant.city.ilike(f"%{city}%"))
    if available is not None:
        stmt = stmt.where(Restaurant.available.is_(available))
    stmt = stmt.order_by(Restaurant.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/search", response_model=list[RestaurantOut])
async def search_restaurants(
    q: str = Query("", min_length=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Restaurant).where(Restaurant.name.ilike(f"%{q}%")).order_by(Restaurant.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{restaurant_id}", response_model=RestaurantDetail)
async def get_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Restaurant)
        .where(Restaurant.id == restaurant_id)
        .options(selectinload(Restaurant.products), selectinload(Restaurant.hours))
    )
    result = await db.execute(stmt)
    restaurant = result.scalar_one_or_none()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant
