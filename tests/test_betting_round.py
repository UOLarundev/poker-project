import pytest
from poker_engine.player import PlayerState
from poker_engine.actions import Action, ActionType
from poker_engine.betting_round import BettingRoundState

def test_check_around():
    # 2 players, current bet is 0
    p1 = PlayerState(player_id="A", stack=100)
    p2 = PlayerState(player_id="B", stack=100)
    
    # Initialize round
    state = BettingRoundState.initialize([p1, p2], first_actor_index=0, current_bet=0, last_raise_increment=10, big_blind=10)
    
    # Player A checks
    assert Action(ActionType.CHECK) in state.get_allowed_actions("A")
    state = state.apply_action(Action(ActionType.CHECK))
    
    assert not state.is_round_complete()
    assert state.current_actor.player_id == "B"
    
    # Player B checks
    assert Action(ActionType.CHECK) in state.get_allowed_actions("B")
    state = state.apply_action(Action(ActionType.CHECK))
    
    # Round should be complete
    assert state.is_round_complete()

def test_bet_and_call():
    p1 = PlayerState(player_id="A", stack=100)
    p2 = PlayerState(player_id="B", stack=100)
    
    state = BettingRoundState.initialize([p1, p2], first_actor_index=0, current_bet=0, last_raise_increment=10, big_blind=10)
    
    # A bets 20
    state = state.apply_action(Action(ActionType.RAISE, amount=20))
    
    assert state.current_bet == 20
    assert state.last_raise_increment == 20
    assert not state.is_round_complete()
    assert state.current_actor.player_id == "B"
    
    # B cannot check (must call, raise, fold)
    allowed = state.get_allowed_actions("B")
    assert Action(ActionType.CHECK) not in allowed
    assert Action(ActionType.CALL) in allowed
    
    # B calls
    state = state.apply_action(Action(ActionType.CALL))
    
    assert state.is_round_complete()
    assert state.players[0].chips_in_street == 20
    assert state.players[1].chips_in_street == 20

def test_raise_and_reopen():
    p1 = PlayerState(player_id="A", stack=200)
    p2 = PlayerState(player_id="B", stack=200)
    p3 = PlayerState(player_id="C", stack=200)
    
    state = BettingRoundState.initialize([p1, p2, p3], first_actor_index=0, current_bet=0, last_raise_increment=10, big_blind=10)
    
    # A bets 10
    state = state.apply_action(Action(ActionType.RAISE, amount=10))
    # B raises to 30
    state = state.apply_action(Action(ActionType.RAISE, amount=30))
    # C calls 30
    state = state.apply_action(Action(ActionType.CALL))
    
    # Current actor should be A (A bet 10, now faces 30).
    assert state.current_actor.player_id == "A"
    # A has already acted (bet 10), but since B raised, A's betting is reopened. A should be able to raise.
    assert Action(ActionType.RAISE) in state.get_allowed_actions("A")
    
    # A calls 30
    state = state.apply_action(Action(ActionType.CALL))
    
    # Round is complete because C called 30, A called 30, and B raised to 30.
    assert state.is_round_complete()

def test_under_all_in_does_not_reopen_betting():
    # Scenario: A bets 100, B calls 100, C is short stack all-in for 150 (min raise was 200).
    # Betting should NOT reopen for A or B to raise.
    p1 = PlayerState(player_id="A", stack=500)
    p2 = PlayerState(player_id="B", stack=500)
    p3 = PlayerState(player_id="C", stack=150)
    
    state = BettingRoundState.initialize([p1, p2, p3], first_actor_index=0, current_bet=0, last_raise_increment=10, big_blind=10)
    
    # A bets 100
    state = state.apply_action(Action(ActionType.RAISE, amount=100))
    # B calls 100
    state = state.apply_action(Action(ActionType.CALL))
    # C goes all-in for 150 (this is a raise of 50, but last raise was 100, so it's short)
    state = state.apply_action(Action(ActionType.ALL_IN))
    
    assert state.current_bet == 150
    assert state.last_raise_increment == 100  # remains 100
    
    # Next actor should be A
    assert state.current_actor.player_id == "A"
    # A called 100. C's short raise does not reopen. A can only CALL or FOLD.
    actions = state.get_allowed_actions("A")
    assert Action(ActionType.CALL) in actions
    assert Action(ActionType.FOLD) in actions
    assert Action(ActionType.RAISE) not in actions
    
    # A calls
    state = state.apply_action(Action(ActionType.CALL))
    
    # Next actor should be B
    assert state.current_actor.player_id == "B"
    # B also cannot raise
    actions = state.get_allowed_actions("B")
    assert Action(ActionType.CALL) in actions
    assert Action(ActionType.RAISE) not in actions
    
    # B calls
    state = state.apply_action(Action(ActionType.CALL))
    
    # All active players (A, B, C) have acted and equalized or are all-in.
    assert state.is_round_complete()

def test_invalid_raise_amount():
    p1 = PlayerState(player_id="A", stack=100)
    p2 = PlayerState(player_id="B", stack=100)
    
    state = BettingRoundState.initialize([p1, p2], first_actor_index=0, current_bet=10, last_raise_increment=10, big_blind=10)
    
    # A tries to raise to 15 (min raise is 20)
    with pytest.raises(ValueError):
        state.apply_action(Action(ActionType.RAISE, amount=15))
        
    # A tries to raise to 105 (stack is 100)
    with pytest.raises(ValueError):
        state.apply_action(Action(ActionType.RAISE, amount=105))
