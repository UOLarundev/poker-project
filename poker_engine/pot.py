from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Pot:
    """A single pot (main or side) that players can contest at showdown."""
    amount: int
    eligible_player_ids: set[str]


def resolve_pots(contributions: dict[str, int], active_ids: set[str]) -> list[Pot]:
    """Calculate the main and side pots from player contributions and active status.
    
    Any uncalled bet from the leading active player is excluded and should be
    refunded to them (the caller should handle adjusting the player's stack).
    
    Returns a list of Pot objects.
    """
    contributions = contributions.copy()
    
    # 1. Identify and handle uncalled bets.
    # If the player with the highest contribution is active and has bet more than 
    # the second highest contribution, the difference is uncalled and refunded.
    while True:
        sorted_contribs = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_contribs) <= 1:
            break
        top_pid, top_amt = sorted_contribs[0]
        sec_pid, sec_amt = sorted_contribs[1]
        
        if top_amt == sec_amt:
            break
            
        if top_pid in active_ids:
            # Active player has bet more than the second place; refund the difference
            contributions[top_pid] = sec_amt
        else:
            # The top player is folded, so their excess bet is "dead money" and cannot be refunded
            break

    # 2. Get all positive contributions of ACTIVE players.
    active_contribs = [amt for pid, amt in contributions.items() if pid in active_ids and amt > 0]
    if not active_contribs:
        # If no active player has contributed anything (e.g. check down in blinds),
        # but there is money in the pot (from blinds or folded players),
        # all active players are eligible for it.
        total_pot = sum(contributions.values())
        if total_pot > 0:
            return [Pot(amount=total_pot, eligible_player_ids=set(active_ids))]
        return []

    # Sort the unique active contribution levels in ascending order.
    active_levels = sorted(list(set(active_contribs)))
    
    pots = []
    prev_level = 0
    
    for level in active_levels:
        step = level - prev_level
        pot_amount = 0
        eligible_players = set()
        
        # Collect contributions for this step
        for pid, amt in contributions.items():
            contributed_to_step = min(amt, step)
            pot_amount += contributed_to_step
            contributions[pid] -= contributed_to_step
            
            # Eligible if active and contributed to this step
            if pid in active_ids and contributed_to_step > 0:
                eligible_players.add(pid)
                
        pots.append(Pot(amount=pot_amount, eligible_player_ids=eligible_players))
        prev_level = level

    # 3. Add any remaining chips (from folded players who bet more than the highest active player)
    # to the last pot.
    remaining_chips = sum(contributions.values())
    if remaining_chips > 0 and pots:
        last_pot = pots[-1]
        pots[-1] = Pot(amount=last_pot.amount + remaining_chips, eligible_player_ids=last_pot.eligible_player_ids)
        
    return pots
