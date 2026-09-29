import json
import random
from typing import Any

from test_serializers import random_legal_action

from api.serializers import card_to_str
from api.views import to_player_view
from poker_engine.actions import Action, ActionType
from poker_engine.game import GameState
from poker_engine.player import PlayerState


def leaf_strings(obj: Any) -> set[str]:
    """Every string value anywhere in a JSON-like structure."""
    if isinstance(obj, str):
        return {obj}
    if isinstance(obj, dict):
        return set().union(*(leaf_strings(v) for v in obj.values())) if obj else set()
    if isinstance(obj, list):
        return set().union(*(leaf_strings(v) for v in obj)) if obj else set()
    return set()


def assert_no_hidden_info(state: GameState, viewer_id: str) -> None:
    view = json.loads(json.dumps(to_player_view(state, viewer_id)))  # must be JSON-safe
    seen = leaf_strings(view)

    for card in state.deck_cards:
        assert card_to_str(card) not in seen, f"undealt deck card leaked to {viewer_id}"

    for pid, hand in state.player_hands.items():
        if pid == viewer_id:
            continue
        for card in hand:
            assert card_to_str(card) not in seen, f"{pid}'s hole card leaked to {viewer_id}"


def test_no_seat_ever_sees_hidden_cards_mid_hand():
    rng = random.Random(2024)
    random.seed(2024)

    for hand_no in range(25):
        players = [PlayerState(pid, stack=rng.choice([30, 100, 1000])) for pid in ("A", "B", "C")]
        state = GameState.start_new_hand(players, hand_no % 3, 5, 10)

        while state.street not in ("SHOWDOWN", "HAND_OVER"):
            for pid in ("A", "B", "C"):
                assert_no_hidden_info(state, pid)
            state = state.apply_action(random_legal_action(state, rng))

        # Even at hand end the deck is never sent.
        for pid in ("A", "B", "C"):
            view = to_player_view(state, pid)
            assert "deck_cards" not in view


def test_viewer_always_sees_own_cards_and_only_own_legal_actions():
    random.seed(5)
    state = GameState.start_new_hand([PlayerState("A", 500), PlayerState("B", 500), PlayerState("C", 500)], 0, 5, 10)
    actor = state.betting_state.current_actor.player_id

    for pid in ("A", "B", "C"):
        view = to_player_view(state, pid)
        me = next(p for p in view["players"] if p["player_id"] == pid)
        assert me["hole_cards"] == [card_to_str(c) for c in state.player_hands[pid]]
        assert view["to_act"] == actor
        assert view["is_your_turn"] == (pid == actor)
        assert bool(view["legal_actions"]) == (pid == actor)


def test_showdown_reveals_unfolded_hands_but_not_folded_ones():
    # A folds; B (short) shoves; C calls -> real showdown between B and C.
    random.seed(11)
    players = [PlayerState("A", 500), PlayerState("B", 40), PlayerState("C", 500)]
    state = GameState.start_new_hand(players, 0, 5, 10)  # A is button and acts first

    state = state.apply_action(Action(ActionType.FOLD))    # A
    state = state.apply_action(Action(ActionType.ALL_IN))  # B
    state = state.apply_action(Action(ActionType.CALL))    # C
    assert state.street == "HAND_OVER" and state.pots_at_showdown is not None

    view = to_player_view(state, "A")
    by_id = {p["player_id"]: p for p in view["players"]}
    assert by_id["B"]["hole_cards"] is not None
    assert by_id["C"]["hole_cards"] is not None
    assert by_id["A"]["hole_cards"] is not None  # own cards, always
    assert view["winners"] == state.winners

    # Folded player's cards stay hidden from the others.
    assert {p["player_id"]: p for p in to_player_view(state, "B")["players"]}["A"]["hole_cards"] is None


def test_fold_win_reveals_nothing():
    random.seed(12)
    state = GameState.start_new_hand([PlayerState("A", 500), PlayerState("B", 500), PlayerState("C", 500)], 0, 5, 10)
    state = state.apply_action(Action(ActionType.FOLD))  # A
    state = state.apply_action(Action(ActionType.FOLD))  # B -> C wins uncontested
    assert state.street == "HAND_OVER" and state.pots_at_showdown is None

    view = to_player_view(state, "A")
    by_id = {p["player_id"]: p for p in view["players"]}
    assert by_id["C"]["hole_cards"] is None
    assert by_id["B"]["hole_cards"] is None
    assert view["is_hand_over"] is True
    assert view["winners"] == state.winners
