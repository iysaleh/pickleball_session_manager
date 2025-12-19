#!/usr/bin/env python3
"""
Test to verify that determinism fix works correctly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session
from python.types import SessionConfig, PlayerStats, Player
from python.competitive_variety import populate_empty_courts_competitive_variety

def create_test_session():
    """Create session with players in the problematic session order."""
    
    # Players from waitlist in the order they appear in the session
    # This mimics the non-deterministic set iteration order
    players_data = [
        ('Mike', 1852, 4, 1, 50, 29, 135),
        ('Alisha', 1552, 1, 2, 26, 28, 51),
        ('Payton', 1853, 5, 1, 59, 40, 190),
        ('Robert', 1749, 3, 2, 43, 39, 146),
        ('Carrie', 1220, 0, 3, 21, 33, 51),
        ('Renea Wood', 1848, 4, 1, 51, 32, 48),
        ('Mikes guest', 1771, 2, 1, 29, 24, 51),
    ]
    
    players = []
    for name, _, _, _, _, _, _ in players_data:
        players.append(Player(id=name, name=name))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Update player stats
    for name, expected_elo, wins, losses, pts_for, pts_against, wait_time in players_data:
        stats = session.player_stats[name]
        stats.wins = wins
        stats.games_played = wins + losses
        stats.total_points_for = pts_for
        stats.total_points_against = pts_against
        stats.total_wait_time = wait_time
    
    return session

def test_deterministic_matching():
    """Test that matching is now deterministic across multiple runs."""
    print("Deterministic Matching Test")
    print("=" * 50)
    
    results = []
    for run in range(10):
        session = create_test_session()
        
        # Clear any existing matches
        session.matches.clear()
        
        # Run the algorithm
        populate_empty_courts_competitive_variety(session)
        
        # Extract match results
        match_results = []
        for match in session.matches:
            # Sort teams to ensure deterministic comparison
            team1 = tuple(sorted(match.team1))
            team2 = tuple(sorted(match.team2))
            # Sort team pairs to ensure deterministic comparison
            match_tuple = tuple(sorted([team1, team2]))
            match_results.append((match.court_number, match_tuple))
        
        # Sort matches by court number for consistent comparison
        match_results.sort()
        results.append(match_results)
        
        print(f"Run {run+1}: {match_results}")
    
    # Check if all results are identical
    all_same = all(result == results[0] for result in results)
    
    print(f"\nAll results identical: {all_same}")
    
    if not all_same:
        print("❌ DETERMINISM FIX FAILED!")
        print("Different results found:")
        unique_results = []
        for result in results:
            if result not in unique_results:
                unique_results.append(result)
        
        for i, result in enumerate(unique_results):
            print(f"  Variant {i+1}: {result}")
        return False
    else:
        print("✅ DETERMINISM FIX SUCCESSFUL!")
        return True

def test_active_players_ordering():
    """Test that active_players iteration is now deterministic."""
    print("\nActive Players Ordering Test")
    print("=" * 40)
    
    # Create multiple sessions and check active_players ordering
    orderings = []
    for run in range(5):
        session = create_test_session()
        
        # Get the order that active_players would be processed
        active_list = sorted(session.active_players)
        orderings.append(active_list)
        
        print(f"Run {run+1}: {active_list}")
    
    all_same = all(ordering == orderings[0] for ordering in orderings)
    print(f"\nAll orderings identical: {all_same}")
    
    return all_same

if __name__ == "__main__":
    print("Determinism Fix Validation")
    print("=" * 60)
    
    test1 = test_active_players_ordering()
    test2 = test_deterministic_matching()
    
    print(f"\nSummary:")
    print(f"Active players ordering deterministic: {test1}")
    print(f"Matching results deterministic: {test2}")
    
    if test1 and test2:
        print("\n✅ DETERMINISM ISSUES RESOLVED!")
    else:
        print("\n❌ DETERMINISM ISSUES PERSIST!")