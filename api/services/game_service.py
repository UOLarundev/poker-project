"""Business logic for creating and reading games.

Routes stay thin (parse request, call here, shape response). This is where
the engine, the ORM, and the serializer actually meet.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from poker_engine.game import GameState
from poker_engine.player import PlayerState

from api import models
from api.serializers import card_to_str, game_state_from_dict, game_state_to_dict

STARTING_STACK = 1000
SB_AMOUNT = 5
BB_AMOUNT = 10
BOT_IDS = ("Bot A", "Bot B")


def get_or_create_player(db: Session, username: str) -> models.Player:
    player = db.scalar(select(models.Player).where(models.Player.username == username))
    if player is not None:
        return player
    player = models.Player(username=username)
    db.add(player)
    db.flush()  # assigns player.id without ending the transaction
    return player


def create_game(db: Session, username: str) -> tuple[models.Game, models.Hand, GameState]:
    """Seat the human against two bots and deal hand #1."""
    player = get_or_create_player(db, username)

    seats = [
        PlayerState(player_id=username, stack=STARTING_STACK),
        PlayerState(player_id=BOT_IDS[0], stack=STARTING_STACK),
        PlayerState(player_id=BOT_IDS[1], stack=STARTING_STACK),
    ]
    state = GameState.start_new_hand(seats, dealer_button_index=0, sb_amount=SB_AMOUNT, bb_amount=BB_AMOUNT)

    game = models.Game(
        player_id=player.id,
        status="in_progress",
        current_state=game_state_to_dict(state),
        version=0,
    )
    db.add(game)
    db.flush()  # assigns game.id, needed for the Hand's foreign key below

    hand = models.Hand(
        game_id=game.id,
        player_id=player.id,
        hand_number=1,
        hero_hole=[card_to_str(c) for c in state.player_hands[username]],
    )
    db.add(hand)
    db.commit()
    return game, hand, state


def get_game(db: Session, game_id: uuid.UUID) -> tuple[models.Game, models.Hand | None, GameState] | None:
    game = db.get(models.Game, game_id)
    if game is None:
        return None

    # The hand still in progress for this game. No hand ever gets ended_at
    # set yet (that lands with next weekend's action endpoint), so today
    # this always resolves — the None case is a placeholder for that.
    hand = db.scalar(
        select(models.Hand)
        .where(models.Hand.game_id == game.id, models.Hand.ended_at.is_(None))
        .order_by(models.Hand.started_at.desc())
    )
    state = game_state_from_dict(game.current_state)
    return game, hand, state
