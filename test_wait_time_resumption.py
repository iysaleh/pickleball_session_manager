#!/usr/bin/env python3
"""
Test wait time resumption after session save/load - specifically testing that
negative wait times are avoided when resuming sessions.
"""

import sys
sys.path.append('.')

import time
from datetime import datetime, timedelta
from python.time_manager import initialize_time_manager, now, start_session
from python.session import create_session
from python.pickleball_types import SessionConfig, Player
from python.session_persistence import serialize_session, deserialize_session
from python.utils import start_player_wait_timer, get_current_wait_time, stop_player_wait_timer

def test_wait_time_resumption():
    """Test that wait times resume correctly after save/load"""
    print("=== Testing Wait Time Resumption ===")
    
    # Initialize time manager with acceleration for faster testing
    time_manager = initialize_time_manager(test_mode=True)
    
    # Create a session
    players = [Player(id="p1", name="Alice"), Player(id="p2", name="Bob")]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session1 = create_session(config)
    print(f"Original session start time: {session1.session_start_time}")
    
    # Start wait timers for both players
    alice_stats = session1.player_stats["p1"]
    bob_stats = session1.player_stats["p2"]
    
    start_player_wait_timer(alice_stats)
    print(f"Started Alice's wait timer at: {alice_stats.wait_start_time}")
    
    # Wait some time (Alice waits longer)
    time.sleep(0.5)  # 7.5 virtual seconds
    
    start_player_wait_timer(bob_stats)
    print(f"Started Bob's wait timer at: {bob_stats.wait_start_time}")
    
    # Wait more time
    time.sleep(0.5)  # Another 7.5 virtual seconds
    
    # Check wait times before saving
    alice_wait_before = get_current_wait_time(alice_stats)
    bob_wait_before = get_current_wait_time(bob_stats)
    
    print(f"Wait times before save - Alice: {alice_wait_before}s, Bob: {bob_wait_before}s")
    
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
    
    # Now adjust the wait times
    from python.session_persistence import adjust_wait_times_after_time_manager_start
    adjust_wait_times_after_time_manager_start(session2)
    print(f"Restored session start time: {session2.session_start_time}")
    
    # Check that we can access the restored player stats
    alice_stats_restored = session2.player_stats["p1"]
    bob_stats_restored = session2.player_stats["p2"]
    
    print(f"Restored Alice wait start time: {alice_stats_restored.wait_start_time}")
    print(f"Restored Bob wait start time: {bob_stats_restored.wait_start_time}")
    
    # Check wait times immediately after load
    alice_wait_after = get_current_wait_time(alice_stats_restored)
    bob_wait_after = get_current_wait_time(bob_stats_restored)
    
    print(f"Wait times after load - Alice: {alice_wait_after}s, Bob: {bob_wait_after}s")
    
    # Most important: Check that no wait times are negative
    if alice_wait_after < 0:
        print(f"❌ Alice has negative wait time: {alice_wait_after}s")
        return False
    
    if bob_wait_after < 0:
        print(f"❌ Bob has negative wait time: {bob_wait_after}s")
        return False
    
    print("✓ No negative wait times")
    
    # The wait times should be approximately the same as before save
    alice_diff = abs(alice_wait_after - alice_wait_before)
    bob_diff = abs(bob_wait_after - bob_wait_before)
    
    print(f"Differences - Alice: {alice_diff}s, Bob: {bob_diff}s")
    
    # Allow some tolerance for execution time
    if alice_diff <= 2 and bob_diff <= 2:
        print("✓ Wait times preserved correctly during save/load")
    else:
        print(f"❌ Wait times not preserved: Alice diff {alice_diff}s, Bob diff {bob_diff}s")
        return False
    
    # Now wait some more time and verify the timers continue to increment
    print("\n--- Testing continued timer progression ---")
    time.sleep(0.3)  # 4.5 more virtual seconds
    
    alice_wait_continued = get_current_wait_time(alice_stats_restored)
    bob_wait_continued = get_current_wait_time(bob_stats_restored)
    
    print(f"Wait times after additional 0.3s - Alice: {alice_wait_continued}s, Bob: {bob_wait_continued}s")
    
    # Check for negatives again
    if alice_wait_continued < 0 or bob_wait_continued < 0:
        print(f"❌ Negative wait times after progression: Alice {alice_wait_continued}s, Bob {bob_wait_continued}s")
        return False
    
    # These should be higher than the previous values
    alice_increase = alice_wait_continued - alice_wait_after
    bob_increase = bob_wait_continued - bob_wait_after
    
    print(f"Increases - Alice: +{alice_increase}s, Bob: +{bob_increase}s")
    
    # Should be approximately 4.5 seconds (0.3s * 15x acceleration)
    if 3 <= alice_increase <= 6 and 3 <= bob_increase <= 6:
        print("✓ Timers continue to increment correctly after resume")
    else:
        print(f"❌ Timers not incrementing correctly: Alice +{alice_increase}s, Bob +{bob_increase}s")
        return False
    
    # Test stopping timers
    alice_total_wait = stop_player_wait_timer(alice_stats_restored)
    bob_total_wait = stop_player_wait_timer(bob_stats_restored)
    
    print(f"Final total wait times - Alice: {alice_total_wait}s, Bob: {bob_total_wait}s")
    
    # Alice should have waited longer since she started earlier
    if alice_total_wait > bob_total_wait:
        print("✓ Relative wait times correct (Alice waited longer)")
    else:
        print(f"❌ Relative wait times incorrect: Alice {alice_total_wait}s, Bob {bob_total_wait}s")
        return False
    
    print("✓ All wait time resumption tests passed!")
    return True

def run_all_tests():
    """Run all wait time resumption tests"""
    print("Running Wait Time Resumption Tests...")
    print("=" * 50)
    
    try:
        success = test_wait_time_resumption()
        
        print("=" * 50)
        if success:
            print("✓ All wait time resumption tests passed!")
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