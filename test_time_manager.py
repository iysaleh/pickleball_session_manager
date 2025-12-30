#!/usr/bin/env python3
"""
Test the time manager relative timing and acceleration functionality
"""

import sys
sys.path.append('.')

import time
from datetime import datetime, timedelta
from python.time_manager import initialize_time_manager, now, start_session, pause_session, resume_session, get_session_start_time, get_elapsed_session_time
from python.session import create_session
from python.pickleball_types import SessionConfig, Player
from python.session_persistence import serialize_session, deserialize_session

def test_time_manager_basic():
    """Test basic time manager functionality without acceleration"""
    print("=== Testing Basic Time Manager ===")
    
    # Initialize time manager in normal mode
    time_manager = initialize_time_manager(test_mode=False)
    
    # Test before session starts
    pre_start_time = now()
    print(f"Current time before session start: {pre_start_time}")
    
    # Start a session
    start_session()
    session_start = get_session_start_time()
    print(f"Session start time: {session_start}")
    
    # Wait briefly and check time progression
    time.sleep(0.1)
    current_time = now()
    elapsed = get_elapsed_session_time()
    print(f"After 0.1s real time - Current: {current_time}, Elapsed: {elapsed.total_seconds():.3f}s")
    
    # Test pause/resume
    pause_session()
    pause_time = now()
    print(f"Paused at: {pause_time}")
    
    time.sleep(0.1)
    paused_check = now()
    print(f"After 0.1s pause - Time should be same: {paused_check}")
    assert paused_check == pause_time, "Time should not advance during pause"
    
    resume_session()
    time.sleep(0.1)
    resumed_time = now()
    elapsed_after_resume = get_elapsed_session_time()
    print(f"After resume + 0.1s - Current: {resumed_time}, Elapsed: {elapsed_after_resume.total_seconds():.3f}s")
    
    print("✓ Basic time manager test passed\n")

def test_time_manager_acceleration():
    """Test time manager with 15x acceleration"""
    print("=== Testing Time Manager with 15x Acceleration ===")
    
    # Initialize time manager in test mode (15x acceleration)
    time_manager = initialize_time_manager(test_mode=True)
    
    start_session()
    session_start = get_session_start_time()
    print(f"Session start time: {session_start}")
    
    # Wait 1 real second - should advance 15 virtual seconds
    time.sleep(1.0)
    elapsed = get_elapsed_session_time()
    print(f"After 1.0s real time with 15x acceleration - Elapsed: {elapsed.total_seconds():.1f}s")
    
    # Should be approximately 15 seconds (with some tolerance for execution time)
    assert 14.0 <= elapsed.total_seconds() <= 16.0, f"Expected ~15s, got {elapsed.total_seconds():.1f}s"
    
    # Test pause/resume with acceleration
    pause_session()
    pause_elapsed = get_elapsed_session_time()
    time.sleep(0.5)  # Real time pause
    
    resume_session()
    time.sleep(0.5)  # Should add ~7.5 virtual seconds
    final_elapsed = get_elapsed_session_time()
    
    expected_increase = 0.5 * 15  # 7.5 seconds
    actual_increase = (final_elapsed - pause_elapsed).total_seconds()
    print(f"Pause-resume test - Expected increase: ~{expected_increase:.1f}s, Actual: {actual_increase:.1f}s")
    
    assert 6.5 <= actual_increase <= 8.5, f"Expected ~7.5s increase, got {actual_increase:.1f}s"
    
    print("✓ Acceleration test passed\n")

def test_session_persistence():
    """Test that session start time persists across save/load"""
    print("=== Testing Session Persistence ===")
    
    # Initialize time manager
    time_manager = initialize_time_manager(test_mode=False)
    
    # Create a session
    players = [Player(id="p1", name="Alice"), Player(id="p2", name="Bob")]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session = create_session(config)
    original_start_time = session.session_start_time
    print(f"Original session start time: {original_start_time}")
    
    # Wait a bit so we have some elapsed time
    time.sleep(0.1)
    
    # Serialize and deserialize
    serialized_data = serialize_session(session)
    restored_session = deserialize_session(serialized_data)
    
    print(f"Restored session start time: {restored_session.session_start_time}")
    
    assert restored_session.session_start_time == original_start_time, "Session start time should be preserved"
    
    # Test loading the session start time into time manager
    start_session(restored_session.session_start_time)
    manager_start_time = get_session_start_time()
    
    assert manager_start_time == original_start_time, "Time manager should use loaded start time"
    
    print("✓ Session persistence test passed\n")

def test_wait_time_integration():
    """Test that wait times use the relative time system"""
    print("=== Testing Wait Time Integration ===")
    
    # Initialize with acceleration for faster testing
    time_manager = initialize_time_manager(test_mode=True)
    start_session()
    
    # Create session and player
    players = [Player(id="p1", name="Alice")]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session = create_session(config)
    
    # Start a wait timer
    from python.utils import start_player_wait_timer, get_current_wait_time, stop_player_wait_timer
    player_stats = session.player_stats["p1"]
    
    start_player_wait_timer(player_stats)
    start_time = player_stats.wait_start_time
    print(f"Started wait timer at: {start_time}")
    
    # Wait some real time (should be accelerated)
    time.sleep(0.5)  # Should be ~7.5 virtual seconds
    
    current_wait = get_current_wait_time(player_stats)
    print(f"Current wait time after 0.5s real time: {current_wait}s")
    
    # Should be approximately 7.5 seconds due to acceleration
    assert 6.0 <= current_wait <= 9.0, f"Expected ~7.5s wait time, got {current_wait}s"
    
    # Stop the timer
    total_wait = stop_player_wait_timer(player_stats)
    print(f"Total wait time when stopped: {total_wait}s")
    print(f"Accumulated total_wait_time: {player_stats.total_wait_time}s")
    
    assert player_stats.total_wait_time == total_wait, "Accumulated wait time should match"
    
    print("✓ Wait time integration test passed\n")

def run_all_tests():
    """Run all time manager tests"""
    print("Running Time Manager Tests...")
    print("=" * 50)
    
    try:
        test_time_manager_basic()
        test_time_manager_acceleration()
        test_session_persistence()
        test_wait_time_integration()
        
        print("=" * 50)
        print("✓ All time manager tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()