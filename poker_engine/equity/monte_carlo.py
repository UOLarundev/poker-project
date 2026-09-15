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


def equity_vs_random(
    hero_cards: list[Card],
    board_cards: list[Card],
    num_opponents: int = 1,
    trials: int = 5000,
    rng: random.Random | None = None
) -> float:
    """Estimate hero's equity against random, unknown opponent hand(s).

    Unlike monte_carlo_equity/exact_equity, opponent hole cards are not known —
    each trial samples random opponent hands as well as a random runout.
    Returns hero's estimated equity as a float between 0 and 1.
    """
    if rng is None:
        rng = random.Random()

    known_cards = set(hero_cards) | set(board_cards)
    remaining_deck = [card for card in Deck()._cards if card not in known_cards]
    cards_to_deal = 5 - len(board_cards)
    needed = cards_to_deal + num_opponents * 2

    wins = 0.0

    for _ in range(trials):
        sample = rng.sample(remaining_deck, needed)
        runout = sample[:cards_to_deal]
        complete_board = board_cards + runout

        hero_score = evaluate(hero_cards + complete_board)
        opponent_scores = [
            evaluate(sample[cards_to_deal + i * 2: cards_to_deal + i * 2 + 2] + complete_board)
            for i in range(num_opponents)
        ]

        best_opponent_score = max(opponent_scores)
        if hero_score > best_opponent_score:
            wins += 1
        elif hero_score == best_opponent_score:
            # Hero ties for best; split among however many opponents also hit it.
            tied_opponents = sum(1 for score in opponent_scores if score == best_opponent_score)
            wins += 1 / (1 + tied_opponents)

    return wins / trials
