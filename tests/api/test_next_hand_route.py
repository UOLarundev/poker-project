"""Tests for POST /api/hands/{hand_id}/next.

Reuses the same idempotency ledger and locking pattern as the action
endpoint (see test_actions_route.py for the concurrency-focused tests of
that shared mechanism) — these tests focus on what's new here: carrying
stacks over, rotating the dealer, and the two distinct "game over" cases.
"""

from datetime import datetime, timezone

from sqlalchemy import select

from api.db import SessionLocal
from api.models import Game, Hand
from api.serializers import game_state_to_dict
from poker_engine.cards import Card, Rank, Suit
from poker_engine.game import GameState
from poker_engine.player import PlayerState


def create_game(client, username="arun"):
    body = client.post("/api/games", json={"username": username}).json()
    return body["game_id"], body["hand_id"]


def end_current_hand_by_folding(client, hand_id):
    return client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": "f0000000-0000-0000-0000-000000000000", "action_type": "fold",
    }).json()


def force_finished_state(game_id, hand_id, stacks: dict[str, int], winner: str):
    """Directly overwrite the persisted state to a hand-crafted terminal
    GameState with the given stack distribution — far simpler and more
    deterministic than trying to steer the random bots into busting
    someone via real play."""
    hole_cards = [
        Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.HEARTS),
        Card(Rank.FOUR, Suit.HEARTS), Card(Rank.FIVE, Suit.HEARTS),
        Card(Rank.SIX, Suit.HEARTS), Card(Rank.SEVEN, Suit.HEARTS),
    ]
    ids = list(stacks.keys())
    state = GameState(
        players=tuple(PlayerState(pid, stack=stacks[pid], is_folded=(stacks[pid] == 0)) for pid in ids),
        dealer_button_index=0,
        sb_amount=5,
        bb_amount=10,
        deck_cards=(),
        board_cards=(),
        street="HAND_OVER",
        player_hands={pid: (hole_cards[i * 2], hole_cards[i * 2 + 1]) for i, pid in enumerate(ids)},
        betting_state=None,
        winners={winner: sum(stacks.values())},
    )
    with SessionLocal() as db:
        game = db.get(Game, game_id)
        game.current_state = game_state_to_dict(state)
        hand = db.get(Hand, hand_id)
        hand.ended_at = datetime.now(timezone.utc)
        db.commit()


def test_next_hand_deals_a_new_hand_and_rotates_dealer(client):
    game_id, hand_id = create_game(client)
    end_current_hand_by_folding(client, hand_id)

    resp = client.post(f"/api/hands/{hand_id}/next", json={
        "action_id": "e0000000-0000-0000-0000-000000000001",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["street"] == "PRE_FLOP"
    assert body["dealer_button_index"] == 1
    assert body["hand_id"] != hand_id

    with SessionLocal() as db:
        hands = db.execute(select(Hand).where(Hand.game_id == game_id).order_by(Hand.hand_number)).scalars().all()
        assert [h.hand_number for h in hands] == [1, 2]
        # dealer_button_index=0 in hand #1 means the human acts first with
        # no blind posted yet, so folding immediately costs them nothing —
        # stack carries into hand #2 unchanged.
        assert hands[1].hero_stack_start == 1000
        assert hands[0].ended_at is not None
        assert hands[1].ended_at is None


def test_replaying_next_hand_is_not_reapplied(client):
    game_id, hand_id = create_game(client)
    end_current_hand_by_folding(client, hand_id)
    payload = {"action_id": "e0000000-0000-0000-0000-000000000002"}

    first = client.post(f"/api/hands/{hand_id}/next", json=payload)
    second = client.post(f"/api/hands/{hand_id}/next", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["idempotent-replay"] == "true"
    assert first.json() == second.json()

    with SessionLocal() as db:
        hands = db.execute(select(Hand).where(Hand.game_id == game_id)).scalars().all()
        assert len(hands) == 2  # the retry did not deal a second new hand


def test_next_hand_while_current_hand_still_in_progress_is_409(client):
    _, hand_id = create_game(client)  # hand not finished
    resp = client.post(f"/api/hands/{hand_id}/next", json={
        "action_id": "e0000000-0000-0000-0000-000000000003",
    })
    assert resp.status_code == 409


def test_next_hand_unknown_hand_is_404(client):
    resp = client.post("/api/hands/00000000-0000-0000-0000-000000000000/next", json={
        "action_id": "e0000000-0000-0000-0000-000000000004",
    })
    assert resp.status_code == 404


def test_game_over_when_only_one_player_has_chips(client):
    game_id, hand_id = create_game(client)
    force_finished_state(game_id, hand_id, {"arun": 0, "Bot A": 3000, "Bot B": 0}, winner="Bot A")

    resp = client.post(f"/api/hands/{hand_id}/next", json={
        "action_id": "e0000000-0000-0000-0000-000000000005",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["game_over"] is True
    assert body["winner"] == "Bot A"
    assert body["final_stacks"] == {"arun": 0, "Bot A": 3000, "Bot B": 0}

    with SessionLocal() as db:
        assert db.get(Game, game_id).status == "finished"


def test_game_over_when_human_busts_even_if_two_bots_remain(client):
    """The human-specific rule beyond the generic CLI 'len(survivors)<2':
    two players technically still have chips, but neither is the human,
    so there is no one left for this API game to serve."""
    game_id, hand_id = create_game(client)
    force_finished_state(game_id, hand_id, {"arun": 0, "Bot A": 1500, "Bot B": 1500}, winner="Bot A")

    resp = client.post(f"/api/hands/{hand_id}/next", json={
        "action_id": "e0000000-0000-0000-0000-000000000006",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["game_over"] is True
    assert body["winner"] is None  # ambiguous: two players still contesting, just not the human

    with SessionLocal() as db:
        assert db.get(Game, game_id).status == "finished"
