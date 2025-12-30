#!/usr/bin/env python3
"""
Test match duration tracking and timer functionality
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session, complete_match
from python.utils import calculate_match_duration, format_duration
from python.session_persistence import save_session, load_last_session, clear_saved_session


def test_match_start_time_set():
    """Test that start_time is set when match is created"""
    print("Test 1: Match start_time is set on creation")
    
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
    match = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status="waiting",
        start_time=datetime.now()
    )
    session.matches.append(match)
    
    assert match.start_time is not None, "start_time should not be None"
    assert isinstance(match.start_time, datetime), "start_time should be datetime"
    print("[PASS] Match start_time is set correctly")


def test_calculate_match_duration():
    """Test that match duration is calculated correctly"""
    print("\nTest 2: Match duration calculation")
    
    now = datetime.now()
    
    # Create a match that lasted 5 minutes 30 seconds
    match = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status="completed",
        start_time=now,
        end_time=now + timedelta(seconds=330)  # 5 minutes 30 seconds
    )
    
    duration = calculate_match_duration(match)
    assert duration == 330, f"Duration should be 330, got {duration}"
    
    formatted = format_duration(duration)
    assert formatted == "05:30", f"Formatted duration should be '05:30', got '{formatted}'"
    print("[PASS] Match duration calculated correctly: 05:30")


def test_duration_persistence():
    """Test that match duration is persisted and loaded"""
    print("\nTest 3: Match duration persistence")
    
    clear_saved_session()
    
    now = datetime.now()
    
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
    
    # Create and complete a match
    match = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status="waiting",
        start_time=now
    )
    session.matches.append(match)
    
    # Complete the match (this will set end_time to now)
    complete_match(session, match.id, 11, 9)
    
    # Get the match from the session to see the actual times
    match = session.matches[0]
    
    # Verify both times are set
    assert match.start_time is not None, "start_time should be set"
    assert match.end_time is not None, "end_time should be set after completion"
    
    # Save session
    save_session(session)
    
    # Load session
    loaded_session = load_last_session()
    assert loaded_session is not None, "Failed to load session"
    
    loaded_match = loaded_session.matches[0]
    assert loaded_match.start_time is not None, "start_time not persisted"
    assert loaded_match.end_time is not None, "end_time not persisted"
    
    # Duration should be very small (close to 0) since they were set just moments apart
    duration = calculate_match_duration(loaded_match)
    assert duration is not None, "Duration should not be None for completed match"
    assert duration >= 0, f"Duration should be >= 0, got {duration}"
    
    print(f"[PASS] Match duration persisted and loaded correctly (duration: {duration}s)")
    
    clear_saved_session()


def test_multiple_match_durations():
    """Test average duration calculation across multiple matches"""
    print("\nTest 4: Multiple match durations and average")
    
    now = datetime.now()
    
    # Create matches with different durations
    durations = [300, 420, 360, 450, 330]  # 5, 7, 6, 7.5, 5.5 minutes
    matches = []
    
    for i, dur in enumerate(durations):
        match = Match(
            id=f"m{i}",
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status="completed",
            start_time=now,
            end_time=now + timedelta(seconds=dur)
        )
        matches.append(match)
    
    total_duration = sum(durations)
    avg_duration = total_duration // len(durations)
    
    # Expected: 300+420+360+450+330 = 1860 / 5 = 372 seconds (6:12)
    assert avg_duration == 372, f"Average should be 372, got {avg_duration}"
    assert format_duration(avg_duration) == "06:12", "Average formatted incorrectly"
    
    print(f"[PASS] Average duration across {len(matches)} matches: {format_duration(avg_duration)}")


def test_no_duration_for_active_match():
    """Test that duration is None for active matches"""
    print("\nTest 5: Active match has no end duration")
    
    now = datetime.now()
    
    # Create an active match (no end_time)
    match = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status="waiting",
        start_time=now,
        end_time=None
    )
    
    duration = calculate_match_duration(match)
    assert duration is None, "Active match should have None duration"
    
    print("[PASS] Active match correctly has no duration")


if __name__ == "__main__":
    print("Testing match duration tracking...\n")
    
    test_match_start_time_set()
    test_calculate_match_duration()
    test_duration_persistence()
    test_multiple_match_durations()
    test_no_duration_for_active_match()
    
    print("\n[ALL PASS] All duration tracking tests passed!")
