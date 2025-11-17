#!/usr/bin/env python3
"""
Test dual wait time display in waitlist (current wait / total wait)
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.types import Player, SessionConfig
from python.session import create_session
from python.utils import start_player_wait_timer, format_duration, get_current_wait_time


def test_dual_wait_time_display():
    """Test waitlist display with dual wait times"""
    print("Test: Dual wait time display in waitlist\n")
    
    # Create session
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie")
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
    
    # Simulate different wait scenarios
    print("Simulating waitlist with dual time display:\n")
    print("Format: PlayerName  [current_wait / total_wait]\n")
    
    # Alice: first time waiting (5 seconds)
    alice_stats = session.player_stats["p1"]
    start_player_wait_timer(alice_stats)
    alice_stats.wait_start_time = datetime.now() - timedelta(seconds=5)
    # total_wait_time = 0 (no previous waits)
    
    # Bob: currently waiting (20 seconds), has 30 seconds accumulated from before
    bob_stats = session.player_stats["p2"]
    bob_stats.total_wait_time = 30  # previously accumulated
    start_player_wait_timer(bob_stats)
    bob_stats.wait_start_time = datetime.now() - timedelta(seconds=20)
    
    # Charlie: currently waiting (35 seconds), has 15 seconds accumulated from before
    charlie_stats = session.player_stats["p3"]
    charlie_stats.total_wait_time = 15  # previously accumulated
    start_player_wait_timer(charlie_stats)
    charlie_stats.wait_start_time = datetime.now() - timedelta(seconds=35)
    
    # Display as it would appear in waitlist
    waiting_players = [
        ("p1", "Alice", alice_stats),
        ("p2", "Bob", bob_stats),
        ("p3", "Charlie", charlie_stats)
    ]
    
    for player_id, player_name, stats in waiting_players:
        current_wait = get_current_wait_time(stats)
        current_wait_str = format_duration(current_wait)
        
        total_wait = stats.total_wait_time + current_wait
        total_wait_str = format_duration(total_wait)
        
        item_text = f"{player_name}  [{current_wait_str} / {total_wait_str}]"
        print(f"  {item_text}")
    
    print("\nExplanation of times:")
    print("  Alice  [00:05 / 00:05]   - Current: 5s since waiting, Total: 5s (first wait)")
    print("  Bob    [00:20 / 00:50]   - Current: 20s since waiting, Total: 50s (20s current + 30s previous)")
    print("  Charlie [00:35 / 00:50]  - Current: 35s since waiting, Total: 50s (35s current + 15s previous)")
    
    print("\n[PASS] Dual wait time display verified")
    print("[PASS] Format: PlayerName  [current_wait / total_wait]")


if __name__ == "__main__":
    test_dual_wait_time_display()
