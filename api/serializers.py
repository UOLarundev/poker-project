"""GameState <-> JSON-safe dict.

This is the only module in `api` that touches engine internals. Everything
above it works with plain dicts, so the engine's dataclass layout can change
without leaking into routes, storage, or the frontend.

Wire format is a contract with Postgres and the browser, so it is defined
here explicitly rather than derived from the engine's __str__ methods.
"""

from __future__ import annotations

from typing import Any

from poker_engine.betting_round import BettingRoundState
from poker_engine.cards import Card, Rank, Suit
from poker_engine.game import GameState
from poker_engine.player import PlayerState
from poker_engine.pot import Pot

# Standard poker notation: every card is exactly two characters, e.g. "AS", "TH", "9C".
_RANK_TO_CHAR = {
    Rank.TWO: "2", Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5", Rank.SIX: "6",
    Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9", Rank.TEN: "T",
    Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A",
}
_CHAR_TO_RANK = {char: rank for rank, char in _RANK_TO_CHAR.items()}


def card_to_str(card: Card) -> str:
    return f"{_RANK_TO_CHAR[card.rank]}{card.suit.value}"


def card_from_str(text: str) -> Card:
    if len(text) != 2 or text[0] not in _CHAR_TO_RANK:
        raise ValueError(f"Invalid card code: {text!r}")
    return Card(rank=_CHAR_TO_RANK[text[0]], suit=Suit(text[1]))


def _cards_to_list(cards) -> list[str]:
    return [card_to_str(c) for c in cards]


def _cards_from_list(codes) -> tuple[Card, ...]:
    return tuple(card_from_str(c) for c in codes)


def _player_to_dict(p: PlayerState) -> dict[str, Any]:
    return {
        "player_id": p.player_id,
        "stack": p.stack,
        "chips_in_street": p.chips_in_street,
        "chips_in_hand": p.chips_in_hand,
        "is_folded": p.is_folded,
        "is_all_in": p.is_all_in,
    }


def _player_from_dict(d: dict[str, Any]) -> PlayerState:
    return PlayerState(
        player_id=d["player_id"],
        stack=d["stack"],
        chips_in_street=d["chips_in_street"],
        chips_in_hand=d["chips_in_hand"],
        is_folded=d["is_folded"],
        is_all_in=d["is_all_in"],
    )


def _betting_to_dict(b: BettingRoundState) -> dict[str, Any]:
    return {
        "players": [_player_to_dict(p) for p in b.players],
        "current_actor_index": b.current_actor_index,
        "current_bet": b.current_bet,
        "last_raise_increment": b.last_raise_increment,
        "big_blind": b.big_blind,
        # Sets have no JSON form; sorted lists keep the output deterministic.
        "acted_player_ids": sorted(b.acted_player_ids),
        "can_raise_player_ids": sorted(b.can_raise_player_ids),
    }


def _betting_from_dict(d: dict[str, Any]) -> BettingRoundState:
    return BettingRoundState(
        players=tuple(_player_from_dict(p) for p in d["players"]),
        current_actor_index=d["current_actor_index"],
        current_bet=d["current_bet"],
        last_raise_increment=d["last_raise_increment"],
        big_blind=d["big_blind"],
        acted_player_ids=frozenset(d["acted_player_ids"]),
        can_raise_player_ids=frozenset(d["can_raise_player_ids"]),
    )


def _pot_to_dict(pot: Pot) -> dict[str, Any]:
    return {"amount": pot.amount, "eligible_player_ids": sorted(pot.eligible_player_ids)}


def _pot_from_dict(d: dict[str, Any]) -> Pot:
    return Pot(amount=d["amount"], eligible_player_ids=set(d["eligible_player_ids"]))


def game_state_to_dict(state: GameState) -> dict[str, Any]:
    return {
        "players": [_player_to_dict(p) for p in state.players],
        "dealer_button_index": state.dealer_button_index,
        "sb_amount": state.sb_amount,
        "bb_amount": state.bb_amount,
        "deck_cards": _cards_to_list(state.deck_cards),
        "board_cards": _cards_to_list(state.board_cards),
        "street": state.street,
        "player_hands": {pid: _cards_to_list(hand) for pid, hand in state.player_hands.items()},
        "betting_state": _betting_to_dict(state.betting_state) if state.betting_state is not None else None,
        "winners": dict(state.winners) if state.winners is not None else None,
        "pots_at_showdown": (
            [_pot_to_dict(p) for p in state.pots_at_showdown]
            if state.pots_at_showdown is not None else None
        ),
        "all_in_snapshot_board": (
            _cards_to_list(state.all_in_snapshot_board)
            if state.all_in_snapshot_board is not None else None
        ),
    }


def game_state_from_dict(d: dict[str, Any]) -> GameState:
    return GameState(
        players=tuple(_player_from_dict(p) for p in d["players"]),
        dealer_button_index=d["dealer_button_index"],
        sb_amount=d["sb_amount"],
        bb_amount=d["bb_amount"],
        deck_cards=_cards_from_list(d["deck_cards"]),
        board_cards=_cards_from_list(d["board_cards"]),
        street=d["street"],
        player_hands={pid: _cards_from_list(hand) for pid, hand in d["player_hands"].items()},
        betting_state=_betting_from_dict(d["betting_state"]) if d["betting_state"] is not None else None,
        winners=dict(d["winners"]) if d["winners"] is not None else None,
        pots_at_showdown=(
            tuple(_pot_from_dict(p) for p in d["pots_at_showdown"])
            if d["pots_at_showdown"] is not None else None
        ),
        all_in_snapshot_board=(
            _cards_from_list(d["all_in_snapshot_board"])
            if d["all_in_snapshot_board"] is not None else None
        ),
    )
