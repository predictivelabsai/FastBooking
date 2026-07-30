# FastBooking

FastBooking is a multi-tenant booking and commerce platform for restaurants,
hotels, private clinics, and ticketed events. Tenant administrators enable only
the product modules they use.

## Product modules

- **Restaurants:** menus, carts, pickup orders, reservation-linked dine-in
  pre-orders, tables, party capacity, and table reservations.
- **Hotels:** room-type inventory, per-night pricing, and half-open stay ranges.
- **Private clinics:** public scheduling backed by FastClinic-owned
  practitioners, availability, and appointments. FastBooking stores no clinical
  records.
- **Events:** scheduled concerts or events, ticket types, sale windows,
  capacity, and per-booking limits.

All modules share tenants, locations, guests, booking references, allocations,
notifications, trials, usage records, and secure management tokens.

## Architecture

The production monolith mounts FastAPI at `/api` and FastHTML at `/`. PostgreSQL
is the source of truth. Inventory changes use database row locks to prevent
double-booking. Alembic owns schema upgrades.

Key paths:

```text
app/db/platform_models.py   tenant, booking, inventory, and SaaS models
app/services/booking.py     module-specific allocation strategies
app/api/routers/platform.py tenant configuration and public API v1
app/ui/pages/platform.py    landing, Google SSO, onboarding, module admin
alembic/                    database migrations
seed.py                     representative four-module demo tenant
```

## Local development

Requirements are Python 3.11+, `uv`, and PostgreSQL.

```bash
uv venv
uv pip install --python .venv/bin/python -e ".[dev]"
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m seed
.venv/bin/python -m app.main_monolith
```

Open `http://localhost:5023`. Useful checks:

```bash
.venv/bin/ruff check app tests alembic seed.py
.venv/bin/pytest -q
docker build -t fastbooking:dev .
```

Public tenant pages use `/book/{tenant_slug}`. The API catalogue is
`/api/v1/public/{tenant_slug}/catalogue`; interactive API documentation is
available under `/api/docs`.

## Configuration and deployment

Copy variable names from `.env.example`; never commit values. Production
requires `DATABASE_URL`, `SESSION_SECRET`, Google OAuth credentials, Postmark,
and a dedicated FastBooking-to-FastClinic connector token. Stripe variables are
placeholders only:
the MVP remains pay-later and cannot capture funds.

The root `Dockerfile` listens on `0.0.0.0:5023`, runs migrations before startup,
and exposes `/healthz` and `/readyz`. FastDevOps declares the Coolify service at
`https://booking.fastsme.com`; `scripts/coolify.py` delegates validation,
environment synchronization, and deployment to that control plane.
