"""Shared fixtures for API tests.

Known limitation: there's no disposable test database yet (that lands with
CI, still pending). These tests run against the same local Postgres from
docker-compose.yml, and the `clean_db` fixture truncates the tables after
every test so tests don't see each other's leftover rows.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from api.db import engine
from api.main import app


@pytest.fixture(autouse=True)
def clean_db():
    yield
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE actions, hands, games, players, request_metrics RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def client():
    return TestClient(app)
