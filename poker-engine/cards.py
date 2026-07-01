from __future__ import annotations
 
import random
from enum import Enum, IntEnum
from dataclasses import dataclass

class Suit(Enum):
    HEARTS = "H"
    DIAMONDS = "D"
    CLUBS = "C"
    SPADES = "S"

    def __str__(self) -> str:
        return self.value
    
class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    def __str__(self) -> str:
        match self:
            case Rank.JACK: 
                return "J"
            case Rank.QUEEN:
                return "Q"
            case Rank.KING:
                return "K"
            case Rank.ACE:
                return "A"
            case _:
                return str(self.value)
            
@dataclass(frozen=True, order=True)
class Card:
    """A single playing card. Immutable and hashable.
 
    frozen=True  -> can't be changed after creation, can go in sets/dicts
    order=True   -> comparisons (<, >) work automatically, rank compared first
    """
    rank: Rank
    suit: Suit
 
    def __str__(self) -> str:
        # TODO: return e.g. "AS" for Ace of Spades, "10H" for Ten of Hearts
        return f"{self.rank}{self.suit}" 
    

class Deck:
    """A standard 52-card deck. Cards are removed as they are dealt."""
 
    def __init__(self) -> None:
        # TODO: build self._cards as a list of all 52 Card combinations
        # hint: loop over every Suit and every Rank
        self.cards = [Card(rank, suit) for suit in Suit for rank in Rank]
 
    def __len__(self) -> int:
        # TODO: return how many cards remain in the deck
        return len(self.cards)
 
    def shuffle(self) -> None:
        # TODO: shuffle self._cards in place
        # hint: random.shuffle()
        random.shuffle(self.cards)
 
    def deal(self, n: int = 1) -> list[Card]:
        """Remove and return n cards from the top of the deck.
 
        Raises ValueError if there aren't enough cards remaining.
        """
        # TODO: raise ValueError if n > len(self._cards)
        if n > len(self.cards):
            raise ValueError("Not enough cards in the deck.")
        # TODO: remove the first n cards from self._cards and return them
        # hint: think about how to split a list in one line
        dealt_cards = self.cards[:n]
        self.cards = self.cards[n:]
        return dealt_cards
 
    def reset(self) -> None:
        """Restore the deck to a full 52 cards (unshuffled)."""
        # TODO: rebuild the deck from scratch
        # hint: one line — you've already written the logic somewhere above
        self.cards = [Card(rank, suit) for suit in Suit for rank in Rank]