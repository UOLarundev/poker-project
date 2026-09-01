"""Exact equity calculation via full enumeration.

Used when all hole cards are known (all-in situations).
"""

from __future__ import annotations
from itertools import combinations

from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.hand_eval import evaluate


def exact_equity(
    player_hands: dict[str, list[Card]],
    board_cards: list[Card]
) -> dict[str, float]:
    """Calculate exact equity by enumerating all possible runouts.
    
    Returns a dictionary mapping player IDs to their equity as floats between 0 and 1.
    """
    known_cards = set(card for cards in player_hands.values() for card in cards) | set(board_cards)
    remaining_deck = [card for card in Deck()._cards if card not in known_cards]
    cards_to_deal = 5 - len(board_cards)

    wins = {player_id: 0 for player_id in player_hands}
    total = 0

    # iterates over every possible runout using combinations()
    for runout in combinations(remaining_deck, cards_to_deal):
        total += 1
        complete_board = board_cards + list(runout)

        scores = {player_id: evaluate(cards + complete_board) for player_id, cards in player_hands.items()}
        best = max(scores.values())
        winners = [player_id for player_id, score in scores.items() if score == best]
        for player_id in winners:
            wins[player_id] += 1 / len(winners)  # split evenly if tied

    # returns equity for each player
    return {player_id: wins[player_id] / total for player_id in player_hands}