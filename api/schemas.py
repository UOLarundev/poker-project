"""Pydantic request/response DTOs.

These are the shapes that actually cross HTTP — distinct from api/views.py's
plain dict (which is what a Python caller works with) and api/models.py's
ORM classes (which is what Postgres works with). FastAPI uses the type
hints below to validate incoming JSON and to generate the interactive
schema shown at /docs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)


class SubmitActionRequest(BaseModel):
    # Client-generated: the whole idempotency mechanism depends on the
    # SAME retried request carrying the SAME id, not one assigned by the
    # server after the fact.
    action_id: uuid.UUID
    action_type: Literal["fold", "check", "call", "raise", "all_in"]
    amount: int | None = None


class NextHandRequest(BaseModel):
    # Same idempotency mechanism as SubmitActionRequest, and for the same
    # reason: dealing a hand involves a real shuffle, so a naive retry
    # would deal a DIFFERENT hand rather than just reapplying the same one.
    action_id: uuid.UUID


class LegalAction(BaseModel):
    type: str
    amount: int | None = None
    min: int | None = None
    max: int | None = None


class ActionLogEntry(BaseModel):
    actor_id: str
    action_type: str
    amount: int | None = None


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
    # What happened since the client's last view of this game: the human's
    # own action (if any) followed by whatever bots did in response.
    # Ephemeral per-request narration, not derived from the persisted
    # GameState — always present, but genuinely empty for a fresh game or
    # a plain GET refresh (nothing happened as a result of those).
    action_log: list[ActionLogEntry]
    # Mirrors interface/cli.py's own live equity display exactly — same
    # trial count, same "only when it's actually your turn" timing. Null
    # whenever it's not your turn (not computed at all in that case, not
    # just hidden — this is a real Monte Carlo simulation, not free).
    your_equity: float | None


class HandHistoryEntry(BaseModel):
    """One row from the hands table. ended_at/winners/pot_total/hero_net
    are null for a hand still in progress — deliberately not filtered out
    in SQL (see history_service.get_hand_history)."""

    hand_id: uuid.UUID
    game_id: uuid.UUID
    hand_number: int
    started_at: datetime
    ended_at: datetime | None
    board: list[str] | None
    hero_hole: list[str] | None
    winners: dict[str, int] | None
    pot_total: int | None
    hero_net: int | None


class PercentileStats(BaseModel):
    """p50/p95/p99 are exact (SQL percentile_cont over the raw recorded
    durations), not bucket-interpolated estimates — see docs/latency.md."""

    count: int
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None


class RouteStats(PercentileStats):
    route: str
    method: str


class MetricsSummary(BaseModel):
    overall: PercentileStats
    by_route: list[RouteStats]


class GameOverView(BaseModel):
    """Returned instead of GameView when fewer than 2 players have chips
    left after a hand — there is no next hand to deal. Structurally
    distinct from GameView (no hand_id, no legal_actions, ...) so FastAPI's
    Union response_model can tell the two apart without an explicit
    discriminator field."""

    game_id: uuid.UUID
    game_over: Literal[True] = True
    winner: str | None
    final_stacks: dict[str, int]
