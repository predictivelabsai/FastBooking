"""Remove trials and make admin the sole configuration role."""

from __future__ import annotations

from alembic import op
from app.config import settings

revision = "20260809_0003"
down_revision = "20260809_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = settings.DB_SCHEMA
    op.execute(
        f'UPDATE "{schema}".tenants SET status = \'active\' WHERE status = \'trial\''
    )
    op.drop_constraint(
        "ck_tenants_status", "tenants", schema=schema, type_="check"
    )
    op.create_check_constraint(
        "ck_tenants_status",
        "tenants",
        "status IN ('active', 'suspended', 'closed')",
        schema=schema,
    )
    op.execute(
        f'UPDATE "{schema}".memberships SET role = \'admin\' WHERE role = \'owner\''
    )
    op.drop_constraint(
        "ck_memberships_role", "memberships", schema=schema, type_="check"
    )
    op.create_check_constraint(
        "ck_memberships_role",
        "memberships",
        "role IN ('admin', 'staff', 'viewer')",
        schema=schema,
    )
    op.execute(f'DROP TABLE IF EXISTS "{schema}".trial_entitlements CASCADE')


def downgrade() -> None:
    schema = settings.DB_SCHEMA
    op.drop_constraint(
        "ck_memberships_role", "memberships", schema=schema, type_="check"
    )
    op.create_check_constraint(
        "ck_memberships_role",
        "memberships",
        "role IN ('owner', 'admin', 'staff', 'viewer')",
        schema=schema,
    )
    op.drop_constraint(
        "ck_tenants_status", "tenants", schema=schema, type_="check"
    )
    op.create_check_constraint(
        "ck_tenants_status",
        "tenants",
        "status IN ('trial', 'active', 'suspended', 'closed')",
        schema=schema,
    )
