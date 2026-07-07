from poker_engine.pot import resolve_pots, Pot

def test_simple_pot_no_side_pots():
    contributions = {"A": 100, "B": 100, "C": 100}
    active_ids = {"A", "B", "C"}
    pots = resolve_pots(contributions, active_ids)
    
    assert len(pots) == 1
    assert pots[0].amount == 300
    assert pots[0].eligible_player_ids == {"A", "B", "C"}

def test_folded_player_dead_money():
    contributions = {"A": 100, "B": 100, "C": 50}
    active_ids = {"A", "B"}  # C is folded
    pots = resolve_pots(contributions, active_ids)
    
    # Active levels: [100]
    # Step 100: A (100) -> 100, B (100) -> 100, C (50) -> 50. Total = 250.
    # Eligible: {A, B}
    assert len(pots) == 1
    assert pots[0].amount == 250
    assert pots[0].eligible_player_ids == {"A", "B"}

def test_uncalled_bet_refund():
    contributions = {"A": 300, "B": 150, "C": 150}
    active_ids = {"A", "B", "C"}
    
    # A's bet is uncalled. Excess 150 should be refunded.
    # Net contributions for pot: A (150), B (150), C (150). Total pot = 450.
    pots = resolve_pots(contributions, active_ids)
    
    assert len(pots) == 1
    assert pots[0].amount == 450
    assert pots[0].eligible_player_ids == {"A", "B", "C"}

def test_single_all_in_creates_side_pot():
    contributions = {"A": 100, "B": 300, "C": 300}
    active_ids = {"A", "B", "C"}
    
    # A is all-in for 100. B and C continue betting up to 300.
    # Pot 1 (Main): level 100. Amount: 100 from A, 100 from B, 100 from C = 300. Eligible: {A, B, C}
    # Pot 2 (Side): level 300 (step 200). Amount: 200 from B, 200 from C = 400. Eligible: {B, C}
    pots = resolve_pots(contributions, active_ids)
    
    assert len(pots) == 2
    assert pots[0].amount == 300
    assert pots[0].eligible_player_ids == {"A", "B", "C"}
    
    assert pots[1].amount == 400
    assert pots[1].eligible_player_ids == {"B", "C"}

def test_multiple_side_pots():
    contributions = {
        "A": 50,    # Active all-in
        "B": 100,   # Active all-in
        "C": 200,   # Active all-in
        "D": 300    # Active, bets 300.
    }
    active_ids = {"A", "B", "C", "D"}
    
    # First, D's bet of 300 is refunded down to C's 200 (since D is active and leading).
    # Contributions considered: A (50), B (100), C (200), D (200)
    # Active levels: [50, 100, 200]
    # Pot 1 (level 50): 50 * 4 = 200. Eligible: {A, B, C, D}
    # Pot 2 (level 100, step 50): 50 * 3 = 150. Eligible: {B, C, D}
    # Pot 3 (level 200, step 100): 100 * 2 = 200. Eligible: {C, D}
    pots = resolve_pots(contributions, active_ids)
    
    assert len(pots) == 3
    assert pots[0].amount == 200
    assert pots[0].eligible_player_ids == {"A", "B", "C", "D"}
    
    assert pots[1].amount == 150
    assert pots[1].eligible_player_ids == {"B", "C", "D"}
    
    assert pots[2].amount == 200
    assert pots[2].eligible_player_ids == {"C", "D"}

def test_folded_player_bets_more_than_active():
    contributions = {"A": 300, "B": 100, "C": 100}
    active_ids = {"B", "C"}  # A folded
    
    # A is folded, so A's excess cannot be refunded.
    # Active levels: [100]
    # Pot 1 (level 100): A (100), B (100), C (100) = 300. Eligible: {B, C}
    # Remaining chips from A (200) are swept into Pot 1.
    # Total pot = 500. Eligible: {B, C}
    pots = resolve_pots(contributions, active_ids)
    
    assert len(pots) == 1
    assert pots[0].amount == 500
    assert pots[0].eligible_player_ids == {"B", "C"}

def test_no_active_contributions_but_money_exists():
    # E.g. Check down, but blinds are in the pot.
    contributions = {"A": 10, "B": 20, "C": 0}
    active_ids = {"A", "B", "C"}
    
    # B's bet of 20 is uncalled relative to A's 10.
    # B refunded 10. Contributions: A: 10, B: 10, C: 0.
    # Active levels: [10]
    # Pot 1: A (10), B (10), C (0) = 20. Eligible: {A, B} (C didn't contribute to level 10).
    pots = resolve_pots(contributions, active_ids)
    
    assert len(pots) == 1
    assert pots[0].amount == 20
    assert pots[0].eligible_player_ids == {"A", "B"}
