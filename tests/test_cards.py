import pytest

from poker_engine.cards import Card, Deck, Rank, Suit 

def get_card_sort_key(card): 
    #helper function to sort cards by rank and suit
    return (card.rank.value, card.suit.value)

def test_two_different_cards_are_not_equal():
    assert Card(Rank.ACE, Suit.SPADES) != Card(Rank.KING, Suit.SPADES), "Different cards should not be equal"

def test_two_identical_cards_are_equal():
    assert Card(Rank.ACE, Suit.SPADES) == Card(Rank.ACE, Suit.SPADES), "Identical cards should be equal"

def test_deck_deals_consistent_order():
    deck1 = Deck()
    deck2 = Deck()
    assert deck1.deal(5) == deck2.deal(5), "Two fresh decks should deal in the same order"

def test_deck_deals_unique_cards():
    deck = Deck()
    dealt_cards = deck.deal(52)
    assert len(set(dealt_cards)) == 52, "Dealt cards should be unique"

def test_deal_from_empty_deck_raises_error():
    deck = Deck()
    deck.deal(52)
    with pytest.raises(ValueError):
        deck.deal(1)

def test_reset_deck_restores_all_cards():
    deck = Deck()
    deck.deal(52)  # Deal all cards
    deck.reset()   # Reset the deck
    assert len(deck) == 52, "Resetting the deck should restore all cards"

