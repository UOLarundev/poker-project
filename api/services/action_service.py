"""Submitting a player action: idempotent, and safe under concurrency.

These are two separate guarantees, given by two separate mechanisms:

- Concurrency (no lost updates when different actions race): a
  `SELECT ... FOR UPDATE` on the game row. Postgres blocks any other
  transaction touching the same game until this one commits or rolls
  back, so two different actions can never both read the same stale
  state and stomp on each other.

- Idempotency (the same action, retried, only ever applies once): the
  UNIQUE(hand_id, action_id) constraint on `actions`. The insert is
  attempted with `flush()` (not `commit()`) specifically so a duplicate
  is caught *before* anything else happens, and so a REJECTED action
  (illegal move) can be rolled back without permanently burning that
  action_id — flush sends the INSERT to Postgres for constraint
  checking, but nothing is durable until commit.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api import models
from api.serializers import card_to_str, game_state_from_dict, game_state_to_dict
from api.services.bot_service import resolve_bots
from api.services.game_service import BB_AMOUNT, SB_AMOUNT
from api.views import TERMINAL_STREETS, to_player_view
from poker_engine.actions import Action, ActionType
from poker_engine.game import GameState
from poker_engine.player import PlayerState


class HandNotFoundError(Exception):
    pass


class HandAlreadyOverError(Exception):
    pass


class NotYourTurnError(Exception):
    pass


class IllegalActionError(Exception):
    pass


def _next_seq(db: Session, hand_id: uuid.UUID) -> int:
    # Safe from races only because the caller already holds the game row's
    # FOR UPDATE lock before this runs — every action for hands under this
    # game funnels through that same lock first.
    max_seq = db.scalar(select(func.max(models.Action.seq)).where(models.Action.hand_id == hand_id))
    return (max_seq or 0) + 1


def submit_action(
    db: Session,
    hand_id: uuid.UUID,
    action_id: uuid.UUID,
    action_type: str,
    amount: int | None,
) -> tuple[dict, bool]:
    """Returns (response_body, is_replay)."""
    hand = db.get(models.Hand, hand_id)
    if hand is None:
        raise HandNotFoundError(f"No hand {hand_id}")

    # Lock the game row FIRST, before touching anything else. Any other
    # request for this same game now waits right here until we commit or
    # roll back.
    game = db.execute(select(models.Game).where(models.Game.id == hand.game_id).with_for_update()).scalar_one()
    human_id = game.player.username

    action_row = models.Action(
        hand_id=hand_id,
        action_id=action_id,
        seq=_next_seq(db, hand_id),
        actor_id=human_id,
        action_type=action_type,
        amount=amount,
    )
    db.add(action_row)
    try:
        db.flush()
    except IntegrityError:
        # Same (hand_id, action_id) already exists: a retry, not a new
        # action. Replay exactly what was returned the first time.
        db.rollback()
        existing = db.execute(
            select(models.Action).where(models.Action.hand_id == hand_id, models.Action.action_id == action_id)
        ).scalar_one()
        return existing.response_body, True

    # Reserved successfully — now actually apply it.
    if hand.ended_at is not None:
        db.rollback()
        raise HandAlreadyOverError("This hand has already finished")

    state = game_state_from_dict(game.current_state)
    if state.street in TERMINAL_STREETS:
        db.rollback()
        raise HandAlreadyOverError("This hand has already finished")
    if state.betting_state.current_actor.player_id != human_id:
        db.rollback()
        raise NotYourTurnError(f"It is {state.betting_state.current_actor.player_id}'s turn, not yours")

    try:
        state = state.apply_action(Action(ActionType(action_type), amount=amount))
    except ValueError as e:
        # Illegal move (e.g. checking into a bet). Rolling back discards the
        # reserved action_id too, so the client can legitimately retry with
        # a corrected action under the same id.
        db.rollback()
        raise IllegalActionError(str(e)) from e

    # The human's own action starts the narration log; whatever the bots do
    # next (possibly nothing, if it's still someone else's turn — it isn't,
    # here, by construction) is appended after it.
    action_log = [{"actor_id": human_id, "action_type": action_type, "amount": amount}]
    state, bot_log = resolve_bots(state, human_id)
    action_log.extend(bot_log)

    if state.street in TERMINAL_STREETS:
        hand.ended_at = datetime.now(timezone.utc)
        hand.board = [card_to_str(c) for c in state.board_cards]
        hand.winners = dict(state.winners) if state.winners is not None else None
        hand.pot_total = sum(state.winners.values()) if state.winners is not None else 0
        human_stack = next(p.stack for p in state.players if p.player_id == human_id)
        hand.hero_net = human_stack - hand.hero_stack_start

    game.current_state = game_state_to_dict(state)
    game.version += 1

    view = to_player_view(state, human_id)
    response_body = {**view, "game_id": str(game.id), "hand_id": str(hand.id), "action_log": action_log}
    action_row.response_body = response_body

    db.commit()
    return response_body, False


def start_next_hand(db: Session, finished_hand_id: uuid.UUID, action_id: uuid.UUID) -> tuple[dict, bool]:
    """Returns (response_body, is_replay). response_body is either a
    GameView-shaped dict (a new hand was dealt) or a GameOverView-shaped
    dict (fewer than 2 players — or not the human — have chips left)."""
    finished_hand = db.get(models.Hand, finished_hand_id)
    if finished_hand is None:
        raise HandNotFoundError(f"No hand {finished_hand_id}")

    game = db.execute(
        select(models.Game).where(models.Game.id == finished_hand.game_id).with_for_update()
    ).scalar_one()
    human_id = game.player.username

    # Same idempotency ledger as poker actions, reused deliberately: "has
    # 'next_hand' already been recorded against this now-finished hand?"
    # is the same shape of question as "was this action already applied?"
    # — and dealing involves a real shuffle, so a naive retry would deal a
    # DIFFERENT hand, not just reapply the same one.
    action_row = models.Action(
        hand_id=finished_hand_id,
        action_id=action_id,
        seq=_next_seq(db, finished_hand_id),
        actor_id=human_id,
        action_type="next_hand",
        amount=None,
    )
    db.add(action_row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.execute(
            select(models.Action).where(
                models.Action.hand_id == finished_hand_id, models.Action.action_id == action_id
            )
        ).scalar_one()
        return existing.response_body, True

    if finished_hand.ended_at is None:
        db.rollback()
        raise HandAlreadyOverError("Cannot start the next hand: the current hand is still in progress")

    state = game_state_from_dict(game.current_state)

    # Carry over chips, drop anyone who busted, rotate the dealer button.
    # Mirrors interface/cli.py's play_game() loop exactly — that logic is
    # inline there, not a callable, so it's reproduced here rather than
    # imported (frozen file, nothing to import).
    survivors = [PlayerState(p.player_id, p.stack) for p in state.players if p.stack > 0]

    # len(survivors) < 2 is the generic "hand can't continue" rule (matches
    # the CLI). The human-specific check is API-only: the CLI's loop simply
    # has no one left to prompt if the human busts, even with 2 bots still
    # playing each other; here that has to be a real, explicit decision
    # since there's no interactive "still there?" moment.
    human_survived = any(p.player_id == human_id for p in survivors)
    if len(survivors) < 2 or not human_survived:
        game.status = "finished"
        response_body = {
            "game_id": str(game.id),
            "game_over": True,
            "winner": survivors[0].player_id if len(survivors) == 1 else None,
            "final_stacks": {p.player_id: p.stack for p in state.players},
        }
        action_row.response_body = response_body
        db.commit()
        return response_body, False

    # Not a precise seat-remapping through a bust (this models a rotating
    # marker, not fixed physical seats) — fine here since the only
    # consequence is which of two remaining players is next to act, not
    # any corruption of chips.
    next_dealer_index = (state.dealer_button_index + 1) % len(survivors)
    new_state = GameState.start_new_hand(survivors, dealer_button_index=next_dealer_index, sb_amount=SB_AMOUNT, bb_amount=BB_AMOUNT)
    # No human action to prepend here — dealing a hand isn't a poker action
    # — just whatever bots did before it came back around to the human.
    new_state, action_log = resolve_bots(new_state, human_id)

    new_hand = models.Hand(
        game_id=game.id,
        player_id=finished_hand.player_id,
        hand_number=finished_hand.hand_number + 1,
        hero_stack_start=next(p.stack for p in survivors if p.player_id == human_id),
        hero_hole=[card_to_str(c) for c in new_state.player_hands[human_id]],
    )
    db.add(new_hand)
    db.flush()  # assigns new_hand.id, needed for the response below

    game.current_state = game_state_to_dict(new_state)
    game.version += 1

    view = to_player_view(new_state, human_id)
    response_body = {**view, "game_id": str(game.id), "hand_id": str(new_hand.id), "action_log": action_log}
    action_row.response_body = response_body

    db.commit()
    return response_body, False
