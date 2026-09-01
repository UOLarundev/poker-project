import random
import sys
from poker_engine.player import PlayerState
from poker_engine.actions import Action, ActionType
from poker_engine.game import GameState
from poker_engine.equity import calculate_equity


def choose_bot_action(state: GameState) -> Action:
    bot_id = state.betting_state.current_actor.player_id
    allowed = state.betting_state.get_allowed_actions(bot_id)
    allowed_types = {a.action_type for a in allowed}

    actor = state.betting_state.current_actor
    current_bet = state.betting_state.current_bet
    last_raise = state.betting_state.last_raise_increment
    bb = state.betting_state.big_blind

    min_raise = bb if current_bet == 0 else current_bet + last_raise
    max_raise = actor.chips_in_street + actor.stack

    choice = random.random()

    if ActionType.CHECK in allowed_types:
        if choice < 0.8 or ActionType.RAISE not in allowed_types:
            return Action(ActionType.CHECK)
        else:
            return Action(ActionType.RAISE, amount=min(min_raise, max_raise))

    if ActionType.CALL in allowed_types:
        if choice < 0.7:
            return Action(ActionType.CALL)
        elif choice < 0.85 and ActionType.RAISE in allowed_types:
            return Action(ActionType.RAISE, amount=min(min_raise, max_raise))
        elif ActionType.FOLD in allowed_types:
            return Action(ActionType.FOLD)
        else:
            return Action(ActionType.CALL)

    if ActionType.ALL_IN in allowed_types:
        return Action(ActionType.ALL_IN)

    if ActionType.FOLD in allowed_types:
        return Action(ActionType.FOLD)

    # Should never reach here — return first allowed action as safety net
    return allowed[0]

def display_equity_if_allin(state: GameState) -> None:
    active_players = [p for p in state.players if not p.is_folded]
    if all(p.is_all_in for p in active_players) and len(active_players) > 1 and state.board_cards:
        # Use the board as it stood when the all-in was locked in, not the
        # fully-dealt board — otherwise equity is always 100%/0% for whoever
        # the already-known runout favors.
        board = state.all_in_snapshot_board if state.all_in_snapshot_board is not None else state.board_cards
        player_hands = {p.player_id: list(state.player_hands[p.player_id]) for p in active_players}
        equities = calculate_equity(player_hands, list(board))
        print("\n--- ALL-IN EQUITY ---")
        for pid, eq in equities.items():
            print(f"  {pid}: {eq:.1%}")
        print("---------------------")


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
    print("          POKER CLI          ")
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
                display_equity_if_allin(state)                
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
                display_equity_if_allin(state)
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
                display_equity_if_allin(state)
                    
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
        # Update stacks for the next hand — reset all hand state, keep only id and chips
        players = [
            PlayerState(player_id=p.player_id, stack=p.stack)
            for p in state.players
            if p.stack > 0
        ]
        
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
