#!/usr/bin/env python3
"""
Comprehensive test simulating a real user scenario of resuming a session
with wait timers that were active when the session was saved.
"""

import sys
sys.path.append('.')

import time
from datetime import datetime, timedelta
from python.time_manager import initialize_time_manager, now, start_session
from python.session import create_session
from python.pickleball_types import SessionConfig, Player
from python.session_persistence import serialize_session, deserialize_session, adjust_wait_times_after_time_manager_start
from python.utils import start_player_wait_timer, get_current_wait_time, stop_player_wait_timer

def test_realistic_session_resumption():
    """Test a realistic scenario of session save/load with active wait timers"""
    print("=== Testing Realistic Session Resumption ===")
    
    # === PART 1: Initial Session ===
    print("Creating initial session...")
    time_manager = initialize_time_manager(test_mode=True)
    
    players = [Player(id=f"p{i}", name=f"Player{i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    print(f"Session created at: {session.session_start_time}")
    
    # === PART 2: Simulate Some Play Time ===
    print("\nSimulating game play...")
    
    # Start wait timers for different players at different times
    # (simulating real play where players join waitlist at different times)
    p1_stats = session.player_stats["p1"]
    p3_stats = session.player_stats["p3"]
    p5_stats = session.player_stats["p5"]
    p7_stats = session.player_stats["p7"]
    
    # Player 1 starts waiting first
    start_player_wait_timer(p1_stats)
    print(f"Player 1 starts waiting at {p1_stats.wait_start_time}")
    
    time.sleep(0.2)  # 3 virtual seconds
    
    # Player 3 joins waitlist
    start_player_wait_timer(p3_stats)
    print(f"Player 3 starts waiting at {p3_stats.wait_start_time}")
    
    time.sleep(0.3)  # 4.5 virtual seconds
    
    # Player 5 joins waitlist
    start_player_wait_timer(p5_stats)
    print(f"Player 5 starts waiting at {p5_stats.wait_start_time}")
    
    time.sleep(0.2)  # 3 virtual seconds
    
    # Player 7 joins waitlist
    start_player_wait_timer(p7_stats)
    print(f"Player 7 starts waiting at {p7_stats.wait_start_time}")
    
    time.sleep(0.1)  # 1.5 virtual seconds
    
    # Check wait times before saving
    p1_wait_before = get_current_wait_time(p1_stats)
    p3_wait_before = get_current_wait_time(p3_stats)
    p5_wait_before = get_current_wait_time(p5_stats)
    p7_wait_before = get_current_wait_time(p7_stats)
    
    print(f"\nWait times before save:")
    print(f"  Player 1: {p1_wait_before}s")
    print(f"  Player 3: {p3_wait_before}s") 
    print(f"  Player 5: {p5_wait_before}s")
    print(f"  Player 7: {p7_wait_before}s")
    
    # === PART 3: Save Session ===
    print("\n--- SAVING SESSION ---")
    session_data = serialize_session(session)
    print("Session saved successfully")
    
    # === PART 4: Simulate App Restart ===
    print("\n--- SIMULATING APP RESTART ---")
    
    # Fresh time manager (simulating complete app restart)
    time_manager = initialize_time_manager(test_mode=True)
    
    # Load the session
    restored_session = deserialize_session(session_data)
    
    # Start time manager with the restored session's timeline
    from python.time_manager import start_session as tm_start_session
    tm_start_session(restored_session.session_start_time)
    
    # Adjust wait times for the new session context
    adjust_wait_times_after_time_manager_start(restored_session)
    
    print(f"Session restored with start time: {restored_session.session_start_time}")
    
    # === PART 5: Verify Wait Times ===
    print("\nVerifying wait times after resumption...")
    
    p1_stats_restored = restored_session.player_stats["p1"]
    p3_stats_restored = restored_session.player_stats["p3"]
    p5_stats_restored = restored_session.player_stats["p5"]
    p7_stats_restored = restored_session.player_stats["p7"]
    
    p1_wait_after = get_current_wait_time(p1_stats_restored)
    p3_wait_after = get_current_wait_time(p3_stats_restored)
    p5_wait_after = get_current_wait_time(p5_stats_restored)
    p7_wait_after = get_current_wait_time(p7_stats_restored)
    
    print(f"Wait times after load:")
    print(f"  Player 1: {p1_wait_after}s (was {p1_wait_before}s)")
    print(f"  Player 3: {p3_wait_after}s (was {p3_wait_before}s)")
    print(f"  Player 5: {p5_wait_after}s (was {p5_wait_before}s)")
    print(f"  Player 7: {p7_wait_after}s (was {p7_wait_before}s)")
    
    # Verify no negative times
    all_wait_times = [p1_wait_after, p3_wait_after, p5_wait_after, p7_wait_after]
    negative_times = [t for t in all_wait_times if t < 0]
    
    if negative_times:
        print(f"❌ Found negative wait times: {negative_times}")
        return False
    
    print("✓ No negative wait times")
    
    # Verify relative ordering is preserved (Player 1 should have waited longest)
    if not (p1_wait_after >= p3_wait_after >= p5_wait_after >= p7_wait_after):
        print(f"❌ Wait time ordering not preserved")
        print(f"   Expected: P1 >= P3 >= P5 >= P7")
        print(f"   Actual: {p1_wait_after} >= {p3_wait_after} >= {p5_wait_after} >= {p7_wait_after}")
        return False
    
    print("✓ Wait time ordering preserved correctly")
    
    # Verify times are approximately preserved (with some tolerance)
    tolerance = 2  # 2 second tolerance
    
    if (abs(p1_wait_after - p1_wait_before) > tolerance or
        abs(p3_wait_after - p3_wait_before) > tolerance or
        abs(p5_wait_after - p5_wait_before) > tolerance or
        abs(p7_wait_after - p7_wait_before) > tolerance):
        print(f"❌ Wait times not preserved within tolerance ({tolerance}s)")
        return False
    
    print("✓ Wait times preserved within tolerance")
    
    # === PART 6: Test Continued Operation ===
    print("\n--- TESTING CONTINUED OPERATION ---")
    
    # Continue waiting and verify timers still work
    time.sleep(0.2)  # 3 more virtual seconds
    
    p1_wait_continued = get_current_wait_time(p1_stats_restored)
    p3_wait_continued = get_current_wait_time(p3_stats_restored)
    p5_wait_continued = get_current_wait_time(p5_stats_restored)
    p7_wait_continued = get_current_wait_time(p7_stats_restored)
    
    print(f"Wait times after continuing:")
    print(f"  Player 1: {p1_wait_continued}s (+{p1_wait_continued - p1_wait_after})")
    print(f"  Player 3: {p3_wait_continued}s (+{p3_wait_continued - p3_wait_after})")
    print(f"  Player 5: {p5_wait_continued}s (+{p5_wait_continued - p5_wait_after})")
    print(f"  Player 7: {p7_wait_continued}s (+{p7_wait_continued - p7_wait_after})")
    
    # All should have increased by approximately 3 seconds
    increases = [
        p1_wait_continued - p1_wait_after,
        p3_wait_continued - p3_wait_after,
        p5_wait_continued - p5_wait_after,
        p7_wait_continued - p7_wait_after
    ]
    
    expected_increase = 3  # 0.2s * 15x = 3s
    for increase in increases:
        if not (1 <= increase <= 5):  # Allow some tolerance
            print(f"❌ Unexpected timer increase: {increase}s (expected ~{expected_increase}s)")
            return False
    
    print("✓ Timers continue to work correctly after resumption")
    
    # === PART 7: Test Final Wait Times ===
    print("\n--- TESTING FINAL WAIT TIME ACCUMULATION ---")
    
    # Stop all timers and check final accumulated times
    p1_total = stop_player_wait_timer(p1_stats_restored)
    p3_total = stop_player_wait_timer(p3_stats_restored)
    p5_total = stop_player_wait_timer(p5_stats_restored)
    p7_total = stop_player_wait_timer(p7_stats_restored)
    
    print(f"Final accumulated wait times:")
    print(f"  Player 1: {p1_total}s (total_wait_time: {p1_stats_restored.total_wait_time})")
    print(f"  Player 3: {p3_total}s (total_wait_time: {p3_stats_restored.total_wait_time})")
    print(f"  Player 5: {p5_total}s (total_wait_time: {p5_stats_restored.total_wait_time})")
    print(f"  Player 7: {p7_total}s (total_wait_time: {p7_stats_restored.total_wait_time})")
    
    # Verify the total_wait_time matches what was returned by stop_player_wait_timer
    if (p1_stats_restored.total_wait_time != p1_total or
        p3_stats_restored.total_wait_time != p3_total or
        p5_stats_restored.total_wait_time != p5_total or
        p7_stats_restored.total_wait_time != p7_total):
        print("❌ total_wait_time doesn't match returned value from stop_player_wait_timer")
        return False
    
    print("✓ total_wait_time values are consistent")
    
    # Verify final ordering is still correct
    if not (p1_total >= p3_total >= p5_total >= p7_total):
        print("❌ Final wait time ordering is incorrect")
        return False
    
    print("✓ Final wait time ordering is correct")
    
    print("\n✅ All realistic session resumption tests passed!")
    return True

def run_all_tests():
    """Run all realistic session resumption tests"""
    print("Running Realistic Session Resumption Tests...")
    print("=" * 60)
    
    try:
        success = test_realistic_session_resumption()
        
        print("=" * 60)
        if success:
            print("✅ All realistic session resumption tests passed!")
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