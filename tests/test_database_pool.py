"""Process-wide async database pool configuration."""

import app.db.engine as database
from app.config import Settings


def test_async_engine_is_process_singleton_with_bounded_pool():
    assert database.engine is database.engine
    assert database.engine.pool.size() == 3


def test_pool_defaults_match_shared_postgres_budget():
    fields = Settings.model_fields
    assert fields["DB_POOL_SIZE"].default == 3
    assert fields["DB_MAX_OVERFLOW"].default == 2
    assert fields["DB_POOL_TIMEOUT"].default == 10
    assert fields["DB_APPLICATION_NAME"].default == "fastbooking"
