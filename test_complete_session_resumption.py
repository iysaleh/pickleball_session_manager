#!/usr/bin/env python3
"""
Comprehensive test combining both wait timers and match duration timers
to ensure complete session resumption functionality.
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

def test_complete_session_resumption():
    """Test resumption with both wait timers and match duration timers active"""
    print("=== Testing Complete Session Resumption (Wait + Match Timers) ===")
    
    # Initialize time manager with acceleration for faster testing
    time_manager = initialize_time_manager(test_mode=True)
    
    # Create a session with 6 players - some will be in matches, some waiting
    players = [Player(id=f"p{i}", name=f"Player{i}") for i in range(1, 7)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session1 = create_session(config)
    print(f"Original session start time: {session1.session_start_time}")
    
    # Start wait timers for players 5 and 6 (they'll be waiting)
    p5_stats = session1.player_stats["p5"]
    p6_stats = session1.player_stats["p6"]
    
    start_player_wait_timer(p5_stats)
    print(f"Started Player 5 wait timer at: {p5_stats.wait_start_time}")
    
    time.sleep(0.3)  # 4.5 virtual seconds
    
    start_player_wait_timer(p6_stats)
    print(f"Started Player 6 wait timer at: {p6_stats.wait_start_time}")
    
    time.sleep(0.2)  # 3 virtual seconds
    
    # Create a match in progress (players 1,2 vs 3,4)
    match_result = create_manual_match(session1, 1, ["p1", "p2"], ["p3", "p4"])
    print(f"Created match: {match_result['success']}")
    
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
    
    # Wait more time to let both wait timers and match timer accumulate
    time.sleep(0.4)  # 6 more virtual seconds
    
    # Check all timers before saving
    p5_wait_before = get_current_wait_time(p5_stats)
    p6_wait_before = get_current_wait_time(p6_stats)
    match_duration_before = int((now() - active_match.start_time).total_seconds())
    
    print(f"Before save:")
    print(f"  Player 5 wait: {p5_wait_before}s")
    print(f"  Player 6 wait: {p6_wait_before}s")
    print(f"  Match duration: {match_duration_before}s")
    
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
    
    # Now adjust both wait times and match times
    adjust_wait_times_after_time_manager_start(session2)
    
    print(f"Restored session start time: {session2.session_start_time}")
    
    # Check restored timers
    p5_stats_restored = session2.player_stats["p5"]
    p6_stats_restored = session2.player_stats["p6"]
    
    # Find the restored match
    restored_match = None
    for match in session2.matches:
        if match.court_number == 1:
            restored_match = match
            break
    
    p5_wait_after = get_current_wait_time(p5_stats_restored)
    p6_wait_after = get_current_wait_time(p6_stats_restored)
    match_duration_after = int((now() - restored_match.start_time).total_seconds()) if restored_match else 0
    
    print(f"After load:")
    print(f"  Player 5 wait: {p5_wait_after}s (was {p5_wait_before}s)")
    print(f"  Player 6 wait: {p6_wait_after}s (was {p6_wait_before}s)")
    print(f"  Match duration: {match_duration_after}s (was {match_duration_before}s)")
    
    # Check for any negative values
    if p5_wait_after < 0 or p6_wait_after < 0 or match_duration_after < 0:
        print(f"❌ Found negative times: P5={p5_wait_after}, P6={p6_wait_after}, Match={match_duration_after}")
        return False
    
    print("✓ No negative times after resumption")
    
    # Check preservation (with tolerance)
    p5_diff = abs(p5_wait_after - p5_wait_before)
    p6_diff = abs(p6_wait_after - p6_wait_before)
    match_diff = abs(match_duration_after - match_duration_before)
    
    if p5_diff <= 2 and p6_diff <= 2 and match_diff <= 2:
        print("✓ All timers preserved correctly during save/load")
    else:
        print(f"❌ Timers not preserved: P5 diff={p5_diff}, P6 diff={p6_diff}, Match diff={match_diff}")
        return False
    
    # Test continued operation
    print("\n--- Testing continued timer progression ---")
    time.sleep(0.3)  # 4.5 more virtual seconds
    
    p5_wait_continued = get_current_wait_time(p5_stats_restored)
    p6_wait_continued = get_current_wait_time(p6_stats_restored)
    match_duration_continued = int((now() - restored_match.start_time).total_seconds())
    
    print(f"After continuing:")
    print(f"  Player 5 wait: {p5_wait_continued}s (+{p5_wait_continued - p5_wait_after})")
    print(f"  Player 6 wait: {p6_wait_continued}s (+{p6_wait_continued - p6_wait_after})")
    print(f"  Match duration: {match_duration_continued}s (+{match_duration_continued - match_duration_after})")
    
    # All should have increased by approximately 4.5 seconds
    increases = [
        p5_wait_continued - p5_wait_after,
        p6_wait_continued - p6_wait_after,
        match_duration_continued - match_duration_after
    ]
    
    for i, increase in enumerate(['P5', 'P6', 'Match']):
        if not (3 <= increases[i] <= 6):
            print(f"❌ {increase} timer not incrementing correctly: +{increases[i]}s")
            return False
    
    print("✓ All timers continue to work correctly after resumption")
    
    # Final validation - check relative ordering
    if p5_wait_continued > p6_wait_continued:  # P5 started waiting first
        print("✓ Wait time ordering preserved (P5 > P6)")
    else:
        print(f"❌ Wait time ordering not preserved: P5={p5_wait_continued}, P6={p6_wait_continued}")
        return False
    
    # Test stopping wait timers
    p5_total = stop_player_wait_timer(p5_stats_restored)
    p6_total = stop_player_wait_timer(p6_stats_restored)
    
    print(f"Final accumulated wait times: P5={p5_total}s, P6={p6_total}s")
    print(f"Final match duration: {match_duration_continued}s")
    
    print("✅ Complete session resumption test passed!")
    return True

def run_all_tests():
    """Run the complete session resumption test"""
    print("Running Complete Session Resumption Tests...")
    print("=" * 60)
    
    try:
        success = test_complete_session_resumption()
        
        print("=" * 60)
        if success:
            print("✅ Complete session resumption test passed!")
        else:
            print("❌ Test failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()