#!/usr/bin/env python3
"""
Test that first match player placement is randomized between runs.

The first match should randomly spread players on courts that are not 
specified on the first bye list, and should not be consistent between runs.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session
from python.types import SessionConfig, Player, GameMode, SessionType
from python.competitive_variety import populate_empty_courts_competitive_variety

def test_first_match_randomization():
    """Test that first match placement is not deterministic"""
    print("Testing first match randomization")
    
    # Create 12 players
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    
    # Configuration with no bye players
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,  # 2 courts = 8 players in matches, 4 waiting
        first_bye_players=[],  # No specific bye players
    )
    
    # Collect first match compositions across multiple runs
    first_match_compositions = []
    
    for run in range(10):
        session = create_session(config)
        populate_empty_courts_competitive_variety(session)
        
        # Get the composition of the first two matches
        matches = session.matches
        assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"
        
        # Create a sorted composition to compare
        composition = []
        for match in sorted(matches, key=lambda m: m.court_number):
            all_players = sorted(match.team1 + match.team2)
            composition.append(tuple(all_players))
        
        first_match_compositions.append(tuple(composition))
        print(f"Run {run + 1}: {composition}")
    
    # Check if all compositions are identical
    unique_compositions = set(first_match_compositions)
    print(f"\nTotal runs: {len(first_match_compositions)}")
    print(f"Unique compositions: {len(unique_compositions)}")
    
    if len(unique_compositions) == 1:
        print("❌ FAIL: All first match compositions are identical - no randomization!")
        return False
    else:
        print("✅ PASS: Multiple unique first match compositions found - randomization working!")
        return True

def test_first_match_randomization_with_byes():
    """Test that randomization works with bye players specified"""
    print("\nTesting first match randomization with bye players")
    
    # Create 12 players
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    
    # Configuration with 2 bye players
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,  # 2 courts = 8 players in matches, 2 waiting + 2 bye = 4 total waiting
        first_bye_players=['p0', 'p1'],  # First two players sit out first match
    )
    
    # Collect first match compositions across multiple runs
    first_match_compositions = []
    
    for run in range(10):
        session = create_session(config)
        populate_empty_courts_competitive_variety(session)
        
        # Get the composition of the first two matches
        matches = session.matches
        assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"
        
        # Verify bye players are not in first round
        all_players_in_matches = set()
        for match in matches:
            all_players_in_matches.update(match.team1 + match.team2)
        
        assert 'p0' not in all_players_in_matches, "Bye player p0 should not be in first round"
        assert 'p1' not in all_players_in_matches, "Bye player p1 should not be in first round"
        
        # Create a sorted composition to compare
        composition = []
        for match in sorted(matches, key=lambda m: m.court_number):
            all_players = sorted(match.team1 + match.team2)
            composition.append(tuple(all_players))
        
        first_match_compositions.append(tuple(composition))
        print(f"Run {run + 1}: {composition}")
    
    # Check if all compositions are identical
    unique_compositions = set(first_match_compositions)
    print(f"\nTotal runs: {len(first_match_compositions)}")
    print(f"Unique compositions: {len(unique_compositions)}")
    
    if len(unique_compositions) == 1:
        print("❌ FAIL: All first match compositions are identical - no randomization!")
        return False
    else:
        print("✅ PASS: Multiple unique first match compositions found - randomization working!")
        return True

if __name__ == "__main__":
    success1 = test_first_match_randomization()
    success2 = test_first_match_randomization_with_byes()
    
    if success1 and success2:
        print("\n🎉 All randomization tests passed!")
        exit(0)
    else:
        print("\n💥 Randomization tests failed!")
        exit(1)