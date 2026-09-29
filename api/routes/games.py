from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas import CreateGameRequest, GameView
from api.services import game_service
from api.views import to_player_view

router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("", response_model=GameView, status_code=status.HTTP_201_CREATED)
def create_game(body: CreateGameRequest, db: Session = Depends(get_db)) -> dict:
    game, hand, state = game_service.create_game(db, body.username)
    view = to_player_view(state, body.username)
    return {**view, "game_id": game.id, "hand_id": hand.id}


@router.get("/{game_id}", response_model=GameView)
def read_game(game_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    result = game_service.get_game(db, game_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    game, hand, state = result
    viewer_id = game.player.username
    view = to_player_view(state, viewer_id)
    return {**view, "game_id": game.id, "hand_id": hand.id}
