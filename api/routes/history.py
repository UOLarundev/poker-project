from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import HandHistoryEntry
from api.services import history_service

router = APIRouter(prefix="/api/players", tags=["history"])


@router.get("/{username}/hands", response_model=list[HandHistoryEntry])
def get_hand_history(
    username: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    try:
        hands = history_service.get_hand_history(db, username, limit=limit, offset=offset)
    except history_service.PlayerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return [
        {
            "hand_id": h.id,
            "game_id": h.game_id,
            "hand_number": h.hand_number,
            "started_at": h.started_at,
            "ended_at": h.ended_at,
            "board": h.board,
            "hero_hole": h.hero_hole,
            "winners": h.winners,
            "pot_total": h.pot_total,
            "hero_net": h.hero_net,
        }
        for h in hands
    ]
