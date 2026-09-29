import json
import random

from poker_engine.actions import Action, ActionType
from poker_engine.cards import Card, Rank, Suit
from poker_engine.game import GameState
from poker_engine.player import PlayerState

from api.serializers import (
    card_from_str,
    card_to_str,
    game_state_from_dict,
    game_state_to_dict,
)


def roundtrip(state: GameState) -> GameState:
    # Go through real JSON text, not just dict -> dict, so tuples/sets that
    # json.dumps can't encode (or that come back as lists) are actually caught.
    return game_state_from_dict(json.loads(json.dumps(game_state_to_dict(state))))


def random_legal_action(state: GameState, rng: random.Random) -> Action:
    bs = state.betting_state
    actor = bs.current_actor
    allowed = bs.get_allowed_actions(actor.player_id)
    action = rng.choice(allowed)
    if action.action_type is ActionType.RAISE:
        min_raise = bs.big_blind if bs.current_bet == 0 else bs.current_bet + bs.last_raise_increment
        max_raise = actor.chips_in_street + actor.stack
        return Action(ActionType.RAISE, amount=min(min_raise, max_raise))
    return action


def test_every_card_survives_roundtrip():
    for suit in Suit:
        for rank in Rank:
            card = Card(rank, suit)
            code = card_to_str(card)
            assert len(code) == 2
            assert card_from_str(code) == card


def test_random_hands_survive_roundtrip_at_every_step():
    rng = random.Random(1234)
    random.seed(1234)  # Deck.shuffle() uses the global random module

    for hand_no in range(25):
        # Mixed stack sizes so all-ins and side pots actually happen.
        players = [
            PlayerState("A", stack=rng.choice([30, 100, 1000])),
            PlayerState("B", stack=rng.choice([30, 100, 1000])),
            PlayerState("C", stack=rng.choice([30, 100, 1000])),
        ]
        state = GameState.start_new_hand(players, dealer_button_index=hand_no % 3, sb_amount=5, bb_amount=10)

        while state.street not in ("SHOWDOWN", "HAND_OVER"):
            assert roundtrip(state) == state
            state = state.apply_action(random_legal_action(state, rng))

        assert roundtrip(state) == state


def test_rehydrated_state_plays_on_identically():
    rng = random.Random(99)
    random.seed(99)
    players = [PlayerState("A", stack=500), PlayerState("B", stack=500), PlayerState("C", stack=500)]
    original = GameState.start_new_hand(players, 0, 5, 10)

    # Advance a few actions, then "restart the server" by rehydrating from JSON.
    for _ in range(3):
        if original.street in ("SHOWDOWN", "HAND_OVER"):
            break
        original = original.apply_action(random_legal_action(original, rng))
    restored = roundtrip(original)

    # Same future actions applied to both must yield the same states.
    while original.street not in ("SHOWDOWN", "HAND_OVER"):
        action = random_legal_action(original, rng)
        original = original.apply_action(action)
        restored = restored.apply_action(action)
        assert restored == original


def test_terminal_all_in_state_roundtrips_optional_fields():
    # Short stack shoves, big stack calls: the engine runs the board out and
    # populates winners, pots_at_showdown and all_in_snapshot_board.
    random.seed(7)
    state = GameState.start_new_hand([PlayerState("A", 30), PlayerState("B", 1000)], 0, 5, 10)
    state = state.apply_action(Action(ActionType.ALL_IN))
    state = state.apply_action(Action(ActionType.CALL))

    assert state.street == "HAND_OVER"
    assert state.winners is not None
    assert state.pots_at_showdown is not None
    assert state.all_in_snapshot_board is not None
    assert state.betting_state is None

    assert roundtrip(state) == state
