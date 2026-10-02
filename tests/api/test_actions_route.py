"""Tests for POST /api/hands/{hand_id}/actions — the idempotent action endpoint.

The two concurrency tests at the bottom are the actual evidence for this
depth point: they fire genuinely concurrent HTTP requests (via a thread
pool — our routes are sync `def`, so FastAPI dispatches each one to a real
OS thread) against the same running app and the same Postgres, and assert
on what actually landed in the database afterwards.
"""

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select

from api.db import SessionLocal
from api.models import Action, Game


def create_game(client, username="arun"):
    body = client.post("/api/games", json={"username": username}).json()
    return body["game_id"], body["hand_id"]


def test_submit_legal_action_advances_state(client):
    _, hand_id = create_game(client)
    # Hardcoded dealer_button_index=0 in create_game means the human is
    # always first to act preflop today — no bot-resolution wait needed
    # right after creation. (Flagged in docs/idempotency.md as a
    # consequence of "next hand" not existing yet.)
    resp = client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": "11111111-1111-1111-1111-111111111111",
        "action_type": "fold",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["street"] == "HAND_OVER"
    assert "Idempotent-Replay" not in resp.headers


def test_action_log_narrates_human_action_then_bot_responses(client):
    _, hand_id = create_game(client)
    # Human (first to act, dealer_button_index=0) folds; both bots are then
    # still live and resolve_bots plays the rest of the hand out between
    # them, since neither is "the human" the loop stops for.
    resp = client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": "99999999-1111-1111-1111-111111111111",
        "action_type": "fold",
    })
    log = resp.json()["action_log"]

    assert log[0] == {"actor_id": "arun", "action_type": "fold", "amount": None}
    # Everything after the human's own entry was a bot, never the human
    # again (the hand ended the moment control left them here).
    assert all(entry["actor_id"] in ("Bot A", "Bot B") for entry in log[1:])
    assert len(log) > 1  # the bots had to play the hand to some conclusion


def test_fresh_game_and_plain_get_have_empty_action_log(client):
    game_id, _ = create_game(client)
    created = client.post("/api/games", json={"username": "someoneelse"}).json()
    fetched = client.get(f"/api/games/{game_id}").json()

    assert created["action_log"] == []
    assert fetched["action_log"] == []


def test_replaying_same_action_id_is_not_reapplied(client):
    game_id, hand_id = create_game(client)
    action_id = "22222222-2222-2222-2222-222222222222"
    payload = {"action_id": action_id, "action_type": "fold"}

    first = client.post(f"/api/hands/{hand_id}/actions", json=payload)
    second = client.post(f"/api/hands/{hand_id}/actions", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.headers["idempotent-replay"] == "true"
    assert first.json() == second.json()

    with SessionLocal() as db:
        rows = db.execute(select(Action).where(Action.hand_id == hand_id)).scalars().all()
        assert len(rows) == 1  # the retry never inserted a second row

        game = db.get(Game, game_id)
        assert game.version == 1  # state only ever transitioned once


def test_illegal_action_returns_400_and_does_not_burn_the_action_id(client):
    _, hand_id = create_game(client)
    action_id = "33333333-3333-3333-3333-333333333333"

    # A raise with no amount is illegal regardless of game state — the
    # engine itself requires an amount for a raise.
    bad = client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": action_id, "action_type": "raise",
    })
    assert bad.status_code == 400

    # Same action_id, now with a legal action (fold is always legal for
    # whoever's turn it is) — must succeed, proving the rejected attempt
    # didn't permanently consume the id.
    retry = client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": action_id, "action_type": "fold",
    })
    assert retry.status_code == 201


def test_hand_not_found_is_404(client):
    resp = client.post("/api/hands/00000000-0000-0000-0000-000000000000/actions", json={
        "action_id": "44444444-4444-4444-4444-444444444444", "action_type": "fold",
    })
    assert resp.status_code == 404


def test_acting_on_a_finished_hand_is_409(client):
    _, hand_id = create_game(client)
    client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": "55555555-5555-5555-5555-555555555555", "action_type": "fold",
    })
    again = client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": "66666666-6666-6666-6666-666666666666", "action_type": "fold",
    })
    assert again.status_code == 409


def test_20_concurrent_identical_requests_apply_exactly_once(client):
    """The unique constraint's job: same action, retried under real
    concurrency (not just sequentially), still only ever applies once."""
    game_id, hand_id = create_game(client)
    action_id = "77777777-7777-7777-7777-777777777777"
    payload = {"action_id": action_id, "action_type": "fold"}

    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda _: client.post(f"/api/hands/{hand_id}/actions", json=payload), range(20)))

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200] * 19 + [201]

    with SessionLocal() as db:
        rows = db.execute(select(Action).where(Action.hand_id == hand_id)).scalars().all()
        assert len(rows) == 1

        game = db.get(Game, game_id)
        assert game.version == 1


def test_20_concurrent_different_actions_no_lost_updates(client):
    """The row lock's job: 20 genuinely different, independently-legitimate
    action submissions racing for the same hand — exactly one may win,
    and the other 19 must be cleanly rejected, not silently double-applied
    or corrupt state."""
    game_id, hand_id = create_game(client)
    action_ids = [f"88888888-8888-8888-8888-{i:012d}" for i in range(20)]
    payloads = [{"action_id": aid, "action_type": "fold"} for aid in action_ids]

    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda p: client.post(f"/api/hands/{hand_id}/actions", json=p), payloads))

    statuses = [r.status_code for r in responses]
    assert statuses.count(201) == 1  # exactly one actually applied
    assert statuses.count(409) == 19  # the rest: stale, not silently accepted
    assert all(s in (201, 409) for s in statuses)  # no 5xx, no other surprise

    with SessionLocal() as db:
        # Only the winner's action ever got durably persisted.
        rows = db.execute(select(Action).where(Action.hand_id == hand_id)).scalars().all()
        assert len(rows) == 1

        # State transitioned exactly once — not 20 times, not zero times.
        game = db.get(Game, game_id)
        assert game.version == 1
