"""Pydantic request/response DTOs.

These are the shapes that actually cross HTTP — distinct from api/views.py's
plain dict (which is what a Python caller works with) and api/models.py's
ORM classes (which is what Postgres works with). FastAPI uses the type
hints below to validate incoming JSON and to generate the interactive
schema shown at /docs.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)


class LegalAction(BaseModel):
    type: str
    amount: int | None = None
    min: int | None = None
    max: int | None = None


class PlayerSeat(BaseModel):
    player_id: str
    stack: int
    chips_in_street: int
    chips_in_hand: int
    is_folded: bool
    is_all_in: bool
    hole_cards: list[str] | None


class GameView(BaseModel):
    """Mirrors api.views.to_player_view's dict, plus the DB ids the view
    itself deliberately doesn't know about (game_id, hand_id)."""

    game_id: uuid.UUID
    hand_id: uuid.UUID
    viewer_id: str
    street: str
    is_hand_over: bool
    dealer_button_index: int
    sb_amount: int
    bb_amount: int
    board_cards: list[str]
    pot_total: int
    current_bet: int
    to_act: str | None
    is_your_turn: bool
    legal_actions: list[LegalAction]
    players: list[PlayerSeat]
    winners: dict[str, int] | None
