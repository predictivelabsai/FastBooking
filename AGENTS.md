# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `app/`. `app/api/` contains FastAPI routes; `app/ui/` contains FastHTML pages; `app/db/` contains async SQLAlchemy commerce and platform models; and `app/services/booking.py` owns allocation rules. Shared platform API models are in `app/platform_schemas.py`. Alembic migrations live under `alembic/`, tests under `tests/`, and production packaging in the root `Dockerfile`. `seed.py` creates a representative four-module tenant.

## Build, Test, and Development Commands

- `uv venv && uv pip install -e ".[dev]"` creates `.venv` and installs runtime, test, and lint dependencies.
- `.venv/bin/alembic upgrade head && .venv/bin/python -m seed` migrates PostgreSQL and loads sample records.
- `.venv/bin/python -m app.main_monolith` runs the UI and `/api` together on port 5023.
- `.venv/bin/python -m app.main_api` runs only the API.
- `.venv/bin/ruff check .` checks Python style; `.venv/bin/pytest` runs the test suite.
- `docker build -t fastbooking:dev .` validates the production image.

## Coding Style & Naming Conventions

Use Python 3.11+ syntax, four-space indentation, type hints, and short docstrings for public modules or non-obvious behavior. Follow Ruff defaults and existing PEP 8 conventions. Name modules and functions `snake_case`, classes and Pydantic/SQLAlchemy models `PascalCase`, and constants or environment settings `UPPER_SNAKE_CASE`. Add API resources as focused modules in `app/api/routers/`; keep reusable UI markup in `app/ui/components.py`.

## Testing Guidelines

Tests use `pytest` with `pytest-asyncio`. The suite currently contains only shared scaffolding, so every behavior change should add coverage. Name files `test_<feature>.py` and tests `test_<expected_behavior>`. Prefer API-level tests for routers and isolated async tests for database/client behavior. Run Ruff and the complete test suite before opening a pull request.

## Commit & Pull Request Guidelines

Recent commits use concise, imperative subjects such as `Add DATABASE_URL env var substitution`. Keep each commit focused and explain deployment or schema implications in its body. Pull requests should summarize behavior, list validation commands, link relevant issues, and include screenshots for UI changes. Call out new environment variables or SQL changes explicitly.

## Security & Configuration

Configure variables from `.env.example` in an untracked `.env`; never commit credentials. Every tenant-owned query must include tenant scope. Public booking tokens must be stored hashed, and clinical data must remain in FastClinic.
