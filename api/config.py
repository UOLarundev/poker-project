"""Typed settings, read from the environment.

One class read once, instead of `os.environ.get(...)` scattered across the
codebase with the default duplicated at every call site. The default below
matches docker-compose.yml's local Postgres credentials, so `docker compose
up` + running the API locally just works with no extra setup.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://poker:poker@localhost:5432/poker"


settings = Settings()
