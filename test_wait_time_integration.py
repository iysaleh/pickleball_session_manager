#!/usr/bin/env python3
"""
Integration test: Player wait time tracking with session persistence
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.pickleball_types import Player, SessionConfig
from python.session import create_session
from python.utils import start_player_wait_timer, stop_player_wait_timer, format_duration
from python.session_persistence import save_session, load_last_session, clear_saved_session


def test_wait_time_integration():
    """Test wait time tracking with session persistence"""
    print("Integration Test: Wait time tracking with persistence\n")
    
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
    
    # Simulate players waiting
    print("1. Simulating player wait times...")
    
    # Alice waits for 50 seconds
    alice_stats = session.player_stats["p1"]
    start_player_wait_timer(alice_stats)
    alice_stats.wait_start_time = datetime.now() - timedelta(seconds=50)
    alice_wait = stop_player_wait_timer(alice_stats)
    print(f"   Alice waited: {format_duration(alice_wait)}")
    assert 48 <= alice_wait <= 52, f"Alice wait should be ~50s, got {alice_wait}s"
    
    # Bob waits for 30 seconds
    bob_stats = session.player_stats["p2"]
    start_player_wait_timer(bob_stats)
    bob_stats.wait_start_time = datetime.now() - timedelta(seconds=30)
    bob_wait = stop_player_wait_timer(bob_stats)
    print(f"   Bob waited: {format_duration(bob_wait)}")
    assert 28 <= bob_wait <= 32, f"Bob wait should be ~30s, got {bob_wait}s"
    
    # Charlie is still waiting (20 seconds so far)
    charlie_stats = session.player_stats["p3"]
    start_player_wait_timer(charlie_stats)
    charlie_stats.wait_start_time = datetime.now() - timedelta(seconds=20)
    
    # Save session
    print("\n2. Saving session with wait times...")
    save_session(session)
    print("   Session saved")
    
    # Load session
    print("\n3. Loading session...")
    loaded_session = load_last_session()
    assert loaded_session is not None, "Failed to load session"
    
    # Verify wait times persisted
    print("\n4. Verifying persisted wait times...")
    loaded_alice_stats = loaded_session.player_stats["p1"]
    loaded_bob_stats = loaded_session.player_stats["p2"]
    loaded_charlie_stats = loaded_session.player_stats["p3"]
    
    assert 48 <= loaded_alice_stats.total_wait_time <= 52, f"Alice total wait should be ~50s, got {loaded_alice_stats.total_wait_time}s"
    print(f"   Alice total wait time: {format_duration(loaded_alice_stats.total_wait_time)} [PASS]")
    
    assert 28 <= loaded_bob_stats.total_wait_time <= 32, f"Bob total wait should be ~30s, got {loaded_bob_stats.total_wait_time}s"
    print(f"   Bob total wait time: {format_duration(loaded_bob_stats.total_wait_time)} [PASS]")
    
    # Charlie should have no accumulated time yet (still waiting)
    assert loaded_charlie_stats.total_wait_time == 0, "Charlie should have 0 accumulated time"
    print(f"   Charlie total wait time: {format_duration(loaded_charlie_stats.total_wait_time)} [PASS]")
    
    # Verify wait_start_time is reset for completed waits
    assert loaded_alice_stats.wait_start_time is None, "Alice wait_start_time should be None"
    assert loaded_bob_stats.wait_start_time is None, "Bob wait_start_time should be None"
    
    print("\n[ALL PASS] Wait time integration test passed!")
    
    clear_saved_session()


if __name__ == "__main__":
    test_wait_time_integration()
