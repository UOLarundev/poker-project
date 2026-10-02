"""Auto-resolve bot turns after a human action.

This does NOT reimplement bot decision-making — that logic lives in
interface/cli.py's choose_bot_action, which is frozen (Layer 1/2 code, not
to be touched). This module only decides *when* to call it: keep applying
bot actions until it's the human's turn again or the hand has ended.
"""

from __future__ import annotations

from api.views import TERMINAL_STREETS
from interface.cli import choose_bot_action
from poker_engine.game import GameState


def resolve_bots(state: GameState, human_id: str) -> tuple[GameState, list[dict]]:
    """Returns (final_state, action_log) — the log exists purely for the
    client to narrate what the bots did; it's ephemeral per-request
    information, not part of the persisted GameState, so it's built here
    rather than derived from state afterward."""
    log: list[dict] = []
    while state.street not in TERMINAL_STREETS and state.betting_state.current_actor.player_id != human_id:
        actor_id = state.betting_state.current_actor.player_id
        action = choose_bot_action(state)
        state = state.apply_action(action)
        log.append({"actor_id": actor_id, "action_type": action.action_type.value, "amount": action.amount})
    return state, log
