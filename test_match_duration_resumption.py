#!/usr/bin/env python3
"""
Test match duration timers after session save/load - ensuring they don't show as negative
"""

import sys
sys.path.append('.')

import time
from datetime import datetime, timedelta
from python.time_manager import initialize_time_manager, now, start_session
from python.session import create_session, create_manual_match
from python.pickleball_types import SessionConfig, Player
from python.session_persistence import serialize_session, deserialize_session, adjust_wait_times_after_time_manager_start
from python.utils import start_player_wait_timer, get_current_wait_time, stop_player_wait_timer

def test_match_duration_resumption():
    """Test that match duration timers resume correctly after save/load"""
    print("=== Testing Match Duration Timer Resumption ===")
    
    # Initialize time manager with acceleration for faster testing
    time_manager = initialize_time_manager(test_mode=True)
    
    # Create a session with 4 players so we can have a match
    players = [Player(id="p1", name="Alice"), Player(id="p2", name="Bob"), 
               Player(id="p3", name="Charlie"), Player(id="p4", name="Diana")]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session1 = create_session(config)
    print(f"Original session start time: {session1.session_start_time}")
    
    # Create a match in progress
    match_result = create_manual_match(session1, 1, ["p1", "p2"], ["p3", "p4"])
    print(f"Created match result: {match_result}")
    
    # Find the match we just created
    active_match = None
    for match in session1.matches:
        if match.status == 'waiting' and match.court_number == 1:
            active_match = match
            break
    
    if not active_match:
        print("❌ Could not find the created match")
        return False
    
    print(f"Match start time: {active_match.start_time}")
    
    # Let the match "run" for some time
    time.sleep(0.6)  # 9 virtual seconds
    
    # Check match duration before saving
    match_duration_before = 0
    if active_match.start_time:
        match_duration_before = int((now() - active_match.start_time).total_seconds())
    
    print(f"Match duration before save: {match_duration_before}s")
    
    # Start some wait timers too (to test both types of timers together)
    # These players are not in the match, so they should be waiting
    charlie_stats = session1.player_stats["p3"]
    diana_stats = session1.player_stats["p4"]
    
    # Wait a bit more
    time.sleep(0.3)  # 4.5 more virtual seconds
    
    final_duration_before = int((now() - active_match.start_time).total_seconds())
    print(f"Final match duration before save: {final_duration_before}s")
    
    # Serialize the session
    session_data = serialize_session(session1)
    print("Session serialized")
    
    # Simulate ending the session and starting a new one later
    print("\n--- Simulating session end and later resumption ---")
    
    # Initialize a fresh time manager (simulating app restart)
    time_manager = initialize_time_manager(test_mode=True)
    
    # Deserialize the session
    session2 = deserialize_session(session_data)
    
    # Initialize the time manager with the restored session's start time
    from python.time_manager import start_session as tm_start_session
    tm_start_session(session2.session_start_time)
    
    # Now adjust the wait times and match times
    adjust_wait_times_after_time_manager_start(session2)
    
    print(f"Restored session start time: {session2.session_start_time}")
    
    # Find the restored match
    restored_match = None
    for match in session2.matches:
        if match.court_number == 1:
            restored_match = match
            break
    
    if not restored_match:
        print("❌ Could not find the restored match")
        return False
    
    print(f"Restored match start time: {restored_match.start_time}")
    
    # Check match duration immediately after load
    match_duration_after = 0
    if restored_match.start_time:
        match_duration_after = int((now() - restored_match.start_time).total_seconds())
    
    print(f"Match duration after load: {match_duration_after}s")
    
    # Most important: Check that the match duration is not negative
    if match_duration_after < 0:
        print(f"❌ Match has negative duration: {match_duration_after}s")
        return False
    
    print("✓ No negative match duration")
    
    # The match duration should be approximately the same as before save
    duration_diff = abs(match_duration_after - final_duration_before)
    
    print(f"Duration difference: {duration_diff}s")
    
    # Allow some tolerance for execution time
    if duration_diff <= 2:
        print("✓ Match duration preserved correctly during save/load")
    else:
        print(f"❌ Match duration not preserved: diff {duration_diff}s")
        return False
    
    # Now wait some more time and verify the timer continues to increment
    print("\n--- Testing continued match timer progression ---")
    time.sleep(0.3)  # 4.5 more virtual seconds
    
    match_duration_continued = 0
    if restored_match.start_time:
        match_duration_continued = int((now() - restored_match.start_time).total_seconds())
    
    print(f"Match duration after additional 0.3s: {match_duration_continued}s")
    
    # Check for negatives again
    if match_duration_continued < 0:
        print(f"❌ Negative match duration after progression: {match_duration_continued}s")
        return False
    
    # This should be higher than the previous value
    duration_increase = match_duration_continued - match_duration_after
    
    print(f"Duration increase: +{duration_increase}s")
    
    # Should be approximately 4.5 seconds (0.3s * 15x acceleration)
    if 3 <= duration_increase <= 6:
        print("✓ Match timer continues to increment correctly after resume")
    else:
        print(f"❌ Match timer not incrementing correctly: +{duration_increase}s")
        return False
    
    print("✓ All match duration resumption tests passed!")
    return True

def test_multiple_matches_resumption():
    """Test resumption with multiple matches on different courts"""
    print("\n=== Testing Multiple Matches Resumption ===")
    
    time_manager = initialize_time_manager(test_mode=True)
    
    # Create a session with 8 players for 2 courts
    players = [Player(id=f"p{i}", name=f"Player{i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Create matches on both courts
    match1_result = create_manual_match(session, 1, ["p1", "p2"], ["p3", "p4"])
    print(f"Created match 1: {match1_result}")
    
    # Wait a bit
    time.sleep(0.3)  # 4.5 virtual seconds
    
    match2_result = create_manual_match(session, 2, ["p5", "p6"], ["p7", "p8"])
    print(f"Created match 2: {match2_result}")
    
    # Wait more
    time.sleep(0.4)  # 6 virtual seconds
    
    # Find both matches
    match1 = None
    match2 = None
    for match in session.matches:
        if match.court_number == 1:
            match1 = match
        elif match.court_number == 2:
            match2 = match
    
    if not match1 or not match2:
        print("❌ Could not find both matches")
        return False
    
    # Check durations before save
    duration1_before = int((now() - match1.start_time).total_seconds()) if match1.start_time else 0
    duration2_before = int((now() - match2.start_time).total_seconds()) if match2.start_time else 0
    
    print(f"Durations before save - Match 1: {duration1_before}s, Match 2: {duration2_before}s")
    
    # Save and restore
    session_data = serialize_session(session)
    time_manager = initialize_time_manager(test_mode=True)
    restored_session = deserialize_session(session_data)
    
    from python.time_manager import start_session as tm_start_session
    tm_start_session(restored_session.session_start_time)
    adjust_wait_times_after_time_manager_start(restored_session)
    
    # Find restored matches
    restored_match1 = None
    restored_match2 = None
    for match in restored_session.matches:
        if match.court_number == 1:
            restored_match1 = match
        elif match.court_number == 2:
            restored_match2 = match
    
    # Check durations after restore
    duration1_after = int((now() - restored_match1.start_time).total_seconds()) if restored_match1 and restored_match1.start_time else 0
    duration2_after = int((now() - restored_match2.start_time).total_seconds()) if restored_match2 and restored_match2.start_time else 0
    
    print(f"Durations after load - Match 1: {duration1_after}s, Match 2: {duration2_after}s")
    
    # Check for negatives
    if duration1_after < 0 or duration2_after < 0:
        print(f"❌ Negative durations: Match 1: {duration1_after}s, Match 2: {duration2_after}s")
        return False
    
    print("✓ No negative durations for multiple matches")
    
    # Check preservation (with tolerance)
    if (abs(duration1_after - duration1_before) <= 2 and 
        abs(duration2_after - duration2_before) <= 2):
        print("✓ Multiple match durations preserved correctly")
    else:
        print(f"❌ Durations not preserved: diffs {abs(duration1_after - duration1_before)}, {abs(duration2_after - duration2_before)}")
        return False
    
    print("✓ Multiple matches resumption test passed!")
    return True

def run_all_tests():
    """Run all match duration resumption tests"""
    print("Running Match Duration Resumption Tests...")
    print("=" * 50)
    
    try:
        success = True
        success &= test_match_duration_resumption()
        success &= test_multiple_matches_resumption()
        
        print("=" * 50)
        if success:
            print("✓ All match duration resumption tests passed!")
        else:
            print("❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()