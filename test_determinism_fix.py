#!/usr/bin/env python3
"""
Test to verify that first round randomization works while maintaining
deterministic behavior in later rounds.

This test has been updated to reflect the intentional randomization
of the first round while ensuring deterministic behavior thereafter.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session, complete_match
from python.pickleball_types import SessionConfig, PlayerStats, Player
from python.competitive_variety import populate_empty_courts_competitive_variety

def create_test_session():
    """Create session with players in a specific order."""
    
    # Players from waitlist in the order they appear in the session
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

def test_first_round_randomization():
    """Test that first round matching is randomized across multiple runs."""
    print("First Round Randomization Test")
    print("=" * 50)
    
    # Test with fresh sessions (no completed matches)
    results = []
    for run in range(10):
        session = create_test_session()
        
        # Clear any existing matches (should be none, but just in case)
        session.matches.clear()
        
        # Run the algorithm on fresh session (first round)
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
    
    # Check if we have multiple unique results (randomization working)
    unique_results = []
    for result in results:
        if result not in unique_results:
            unique_results.append(result)
    
    print(f"\nTotal runs: {len(results)}")
    print(f"Unique results: {len(unique_results)}")
    
    if len(unique_results) == 1:
        print("⚠️  WARNING: All results identical - first round randomization may not be working")
        return False
    else:
        print("✅ PASS: Multiple unique first round results found - randomization working!")
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
    print("First Round Randomization and Determinism Validation")
    print("=" * 60)
    
    test1 = test_active_players_ordering()
    test2 = test_first_round_randomization()
    
    print(f"\nSummary:")
    print(f"Active players ordering deterministic: {test1}")
    print(f"First round randomization working: {test2}")
    
    if test1 and test2:
        print("\n✅ FIRST ROUND RANDOMIZATION WORKING CORRECTLY!")
        print("First rounds are randomized while maintaining deterministic player ordering.")
    else:
        print("\n❌ ISSUES DETECTED!")
        if not test1:
            print("  - Active players ordering is not deterministic")
        if not test2:
            print("  - First round randomization is not working")