import pytest
from poker_engine.cards import Card, Deck, Rank, Suit
from poker_engine.player import PlayerState
from poker_engine.actions import Action, ActionType
from poker_engine.game import GameState

class DeterministicDeck(Deck):
    def __init__(self, cards: list[Card]):
        self._cards = cards

    def shuffle(self) -> None:
        pass  # Prevent shuffling to keep deterministic order


def test_start_new_hand_multiplayer():
    p1 = PlayerState(player_id="A", stack=1000)
    p2 = PlayerState(player_id="B", stack=1000)
    p3 = PlayerState(player_id="C", stack=1000)
    
    # 3 players, dealer is index 0 ("A")
    # Blinds: SB = "B" (posts 5), BB = "C" (posts 10)
    # First actor pre-flop: left of BB, which is "A" (index 0)
    cards = [
        # Hole cards (dealt starting from B -> C -> A)
        Card(Rank.ACE, Suit.SPADES),    # B card 1
        Card(Rank.KING, Suit.SPADES),   # C card 1
        Card(Rank.QUEEN, Suit.SPADES),  # A card 1
        Card(Rank.ACE, Suit.HEARTS),    # B card 2
        Card(Rank.KING, Suit.HEARTS),   # C card 2
        Card(Rank.QUEEN, Suit.HEARTS),  # A card 2
    ]
    deck = DeterministicDeck(cards)
    
    state = GameState.start_new_hand(
        players=[p1, p2, p3],
        dealer_button_index=0,
        sb_amount=5,
        bb_amount=10,
        deck=deck
    )
    
    # Verify blinds posted
    assert state.players[0].stack == 1000  # A (Button)
    assert state.players[1].stack == 995   # B (SB)
    assert state.players[2].stack == 990   # C (BB)
    
    # Verify hole cards dealt clockwise starting left of button (SB = B)
    assert state.player_hands["B"] == (Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.HEARTS))
    assert state.player_hands["C"] == (Card(Rank.KING, Suit.SPADES), Card(Rank.KING, Suit.HEARTS))
    assert state.player_hands["A"] == (Card(Rank.QUEEN, Suit.SPADES), Card(Rank.QUEEN, Suit.HEARTS))
    
    # Verify actor index: 0 (A)
    assert state.betting_state.current_actor.player_id == "A"
    assert state.street == "PRE_FLOP"


def test_start_new_hand_heads_up():
    p1 = PlayerState(player_id="A", stack=1000)
    p2 = PlayerState(player_id="B", stack=1000)
    
    # 2 players: heads-up. Button = 0 ("A")
    # SB: "A" (Button, posts 5)
    # BB: "B" (Non-button, posts 10)
    # First actor pre-flop: SB = "A" (Button)
    cards = [
        Card(Rank.ACE, Suit.SPADES),   # B card 1 (non-button)
        Card(Rank.KING, Suit.SPADES),  # A card 1 (button)
        Card(Rank.ACE, Suit.HEARTS),   # B card 2
        Card(Rank.KING, Suit.HEARTS),  # A card 2
    ]
    deck = DeterministicDeck(cards)
    
    state = GameState.start_new_hand(
        players=[p1, p2],
        dealer_button_index=0,
        sb_amount=5,
        bb_amount=10,
        deck=deck
    )
    
    assert state.players[0].stack == 995  # A (SB)
    assert state.players[1].stack == 990  # B (BB)
    assert state.betting_state.current_actor.player_id == "A"


def test_fold_out_preflop():
    p1 = PlayerState(player_id="A", stack=1000)
    p2 = PlayerState(player_id="B", stack=1000)
    p3 = PlayerState(player_id="C", stack=1000)
    
    # B posts 5, C posts 10. A acts first.
    cards = [Card(Rank.TWO, Suit.CLUBS)] * 20
    deck = DeterministicDeck(cards)
    
    state = GameState.start_new_hand([p1, p2, p3], 0, 5, 10, deck)
    
    # A folds
    state = state.apply_action(Action(ActionType.FOLD))
    assert not state.street == "HAND_OVER"
    
    # B folds
    state = state.apply_action(Action(ActionType.FOLD))
    
    # Now only C is left. C wins the pot (B's 5 + C's 5 = 10). C's extra 5 is refunded.
    # C's net stack should be 990 (post BB) + 5 (refund) + 10 (winnings) = 1005.
    assert state.street == "HAND_OVER"
    assert state.players[2].stack == 1005
    assert state.winners == {"C": 10}


def test_check_down_to_showdown():
    # 2 players. A is Button. A posts 5, B posts 10.
    # A acts first preflop (heads-up).
    # Board cards:
    # Burn 1, Flop: 2H, 3H, 4H. Burn 1, Turn: 5H. Burn 1, River: 6H.
    # Total board: 2H, 3H, 4H, 5H, 6H (Straight Flush board!)
    # Player A hole: AH, KH
    # Player B hole: 7H, 8H
    # Deal sequence heads-up: B first, A second
    cards = [
        Card(Rank.SEVEN, Suit.HEARTS), # B hole 1
        Card(Rank.ACE, Suit.HEARTS),   # A hole 1
        Card(Rank.EIGHT, Suit.HEARTS), # B hole 2
        Card(Rank.KING, Suit.HEARTS),  # A hole 2
        
        # Flop deal: burn 1, deal 3
        Card(Rank.TWO, Suit.CLUBS),    # BURN 1
        Card(Rank.TWO, Suit.HEARTS),   # FLOP 1
        Card(Rank.THREE, Suit.HEARTS), # FLOP 2
        Card(Rank.FOUR, Suit.HEARTS),  # FLOP 3
        
        # Turn deal: burn 1, deal 1
        Card(Rank.THREE, Suit.CLUBS),  # BURN 2
        Card(Rank.FIVE, Suit.HEARTS),  # TURN
        
        # River deal: burn 1, deal 1
        Card(Rank.FOUR, Suit.CLUBS),   # BURN 3
        Card(Rank.SIX, Suit.HEARTS),   # RIVER
    ]
    deck = DeterministicDeck(cards)
    
    p1 = PlayerState(player_id="A", stack=1000)
    p2 = PlayerState(player_id="B", stack=1000)
    
    state = GameState.start_new_hand([p1, p2], 0, 5, 10, deck)
    
    # --- PRE_FLOP ---
    # A (SB) calls 10 (needs to pay 5 more)
    state = state.apply_action(Action(ActionType.CALL))
    # B (BB) checks
    state = state.apply_action(Action(ActionType.CHECK))
    
    # --- FLOP ---
    assert state.street == "FLOP"
    assert state.board_cards == (Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.HEARTS), Card(Rank.FOUR, Suit.HEARTS))
    # B (BB) acts first post-flop
    assert state.betting_state.current_actor.player_id == "B"
    state = state.apply_action(Action(ActionType.CHECK))
    state = state.apply_action(Action(ActionType.CHECK))
    
    # --- TURN ---
    assert state.street == "TURN"
    assert state.board_cards == (Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.HEARTS), Card(Rank.FOUR, Suit.HEARTS), Card(Rank.FIVE, Suit.HEARTS))
    state = state.apply_action(Action(ActionType.CHECK))
    state = state.apply_action(Action(ActionType.CHECK))
    
    # --- RIVER ---
    assert state.street == "RIVER"
    assert state.board_cards == (Card(Rank.TWO, Suit.HEARTS), Card(Rank.THREE, Suit.HEARTS), Card(Rank.FOUR, Suit.HEARTS), Card(Rank.FIVE, Suit.HEARTS), Card(Rank.SIX, Suit.HEARTS))
    state = state.apply_action(Action(ActionType.CHECK))
    state = state.apply_action(Action(ActionType.CHECK))
    
    # --- SHOWDOWN ---
    assert state.street == "HAND_OVER"
    # A's hand: AH, KH + board (2H, 3H, 4H, 5H, 6H) -> Best 5-card: 2-3-4-5-6 Hearts (Straight Flush, 6-high)
    # B's hand: 7H, 8H + board -> Best 5-card: 4-5-6-7-8 Hearts (Straight Flush, 8-high)
    # B should win the pot of 20.
    assert state.winners == {"B": 20}
    assert state.players[0].stack == 990  # A lost 10
    assert state.players[1].stack == 1010 # B won 10 net


def test_all_in_skips_betting_rounds():
    # 2 players. A is Button (SB, posts 5, has 50 stack). B is BB (posts 10, has 1000 stack).
    p1 = PlayerState(player_id="A", stack=50)
    p2 = PlayerState(player_id="B", stack=1000)
    
    cards = [
        Card(Rank.SEVEN, Suit.HEARTS), # B hole 1
        Card(Rank.ACE, Suit.HEARTS),   # A hole 1
        Card(Rank.EIGHT, Suit.HEARTS), # B hole 2
        Card(Rank.KING, Suit.HEARTS),  # A hole 2
        
        # Board
        Card(Rank.TWO, Suit.CLUBS),    # BURN 1
        Card(Rank.TWO, Suit.HEARTS),   # FLOP 1
        Card(Rank.THREE, Suit.HEARTS), # FLOP 2
        Card(Rank.FOUR, Suit.HEARTS),  # FLOP 3
        Card(Rank.THREE, Suit.CLUBS),  # BURN 2
        Card(Rank.FIVE, Suit.HEARTS),  # TURN
        Card(Rank.FOUR, Suit.CLUBS),   # BURN 3
        Card(Rank.SIX, Suit.HEARTS),   # RIVER
    ]
    deck = DeterministicDeck(cards)
    
    state = GameState.start_new_hand([p1, p2], 0, 5, 10, deck)
    
    # A (SB) goes all-in for 50 total (needs to put in 45 more)
    state = state.apply_action(Action(ActionType.ALL_IN))
    
    # B (BB) calls A's 50 (needs to pay 40 more)
    state = state.apply_action(Action(ActionType.CALL))
    
    # Since A is all-in, betting rounds are complete.
    # The game should automatically deal the board and run to SHOWDOWN.
    assert state.street == "HAND_OVER"
    assert len(state.board_cards) == 5
    # B has straight flush 8-high (4-5-6-7-8 Hearts), A has straight flush 6-high.
    # B wins pot of 100.
    assert state.winners == {"B": 100}
    assert state.players[0].stack == 0
    assert state.players[1].stack == 1050
