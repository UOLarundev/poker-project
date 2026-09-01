from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from poker_engine.cards import Card, Deck
from poker_engine.player import PlayerState
from poker_engine.actions import Action
from poker_engine.betting_round import BettingRoundState
from poker_engine.pot import resolve_pots, Pot
from poker_engine.hand_eval import evaluate


@dataclass(frozen=True)
class GameState:
    """Immutable state machine representing a full hand of Texas Hold'em."""
    players: tuple[PlayerState, ...]
    dealer_button_index: int
    sb_amount: int
    bb_amount: int
    
    deck_cards: tuple[Card, ...]
    board_cards: tuple[Card, ...]
    street: str  # "PRE_FLOP", "FLOP", "TURN", "RIVER", "SHOWDOWN", "HAND_OVER"
    player_hands: dict[str, tuple[Card, Card]]  # player_id -> (card1, card2)
    
    betting_state: BettingRoundState | None
    winners: dict[str, int] | None = None  # player_id -> chips won
    pots_at_showdown: tuple[Pot, ...] | None = None
    # Board as it stood the instant the last player went all-in, before the
    # remaining streets were auto-dealt. Lets callers (e.g. the CLI) compute
    # true equity-with-cards-to-come instead of a deterministic result against
    # the already-completed board.
    all_in_snapshot_board: tuple[Card, ...] | None = None

    @classmethod
    def start_new_hand(
        cls,
        players: Sequence[PlayerState],
        dealer_button_index: int,
        sb_amount: int,
        bb_amount: int,
        deck: Deck | None = None
    ) -> GameState:
        """Set up and start a new hand, posting blinds and dealing hole cards."""
        n = len(players)
        if n < 2:
            raise ValueError("Must have at least 2 players to start a hand")

        if deck is None:
            deck = Deck()
            deck.shuffle()
        
        # Convert deck to tuple for immutability
        deck_cards = tuple(deck._cards)

        # 1. Post Blinds
        # In heads-up (2 players): dealer is SB, non-dealer is BB.
        # In multi-player (>2): SB is button + 1, BB is button + 2.
        if n == 2:
            sb_idx = dealer_button_index
            bb_idx = (dealer_button_index + 1) % 2
        else:
            sb_idx = (dealer_button_index + 1) % n
            bb_idx = (dealer_button_index + 2) % n

        temp_players = list(players)
        
        # Post SB
        sb_player = temp_players[sb_idx]
        posted_sb = min(sb_amount, sb_player.stack)
        temp_players[sb_idx] = sb_player.bet_chips(posted_sb)

        # Post BB
        bb_player = temp_players[bb_idx]
        posted_bb = min(bb_amount, bb_player.stack)
        temp_players[bb_idx] = bb_player.bet_chips(posted_bb)

        # 2. Deal Hole Cards
        # Deal starts clockwise from the player to the left of the button.
        start_deal_idx = (dealer_button_index + 1) % n
        player_hands = {}
        
        # We need 2 cards per player
        curr_deck = list(deck_cards)
        
        # Initialize empty hands
        for p in temp_players:
            player_hands[p.player_id] = []

        # Deal first card to everyone, then second card
        for _ in range(2):
            for i in range(n):
                idx = (start_deal_idx + i) % n
                card = curr_deck.pop(0)
                player_hands[temp_players[idx].player_id].append(card)

        # Convert to tuple for safety
        final_player_hands = {pid: (cards[0], cards[1]) for pid, cards in player_hands.items()}
        remaining_deck = tuple(curr_deck)

        # 3. Determine first actor and start PRE_FLOP betting
        # Pre-flop first actor:
        # heads-up: dealer acts first.
        # multi-player: player left of BB acts first.
        if n == 2:
            first_actor = dealer_button_index
        else:
            first_actor = (dealer_button_index + 3) % n

        # If the first actor is already all-in, find the next active player
        # Note: BettingRoundState.initialize takes care of initializing active lists.
        # But we need to make sure first_actor_index points to a valid actor.
        round_players = tuple(temp_players)
        
        # Enforce that if first actor is all-in, find the next one who isn't
        if round_players[first_actor].is_all_in:
            first_actor = cls._find_next_actor_static(round_players, first_actor)

        # Initialize the Preflop Betting Round
        # current_bet is bb_amount, last_raise_increment is bb_amount
        betting_state = BettingRoundState.initialize(
            players=round_players,
            first_actor_index=first_actor,
            current_bet=bb_amount,
            last_raise_increment=bb_amount,
            big_blind=bb_amount
        )

        return cls(
            players=round_players,
            dealer_button_index=dealer_button_index,
            sb_amount=sb_amount,
            bb_amount=bb_amount,
            deck_cards=remaining_deck,
            board_cards=(),
            street="PRE_FLOP",
            player_hands=final_player_hands,
            betting_state=betting_state
        )

    def apply_action(self, action: Action) -> GameState:
        """Apply a player's action to the game state, transitioning streets as needed."""
        if self.street in ("SHOWDOWN", "HAND_OVER"):
            raise ValueError(f"Cannot apply actions in terminal street {self.street}")

        if self.betting_state is None:
            raise ValueError("No active betting round in progress")

        # Apply action to current betting round
        new_betting_state = self.betting_state.apply_action(action)
        new_players = new_betting_state.players

        # If the betting round is NOT complete, just update the betting round state and player list
        if not new_betting_state.is_round_complete():
            return GameState(
                players=new_players,
                dealer_button_index=self.dealer_button_index,
                sb_amount=self.sb_amount,
                bb_amount=self.bb_amount,
                deck_cards=self.deck_cards,
                board_cards=self.board_cards,
                street=self.street,
                player_hands=self.player_hands,
                betting_state=new_betting_state
            )

        # If the round is complete, collect all street bets into player chips_in_hand
        collected_players = []
        for p in new_players:
            collected_players.append(
                PlayerState(
                    player_id=p.player_id,
                    stack=p.stack,
                    chips_in_street=0,
                    chips_in_hand=p.chips_in_hand,
                    is_folded=p.is_folded,
                    is_all_in=p.is_all_in
                )
            )
        new_players = tuple(collected_players)

        # Check the number of active (non-folded) players
        active_players = [p for p in new_players if not p.is_folded]
        if len(active_players) <= 1:
            # Everyone folded except one player; they win the hand immediately
            winner_id = active_players[0].player_id if active_players else new_players[0].player_id
            return self._resolve_hand_winner_by_folding(new_players, winner_id)

        # Check if we should skip remaining betting rounds (i.e. all except at most one are all-in)
        non_all_in_active = [p for p in active_players if not p.is_all_in]
        if len(non_all_in_active) <= 1:
            # Run out all remaining board cards and go straight to showdown
            return self._run_allout_to_showdown(new_players, self.deck_cards)

        # Advance to the next street
        return self._advance_street(new_players, self.deck_cards)

    def _advance_street(self, current_players: tuple[PlayerState, ...], remaining_deck: tuple[Card, ...]) -> GameState:
        """Transition the hand to the next street (FLOP, TURN, RIVER, SHOWDOWN)."""
        deck_list = list(remaining_deck)
        new_board = list(self.board_cards)
        
        if self.street == "PRE_FLOP":
            next_street = "FLOP"
            # Burn 1, deal 3
            deck_list.pop(0)
            new_board.extend(deck_list[:3])
            deck_list = deck_list[3:]
        elif self.street == "FLOP":
            next_street = "TURN"
            # Burn 1, deal 1
            deck_list.pop(0)
            new_board.append(deck_list.pop(0))
        elif self.street == "FLOP_RUNOUT": # internal runout step
            next_street = "TURN"
            deck_list.pop(0)
            new_board.append(deck_list.pop(0))
        elif self.street == "TURN":
            next_street = "RIVER"
            # Burn 1, deal 1
            deck_list.pop(0)
            new_board.append(deck_list.pop(0))
        elif self.street == "RIVER":
            # Run showdown
            return self._run_showdown(current_players, self.board_cards)
        else:
            raise ValueError(f"Unknown street transition from {self.street}")

        # Post-flop first actor: first active, non-all-in player left of dealer button.
        first_actor = self._find_first_postflop_actor(current_players)

        # Initialize the betting round for the new street
        new_betting_state = BettingRoundState.initialize(
            players=current_players,
            first_actor_index=first_actor,
            current_bet=0,
            last_raise_increment=self.bb_amount,
            big_blind=self.bb_amount
        )

        return GameState(
            players=current_players,
            dealer_button_index=self.dealer_button_index,
            sb_amount=self.sb_amount,
            bb_amount=self.bb_amount,
            deck_cards=tuple(deck_list),
            board_cards=tuple(new_board),
            street=next_street,
            player_hands=self.player_hands,
            betting_state=new_betting_state
        )

    def _run_allout_to_showdown(self, current_players: tuple[PlayerState, ...], remaining_deck: tuple[Card, ...]) -> GameState:
        """Deal all remaining board cards directly to showdown (no more betting rounds)."""
        deck_list = list(remaining_deck)
        new_board = list(self.board_cards)
        pre_runout_board = tuple(self.board_cards)

        # Deal Flop if not dealt
        if len(new_board) == 0:
            deck_list.pop(0) # burn
            new_board.extend(deck_list[:3])
            deck_list = deck_list[3:]

        # Deal Turn if not dealt
        if len(new_board) == 3:
            deck_list.pop(0) # burn
            new_board.append(deck_list.pop(0))

        # Deal River if not dealt
        if len(new_board) == 4:
            deck_list.pop(0) # burn
            new_board.append(deck_list.pop(0))

        return self._run_showdown(current_players, tuple(new_board), all_in_snapshot_board=pre_runout_board)

    def _run_showdown(
        self,
        current_players: tuple[PlayerState, ...],
        final_board: tuple[Card, ...],
        all_in_snapshot_board: tuple[Card, ...] | None = None
    ) -> GameState:
        """Run showdown logic: evaluate hands, calculate side pots, and award chips."""
        # 1. Apply refunds for any uncalled bets
        contributions = {p.player_id: p.chips_in_hand for p in current_players}
        active_ids = {p.player_id for p in current_players if not p.is_folded}

        while True:
            sorted_contribs = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_contribs) <= 1:
                break
            top_pid, top_amt = sorted_contribs[0]
            sec_pid, sec_amt = sorted_contribs[1]
            if top_amt == sec_amt:
                break
            if top_pid in active_ids:
                contributions[top_pid] = sec_amt
            else:
                break

        # Apply refunds to player stacks
        refunded_players = []
        for p in current_players:
            refund = p.chips_in_hand - contributions[p.player_id]
            refunded_players.append(
                PlayerState(
                    player_id=p.player_id,
                    stack=p.stack + refund,
                    chips_in_street=0,
                    chips_in_hand=contributions[p.player_id],
                    is_folded=p.is_folded,
                    is_all_in=p.is_all_in
                )
            )
        current_players = tuple(refunded_players)

        # 2. Resolve Pots (Main and Side Pots)
        pots = resolve_pots(contributions, active_ids)
        winners_dict = {p.player_id: 0 for p in current_players}

        # 3. Evaluate hands and distribute chips for each pot
        for pot in pots:
            # Evaluate only the eligible players for this specific pot
            player_scores = {
                pid: evaluate(list(self.player_hands[pid]) + list(final_board))
                for pid in pot.eligible_player_ids
            }
            
            best_score = max(player_scores.values())
            pot_winners = [pid for pid, score in player_scores.items() if score == best_score]
            
            # Split pot
            share = pot.amount // len(pot_winners)
            remainder = pot.amount % len(pot_winners)
            
            for pid in pot_winners:
                winners_dict[pid] += share

            # Distribute odd chips starting from the player left of the button
            if remainder > 0:
                # Find player indexes
                n = len(current_players)
                # Sort winners by distance clockwise from (dealer_button_index + 1)
                sorted_winners = sorted(
                    pot_winners,
                    key=lambda pid: (
                        self._get_player_index_by_id(current_players, pid) - (self.dealer_button_index + 1)
                    ) % n
                )
                for i in range(remainder):
                    winner_pid = sorted_winners[i % len(sorted_winners)]
                    winners_dict[winner_pid] += 1

        # 4. Award chips to player stacks
        final_players = []
        for p in current_players:
            winnings = winners_dict[p.player_id]
            final_players.append(
                PlayerState(
                    player_id=p.player_id,
                    stack=p.stack + winnings,
                    chips_in_street=0,
                    chips_in_hand=0,
                    is_folded=p.is_folded,
                    is_all_in=p.is_all_in
                )
            )

        return GameState(
            players=tuple(final_players),
            dealer_button_index=self.dealer_button_index,
            sb_amount=self.sb_amount,
            bb_amount=self.bb_amount,
            deck_cards=(),
            board_cards=final_board,
            street="HAND_OVER",
            player_hands=self.player_hands,
            betting_state=None,
            winners={pid: amt for pid, amt in winners_dict.items() if amt > 0},
            pots_at_showdown=tuple(pots),
            all_in_snapshot_board=all_in_snapshot_board
        )

    def _resolve_hand_winner_by_folding(self, current_players: tuple[PlayerState, ...], winner_id: str) -> GameState:
        """Resolve the hand when all players except one fold."""
        contributions = {p.player_id: p.chips_in_hand for p in current_players}
        active_ids = {winner_id}

        # Refund uncalled bets
        while True:
            sorted_contribs = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_contribs) <= 1:
                break
            top_pid, top_amt = sorted_contribs[0]
            sec_pid, sec_amt = sorted_contribs[1]
            if top_amt == sec_amt:
                break
            if top_pid in active_ids:
                contributions[top_pid] = sec_amt
            else:
                break

        # Apply refunds
        refunded_players = []
        for p in current_players:
            refund = p.chips_in_hand - contributions[p.player_id]
            refunded_players.append(
                PlayerState(
                    player_id=p.player_id,
                    stack=p.stack + refund,
                    chips_in_street=0,
                    chips_in_hand=contributions[p.player_id],
                    is_folded=p.is_folded,
                    is_all_in=p.is_all_in
                )
            )
        current_players = tuple(refunded_players)

        # Winner takes the whole pot (sum of all remaining contributions)
        total_pot = sum(contributions.values())
        
        final_players = []
        for p in current_players:
            winnings = total_pot if p.player_id == winner_id else 0
            final_players.append(
                PlayerState(
                    player_id=p.player_id,
                    stack=p.stack + winnings,
                    chips_in_street=0,
                    chips_in_hand=0,
                    is_folded=p.is_folded,
                    is_all_in=p.is_all_in
                )
            )

        return GameState(
            players=tuple(final_players),
            dealer_button_index=self.dealer_button_index,
            sb_amount=self.sb_amount,
            bb_amount=self.bb_amount,
            deck_cards=(),
            board_cards=self.board_cards,
            street="HAND_OVER",
            player_hands=self.player_hands,
            betting_state=None,
            winners={winner_id: total_pot}
        )

    def _find_first_postflop_actor(self, players: tuple[PlayerState, ...]) -> int:
        n = len(players)
        for i in range(1, n + 1):
            idx = (self.dealer_button_index + i) % n
            p = players[idx]
            if not p.is_folded and not p.is_all_in:
                return idx
        raise ValueError("No active players to act")

    def _get_player_index_by_id(self, players: tuple[PlayerState, ...], player_id: str) -> int:
        for idx, p in enumerate(players):
            if p.player_id == player_id:
                return idx
        raise ValueError(f"Player {player_id} not found")

    @staticmethod
    def _find_next_actor_static(players: tuple[PlayerState, ...], start_idx: int) -> int:
        n = len(players)
        for i in range(1, n + 1):
            idx = (start_idx + i) % n
            p = players[idx]
            if not p.is_folded and not p.is_all_in:
                return idx
        raise ValueError("No active players to act")
