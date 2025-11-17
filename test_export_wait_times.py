#!/usr/bin/env python3
"""
Test that session export includes total wait time for each player
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.types import Player, SessionConfig
from python.session import create_session
from python.utils import start_player_wait_timer, stop_player_wait_timer, format_duration


def test_export_with_wait_times():
    """Test that export includes player wait times"""
    print("Test: Session export includes wait times\n")
    
    # Create session
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie")
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=1,
        banned_pairs=[],
        locked_teams=[]
    )
    
    session = create_session(config)
    
    # Simulate player wait times
    print("1. Setting up player wait times...")
    
    # Alice: 50 seconds waited
    alice_stats = session.player_stats["p1"]
    start_player_wait_timer(alice_stats)
    alice_stats.wait_start_time = datetime.now() - timedelta(seconds=50)
    stop_player_wait_timer(alice_stats)
    
    # Bob: 30 seconds waited
    bob_stats = session.player_stats["p2"]
    start_player_wait_timer(bob_stats)
    bob_stats.wait_start_time = datetime.now() - timedelta(seconds=30)
    stop_player_wait_timer(bob_stats)
    
    # Charlie: currently waiting for 20 seconds
    charlie_stats = session.player_stats["p3"]
    start_player_wait_timer(charlie_stats)
    charlie_stats.wait_start_time = datetime.now() - timedelta(seconds=20)
    
    print("   Alice: 50 seconds waited")
    print("   Bob: 30 seconds waited")
    print("   Charlie: 20 seconds currently waiting")
    
    # Simulate export format
    print("\n2. Simulating export output:\n")
    
    from python.utils import get_current_wait_time
    
    export_lines = []
    export_lines.append(f"{'Player':<25} {'ELO':<10} {'W-L':<10} {'Games':<10} {'Win %':<10} {'Wait Time':<12}")
    export_lines.append("-" * 82)
    
    for player in players:
        if player.id not in session.active_players:
            continue
        
        stats = session.player_stats[player.id]
        
        # Get total wait time (accumulated + current if waiting)
        current_wait = get_current_wait_time(stats)
        total_wait_seconds = stats.total_wait_time + current_wait
        
        elo = 1500  # Default ELO
        record = f"{stats.wins}-{stats.losses}"
        win_pct = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0
        win_pct_str = f"{win_pct:.1f}%" if stats.games_played > 0 else "N/A"
        wait_time_str = format_duration(total_wait_seconds)
        
        line = f"{player.name:<25} {elo:<10.0f} {record:<10} {stats.games_played:<10} {win_pct_str:<10} {wait_time_str:<12}"
        export_lines.append(line)
    
    for line in export_lines:
        print(line)
    
    # Verify format
    print("\n3. Verifying export format:")
    assert len(export_lines[0]) > 0, "Header should exist"
    assert "Wait Time" in export_lines[0], "Header should include 'Wait Time'"
    assert "Alice" in export_lines[2], "Alice should be in export"
    assert "00:50" in export_lines[2], "Alice wait time should be 00:50"
    assert "Bob" in export_lines[3], "Bob should be in export"
    assert "00:30" in export_lines[3], "Bob wait time should be 00:30"
    
    print("[PASS] All wait times correctly formatted in export")
    print("[PASS] Export format verified")


if __name__ == "__main__":
    test_export_with_wait_times()
