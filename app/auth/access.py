"""Shared role-based access rules for tenant operations."""

ADMIN_ROLE = "admin"
MEMBERSHIP_ROLES = (ADMIN_ROLE, "staff", "viewer")


def can_configure_products(role: str | None) -> bool:
    """Return whether a tenant membership may change product configuration."""
    return role == ADMIN_ROLE
