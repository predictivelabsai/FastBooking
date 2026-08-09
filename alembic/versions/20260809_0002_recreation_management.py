"""Add sport and recreation management, attendance, and payment records."""

from __future__ import annotations

from alembic import op
from app.config import settings
from app.db.base import Base

revision = "20260809_0002"
down_revision = "20260730_0001"
branch_labels = None
depends_on = None

MODULE_CHECKS = (
    ("tenant_modules", "ck_tenant_modules_module"),
    ("offerings", "ck_offerings_module"),
    ("resources", "ck_resources_module"),
    ("bookings", "ck_bookings_module"),
)


def upgrade() -> None:
    connection = op.get_bind()
    Base.metadata.create_all(bind=connection, checkfirst=True)
    for table, constraint in MODULE_CHECKS:
        op.drop_constraint(constraint, table, schema=settings.DB_SCHEMA, type_="check")
        op.create_check_constraint(
            constraint,
            table,
            "module IN ('restaurant', 'hotel', 'clinic', 'events', 'recreation')",
            schema=settings.DB_SCHEMA,
        )


def downgrade() -> None:
    connection = op.get_bind()
    schema = settings.DB_SCHEMA
    connection.exec_driver_sql(
        f'DELETE FROM "{schema}".booking_allocations WHERE booking_id IN '
        f'(SELECT id FROM "{schema}".bookings WHERE module = \'recreation\')'
    )
    connection.exec_driver_sql(
        f'DELETE FROM "{schema}".bookings WHERE module = \'recreation\''
    )
    for name in (
        "payment_transactions",
        "attendance_records",
        "programme_enrolments",
        "customer_memberships",
        "membership_plans",
        "recreation_programmes",
    ):
        Base.metadata.tables[f"{schema}.{name}"].drop(connection, checkfirst=True)
    connection.exec_driver_sql(
        f'DELETE FROM "{schema}".resources WHERE module = \'recreation\''
    )
    connection.exec_driver_sql(
        f'DELETE FROM "{schema}".offerings WHERE module = \'recreation\''
    )
    connection.exec_driver_sql(
        f'DELETE FROM "{schema}".tenant_modules WHERE module = \'recreation\''
    )
    for table, constraint in MODULE_CHECKS:
        op.drop_constraint(constraint, table, schema=schema, type_="check")
        op.create_check_constraint(
            constraint,
            table,
            "module IN ('restaurant', 'hotel', 'clinic', 'events')",
            schema=schema,
        )
