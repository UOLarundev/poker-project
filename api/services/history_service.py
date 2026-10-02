"""Reading a player's hand history.

The query here — filter by player_id, order by started_at, limit — is the
exact one Weekend 4's indexing depth point measures before/after adding
CREATE INDEX idx_hands_player_started ON hands (player_id, started_at DESC).
Deliberately not filtered further (e.g. to exclude in-progress hands) so
that query stays the one actually benchmarked later.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from api import models


class PlayerNotFoundError(Exception):
    pass


def get_hand_history(db: Session, username: str, limit: int = 20, offset: int = 0) -> list[models.Hand]:
    player = db.scalar(select(models.Player).where(models.Player.username == username))
    if player is None:
        raise PlayerNotFoundError(f"No player {username!r}")

    return list(
        db.scalars(
            select(models.Hand)
            .where(models.Hand.player_id == player.id)
            .order_by(models.Hand.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
