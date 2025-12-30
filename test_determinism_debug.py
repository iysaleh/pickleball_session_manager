#!/usr/bin/env python3
"""
Test to debug determinism issues in match creation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session
from python.pickleball_types import SessionConfig, PlayerStats, Player
from python.competitive_variety import populate_empty_courts_competitive_variety
from python.wait_priority import get_priority_aware_candidates, sort_players_by_wait_priority

def create_session_from_export():
    """Create session matching the export file state."""
    
    # Players from the waitlist with their ELOs
    players_data = [
        ('Mike', 1852, 4, 1, 50, 29),
        ('Alisha', 1552, 1, 2, 26, 28),
        ('Payton', 1853, 5, 1, 59, 40),
        ('Robert', 1749, 3, 2, 43, 39),
        ('Carrie', 1220, 0, 3, 21, 33),
        ('Renea Wood', 1848, 4, 1, 51, 32),
        ('Mikes guest', 1771, 2, 1, 29, 24),
    ]
    
    players = []
    for name, _, _, _, _, _ in players_data:
        players.append(Player(id=name, name=name))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Update player stats to match export
    for name, expected_elo, wins, losses, pts_for, pts_against in players_data:
        stats = session.player_stats[name]
        stats.wins = wins
        stats.games_played = wins + losses
        stats.total_points_for = pts_for
        stats.total_points_against = pts_against
        
        # Set wait times to match the export (converting from "MM:SS" format)
        wait_times = {
            'Mike': 135,      # 02:15
            'Alisha': 51,     # 00:51
            'Payton': 190,    # 03:10
            'Robert': 146,    # 02:26
            'Carrie': 51,     # 00:51
            'Renea Wood': 48, # 00:48
            'Mikes guest': 51 # 00:51
        }
        stats.total_wait_time = wait_times.get(name, 0)
    
    # Simulate match history to create partner/opponent constraints
    # From the export, we can see recent partnerships that would create constraints
    
    return session

def test_candidate_selection_determinism():
    """Test if candidate selection is deterministic."""
    session = create_session_from_export()
    
    print("Determinism Test for Candidate Selection")
    print("=" * 60)
    
    available_players = list(session.active_players)
    print(f"Available players: {available_players}")
    print()
    
    # Test candidate selection multiple times
    print("Testing candidate selection consistency:")
    results = []
    for i in range(5):
        candidates = get_priority_aware_candidates(session, available_players, 16)
        results.append(candidates)
        print(f"Run {i+1}: {candidates}")
    
    # Check if all results are identical
    all_same = all(result == results[0] for result in results)
    print(f"\nAll results identical: {all_same}")
    
    if not all_same:
        print("❌ NON-DETERMINISTIC BEHAVIOR DETECTED!")
        return False
    
    return True

def test_sorting_determinism():
    """Test if wait priority sorting is deterministic."""
    session = create_session_from_export()
    
    print("\nSorting Determinism Test")
    print("=" * 40)
    
    available_players = list(session.active_players)
    
    # Test sorting multiple times
    print("Testing sort consistency:")
    results = []
    for i in range(5):
        sorted_players = sort_players_by_wait_priority(session, available_players)
        results.append(sorted_players)
        print(f"Run {i+1}: {sorted_players}")
    
    # Check if all results are identical
    all_same = all(result == results[0] for result in results)
    print(f"\nAll sorting results identical: {all_same}")
    
    if not all_same:
        print("❌ SORTING IS NON-DETERMINISTIC!")
        # Check for ties that might cause instability
        from python.wait_priority import calculate_relative_wait_priority_infos
        priority_infos = calculate_relative_wait_priority_infos(session, available_players)
        
        print("\nPriority analysis:")
        for info in priority_infos:
            print(f"  {info.player_id}: tier={info.priority_tier}, wait={info.total_wait_seconds}, games={info.games_waited}")
        
        return False
    
    return True

def test_combination_order():
    """Test if itertools.combinations produces consistent results."""
    from itertools import combinations
    
    print("\nCombination Order Test")  
    print("=" * 30)
    
    session = create_session_from_export()
    candidates = get_priority_aware_candidates(session, list(session.active_players), 16)
    
    print(f"Candidates: {candidates}")
    
    # Test combinations multiple times
    results = []
    for i in range(3):
        combos = list(combinations(candidates[:6], 4))  # Test first few combinations
        results.append(combos[:3])  # Just check first 3 combinations
        print(f"Run {i+1} first 3 combos: {combos[:3]}")
    
    all_same = all(result == results[0] for result in results)
    print(f"\nCombination results identical: {all_same}")
    
    return all_same

if __name__ == "__main__":
    print("Determinism Debug Test")
    print("=" * 50)
    
    test1 = test_sorting_determinism()
    test2 = test_candidate_selection_determinism() 
    test3 = test_combination_order()
    
    print(f"\nSummary:")
    print(f"Sorting deterministic: {test1}")
    print(f"Candidate selection deterministic: {test2}")
    print(f"Combinations deterministic: {test3}")
    
    if test1 and test2 and test3:
        print("✅ All tests passed - algorithm should be deterministic")
    else:
        print("❌ Non-deterministic behavior detected!")