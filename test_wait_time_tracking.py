#!/usr/bin/env python3
"""
Test player wait time tracking functionality
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.types import Player, SessionConfig, PlayerStats
from python.utils import (
    start_player_wait_timer, stop_player_wait_timer, 
    get_current_wait_time, format_duration
)


def test_start_wait_timer():
    """Test that wait timer starts correctly"""
    print("Test 1: Start wait timer")
    
    stats = PlayerStats(player_id="p1")
    assert stats.wait_start_time is None, "Wait timer should start as None"
    
    start_player_wait_timer(stats)
    assert stats.wait_start_time is not None, "Wait timer should be set"
    assert isinstance(stats.wait_start_time, datetime), "Wait timer should be datetime"
    
    print("[PASS] Wait timer started correctly")


def test_get_current_wait_time():
    """Test getting current wait time"""
    print("\nTest 2: Get current wait time")
    
    stats = PlayerStats(player_id="p1")
    
    # Not waiting
    current_wait = get_current_wait_time(stats)
    assert current_wait == 0, "Should return 0 when not waiting"
    
    # Start waiting
    stats.wait_start_time = datetime.now() - timedelta(seconds=30)
    current_wait = get_current_wait_time(stats)
    
    # Should be approximately 30 seconds (allow 2 second tolerance)
    assert 28 <= current_wait <= 32, f"Current wait should be ~30s, got {current_wait}s"
    
    print(f"[PASS] Current wait time correctly calculated: {current_wait}s")


def test_stop_wait_timer():
    """Test stopping wait timer and accumulating time"""
    print("\nTest 3: Stop wait timer")
    
    stats = PlayerStats(player_id="p1")
    stats.wait_start_time = datetime.now() - timedelta(seconds=45)
    
    assert stats.total_wait_time == 0, "Total wait time should start at 0"
    
    wait_duration = stop_player_wait_timer(stats)
    
    # Should be approximately 45 seconds
    assert 43 <= wait_duration <= 47, f"Wait duration should be ~45s, got {wait_duration}s"
    assert stats.wait_start_time is None, "Wait start time should be reset"
    
    # Total wait time should accumulate
    assert 43 <= stats.total_wait_time <= 47, f"Total wait time should be ~45s, got {stats.total_wait_time}s"
    
    print(f"[PASS] Wait timer stopped and duration accumulated: {wait_duration}s")


def test_multiple_wait_sessions():
    """Test multiple wait sessions accumulating"""
    print("\nTest 4: Multiple wait sessions")
    
    stats = PlayerStats(player_id="p1")
    
    # First wait session: 20 seconds
    stats.wait_start_time = datetime.now() - timedelta(seconds=20)
    duration1 = stop_player_wait_timer(stats)
    assert 18 <= duration1 <= 22, f"First wait should be ~20s, got {duration1}s"
    
    # Wait a bit
    time.sleep(0.5)
    
    # Second wait session: 15 seconds
    stats.wait_start_time = datetime.now() - timedelta(seconds=15)
    duration2 = stop_player_wait_timer(stats)
    assert 13 <= duration2 <= 17, f"Second wait should be ~15s, got {duration2}s"
    
    # Total should accumulate
    total = duration1 + duration2
    assert 33 <= stats.total_wait_time <= 37, f"Total should be ~{total}s, got {stats.total_wait_time}s"
    
    print(f"[PASS] Multiple wait sessions accumulated: {duration1}s + {duration2}s = {stats.total_wait_time}s")


def test_wait_time_formatting():
    """Test formatting wait times"""
    print("\nTest 5: Format wait time")
    
    # 5 minutes 30 seconds
    formatted = format_duration(330)
    assert formatted == "05:30", f"Format should be '05:30', got '{formatted}'"
    
    # 0 seconds
    formatted = format_duration(0)
    assert formatted == "00:00", f"Format should be '00:00', got '{formatted}'"
    
    # 1 hour 5 minutes 30 seconds
    formatted = format_duration(3930)
    assert formatted == "65:30", f"Format should be '65:30', got '{formatted}'"
    
    print("[PASS] Wait times formatted correctly")


if __name__ == "__main__":
    print("Testing player wait time tracking...\n")
    
    test_start_wait_timer()
    test_get_current_wait_time()
    test_stop_wait_timer()
    test_multiple_wait_sessions()
    test_wait_time_formatting()
    
    print("\n[ALL PASS] All wait time tracking tests passed!")
