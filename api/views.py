"""GameState -> what one seat is allowed to see.

The serializer stores the whole truth (every hand, the undealt deck). This
module is the boundary that decides what leaves the server for a given viewer.
Nothing here is optional: sending the raw state to a browser would reveal the
bots' hole cards and the exact turn/river before they are dealt.
"""

from __future__ import annotations

from typing import Any

from poker_engine.actions import ActionType
from poker_engine.game import GameState

from api.serializers import card_to_str

TERMINAL_STREETS = ("SHOWDOWN", "HAND_OVER")


def _is_showdown(state: GameState) -> bool:
    # _run_showdown populates pots_at_showdown; a hand won by everyone else
    # folding leaves it None. Only a real showdown obliges players to reveal.
    return state.street == "HAND_OVER" and state.pots_at_showdown is not None


def _legal_actions(state: GameState, viewer_id: str) -> list[dict[str, Any]]:
    bs = state.betting_state
    if bs is None or bs.current_actor.player_id != viewer_id:
        return []

    actor = bs.current_actor
    call_amount = bs.current_bet - actor.chips_in_street
    min_raise = bs.big_blind if bs.current_bet == 0 else bs.current_bet + bs.last_raise_increment
    max_raise = actor.chips_in_street + actor.stack

    actions: list[dict[str, Any]] = []
    for a in bs.get_allowed_actions(viewer_id):
        entry: dict[str, Any] = {"type": a.action_type.value}
        if a.action_type is ActionType.CALL:
            entry["amount"] = min(call_amount, actor.stack)
        elif a.action_type is ActionType.RAISE:
            entry["min"] = min(min_raise, max_raise)
            entry["max"] = max_raise
        elif a.action_type is ActionType.ALL_IN:
            entry["amount"] = actor.stack
        actions.append(entry)
    return actions


def to_player_view(state: GameState, viewer_id: str) -> dict[str, Any]:
    showdown = _is_showdown(state)
    to_act = state.betting_state.current_actor.player_id if state.betting_state is not None else None

    players = []
    for p in state.players:
        reveal = p.player_id == viewer_id or (showdown and not p.is_folded)
        players.append({
            "player_id": p.player_id,
            "stack": p.stack,
            "chips_in_street": p.chips_in_street,
            "chips_in_hand": p.chips_in_hand,
            "is_folded": p.is_folded,
            "is_all_in": p.is_all_in,
            "hole_cards": [card_to_str(c) for c in state.player_hands[p.player_id]] if reveal else None,
        })

    return {
        "viewer_id": viewer_id,
        "street": state.street,
        "is_hand_over": state.street in TERMINAL_STREETS,
        "dealer_button_index": state.dealer_button_index,
        "sb_amount": state.sb_amount,
        "bb_amount": state.bb_amount,
        "board_cards": [card_to_str(c) for c in state.board_cards],
        "pot_total": sum(p.chips_in_hand for p in state.players),
        "current_bet": state.betting_state.current_bet if state.betting_state is not None else 0,
        "to_act": to_act,
        "is_your_turn": to_act == viewer_id,
        "legal_actions": _legal_actions(state, viewer_id),
        "players": players,
        "winners": dict(state.winners) if state.winners is not None else None,
    }
