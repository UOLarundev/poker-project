"""Player actions: the moves a player can make during a betting round."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass(frozen=True)
class Action:
    """An action taken by a player.
    
    amount is only relevant for RAISE and ALL_IN, None otherwise.
    """
    action_type: ActionType
    amount: int | None = None