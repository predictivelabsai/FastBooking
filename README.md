# FoodAngels

Food delivery platform built with **FastAPI** (REST API) + **FastHTML** (HTMX web UI) + **SQLAlchemy async** + **TailwindCSS CDN**.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Monolith (Starlette ASGI mount)                │
│  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ FastAPI /api  │  │ FastHTML / (UI)          │  │
│  │   JSON REST   │  │   HTMX + TailwindCSS    │  │
│  └──────┬───────┘  └──────────┬──────────────┘  │
│         │                     │                  │
│         │    DataClient (DbClient)               │
│         └─────────┬───────────┘                  │
│              SQLAlchemy async                     │
│              schema: foodangels                   │
└─────────────────┬───────────────────────────────┘
                  │
           PostgreSQL (finespresso_db)
```

Three deploy modes controlled by `DEPLOY_MODE` env var:

| Mode | What runs | DB access | Use case |
|------|-----------|-----------|----------|
| `monolith` | API + UI on one server | Direct (DbClient) | Development, small deploys |
| `api` | FastAPI only | Direct | Backend service |
| `ui` | FastHTML only | Via REST (HttpClient) | Frontend service |

The **DataClient protocol** (`app/ui/client.py`) is the key abstraction: `DbClient` hits the database directly, `HttpClient` makes REST calls to the API. The UI uses whichever is injected based on deploy mode.

## Project Structure

```
app/
├── config.py                  # Pydantic Settings
├── schemas.py                 # Pydantic request/response models
├── db/
│   ├── base.py                # DeclarativeBase (schema=foodangels)
│   ├── engine.py              # async engine + session factory
│   └── models.py              # 12 SQLAlchemy models
├── api/
│   ├── main.py                # create_api_app() factory
│   ├── deps.py                # get_db, get_current_user stub
│   └── routers/               # 7 routers (restaurants, products, orders, cart, favorites, admin, info)
├── ui/
│   ├── main.py                # create_ui_app() factory
│   ├── client.py              # DataClient protocol + DbClient + HttpClient
│   ├── components.py          # Layout shell, nav, cards, badges
│   └── pages/                 # home, restaurant, cart, orders, admin
├── main_monolith.py           # Monolith entrypoint
├── main_api.py                # API-only entrypoint
└── main_ui.py                 # UI-only entrypoint
sql/
└── schema.sql                 # Full DDL + views (for reference / manual setup)
docker/
├── Dockerfile.monolith
├── Dockerfile.api
├── Dockerfile.ui
└── docker-compose.yaml
seed.py                        # Sample data (3 restaurants, 14 products, 4 users)
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with a database named `finespresso_db`
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### 1. Setup

```bash
# Create venv and install deps
uv venv && uv pip install -r requirements.txt

# Configure database connection
cp .env.example .env
# Edit .env with your DATABASE_URL
```

### 2. Create `.env`

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/finespresso_db
DEPLOY_MODE=monolith
API_BASE_URL=http://localhost:8000
```

### 3. Seed the database

```bash
.venv/bin/python -m seed
```

This creates the `foodangels` schema, all tables, and populates sample data.

### 4. Run

```bash
# Monolith (API + UI)
.venv/bin/python -m app.main_monolith

# API only
.venv/bin/python -m app.main_api

# UI only (requires API running separately)
.venv/bin/python -m app.main_ui
```

Open http://localhost:8000 for the UI, or http://localhost:8000/api/v0/restaurants/ for the API.

## Docker Deployment

### Monolith

```bash
cd docker
docker compose --profile monolith up --build
```

### Split (API + UI separately)

```bash
cd docker
docker compose --profile split up --build
```

This starts the API on port 8000 and the UI on port 8001. The UI connects to the API via `API_BASE_URL=http://api:8000`.

## API Endpoints

All endpoints are under `/api/v0/`.

| Router | Method | Path | Description |
|--------|--------|------|-------------|
| restaurants | GET | `/restaurants/` | List all restaurants |
| restaurants | GET | `/restaurants/search?q=` | Search by name |
| restaurants | GET | `/restaurants/{id}` | Detail with products & hours |
| products | GET | `/products/{id}` | Single product |
| orders | POST | `/orders/` | Create order |
| orders | GET | `/orders/history` | User order history |
| orders | GET | `/orders/{id}` | Order detail |
| cart | GET | `/cart/` | Get cart |
| cart | POST | `/cart/` | Update cart |
| cart | DELETE | `/cart/` | Clear cart |
| favorites | GET | `/favorites/` | List favorites |
| favorites | POST | `/favorites/` | Add favorite |
| favorites | DELETE | `/favorites/{restaurant_id}` | Remove favorite |
| admin | GET/POST | `/admin/products/` | List/create products |
| admin | PUT/DELETE | `/admin/products/{id}` | Update/delete product |
| admin | GET | `/admin/orders/` | Restaurant orders |
| admin | PUT | `/admin/orders/{id}/status` | Accept/refuse/done |
| admin | GET/PUT | `/admin/hours/` | Restaurant hours |
| admin | PUT | `/admin/availability` | Toggle open/closed |
| info | GET | `/info/contact-us` | Contact info |
| info | GET | `/info/user-agreement` | User agreement |
| info | GET | `/info/privacy-policy` | Privacy policy |

## UI Pages

| Page | Route | Features |
|------|-------|----------|
| Home | `GET /` | Restaurant grid, HTMX live search |
| Restaurant | `GET /restaurants/{id}` | Info, hours, categorized menu, add-to-cart |
| Cart | `GET /cart` | Items by restaurant, place order |
| Orders | `GET /orders` | Order history with status badges |
| Order Detail | `GET /orders/{id}` | Items, status, HTMX polling |
| Admin | `GET /admin` | Dashboard, availability toggle |
| Admin Products | `GET /admin/products` | Product CRUD table |
| Admin Orders | `GET /admin/orders` | Accept/refuse/done with HTMX |

## Database

All tables live in the `foodangels` PostgreSQL schema. See `sql/schema.sql` for the full DDL and utility views.

Tables are auto-created on app startup via `Base.metadata.create_all()`. For production, consider adding Alembic migrations.

### Schema overview

| Table | Purpose |
|-------|---------|
| `users` | Customers and restaurant owners |
| `restaurants` | Restaurant profiles |
| `restaurant_hours` | Weekly schedule (0=Mon..6=Sun) |
| `products` | Menu items with categories and dietary flags |
| `orders` | Orders with atomic sequence numbering |
| `order_products` | Line items (snapshot of product at order time) |
| `codes` | Discount/promo codes |
| `user_carts` | JSON cart storage per user |
| `user_favorite_restaurants` | User-restaurant favorites |
| `contact_us` | Support contact info |
| `user_agreements` | Terms of service |
| `privacy_policies` | Privacy policy text |

## Auth

Authentication is currently stubbed for demo purposes. `get_current_user()` returns the first active user. Replace with JWT or session auth for production.
