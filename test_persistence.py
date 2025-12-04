"""
Test session persistence features
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from python.types import Player, SessionConfig
from python.session import create_session, create_manual_match, complete_match
from python.session_persistence import (
    save_session, load_last_session, has_saved_session,
    save_player_history, load_player_history, clear_saved_session
)


def test_player_history_persistence():
    """Test that player history is saved and loaded"""
    print("Testing player history persistence...")
    
    # Clear any existing history
    clear_saved_session()
    
    # Save player history
    players = ['Alice', 'Bob', 'Charlie', 'Diana']
    save_player_history(players)
    
    # Load and verify
    loaded = load_player_history()
    assert loaded == players, "Player history should match"
    
    # Test duplicate removal
    players_with_dupes = ['Alice', 'Bob', 'Alice', 'Charlie']
    save_player_history(players_with_dupes)
    loaded = load_player_history()
    assert loaded == ['Alice', 'Bob', 'Charlie'], "Duplicates should be removed"
    
    print("  [PASS] Player history persistence works")


def test_session_persistence():
    """Test that sessions can be saved and loaded"""
    print("Testing session persistence...")
    
    clear_saved_session()
    
    # Create a session
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 5)]
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Manually create a match
    create_manual_match(session, 1, ["p1", "p2"], ["p3", "p4"])
    
    # Save
    save_session(session)
    assert has_saved_session(), "Should have saved session"
    
    # Load
    loaded = load_last_session()
    assert loaded is not None, "Should load session"
    assert loaded.id == session.id, "Session ID should match"
    assert loaded.config.mode == 'round-robin', "Mode should match"
    assert loaded.config.courts == 2, "Courts should match"
    
    # Verify matches were saved
    from python.queue_manager import get_match_for_court
    match = get_match_for_court(loaded, 1)
    assert match is not None, "Manual match should be saved"
    assert set(match.team1) == {"p1", "p2"}, "Team1 should match"
    assert set(match.team2) == {"p3", "p4"}, "Team2 should match"
    
    print("  [PASS] Session persistence works")


def test_session_with_completed_matches():
    """Test that completed match stats are preserved"""
    print("Testing session with completed matches...")
    
    clear_saved_session()
    
    # Create session
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 5)]
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=1
    )
    session = create_session(config)
    
    # Create and complete a match
    from python.types import Match
    from datetime import datetime
    
    match = Match(
        id="test_match",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='completed',
        score={'team1_score': 11, 'team2_score': 5},
        end_time=datetime.now()
    )
    session.matches.append(match)
    complete_match(session, "test_match", 11, 5)
    
    # Save
    save_session(session)
    
    # Load and verify stats
    loaded = load_last_session()
    p1_stats = loaded.player_stats["p1"]
    assert p1_stats.games_played == 1, "Should have 1 game played"
    assert p1_stats.wins == 1, "Should have 1 win"
    
    # Verify Dict values (counts)
    expected_opponents = {"p3": 1, "p4": 1}
    # Allow comparison with dictionary
    assert p1_stats.opponents_played == expected_opponents, f"Should have correct opponents. Got {p1_stats.opponents_played}"
    
    print("  [PASS] Session with completed matches preserved")


def test_session_with_waiting_players():
    """Test that waiting players list is preserved"""
    print("Testing session with waiting players...")
    
    clear_saved_session()
    
    # Create competitive variety session
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # In competitive variety, all players start in waiting list
    assert len(session.waiting_players) > 0, "Should have waiting players"
    
    # Save and load
    save_session(session)
    loaded = load_last_session()
    
    assert loaded.waiting_players == session.waiting_players, "Waiting players should match"
    
    print("  [PASS] Waiting players preserved")


def test_clear_saved_session():
    """Test that saved sessions can be cleared"""
    print("Testing clear saved session...")
    
    # Create and save a session
    players = [Player(id="p1", name="Alice")]
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=1
    )
    session = create_session(config)
    save_session(session)
    
    assert has_saved_session(), "Should have saved session"
    
    # Clear
    clear_saved_session()
    assert not has_saved_session(), "Should not have saved session after clear"
    
    print("  [PASS] Clear saved session works")


if __name__ == '__main__':
    test_player_history_persistence()
    test_session_persistence()
    test_session_with_completed_matches()
    test_session_with_waiting_players()
    test_clear_saved_session()
    print("\n[ALL PASS] Session persistence tests passed!")
