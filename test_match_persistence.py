#!/usr/bin/env python3
"""
Test that session is saved after every match completion
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.types import Player, SessionConfig
from python.session import create_session, complete_match, forfeit_match
from python.session_persistence import (
    save_session, load_last_session, clear_saved_session, serialize_session
)


def test_session_saves_after_complete_match():
    """Test that session is saved after completing a match"""
    
    # Clear any previous session
    clear_saved_session()
    
    # Create session with 4 players
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana")
    ]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1,
        banned_pairs=[],
        locked_teams=[]
    )
    
    session = create_session(config)
    
    # Manually create a match since we're not running full logic
    from python.types import Match
    match = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status="waiting"
    )
    session.matches.append(match)
    
    # Complete the match
    print("Completing match...")
    success = complete_match(session, match.id, 11, 9)
    assert success, "Failed to complete match"
    
    # Verify match is completed
    assert session.matches[0].status == "completed"
    assert session.matches[0].score == {'team1_score': 11, 'team2_score': 9}
    
    # Save session
    print("Saving session...")
    save_success = save_session(session)
    assert save_success, "Failed to save session"
    
    # Load the session back
    print("Loading session...")
    loaded_session = load_last_session()
    assert loaded_session is not None, "Failed to load session"
    
    # Verify the match data was persisted
    assert len(loaded_session.matches) == 1, "Match not persisted"
    assert loaded_session.matches[0].status == "completed", "Match status not persisted"
    assert loaded_session.matches[0].score['team1_score'] == 11, "Team 1 score not persisted"
    assert loaded_session.matches[0].score['team2_score'] == 9, "Team 2 score not persisted"
    
    # Verify player stats were persisted
    assert loaded_session.player_stats["p1"].wins == 1, "Player 1 wins not persisted"
    assert loaded_session.player_stats["p3"].losses == 1, "Player 3 losses not persisted"
    
    print("[PASS] Test passed: Session persisted after match completion")
    
    # Cleanup
    clear_saved_session()


def test_session_saves_after_forfeit():
    """Test that session is saved after forfeiting a match"""
    
    # Clear any previous session
    clear_saved_session()
    
    # Create session with 4 players
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana")
    ]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1,
        banned_pairs=[],
        locked_teams=[]
    )
    
    session = create_session(config)
    
    # Manually create a match
    from python.types import Match
    match = Match(
        id="m2",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status="waiting"
    )
    session.matches.append(match)
    
    # Forfeit the match
    print("Forfeiting match...")
    success = forfeit_match(session, match.id)
    assert success, "Failed to forfeit match"
    
    # Verify match is forfeited
    assert session.matches[0].status == "forfeited"
    
    # Save session
    print("Saving session...")
    save_success = save_session(session)
    assert save_success, "Failed to save session"
    
    # Load the session back
    print("Loading session...")
    loaded_session = load_last_session()
    assert loaded_session is not None, "Failed to load session"
    
    # Verify the forfeited match was persisted
    assert len(loaded_session.matches) == 1, "Forfeited match not persisted"
    assert loaded_session.matches[0].status == "forfeited", "Forfeited match status not persisted"
    
    print("[PASS] Test passed: Session persisted after match forfeit")
    
    # Cleanup
    clear_saved_session()


def test_multiple_matches_persisted():
    """Test that multiple completed matches are all persisted"""
    
    # Clear any previous session
    clear_saved_session()
    
    # Create session with 6 players
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana"),
        Player(id="p5", name="Eve"),
        Player(id="p6", name="Frank")
    ]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        banned_pairs=[],
        locked_teams=[]
    )
    
    session = create_session(config)
    
    # Create and complete multiple matches
    from python.types import Match
    
    match1 = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status="waiting"
    )
    session.matches.append(match1)
    
    match2 = Match(
        id="m2",
        court_number=2,
        team1=["p5", "p6"],
        team2=["p1", "p3"],
        status="waiting"
    )
    session.matches.append(match2)
    
    # Complete first match
    print("Completing match 1...")
    complete_match(session, "m1", 11, 8)
    
    # Save
    save_session(session)
    
    # Complete second match
    print("Completing match 2...")
    complete_match(session, "m2", 11, 9)
    
    # Save again
    save_session(session)
    
    # Load and verify both matches
    print("Loading session...")
    loaded_session = load_last_session()
    assert loaded_session is not None, "Failed to load session"
    
    completed_matches = [m for m in loaded_session.matches if m.status == "completed"]
    assert len(completed_matches) == 2, f"Expected 2 completed matches, got {len(completed_matches)}"
    
    print("[PASS] Test passed: Multiple matches persisted correctly")
    
    # Cleanup
    clear_saved_session()


if __name__ == "__main__":
    print("Testing session persistence after match completion...\n")
    
    test_session_saves_after_complete_match()
    print()
    
    test_session_saves_after_forfeit()
    print()
    
    test_multiple_matches_persisted()
    print()
    
    print("All tests passed!")
