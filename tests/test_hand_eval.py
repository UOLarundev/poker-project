import pytest
from poker_engine.cards import Card, Rank, Suit
from poker_engine.hand_eval import evaluate, HandRank

def test_high_card_comparison():
    # Both have high card Ace, but different kickers
    # A-K-J-9-8 vs A-Q-J-9-8
    hand1 = [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.KING, Suit.HEARTS),
        Card(Rank.JACK, Suit.DIAMONDS),
        Card(Rank.NINE, Suit.CLUBS),
        Card(Rank.EIGHT, Suit.SPADES)
    ]
    hand2 = [
        Card(Rank.ACE, Suit.CLUBS),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.JACK, Suit.SPADES),
        Card(Rank.NINE, Suit.DIAMONDS),
        Card(Rank.EIGHT, Suit.CLUBS)
    ]
    
    score1 = evaluate(hand1)
    score2 = evaluate(hand2)
    
    assert score1[0] == HandRank.HIGH_CARD
    assert score2[0] == HandRank.HIGH_CARD
    assert score1 > score2  # King kicker beats Queen kicker

def test_pair_kicker_comparison():
    # Pair of Tens with Ace kicker vs Pair of Tens with King kicker
    # 10-10-A-Q-J vs 10-10-K-Q-J
    hand1 = [
        Card(Rank.TEN, Suit.SPADES),
        Card(Rank.TEN, Suit.HEARTS),
        Card(Rank.ACE, Suit.DIAMONDS),
        Card(Rank.QUEEN, Suit.CLUBS),
        Card(Rank.JACK, Suit.SPADES)
    ]
    hand2 = [
        Card(Rank.TEN, Suit.CLUBS),
        Card(Rank.TEN, Suit.DIAMONDS),
        Card(Rank.KING, Suit.HEARTS),
        Card(Rank.QUEEN, Suit.SPADES),
        Card(Rank.JACK, Suit.CLUBS)
    ]
    
    score1 = evaluate(hand1)
    score2 = evaluate(hand2)
    
    assert score1[0] == HandRank.PAIR
    assert score2[0] == HandRank.PAIR
    assert score1 > score2  # Ace kicker beats King kicker

def test_two_pair_comparison():
    # Aces and Jacks with King kicker vs Aces and Jacks with Queen kicker
    # A-A-J-J-K vs A-A-J-J-Q
    hand1 = [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.JACK, Suit.DIAMONDS),
        Card(Rank.JACK, Suit.CLUBS),
        Card(Rank.KING, Suit.SPADES)
    ]
    hand2 = [
        Card(Rank.ACE, Suit.CLUBS),
        Card(Rank.ACE, Suit.DIAMONDS),
        Card(Rank.JACK, Suit.SPADES),
        Card(Rank.JACK, Suit.HEARTS),
        Card(Rank.QUEEN, Suit.CLUBS)
    ]
    
    score1 = evaluate(hand1)
    score2 = evaluate(hand2)
    
    assert score1[0] == HandRank.TWO_PAIR
    assert score2[0] == HandRank.TWO_PAIR
    assert score1 > score2

def test_wheel_straight():
    # A-2-3-4-5 straight (5-high) vs 2-3-4-5-6 straight (6-high)
    wheel = [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.TWO, Suit.HEARTS),
        Card(Rank.THREE, Suit.DIAMONDS),
        Card(Rank.FOUR, Suit.CLUBS),
        Card(Rank.FIVE, Suit.SPADES)
    ]
    six_high = [
        Card(Rank.SIX, Suit.CLUBS),
        Card(Rank.TWO, Suit.DIAMONDS),
        Card(Rank.THREE, Suit.SPADES),
        Card(Rank.FOUR, Suit.HEARTS),
        Card(Rank.FIVE, Suit.CLUBS)
    ]
    
    score_wheel = evaluate(wheel)
    score_six = evaluate(six_high)
    
    assert score_wheel[0] == HandRank.STRAIGHT
    assert score_six[0] == HandRank.STRAIGHT
    assert score_wheel[1] == [Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO, Rank.ACE]
    assert score_six[1] == [Rank.SIX, Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO]
    assert score_six > score_wheel

def test_full_house_trips_rank_determines_winner():
    # Jacks full of Threes vs Tens full of Aces
    # J-J-J-3-3 vs 10-10-10-A-A
    hand1 = [
        Card(Rank.JACK, Suit.SPADES),
        Card(Rank.JACK, Suit.HEARTS),
        Card(Rank.JACK, Suit.DIAMONDS),
        Card(Rank.THREE, Suit.CLUBS),
        Card(Rank.THREE, Suit.SPADES)
    ]
    hand2 = [
        Card(Rank.TEN, Suit.CLUBS),
        Card(Rank.TEN, Suit.DIAMONDS),
        Card(Rank.TEN, Suit.HEARTS),
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.ACE, Suit.CLUBS)
    ]
    
    score1 = evaluate(hand1)
    score2 = evaluate(hand2)
    
    assert score1[0] == HandRank.FULL_HOUSE
    assert score2[0] == HandRank.FULL_HOUSE
    assert score1 > score2  # J-trips beats 10-trips

def test_flush_comparison():
    # Ace-high Flush vs King-high Flush
    hand1 = [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.TEN, Suit.SPADES),
        Card(Rank.EIGHT, Suit.SPADES),
        Card(Rank.FOUR, Suit.SPADES),
        Card(Rank.THREE, Suit.SPADES)
    ]
    hand2 = [
        Card(Rank.KING, Suit.HEARTS),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.JACK, Suit.HEARTS),
        Card(Rank.NINE, Suit.HEARTS),
        Card(Rank.TWO, Suit.HEARTS)
    ]
    
    score1 = evaluate(hand1)
    score2 = evaluate(hand2)
    
    assert score1[0] == HandRank.FLUSH
    assert score2[0] == HandRank.FLUSH
    assert score1 > score2

def test_evaluate_seven_cards_picks_best_five():
    # 7 cards containing trips and a straight
    # Should choose the straight over the trips
    cards = [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.ACE, Suit.DIAMONDS),
        Card(Rank.TEN, Suit.CLUBS),
        Card(Rank.JACK, Suit.SPADES),
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.KING, Suit.DIAMONDS)
    ]
    
    score = evaluate(cards)
    # Best 5 card hand is T-J-Q-K-A straight, not AAA Trips
    assert score[0] == HandRank.STRAIGHT
    assert score[1] == [Rank.ACE, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.TEN]
