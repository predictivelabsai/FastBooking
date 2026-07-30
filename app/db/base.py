from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    __table_args__ = {"schema": settings.DB_SCHEMA}
