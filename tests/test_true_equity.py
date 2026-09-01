import pytest
from poker_engine.cards import Card, Rank, Suit
from poker_engine.equity.true_equity import exact_equity

@pytest.mark.parametrize("hero, villain, board", [
    # Flop scenario: 2 cards left to deal (e.g., Hero flush + straight draw vs Villain pocket Queens)
    (
        [Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.SPADES)],
        [Card(Rank.QUEEN, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS)],
        [Card(Rank.JACK, Suit.SPADES), Card(Rank.TEN, Suit.DIAMONDS), Card(Rank.TWO, Suit.SPADES)]
    ),
    # Turn scenario: 1 card left to deal (e.g., Hero pair + flush draw vs Villain top pair top kicker)
    (
        [Card(Rank.ACE, Suit.SPADES), Card(Rank.TWO, Suit.SPADES)],
        [Card(Rank.ACE, Suit.HEARTS), Card(Rank.KING, Suit.HEARTS)],
        [Card(Rank.ACE, Suit.CLUBS), Card(Rank.SEVEN, Suit.SPADES), Card(Rank.EIGHT, Suit.SPADES), Card(Rank.NINE, Suit.DIAMONDS)]
    ),
    # River scenario: 0 cards left to deal (e.g., complete board, absolute winner or split pot)
    (
        [Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.HEARTS)],
        [Card(Rank.KING, Suit.SPADES), Card(Rank.KING, Suit.HEARTS)],
        [Card(Rank.ACE, Suit.DIAMONDS), Card(Rank.KING, Suit.DIAMONDS), Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.CLUBS), Card(Rank.FOUR, Suit.CLUBS)]
    )
])
def test_equity_sums_to_one(hero, villain, board):
    player_hands = {"hero": hero, "villain": villain}
    equities = exact_equity(player_hands, board)
    assert sum(equities.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("player_hands, board", [
    # Flop scenario
    (
        {
            "hero": [Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.SPADES)],
            "villain_a": [Card(Rank.QUEEN, Suit.HEARTS), Card(Rank.QUEEN, Suit.CLUBS)],
            "villain_b": [Card(Rank.JACK, Suit.DIAMONDS), Card(Rank.TEN, Suit.DIAMONDS)]
        },
        [Card(Rank.TWO, Suit.HEARTS), Card(Rank.FIVE, Suit.CLUBS), Card(Rank.NINE, Suit.DIAMONDS)]
    ),
    # Turn scenario
    (
        {
            "hero": [Card(Rank.ACE, Suit.SPADES), Card(Rank.TWO, Suit.SPADES)],
            "villain_a": [Card(Rank.ACE, Suit.HEARTS), Card(Rank.KING, Suit.HEARTS)],
            "villain_b": [Card(Rank.JACK, Suit.CLUBS), Card(Rank.TEN, Suit.CLUBS)]
        },
        [Card(Rank.ACE, Suit.CLUBS), Card(Rank.SEVEN, Suit.SPADES), Card(Rank.EIGHT, Suit.SPADES), Card(Rank.NINE, Suit.DIAMONDS)]
    ),
    # River scenario
    (
        {
            "hero": [Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.HEARTS)],
            "villain_a": [Card(Rank.KING, Suit.SPADES), Card(Rank.KING, Suit.HEARTS)],
            "villain_b": [Card(Rank.QUEEN, Suit.SPADES), Card(Rank.QUEEN, Suit.HEARTS)]
        },
        [Card(Rank.ACE, Suit.DIAMONDS), Card(Rank.KING, Suit.DIAMONDS), Card(Rank.QUEEN, Suit.DIAMONDS), Card(Rank.TWO, Suit.CLUBS), Card(Rank.THREE, Suit.CLUBS)]
    ),
])

def test_equity_sums_to_one_three_ways(player_hands, board):
    equities = exact_equity(player_hands, board)
    assert sum(equities.values()) == pytest.approx(1.0)
