#!/usr/bin/env python3
"""
Test to reproduce the bug where the 4th court isn't being populated consistently
in a 20 player 4 court scenario with 2 on the first bye list.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session
from python.types import SessionConfig, Player, GameMode, SessionType
from python.competitive_variety import populate_empty_courts_competitive_variety

def test_20_players_4_courts_2_byes():
    """Test that all 4 courts get populated consistently"""
    print("Testing 20 players, 4 courts, 2 first bye players")
    print("=" * 60)
    
    # Create 20 players
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(20)]
    
    # Configuration with 2 bye players
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4,  # 4 courts = 16 players in matches, 2 waiting + 2 bye = 4 total waiting
        first_bye_players=['p0', 'p1'],  # First two players sit out first match
    )
    
    court_fill_results = []
    
    for run in range(20):
        session = create_session(config)
        populate_empty_courts_competitive_variety(session)
        
        # Count how many courts have matches
        courts_with_matches = len(session.matches)
        
        # Get which courts have matches
        court_numbers = sorted([match.court_number for match in session.matches])
        
        print(f"Run {run + 1:2d}: {courts_with_matches} courts filled - Courts: {court_numbers}")
        
        court_fill_results.append(courts_with_matches)
        
        # Verify bye players are not in matches
        all_players_in_matches = set()
        for match in session.matches:
            all_players_in_matches.update(match.team1 + match.team2)
        
        assert 'p0' not in all_players_in_matches, f"Run {run+1}: Bye player p0 should not be in matches"
        assert 'p1' not in all_players_in_matches, f"Run {run+1}: Bye player p1 should not be in matches"
        
        # Check if we have the expected number of players in matches
        expected_players_in_matches = 16  # 4 courts * 4 players per court
        actual_players_in_matches = len(all_players_in_matches)
        
        if courts_with_matches == 4 and actual_players_in_matches != expected_players_in_matches:
            print(f"  ❌ ERROR: Expected {expected_players_in_matches} players, got {actual_players_in_matches}")
        elif courts_with_matches < 4:
            print(f"  ❌ ERROR: Only {courts_with_matches} courts filled, expected 4")
    
    # Analyze results
    unique_counts = set(court_fill_results)
    print(f"\nSummary:")
    print(f"Total runs: {len(court_fill_results)}")
    print(f"Court fill counts: {sorted(list(unique_counts))}")
    
    for count in sorted(unique_counts):
        occurrences = court_fill_results.count(count)
        percentage = (occurrences / len(court_fill_results)) * 100
        print(f"  {count} courts: {occurrences} times ({percentage:.1f}%)")
    
    if len(unique_counts) == 1 and 4 in unique_counts:
        print("\n✅ PASS: All runs filled exactly 4 courts")
        return True
    else:
        print("\n❌ FAIL: Inconsistent court filling detected!")
        return False

if __name__ == "__main__":
    success = test_20_players_4_courts_2_byes()
    
    if success:
        print("\n🎉 Court filling test passed!")
        exit(0)
    else:
        print("\n💥 Court filling test failed!")
        exit(1)