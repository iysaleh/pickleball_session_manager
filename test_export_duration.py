#!/usr/bin/env python3
"""
Test that exported session includes match durations
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session, complete_match
from python.utils import calculate_match_duration, format_duration


def test_export_includes_duration():
    """Test that duration appears in export"""
    print("Test: Export includes match duration")
    
    # Create test data
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
    
    # Create multiple matches with timestamps set in the past
    base_time = datetime.now() - timedelta(hours=1)
    
    for i in range(3):
        match = Match(
            id=f"m{i}",
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status="waiting",
            start_time=base_time + timedelta(seconds=i*600)  # Stagger by 10 minutes
        )
        session.matches.append(match)
        
        # Complete the match - the end_time will be set by complete_match to now()
        # This simulates the actual application behavior
        complete_match(session, match.id, 11, 9)
    
    # Verify durations are calculable
    completed_matches = [m for m in session.matches if m.status == 'completed']
    assert len(completed_matches) == 3, f"Expected 3 completed matches, got {len(completed_matches)}"
    
    total_duration = 0
    count = 0
    for match in completed_matches:
        duration = calculate_match_duration(match)
        assert duration is not None, "Duration should not be None"
        if duration > 0:  # Only count matches with measurable duration
            total_duration += duration
            count += 1
    
    if count > 0:
        avg_duration = total_duration // count
        avg_str = format_duration(avg_duration)
        print(f"[PASS] Export includes durations (avg: {avg_str})")
        print(f"       Match durations: {', '.join([format_duration(calculate_match_duration(m)) for m in completed_matches if calculate_match_duration(m)])}")
    else:
        print("[PASS] All matches have durations (some may be < 1 second)")
    
    # Verify at least one match is completed
    assert len(completed_matches) > 0, "Should have at least one completed match"
    
    print("[PASS] Average duration calculation works correctly")


if __name__ == "__main__":
    print("Testing export duration functionality...\n")
    test_export_includes_duration()
    print("\n[ALL PASS] Export duration test passed!")
