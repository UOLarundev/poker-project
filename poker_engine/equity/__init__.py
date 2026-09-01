from poker_engine.cards import Card
from poker_engine.equity.true_equity import exact_equity
from poker_engine.equity.monte_carlo import monte_carlo_equity

__all__ = ["exact_equity", "monte_carlo_equity", "calculate_equity"]

# Exact enumeration is only fast enough while there are 2 or fewer cards left
# to come (turn/river/flop). Preflop (5 cards to come) enumerates over a
# million runouts, so fall back to Monte Carlo sampling there.
_MAX_EXACT_CARDS_TO_DEAL = 2


def calculate_equity(
    player_hands: dict[str, list[Card]],
    board_cards: list[Card],
    trials: int = 5000
) -> dict[str, float]:
    """Compute equity, enumerating exactly when feasible and sampling otherwise."""
    cards_to_deal = 5 - len(board_cards)
    if cards_to_deal <= _MAX_EXACT_CARDS_TO_DEAL:
        return exact_equity(player_hands, board_cards)
    return monte_carlo_equity(player_hands, board_cards, trials=trials)
