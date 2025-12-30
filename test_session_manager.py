#!/usr/bin/env python3

"""
Test Session Manager Service

Comprehensive tests for the session management service that replaces GUI logic.
This validates that business logic is properly separated and testable.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from python.pickleball_types import Player, SessionConfig, KingOfCourtConfig, Match
from python.session import create_session
from python.session_manager import create_session_manager
from python.time_manager import initialize_time_manager


def test_session_manager_basic():
    """Test basic session manager functionality"""
    initialize_time_manager()
    
    print("=== Testing Session Manager Basic Functionality ===")
    
    # Create test session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Create session manager
    manager = create_session_manager(session)
    
    # Trigger initial evaluation to create matches
    manager.force_session_evaluation()
    
    # Test event listening
    events_received = []
    def event_callback(event_type, *args):
        events_received.append((event_type, args))
    
    manager.add_event_listener('match_completed', lambda *args: event_callback('match_completed', *args))
    manager.add_event_listener('session_updated', lambda *args: event_callback('session_updated', *args))
    
    print(f"Initial matches: {len(session.matches)}")
    assert len(session.matches) >= 2, "Should have initial matches"
    
    # Find a match to complete
    active_match = None
    for match in session.matches:
        if match.status == 'waiting':
            active_match = match
            break
    
    assert active_match is not None, "Should have an active match"
    
    # Test match completion
    print(f"Completing match: {active_match.team1} vs {active_match.team2}")
    success, slides = manager.handle_match_completion(active_match.id, 11, 7)
    
    assert success, "Match completion should succeed"
    assert len(events_received) >= 2, "Should receive match_completed and session_updated events"
    
    # Verify match was completed
    completed_match = next((m for m in session.matches if m.id == active_match.id), None)
    assert completed_match is not None, "Match should exist"
    assert completed_match.status == 'completed', "Match should be completed"
    
    print("✓ Basic session manager functionality working")


def test_session_manager_king_of_court():
    """Test session manager with King of Court mode"""
    initialize_time_manager()
    
    print("\n=== Testing Session Manager with King of Court ===")
    
    # Create King of Court session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2]
    )
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=2,
        king_of_court_config=koc_config
    )
    session = create_session(config)
    
    # Create session manager
    manager = create_session_manager(session)
    
    # Track round advancement events
    round_events = []
    manager.add_event_listener('session_updated', lambda: round_events.append('updated'))
    
    print(f"Initial round: {session.king_of_court_round_number}")
    initial_round = session.king_of_court_round_number
    
    # Complete all matches in round
    active_matches = [m for m in session.matches if m.status == 'waiting']
    print(f"Completing {len(active_matches)} matches")
    
    for match in active_matches:
        success, _ = manager.handle_match_completion(match.id, 11, 7)
        assert success, f"Should complete match {match.id}"
    
    # Should advance round
    print(f"Round after completion: {session.king_of_court_round_number}")
    assert session.king_of_court_round_number > initial_round, "Should advance round"
    
    # Should have new matches
    new_active_matches = [m for m in session.matches if m.status == 'waiting']
    assert len(new_active_matches) >= 2, "Should have new matches after round advancement"
    
    print("✓ King of Court session manager working")


def test_session_manager_player_management():
    """Test player addition/removal through session manager"""
    initialize_time_manager()
    
    print("\n=== Testing Session Manager Player Management ===")
    
    # Create session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 5)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    session = create_session(config)
    
    # Create session manager
    manager = create_session_manager(session)
    
    initial_player_count = len(session.config.players)
    print(f"Initial players: {initial_player_count}")
    
    # Test player addition
    new_players = [Player("new_player_1", "New Player 1"), Player("new_player_2", "New Player 2")]
    manager.handle_player_addition(new_players)
    
    assert len(session.config.players) == initial_player_count + 2, "Should add new players"
    assert "new_player_1" in session.active_players, "New player should be active"
    
    print(f"Players after addition: {len(session.config.players)}")
    
    # Test player removal
    manager.handle_player_removal(["new_player_1"])
    
    assert "new_player_1" not in session.active_players, "Player should be removed from active"
    if "new_player_1" in session.waiting_players:
        assert False, "Removed player should not be in waitlist"
    
    print("✓ Player management working")


def test_session_manager_settings():
    """Test settings changes through session manager"""
    initialize_time_manager()
    
    print("\n=== Testing Session Manager Settings ===")
    
    # Create session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Create session manager
    manager = create_session_manager(session)
    
    # Test variety setting change (using roaming range as variety proxy)
    initial_variety = session.competitive_variety_roaming_range_percent
    manager.handle_settings_change('variety', value=0.7)
    # Note: This would need to be implemented in the session manager
    
    # Test adaptive setting change
    manager.handle_settings_change('adaptive', enabled=False)
    assert session.adaptive_constraints_disabled == True, "Should disable adaptive constraints"
    
    manager.handle_settings_change('adaptive', enabled=True, weight=3.0)
    assert session.adaptive_constraints_disabled == False, "Should enable adaptive constraints"
    assert session.adaptive_balance_weight == 3.0, "Should set adaptive weight"
    
    print("✓ Settings management working")


def test_session_manager_manual_matches():
    """Test manual match creation"""
    initialize_time_manager()
    
    print("\n=== Testing Session Manager Manual Matches ===")
    
    # Create session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Create session manager
    manager = create_session_manager(session)
    
    initial_match_count = len(session.matches)
    
    # Create manual match
    team1 = ["player_1", "player_2"]
    team2 = ["player_3", "player_4"]
    manager.handle_manual_match_creation(1, team1, team2)
    
    assert len(session.matches) > initial_match_count, "Should add new match"
    
    # Find the created match
    manual_match = None
    for match in session.matches:
        if match.team1 == team1 and match.team2 == team2:
            manual_match = match
            break
    
    assert manual_match is not None, "Should find created match"
    assert manual_match.court_number == 1, "Should be on specified court"
    assert manual_match.status == 'waiting', "Should be waiting status"
    
    print("✓ Manual match creation working")


def test_session_manager_error_handling():
    """Test error handling and robustness"""
    initialize_time_manager()
    
    print("\n=== Testing Session Manager Error Handling ===")
    
    # Create session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 5)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    session = create_session(config)
    
    # Create session manager
    manager = create_session_manager(session)
    
    # Test invalid match completion
    success, _ = manager.handle_match_completion("invalid_match_id", 11, 7)
    assert not success, "Should fail for invalid match ID"
    
    # Test invalid match forfeit
    success = manager.handle_match_forfeit("invalid_match_id")
    assert not success, "Should fail for invalid match ID"
    
    # Test removal of non-existent player
    initial_active = len(session.active_players)
    manager.handle_player_removal(["non_existent_player"])
    assert len(session.active_players) == initial_active, "Should not change active players"
    
    print("✓ Error handling working")


def run_all_tests():
    """Run all session manager tests"""
    print("🧪 Running Session Manager Tests")
    
    test_session_manager_basic()
    test_session_manager_king_of_court() 
    test_session_manager_player_management()
    test_session_manager_settings()
    test_session_manager_manual_matches()
    test_session_manager_error_handling()
    
    print("\n🎉 All Session Manager tests passed!")
    print("Business logic successfully separated from GUI!")


if __name__ == "__main__":
    run_all_tests()