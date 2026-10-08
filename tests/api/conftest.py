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
def fast_equity(monkeypatch):
    # api/views.py's `from interface.cli import HUMAN_EQUITY_TRIALS` binds
    # the name into api.views's own namespace, so patching it there (not
    # in interface.cli, where the lookup no longer happens after import)
    # is what actually takes effect. Real route-level tests (games/actions/
    # next-hand) create a game and get is_your_turn=True immediately
    # (dealer_button_index=0 means the human always acts first in hand #1)
    # — at the real 5000 trials, every one of those tests would pay a
    # genuine ~1s Monte Carlo simulation. A smaller trial count still
    # exercises the real equity_vs_random code path end-to-end over actual
    # HTTP, just fast — the same precision/speed tradeoff the app itself
    # already makes between bot (1000) and human (5000) trial counts.
    monkeypatch.setattr("api.views.HUMAN_EQUITY_TRIALS", 50)


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
