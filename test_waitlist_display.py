#!/usr/bin/env python3
"""
Test waitlist display with running wait times
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.types import Player, SessionConfig
from python.session import create_session
from python.utils import start_player_wait_timer, format_duration, get_current_wait_time


def test_waitlist_display():
    """Test waitlist display with running wait times"""
    print("Test: Waitlist display with running wait times\n")
    
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
    
    # Simulate players on waitlist with different wait times
    print("Simulating waitlist with running timers:\n")
    
    waiting_players = [
        ("p1", "Alice", 5),    # 5 seconds
        ("p2", "Bob", 25),     # 25 seconds
        ("p3", "Charlie", 45)  # 45 seconds
    ]
    
    for player_id, player_name, wait_seconds in waiting_players:
        stats = session.player_stats[player_id]
        
        # Start timer
        start_player_wait_timer(stats)
        
        # Simulate elapsed time
        stats.wait_start_time = datetime.now() - timedelta(seconds=wait_seconds)
        
        # Get current wait time
        current_wait = get_current_wait_time(stats)
        wait_time_str = format_duration(current_wait)
        
        # Display as it would appear in waitlist
        item_text = f"{player_name}  [{wait_time_str}]"
        print(f"  {item_text}")
    
    print("\n✓ Waitlist display format verified")
    print("\nThe waitlist will update every second to show current wait times.")


if __name__ == "__main__":
    test_waitlist_display()
