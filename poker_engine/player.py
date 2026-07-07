from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PlayerState:
    """Immutable representation of a player's state during a hand."""
    player_id: str
    stack: int
    chips_in_street: int = 0
    chips_in_hand: int = 0
    is_folded: bool = False
    is_all_in: bool = False

    def bet_chips(self, amount: int) -> PlayerState:
        """Return new PlayerState after betting/calling/raising amount of chips."""
        if amount > self.stack:
            raise ValueError(f"Player {self.player_id} cannot bet {amount} with a stack of {self.stack}")
        
        new_stack = self.stack - amount
        new_all_in = self.is_all_in or (new_stack == 0)
        
        return PlayerState(
            player_id=self.player_id,
            stack=new_stack,
            chips_in_street=self.chips_in_street + amount,
            chips_in_hand=self.chips_in_hand + amount,
            is_folded=self.is_folded,
            is_all_in=new_all_in
        )

    def fold(self) -> PlayerState:
        """Return new PlayerState with is_folded=True."""
        return PlayerState(
            player_id=self.player_id,
            stack=self.stack,
            chips_in_street=self.chips_in_street,
            chips_in_hand=self.chips_in_hand,
            is_folded=True,
            is_all_in=self.is_all_in
        )

    def reset_street_bet(self) -> PlayerState:
        """Reset street contribution to 0 (called at the end of betting street)."""
        return PlayerState(
            player_id=self.player_id,
            stack=self.stack,
            chips_in_street=0,
            chips_in_hand=self.chips_in_hand,
            is_folded=self.is_folded,
            is_all_in=self.is_all_in
        )
