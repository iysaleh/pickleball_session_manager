#!/usr/bin/env python3

"""
Test the rounds-based King of the Court implementation
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from python.pickleball_types import Player, SessionConfig, KingOfCourtConfig
from python.session import create_session
from python.kingofcourt import (
    initialize_king_of_court_session, 
    advance_round, 
    get_court_ordering,
    set_court_ordering
)
from python.time_manager import initialize_time_manager


def setup_tests():
    """Setup for all tests"""
    initialize_time_manager()


def test_king_of_court_basic_setup():
    """Test basic King of Court session setup with different seeding options"""
    print("=== Testing King of Court Basic Setup ===")
    
    # Create players
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    
    # Test different seeding options
    for seeding in ['random', 'highest_to_lowest', 'lowest_to_highest']:
        print(f"\n--- Testing {seeding} seeding ---")
        
        koc_config = KingOfCourtConfig(
            seeding_option=seeding,
            court_ordering=[1, 2]  # 2 courts: Court 1 = Kings, Court 2 = Bottom
        )
        
        config = SessionConfig(
            mode='king-of-court',
            session_type='doubles',
            players=players,
            courts=2,
            king_of_court_config=koc_config
        )
        
        session = create_session(config)
        
        # Verify initialization
        assert session.king_of_court_round_number == 1  # First round is now numbered as 1
        assert len(session.matches) == 2  # Should create matches for 2 courts
        assert len(session.waiting_players) == 0  # 8 players, 2 courts * 4 players = 8 (no waiting)
        
        # Check matches were created
        court_1_match = None
        court_2_match = None
        
        for match in session.matches:
            if match.court_number == 1:
                court_1_match = match
            elif match.court_number == 2:
                court_2_match = match
        
        assert court_1_match is not None, "Court 1 should have a match"
        assert court_2_match is not None, "Court 2 should have a match"
        assert len(court_1_match.team1) == 2, "Court 1 team1 should have 2 players"
        assert len(court_1_match.team2) == 2, "Court 1 team2 should have 2 players"
        assert len(court_2_match.team1) == 2, "Court 2 team1 should have 2 players"
        assert len(court_2_match.team2) == 2, "Court 2 team2 should have 2 players"
        
        print(f"✓ {seeding} seeding: Created {len(session.matches)} matches")
        print(f"  Court 1: {court_1_match.team1} vs {court_1_match.team2}")
        print(f"  Court 2: {court_2_match.team1} vs {court_2_match.team2}")


def test_court_ordering():
    """Test court ordering functionality"""
    print("\n=== Testing Court Ordering ===")
    
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 13)]  # 12 players for 3 courts
    
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[3, 1, 2]  # Custom ordering: Court 3 = Kings, Court 1 = Middle, Court 2 = Bottom
    )
    
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=3,
        king_of_court_config=koc_config
    )
    
    session = create_session(config)
    
    # Test get_court_ordering
    ordering = get_court_ordering(session)
    assert ordering == [3, 1, 2], f"Expected [3, 1, 2], got {ordering}"
    print(f"✓ Court ordering: {ordering}")
    
    # Test set_court_ordering
    new_ordering = [2, 3, 1]
    session = set_court_ordering(session, new_ordering)
    updated_ordering = get_court_ordering(session)
    assert updated_ordering == new_ordering, f"Expected {new_ordering}, got {updated_ordering}"
    print(f"✓ Updated court ordering: {updated_ordering}")


def test_first_bye_handling():
    """Test first bye player handling in King of Court"""
    print("\n=== Testing First Bye Handling ===")
    
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 10)]  # 9 players
    first_bye_players = [players[0].id, players[1].id]  # First 2 players sit out
    
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2]  # 2 courts
    )
    
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=2,
        first_bye_players=first_bye_players,
        king_of_court_config=koc_config
    )
    
    session = create_session(config)
    
    # Check that first bye players are in waitlist
    assert len(session.waiting_players) == 2, f"Expected 2 waiting players (2 bye + 0 excess), got {len(session.waiting_players)}"
    assert players[0].id in session.waiting_players, "First bye player should be in waitlist"
    assert players[1].id in session.waiting_players, "Second bye player should be in waitlist"
    
    # Check wait counts were set
    assert session.king_of_court_wait_counts[players[0].id] == 1, "First bye player should have wait count 1"
    assert session.king_of_court_wait_counts[players[1].id] == 1, "Second bye player should have wait count 1"
    
    print(f"✓ First bye handling: {len(session.waiting_players)} players waiting")
    print(f"  Waiting players: {session.waiting_players}")


def test_singles_mode():
    """Test King of Court with singles"""
    print("\n=== Testing Singles Mode ===")
    
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 7)]  # 6 players
    
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2, 3]  # 3 courts
    )
    
    config = SessionConfig(
        mode='king-of-court',
        session_type='singles',
        players=players,
        courts=3,
        king_of_court_config=koc_config
    )
    
    session = create_session(config)
    
    # Check matches
    assert len(session.matches) == 3, f"Expected 3 matches, got {len(session.matches)}"
    
    for match in session.matches:
        assert len(match.team1) == 1, f"Singles team1 should have 1 player, got {len(match.team1)}"
        assert len(match.team2) == 1, f"Singles team2 should have 1 player, got {len(match.team2)}"
    
    print(f"✓ Singles mode: Created {len(session.matches)} singles matches")
    for match in session.matches:
        print(f"  Court {match.court_number}: {match.team1[0]} vs {match.team2[0]}")


if __name__ == "__main__":
    try:
        setup_tests()
        test_king_of_court_basic_setup()
        test_court_ordering()
        test_first_bye_handling()
        test_singles_mode()
        print("\n🎉 All King of Court tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)