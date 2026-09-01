"""Monte Carlo equity estimation via random sampling.

Used when the number of possible runouts is too large to enumerate exactly
(e.g. all-in situations before the flop, where exact enumeration means
evaluating over a million 7-card hands per player).
"""

from __future__ import annotations
import random

from poker_engine.cards import Card, Deck
from poker_engine.hand_eval import evaluate


def monte_carlo_equity(
    player_hands: dict[str, list[Card]],
    board_cards: list[Card],
    trials: int = 5000,
    rng: random.Random | None = None
) -> dict[str, float]:
    """Estimate equity by sampling random runouts.

    Returns a dictionary mapping player IDs to their equity as floats between 0 and 1.
    """
    if rng is None:
        rng = random.Random()

    known_cards = set(card for cards in player_hands.values() for card in cards) | set(board_cards)
    remaining_deck = [card for card in Deck()._cards if card not in known_cards]
    cards_to_deal = 5 - len(board_cards)

    wins = {player_id: 0.0 for player_id in player_hands}

    for _ in range(trials):
        runout = rng.sample(remaining_deck, cards_to_deal)
        complete_board = board_cards + runout

        scores = {player_id: evaluate(cards + complete_board) for player_id, cards in player_hands.items()}
        best = max(scores.values())
        winners = [player_id for player_id, score in scores.items() if score == best]
        for player_id in winners:
            wins[player_id] += 1 / len(winners)  # split evenly if tied

    return {player_id: wins[player_id] / trials for player_id in player_hands}
