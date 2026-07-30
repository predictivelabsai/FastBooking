"""Create the FastBooking tenant, commerce, and booking platform baseline."""

from __future__ import annotations

from alembic import op
from app.config import settings
from app.db.base import Base

revision = "20260730_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(
        f'CREATE SCHEMA IF NOT EXISTS "{settings.DB_SCHEMA}"'
    )
    Base.metadata.create_all(bind=connection, checkfirst=True)


def downgrade() -> None:
    connection = op.get_bind()
    Base.metadata.drop_all(bind=connection, checkfirst=True)
