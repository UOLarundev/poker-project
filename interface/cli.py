import random
import sys
from poker_engine.player import PlayerState
from poker_engine.actions import Action, ActionType
from poker_engine.game import GameState


def choose_bot_action(state: GameState) -> Action:
    """Determine a simple action for a bot player."""
    bot_id = state.betting_state.current_actor.player_id
    allowed = state.betting_state.get_allowed_actions(bot_id)
    allowed_types = {a.action_type for a in allowed}
    
    actor = state.betting_state.current_actor
    current_bet = state.betting_state.current_bet
    last_raise = state.betting_state.last_raise_increment
    bb = state.betting_state.big_blind
    
    # Calculate raise boundaries
    min_raise = bb if current_bet == 0 else current_bet + last_raise
    max_raise = actor.chips_in_street + actor.stack
    
    choice = random.random()
    
    if ActionType.CHECK in allowed_types:
        # Check 80%, Raise 20%
        if choice < 0.8:
            return Action(ActionType.CHECK)
        elif ActionType.RAISE in allowed_types:
            raise_amt = min(min_raise, max_raise)
            return Action(ActionType.RAISE, amount=raise_amt)
        else:
            return Action(ActionType.CHECK)
            
    elif ActionType.CALL in allowed_types:
        # Call 70%, Raise 15%, Fold 15%
        if choice < 0.7:
            return Action(ActionType.CALL)
        elif choice < 0.85 and ActionType.RAISE in allowed_types:
            raise_amt = min(min_raise, max_raise)
            return Action(ActionType.RAISE, amount=raise_amt)
        else:
            return Action(ActionType.FOLD)
            
    elif ActionType.ALL_IN in allowed_types:
        return Action(ActionType.ALL_IN)
        
    return Action(ActionType.FOLD)


def format_card(card) -> str:
    """Format Card object into a pretty colored string representation."""
    suit_symbols = {
        "H": "♥",
        "D": "♦",
        "C": "♣",
        "S": "♠"
    }
    # Color coding for terminal output
    # Red for Hearts/Diamonds, Blue/Grey for Spades/Clubs
    red = "\033[91m"
    blue = "\033[94m"
    reset = "\033[0m"
    
    color = red if card.suit.value in ("H", "D") else blue
    return f"{color}[{card.rank}{suit_symbols[card.suit.value]}]{reset}"


def format_cards(cards) -> str:
    return " ".join(format_card(c) for c in cards)


def play_game():
    print("=" * 50)
    print("          WELCOME TO ANTIGRAVITY POKER CLI          ")
    print("=" * 50)

    # Initialize players: Human (You) and two bots (Bot A, Bot B)
    players = [
        PlayerState(player_id="You", stack=1000),
        PlayerState(player_id="Bot A", stack=1000),
        PlayerState(player_id="Bot B", stack=1000)
    ]
    
    dealer_button_index = 0
    hand_count = 1
    
    while True:
        # Filter out eliminated players (stack == 0)
        players = [p for p in players if p.stack > 0]
        
        # Check end of game
        if len(players) < 2:
            print("\nGame Over!")
            if players and players[0].player_id == "You":
                print("Congratulations! You won the game!")
            else:
                print("You went bust or were eliminated.")
            break
            
        print(f"\n--- HAND #{hand_count} (Dealer Button: {players[dealer_button_index % len(players)].player_id}) ---")
        for p in players:
            print(f"  * {p.player_id}: ${p.stack}")
            
        # Start new hand
        state = GameState.start_new_hand(
            players=players,
            dealer_button_index=dealer_button_index % len(players),
            sb_amount=5,
            bb_amount=10
        )
        
        # Play betting streets
        prev_street = ""
        while state.street not in ("SHOWDOWN", "HAND_OVER"):
            # Print street header when transitioning
            if state.street != prev_street:
                pot_size = sum(p.chips_in_hand for p in state.players)
                print(f"\n>>> {state.street} (Pot: ${pot_size}) <<<")
                if state.board_cards:
                    print(f"Board: {format_cards(state.board_cards)}")
                prev_street = state.street

            actor = state.betting_state.current_actor
            actor_id = actor.player_id
            
            if actor_id == "You":
                # Print current game state context
                your_hole = state.player_hands["You"]
                pot_size = sum(p.chips_in_hand for p in state.players)
                print(f"\nYour hand: {format_cards(your_hole)}")
                print(f"Pot: ${pot_size} | Your stack: ${actor.stack} | Current bet to call: ${state.betting_state.current_bet} (you have bet ${actor.chips_in_street})")
                
                # Get allowed actions
                allowed = state.betting_state.get_allowed_actions("You")
                allowed_types = [a.action_type for a in allowed]
                
                # Build option string
                options = []
                if ActionType.FOLD in allowed_types:
                    options.append("(f)old")
                if ActionType.CHECK in allowed_types:
                    options.append("(c)heck")
                if ActionType.CALL in allowed_types:
                    call_needed = state.betting_state.current_bet - actor.chips_in_street
                    options.append(f"(ca)ll ${call_needed}")
                if ActionType.RAISE in allowed_types:
                    min_raise = state.betting_state.big_blind if state.betting_state.current_bet == 0 else state.betting_state.current_bet + state.betting_state.last_raise_increment
                    options.append(f"(r)aise (min raise: ${min_raise})")
                if ActionType.ALL_IN in allowed_types:
                    options.append(f"(a)ll-in (${actor.stack})")
                
                print(f"Actions: {', '.join(options)}")
                
                action = None
                while action is None:
                    try:
                        user_input = input("Choose action: ").strip().lower().split()
                        if not user_input:
                            continue
                        cmd = user_input[0]
                        
                        if cmd == "f" and ActionType.FOLD in allowed_types:
                            action = Action(ActionType.FOLD)
                        elif cmd == "c" and ActionType.CHECK in allowed_types:
                            action = Action(ActionType.CHECK)
                        elif cmd == "ca" and ActionType.CALL in allowed_types:
                            action = Action(ActionType.CALL)
                        elif cmd == "a" and ActionType.ALL_IN in allowed_types:
                            action = Action(ActionType.ALL_IN)
                        elif cmd == "r" and ActionType.RAISE in allowed_types:
                            if len(user_input) < 2:
                                print("Please specify raise amount (e.g. 'r 50')")
                                continue
                            amount = int(user_input[1])
                            action = Action(ActionType.RAISE, amount=amount)
                        else:
                            print("Invalid action selection. Try again.")
                    except ValueError as e:
                        print(f"Error parsing raise amount: {e}")
                    except Exception as e:
                        print(f"Error: {e}")
                        
                # Apply action
                state = state.apply_action(action)
                if action.action_type == ActionType.RAISE:
                    print(f"You raised to ${action.amount}")
                elif action.action_type == ActionType.CALL:
                    print("You called")
                else:
                    print(f"You chose: {action.action_type.value}")
            else:
                # Bot action
                action = choose_bot_action(state)
                # Save previous bet size to print details
                prev_bet = state.betting_state.current_bet
                state = state.apply_action(action)
                
                # Format print statements for bots
                if action.action_type == ActionType.FOLD:
                    print(f"{actor_id} folds")
                elif action.action_type == ActionType.CHECK:
                    print(f"{actor_id} checks")
                elif action.action_type == ActionType.CALL:
                    print(f"{actor_id} calls")
                elif action.action_type == ActionType.RAISE:
                    print(f"{actor_id} raises to ${action.amount}")
                elif action.action_type == ActionType.ALL_IN:
                    print(f"{actor_id} goes ALL-IN!")
                    
        # Hand concluded
        print(f"\n--- HAND CONCLUDED ({state.street}) ---")
        if state.board_cards:
            print(f"Board: {format_cards(state.board_cards)}")
            
        # Reveal hands
        print("\nHole Cards:")
        for p in state.players:
            hole = state.player_hands[p.player_id]
            folded_str = " (Folded)" if p.is_folded else ""
            all_in_str = " (All-in)" if p.is_all_in else ""
            print(f"  * {p.player_id}: {format_cards(hole)}{folded_str}{all_in_str}")
            
        print("\nWinners:")
        for pid, amt in state.winners.items():
            print(f"  * {pid} wins ${amt}!")
            
        # Update stacks for the next hand
        players = list(state.players)
        
        # Ask to continue
        cont = input("\nPlay next hand? (y/n): ").strip().lower()
        if cont != "y":
            print("\nThanks for playing!")
            break
            
        dealer_button_index += 1
        hand_count += 1


if __name__ == "__main__":
    try:
        play_game()
    except KeyboardInterrupt:
        print("\nGame aborted. Goodbye!")
        sys.exit(0)
