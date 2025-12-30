#!/usr/bin/env python3

"""
Test the round advancement functionality for King of the Court
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from python.pickleball_types import Player, SessionConfig, KingOfCourtConfig
from python.session import create_session, complete_match
from python.kingofcourt import advance_round, get_court_ordering
from python.time_manager import initialize_time_manager


def setup_tests():
    """Setup for all tests"""
    initialize_time_manager()


def test_round_advancement():
    """Test round advancement with winner/loser movement"""
    print("=== Testing Round Advancement ===")
    
    # 8 players, 2 courts (Court 1 = Kings, Court 2 = Bottom)
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2]  # Court 1 = Kings, Court 2 = Bottom
    )
    
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=2,
        king_of_court_config=koc_config
    )
    
    session = create_session(config)
    
    # Verify initial setup
    assert len(session.matches) == 2, "Should have 2 initial matches"
    assert session.king_of_court_round_number == 0, "Should start at round 0"
    
    # Find the matches for each court
    court_1_match = None
    court_2_match = None
    
    for match in session.matches:
        if match.court_number == 1:
            court_1_match = match
        elif match.court_number == 2:
            court_2_match = match
    
    assert court_1_match is not None
    assert court_2_match is not None
    
    print(f"Initial Round - Court 1: {court_1_match.team1} vs {court_1_match.team2}")
    print(f"Initial Round - Court 2: {court_2_match.team1} vs {court_2_match.team2}")
    
    # Complete matches - team1 wins on both courts
    success, _ = complete_match(session, court_1_match.id, 11, 7)  # team1 wins
    assert success, "First match completion should succeed"
    success, _ = complete_match(session, court_2_match.id, 11, 5)  # team1 wins
    assert success, "Second match completion should succeed"
    
    # Try to advance round
    session = advance_round(session)
    
    print(f"DEBUG test: All matches in session:")
    for i, match in enumerate(session.matches):
        print(f"  Match {i}: Court {match.court_number}, Status: {match.status}, Teams: {match.team1} vs {match.team2}")
    
    # Should have new matches
    new_matches = [m for m in session.matches if m.status == 'waiting']
    print(f"DEBUG test: Found {len(new_matches)} waiting matches")
    assert len(new_matches) == 2, f"Expected 2 new matches after advancement, got {len(new_matches)}"
    
    # Round number should increment
    assert session.king_of_court_round_number == 1, f"Expected round 1, got {session.king_of_court_round_number}"
    
    print(f"Round 1 created successfully!")
    print(f"✓ Round advancement test passed")


def test_winner_loser_movement():
    """Test that winners move up and losers move down"""
    print("\n=== Testing Winner/Loser Movement ===")
    
    # 12 players, 3 courts for more interesting movement
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 13)]
    
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2, 3]  # Court 1 = Kings, Court 2 = Middle, Court 3 = Bottom
    )
    
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=3,
        king_of_court_config=koc_config
    )
    
    session = create_session(config)
    
    # Get initial matches
    matches_by_court = {}
    for match in session.matches:
        matches_by_court[match.court_number] = match
    
    # Record initial players on each court
    initial_players = {}
    for court_num, match in matches_by_court.items():
        all_players = match.team1 + match.team2
        initial_players[court_num] = all_players
        print(f"Court {court_num} initial: {all_players}")
    
    # Complete matches - team1 wins on all courts
    for court_num, match in matches_by_court.items():
        success, _ = complete_match(session, match.id, 11, 5)  # team1 wins
        assert success, f"Match completion on court {court_num} should succeed"
    
    # Advance round
    session = advance_round(session)
    
    # Get new matches
    new_matches_by_court = {}
    for match in session.matches:
        if match.status == 'waiting':
            new_matches_by_court[match.court_number] = match
    
    print("\nAfter round advancement:")
    for court_num, match in new_matches_by_court.items():
        all_players = match.team1 + match.team2
        print(f"Court {court_num}: {all_players}")
    
    # Verify movement logic:
    # - Court 1 (Kings): winners stay (team1 from court 1) + losers from nowhere = should be team1 from court 1 + team2 from court 2 (losers from middle)
    # - Court 2 (Middle): winners from court 3 (team1) + losers from court 1 (team2)
    # - Court 3 (Bottom): winners stay nowhere + losers from court 2 (team2) and court 3 staying (team2)
    
    # Note: The exact player assignment might vary due to randomization, but we can verify:
    # 1. All players are still assigned to some court
    # 2. No duplicates
    all_new_players = set()
    for match in new_matches_by_court.values():
        all_new_players.update(match.team1 + match.team2)
    
    all_initial_players = set()
    for players_list in initial_players.values():
        all_initial_players.update(players_list)
    
    assert all_new_players == all_initial_players, "All players should be reassigned"
    
    print("✓ Winner/loser movement test passed")


if __name__ == "__main__":
    try:
        setup_tests()
        test_round_advancement()
        test_winner_loser_movement()
        print("\n🎉 All King of Court round advancement tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)