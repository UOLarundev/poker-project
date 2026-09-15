import random

from poker_engine.cards import Card, Rank, Suit
from poker_engine.equity.monte_carlo import equity_vs_random


def test_pocket_aces_favored_preflop_heads_up():
    hero = [Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.HEARTS)]
    eq = equity_vs_random(hero, [], num_opponents=1, trials=4000, rng=random.Random(0))
    # True heads-up AA equity vs a random hand is ~85.2%
    assert 0.80 < eq < 0.90


def test_weak_hand_is_underdog_preflop_heads_up():
    hero = [Card(Rank.SEVEN, Suit.CLUBS), Card(Rank.TWO, Suit.DIAMONDS)]
    eq = equity_vs_random(hero, [], num_opponents=1, trials=4000, rng=random.Random(0))
    # True heads-up 72o equity vs a random hand is ~34.6%
    assert 0.28 < eq < 0.42


def test_more_opponents_reduces_equity():
    hero = [Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.SPADES)]
    heads_up = equity_vs_random(hero, [], num_opponents=1, trials=4000, rng=random.Random(1))
    three_way = equity_vs_random(hero, [], num_opponents=2, trials=4000, rng=random.Random(1))
    assert three_way < heads_up


def test_equity_reflects_made_hand_on_board():
    # Hero has flopped a set with only running pairs able to catch up.
    hero = [Card(Rank.NINE, Suit.SPADES), Card(Rank.NINE, Suit.HEARTS)]
    board = [Card(Rank.NINE, Suit.CLUBS), Card(Rank.FOUR, Suit.DIAMONDS), Card(Rank.TWO, Suit.SPADES)]
    eq = equity_vs_random(hero, board, num_opponents=1, trials=4000, rng=random.Random(2))
    assert eq > 0.85
