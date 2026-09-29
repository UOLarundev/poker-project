"""Database engine, session factory, and the declarative base every model inherits from."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from api.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Every ORM model (Player, Game, Hand, Action, ...) inherits from this.

    Alembic's autogenerate reads Base.metadata to diff "what the models say"
    against "what the database actually has" — that's the whole mechanism
    behind `alembic revision --autogenerate`.
    """


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
