"""Seed synthetic hand-history data for the indexing depth point.

Generates ~N_PLAYERS * avg(HANDS_PER_PLAYER_RANGE) rows in `hands` — real
Monte Carlo play costs ~13s/hand locally (worse on a throttled deploy), so
300k real hands isn't happening. None of this needs to be a *valid* poker
hand: the thing being measured is the query planner's behaviour on
WHERE player_id = $1 ORDER BY started_at DESC LIMIT 20, which only cares
about row shape and volume, not game correctness.

Run against LOCAL Postgres only (default DATABASE_URL) — no reason to put
300k fake rows in the real deployed database. Truncates first for a clean,
reproducible baseline.

Usage: python scripts/seed_hands.py [--players 1000] [--min-hands 100] [--max-hands 500]
"""

from __future__ import annotations

import argparse
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from api.db import engine
from api.models import Game, Hand, Player

RANKS = "23456789TJQKA"
SUITS = "HDCS"
CHUNK_SIZE = 5000


def fake_card() -> str:
    return random.choice(RANKS) + random.choice(SUITS)


def fake_cards(n: int) -> list[str]:
    return [fake_card() for _ in range(n)]


def random_timestamp(days_back: int = 180) -> datetime:
    offset = timedelta(seconds=random.randint(0, days_back * 24 * 3600))
    return datetime.now(timezone.utc) - offset


def seed(num_players: int, min_hands: int, max_hands: int) -> None:
    with engine.begin() as conn:
        print("Truncating actions, hands, games, players for a clean baseline...")
        conn.execute(text("TRUNCATE TABLE actions, hands, games, players RESTART IDENTITY CASCADE"))

    total_hands = 0
    t0 = time.perf_counter()

    with engine.begin() as conn:
        for p in range(num_players):
            username = f"seed_player_{p:05d}"
            player_id = uuid.uuid4()
            game_id = uuid.uuid4()

            conn.execute(
                Player.__table__.insert(),
                {"id": player_id, "username": username},
            )
            conn.execute(
                Game.__table__.insert(),
                {
                    "id": game_id,
                    "player_id": player_id,
                    "status": "finished",
                    "current_state": {},
                    "version": random.randint(1, 50),
                },
            )

            n_hands = random.randint(min_hands, max_hands)
            rows = []
            for hand_number in range(1, n_hands + 1):
                started = random_timestamp()
                hero_net = random.randint(-500, 500)
                rows.append({
                    "id": uuid.uuid4(),
                    "game_id": game_id,
                    "player_id": player_id,
                    "hand_number": hand_number,
                    "hero_stack_start": 1000,
                    "started_at": started,
                    "ended_at": started + timedelta(seconds=random.randint(10, 300)),
                    "board": fake_cards(5),
                    "hero_hole": fake_cards(2),
                    "winners": {username: max(hero_net, 0)} if hero_net >= 0 else {"Bot A": -hero_net},
                    "pot_total": abs(hero_net) + random.randint(10, 100),
                    "hero_net": hero_net,
                })

            for i in range(0, len(rows), CHUNK_SIZE):
                conn.execute(Hand.__table__.insert(), rows[i : i + CHUNK_SIZE])

            total_hands += n_hands
            if (p + 1) % 100 == 0:
                elapsed = time.perf_counter() - t0
                print(f"  {p + 1}/{num_players} players, {total_hands} hands so far ({elapsed:.1f}s)")

    elapsed = time.perf_counter() - t0
    print(f"Done: {num_players} players, {total_hands} hands in {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", type=int, default=1000)
    parser.add_argument("--min-hands", type=int, default=100)
    parser.add_argument("--max-hands", type=int, default=500)
    args = parser.parse_args()
    seed(args.players, args.min_hands, args.max_hands)
