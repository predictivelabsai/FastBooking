from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models import ContactUs, PrivacyPolicy, UserAgreement
from app.schemas import ContactUsOut, PrivacyPolicyOut, UserAgreementOut

router = APIRouter()


@router.get("/contact-us", response_model=ContactUsOut | None)
async def contact_us(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactUs).limit(1))
    return result.scalar_one_or_none()


@router.get("/user-agreement", response_model=UserAgreementOut | None)
async def user_agreement(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserAgreement).limit(1))
    return result.scalar_one_or_none()


@router.get("/privacy-policy", response_model=PrivacyPolicyOut | None)
async def privacy_policy(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PrivacyPolicy).limit(1))
    return result.scalar_one_or_none()
