from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from poker_engine.player import PlayerState
from poker_engine.actions import Action, ActionType


@dataclass(frozen=True)
class BettingRoundState:
    """Immutable state representing a single betting round"""
    players: tuple[PlayerState, ...]
    current_actor_index: int
    current_bet: int
    last_raise_increment: int
    big_blind: int
    acted_player_ids: frozenset[str] = frozenset()
    can_raise_player_ids: frozenset[str] = frozenset()

    @classmethod
    def initialize(
        cls, 
        players: Sequence[PlayerState], 
        first_actor_index: int, 
        current_bet: int, 
        last_raise_increment: int, 
        big_blind: int
    ) -> BettingRoundState:
        """Initialize new betting round."""
        players_tuple = tuple(players)
        # Initially, all active players (who are not all-in) can raise
        can_raise = frozenset(
            p.player_id for p in players_tuple if not p.is_folded and not p.is_all_in
        )
        # If starting with a bet (e.g. blinds), set acted_player_ids appropriately.
        return cls(
            players=players_tuple,
            current_actor_index=first_actor_index,
            current_bet=current_bet,
            last_raise_increment=last_raise_increment,
            big_blind=big_blind,
            acted_player_ids=frozenset(),
            can_raise_player_ids=can_raise
        )

    @property
    def current_actor(self) -> PlayerState:
        return self.players[self.current_actor_index]

    def get_allowed_actions(self, player_id: str) -> list[Action]:
        """Return the list of valid actions for the given player."""
        player = next((p for p in self.players if p.player_id == player_id), None)
        if player is None or player.is_folded or player.is_all_in:
            return []

        actions = [Action(ActionType.FOLD)]
        
        # Check
        if self.current_bet == player.chips_in_street:
            actions.append(Action(ActionType.CHECK))
            
        # Call
        if self.current_bet > player.chips_in_street:
            actions.append(Action(ActionType.CALL))
            
        # Raise
        if player_id in self.can_raise_player_ids:
            # Must have chips left to raise beyond the call amount
            call_amount = self.current_bet - player.chips_in_street
            if player.stack > call_amount:
                actions.append(Action(ActionType.RAISE))
                
        # All-in is always a possibility if player has chips
        if player.stack > 0:
            actions.append(Action(ActionType.ALL_IN))
            
        return actions

    def apply_action(self, action: Action) -> BettingRoundState:
        """Validate and apply a player's action, returning a new BettingRoundState."""
        actor = self.current_actor
        allowed_actions = self.get_allowed_actions(actor.player_id)
        
        # Check if the action type is allowed
        if not any(a.action_type == action.action_type for a in allowed_actions):
            raise ValueError(f"Action {action.action_type} is not allowed for {actor.player_id}")

        new_players = list(self.players)
        new_acted = set(self.acted_player_ids)
        new_can_raise = set(self.can_raise_player_ids)
        
        new_current_bet = self.current_bet
        new_last_raise = self.last_raise_increment

        if action.action_type == ActionType.FOLD:
            # Mark player as folded
            new_players[self.current_actor_index] = actor.fold()
            new_acted.add(actor.player_id)
            new_can_raise.discard(actor.player_id)

        elif action.action_type == ActionType.CHECK:
            # Check is only allowed if facing no bet
            new_acted.add(actor.player_id)
            new_can_raise.discard(actor.player_id)

        elif action.action_type == ActionType.CALL:
            call_amount = self.current_bet - actor.chips_in_street
            actual_bet = min(call_amount, actor.stack)
            new_players[self.current_actor_index] = actor.bet_chips(actual_bet)
            new_acted.add(actor.player_id)
            new_can_raise.discard(actor.player_id)

        elif action.action_type == ActionType.RAISE:
            if action.amount is None:
                raise ValueError("Raise action must specify an amount")
            
            # The raise amount is the TOTAL street contribution the player wants to reach
            target_amount = action.amount
            added_chips = target_amount - actor.chips_in_street
            
            if added_chips <= 0 or added_chips > actor.stack:
                raise ValueError(f"Invalid raise amount {target_amount} for player with stack {actor.stack}")
                
            raise_increment = target_amount - self.current_bet
            min_raise_limit = self.current_bet + self.last_raise_increment
            
            # If current_bet is 0, minimum opening bet is big_blind
            if self.current_bet == 0:
                min_raise_limit = self.big_blind

            is_all_in_raise = (added_chips == actor.stack)
            
            # Verify raise size is legal (must be at least min raise, unless all-in)
            if target_amount < min_raise_limit and not is_all_in_raise:
                raise ValueError(
                    f"Raise to {target_amount} is below minimum raise of {min_raise_limit}"
                )

            # Apply the bet
            new_players[self.current_actor_index] = actor.bet_chips(added_chips)
            
            # Determine if this raise reopens the betting (is a full raise)
            is_full_raise = False
            if self.current_bet == 0:
                is_full_raise = (target_amount >= self.big_blind)
            else:
                is_full_raise = (raise_increment >= self.last_raise_increment)

            new_current_bet = target_amount
            if is_full_raise:
                new_last_raise = raise_increment if self.current_bet > 0 else target_amount
                # Reopens betting for all active players except the actor
                new_can_raise = {
                    p.player_id for p in new_players 
                    if not p.is_folded and not p.is_all_in and p.player_id != actor.player_id
                }
            else:
                # Under-all-in raise: does NOT reopen betting for others.
                # Actor cannot raise again.
                new_can_raise.discard(actor.player_id)
                
            # Reset acted player IDs because there is a new bet to face.
            # Everyone except the actor must act again.
            new_acted = {actor.player_id}

        elif action.action_type == ActionType.ALL_IN:
            total_chips_in_street = actor.chips_in_street + actor.stack
            # Treat as raise or call depending on the amount
            if total_chips_in_street > self.current_bet:
                # Check if actor is allowed to raise
                if actor.player_id not in self.can_raise_player_ids:
                    raise ValueError(f"Player {actor.player_id} cannot raise all-in because betting is not reopened")
                # Delegate to raise logic
                return self.apply_action(Action(ActionType.RAISE, amount=total_chips_in_street))
            else:
                # Delegate to call logic
                return self.apply_action(Action(ActionType.CALL))

        # Check if the round is complete
        temp_state = BettingRoundState(
            players=tuple(new_players),
            current_actor_index=self.current_actor_index,
            current_bet=new_current_bet,
            last_raise_increment=new_last_raise,
            big_blind=self.big_blind,
            acted_player_ids=frozenset(new_acted),
            can_raise_player_ids=frozenset(new_can_raise)
        )

        if temp_state.is_round_complete():
            return temp_state

        # Find next actor index
        next_actor_idx = temp_state._find_next_actor(temp_state.players, self.current_actor_index)
        if next_actor_idx is None:
            # No one left to act, round is complete
            return temp_state

        return BettingRoundState(
            players=temp_state.players,
            current_actor_index=next_actor_idx,
            current_bet=temp_state.current_bet,
            last_raise_increment=temp_state.last_raise_increment,
            big_blind=temp_state.big_blind,
            acted_player_ids=temp_state.acted_player_ids,
            can_raise_player_ids=temp_state.can_raise_player_ids
        )

    def is_round_complete(self) -> bool:
        """Return True if the betting round has concluded."""
        active_players = [p for p in self.players if not p.is_folded]
        if len(active_players) <= 1:
            return True

        actors = [p for p in active_players if not p.is_all_in]
        if not actors:
            return True

        # If anyone has not acted, round is not complete
        for p in actors:
            if p.player_id not in self.acted_player_ids:
                return False
            if p.chips_in_street != self.current_bet:
                return False

        return True

    def _find_next_actor(self, players: tuple[PlayerState, ...], start_idx: int) -> int | None:
        n = len(players)
        for i in range(1, n + 1):
            idx = (start_idx + i) % n
            p = players[idx]
            if not p.is_folded and not p.is_all_in:
                return idx
        return None
