#!/usr/bin/env python3
"""
Test that individual player wait_start_time is persisted in saved session
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.types import Player, SessionConfig
from python.session import create_session
from python.utils import start_player_wait_timer, format_duration, get_current_wait_time
from python.session_persistence import save_session, load_last_session, clear_saved_session


def test_wait_start_time_persistence():
    """Test that wait_start_time is persisted for each player"""
    print("Test: Player wait_start_time persistence\n")
    
    clear_saved_session()
    
    # Create session
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
    
    # Simulate players with different wait states
    print("1. Setting up players with different wait states...")
    
    # Alice: was waiting 50 seconds, now stopped (no wait_start_time)
    alice_stats = session.player_stats["p1"]
    start_player_wait_timer(alice_stats)
    alice_stats.wait_start_time = datetime.now() - timedelta(seconds=50)
    from python.utils import stop_player_wait_timer
    stop_player_wait_timer(alice_stats)
    print(f"   Alice: accumulated 50s, wait_start_time = {alice_stats.wait_start_time}")
    
    # Bob: currently waiting for 30 seconds (has wait_start_time)
    bob_stats = session.player_stats["p2"]
    start_player_wait_timer(bob_stats)
    bob_stats.wait_start_time = datetime.now() - timedelta(seconds=30)
    print(f"   Bob: currently waiting, wait_start_time set")
    
    # Charlie: not waiting (no wait_start_time)
    charlie_stats = session.player_stats["p3"]
    print(f"   Charlie: not waiting, wait_start_time = {charlie_stats.wait_start_time}")
    
    # Diana: currently waiting for 15 seconds (has wait_start_time)
    diana_stats = session.player_stats["p4"]
    start_player_wait_timer(diana_stats)
    diana_stats.wait_start_time = datetime.now() - timedelta(seconds=15)
    print(f"   Diana: currently waiting, wait_start_time set")
    
    # Save session
    print("\n2. Saving session with wait states...")
    save_session(session)
    print("   Session saved")
    
    # Load session
    print("\n3. Loading session...")
    loaded_session = load_last_session()
    assert loaded_session is not None, "Failed to load session"
    
    # Verify wait_start_time persistence
    print("\n4. Verifying persisted wait_start_time:")
    
    loaded_alice = loaded_session.player_stats["p1"]
    assert loaded_alice.wait_start_time is None, "Alice wait_start_time should be None"
    assert loaded_alice.total_wait_time >= 48 and loaded_alice.total_wait_time <= 52, f"Alice total wait should be ~50s, got {loaded_alice.total_wait_time}s"
    print(f"   [PASS] Alice: wait_start_time=None, total_wait={format_duration(loaded_alice.total_wait_time)}")
    
    loaded_bob = loaded_session.player_stats["p2"]
    assert loaded_bob.wait_start_time is not None, "Bob wait_start_time should NOT be None"
    current_bob_wait = get_current_wait_time(loaded_bob)
    assert current_bob_wait >= 28 and current_bob_wait <= 32, f"Bob current wait should be ~30s, got {current_bob_wait}s"
    print(f"   [PASS] Bob: wait_start_time=set, current_wait={format_duration(current_bob_wait)}")
    
    loaded_charlie = loaded_session.player_stats["p3"]
    assert loaded_charlie.wait_start_time is None, "Charlie wait_start_time should be None"
    assert loaded_charlie.total_wait_time == 0, "Charlie total wait should be 0"
    print(f"   [PASS] Charlie: wait_start_time=None, total_wait={format_duration(loaded_charlie.total_wait_time)}")
    
    loaded_diana = loaded_session.player_stats["p4"]
    assert loaded_diana.wait_start_time is not None, "Diana wait_start_time should NOT be None"
    current_diana_wait = get_current_wait_time(loaded_diana)
    assert current_diana_wait >= 13 and current_diana_wait <= 17, f"Diana current wait should be ~15s, got {current_diana_wait}s"
    print(f"   [PASS] Diana: wait_start_time=set, current_wait={format_duration(current_diana_wait)}")
    
    print("\n[ALL PASS] wait_start_time persistence verified!")
    print("\nDetails:")
    print("  - Completed waits: wait_start_time=None, accumulated in total_wait_time")
    print("  - Active waits: wait_start_time preserved, current time calculated from it")
    print("  - Not waiting: wait_start_time=None, total_wait_time=0")
    
    clear_saved_session()


if __name__ == "__main__":
    test_wait_start_time_persistence()
