from __future__ import annotations

from collections import Counter
from enum import IntEnum
from itertools import combinations

from poker_engine.cards import Card, Rank # type: ignore

class HandRank(IntEnum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    TRIPS = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    QUADS = 8
    STRAIGHT_FLUSH = 9

def evaluate(cards: list[Card]) -> tuple[HandRank, list[Rank]]:
    """Return the best hand achievable from the given cards (5-7).
    
    Tries all 5-card combinations and returns the highest ranked one.
    """
    # TODO: use combinations() to generate all 5-card subsets
    # TODO: call _evaluate_five() on each, return the best one

    combos = combinations(cards, 5)
    best_hand = None
    for combo in combos:
        hand_rank, tiebreaker = _evaluate_five(combo)
        if best_hand is None or (hand_rank, tiebreaker) > best_hand:
            best_hand = (hand_rank, tiebreaker)
    return best_hand

def _evaluate_five(cards: list[Card]) -> tuple[HandRank, list[Rank]]:
    """Evaluate exactly 5 cards. Checks from best hand to worst."""
    # TODO: build rank_counts (Counter) and suits (list) here
    # then check from best to worst, returning as soon as you find a match
    # _is_straight_flush -> _is_quads -> _is_full_house -> ...

    rank_counts = Counter(card.rank for card in cards)
    if result:=_is_straight_flush(cards):
        return (HandRank.STRAIGHT_FLUSH, result)
    if result:=_is_quads(rank_counts):
        return (HandRank.QUADS, result)
    if result:=_is_full_house(rank_counts):
        return (HandRank.FULL_HOUSE, result)
    if result:=_is_flush(cards):
        return (HandRank.FLUSH, result)
    if result:=_is_straight(cards):
        return (HandRank.STRAIGHT, result)
    if result:=_is_trips(rank_counts):
        return (HandRank.TRIPS, result)
    if result:=_is_two_pair(rank_counts):
        return (HandRank.TWO_PAIR, result)
    if result:=_is_pair(rank_counts):
        return (HandRank.PAIR, result)
    return (HandRank.HIGH_CARD, _high_card(cards))

# --- helper detectors, each takes 5 cards ---
# each returns the tiebreaker rank list if the hand is found, else None

def _is_straight_flush(cards: list[Card]) -> list[Rank] | None:
    # TODO: a hand is a straight flush if it's both a flush and a straight
    # hint: reuse _is_flush and _is_straight
    if _is_flush(cards) and (result := _is_straight(cards)):
        return result
    return None


def _is_quads(rank_counts: Counter) -> list[Rank] | None:
    # TODO: find the rank with count 4, then the kicker
    for rank, count in rank_counts.items():
        if count == 4:
            kickers = sorted((r for r in rank_counts if r != rank), reverse=True)
            return [rank] + kickers[:1]
    return None


def _is_full_house(rank_counts: Counter) -> list[Rank] | None:
    # TODO: find the rank with count 3 and the rank with count 2
    threes = [rank for rank, count in rank_counts.items() if count == 3]
    twos = [rank for rank, count in rank_counts.items() if count == 2]
    if threes and twos:
        return [threes[0]] + [twos[0]]
    return None


def _is_flush(cards: list[Card]) -> list[Rank] | None:
    # TODO: all 5 cards same suit — return ranks highest first
    suits = [card.suit for card in cards]
    if len(set(suits)) == 1:
        return sorted([card.rank for card in cards], reverse=True)
    return None


def _is_straight(cards: list[Card]) -> list[Rank] | None:
    ranks = sorted(set(card.rank for card in cards), reverse=True)
    if len(ranks) == 5 and ranks[0] - ranks[4] == 4:
        return ranks
    if set(ranks) == {Rank.ACE, Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE}:
        return [Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO, Rank.ACE]
    return None


def _is_trips(rank_counts: Counter) -> list[Rank] | None:
    # TODO: one rank appears 3 times, return it then the two kickers
    for rank, count in rank_counts.items():
        if count == 3:
            kickers = sorted((r for r in rank_counts if r != rank), reverse=True)
            return [rank] + kickers[:2]
    return None


def _is_two_pair(rank_counts: Counter) -> list[Rank] | None:
    # TODO: two ranks each appear twice, return higher pair, lower pair, kicker
    pairs = [rank for rank, count in rank_counts.items() if count == 2]
    if len(pairs) == 2:
        kickers = sorted((r for r in rank_counts if r not in pairs), reverse=True)
        return sorted(pairs, reverse=True) + kickers[:1]
    return None


def _is_pair(rank_counts: Counter) -> list[Rank] | None:
    # TODO: one rank appears twice, return it then the three kickers
    for rank, count in rank_counts.items():
        if count == 2:
            kickers = sorted((r for r in rank_counts if r != rank), reverse=True)
            return [rank] + kickers[:3]
    return None


def _high_card(cards: list[Card]) -> list[Rank]:
    # TODO: just return all ranks sorted highest first
    return sorted([card.rank for card in cards], reverse=True)
