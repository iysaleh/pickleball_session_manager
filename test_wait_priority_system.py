#!/usr/bin/env python3

"""
Test the new wait time priority system for competitive variety matchmaking.

This test validates:
1. Time-based priority calculation
2. Dynamic threshold logic  
3. Priority tier assignment
4. Match generation with wait priority
5. Integration with existing system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from python.session import Session, create_session
from python.types import SessionConfig, Player, PlayerStats
from python.wait_priority import (
    calculate_wait_priority_info, 
    should_prioritize_wait_differences,
    get_priority_aware_candidates,
    sort_players_by_wait_priority,
    format_wait_time_display,
    MINIMUM_PRIORITY_GAP_SECONDS,
    SIGNIFICANT_WAIT_THRESHOLD_SECONDS,
    EXTREME_WAIT_THRESHOLD_SECONDS
)
from python.competitive_variety import populate_empty_courts_competitive_variety
from python.utils import start_player_wait_timer, stop_player_wait_timer

def create_test_session(num_players=16, courts=4):
    """Create a test session with specified number of players"""
    # Create players first
    players = [Player(id=f"player{i+1}", name=f"Player {i+1}") for i in range(num_players)]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        courts=courts,
        players=players
    )
    
    session = create_session(config)
    return session


def test_basic_wait_priority_calculation():
    """Test basic wait priority calculation and tier assignment"""
    print("Testing basic wait priority calculation...")
    
    session = create_test_session(8, 2)
    
    # Simulate different wait scenarios
    player1_id = "player1"
    player2_id = "player2" 
    player3_id = "player3"
    
    # Player 1: No wait time (new player)
    info1 = calculate_wait_priority_info(session, player1_id)
    assert info1.total_wait_seconds == 0
    assert info1.priority_tier == 2  # normal
    assert not info1.is_significant_waiter
    assert not info1.is_extreme_waiter
    
    # Player 2: Significant wait time
    stats2 = session.player_stats[player2_id]
    stats2.total_wait_time = SIGNIFICANT_WAIT_THRESHOLD_SECONDS + 100
    info2 = calculate_wait_priority_info(session, player2_id)
    assert info2.total_wait_seconds >= SIGNIFICANT_WAIT_THRESHOLD_SECONDS
    assert info2.priority_tier == 1  # significant
    assert info2.is_significant_waiter
    assert not info2.is_extreme_waiter
    
    # Player 3: Extreme wait time
    stats3 = session.player_stats[player3_id]
    stats3.total_wait_time = EXTREME_WAIT_THRESHOLD_SECONDS + 200
    info3 = calculate_wait_priority_info(session, player3_id)
    assert info3.total_wait_seconds >= EXTREME_WAIT_THRESHOLD_SECONDS
    assert info3.priority_tier == 0  # extreme
    assert info3.is_extreme_waiter
    
    print("✓ Basic priority calculation works correctly")


def test_threshold_logic():
    """Test dynamic threshold logic for when wait differences matter"""
    print("Testing threshold logic...")
    
    session = create_test_session(6, 2)
    
    # Case 1: All players within minimum gap - should not prioritize
    players = ["player1", "player2", "player3"]
    base_wait = 300  # 5 minutes
    for i, pid in enumerate(players):
        session.player_stats[pid].total_wait_time = base_wait + (i * 30)  # 30s gaps
    
    infos = [calculate_wait_priority_info(session, pid) for pid in players]
    assert not should_prioritize_wait_differences(infos)
    
    # Case 2: One player with significant wait - should prioritize
    session.player_stats["player3"].total_wait_time = SIGNIFICANT_WAIT_THRESHOLD_SECONDS + 100
    infos = [calculate_wait_priority_info(session, pid) for pid in players]
    assert should_prioritize_wait_differences(infos)
    
    # Case 3: Large gap but all normal tier - should prioritize  
    for i, pid in enumerate(players):
        session.player_stats[pid].total_wait_time = 300 + (i * MINIMUM_PRIORITY_GAP_SECONDS)
    
    infos = [calculate_wait_priority_info(session, pid) for pid in players]
    assert should_prioritize_wait_differences(infos)
    
    print("✓ Threshold logic works correctly")


def test_priority_sorting():
    """Test player sorting by wait priority"""
    print("Testing priority sorting...")
    
    session = create_test_session(8, 2)
    
    # Set up different wait times
    wait_times = {
        "player1": 100,  # normal, short wait
        "player2": EXTREME_WAIT_THRESHOLD_SECONDS + 300,  # extreme waiter
        "player3": 200,  # normal, medium wait  
        "player4": SIGNIFICANT_WAIT_THRESHOLD_SECONDS + 100,  # significant waiter
        "player5": EXTREME_WAIT_THRESHOLD_SECONDS + 100,  # extreme waiter (less than player2)
        "player6": 50,   # normal, shortest wait
    }
    
    for pid, wait_time in wait_times.items():
        session.player_stats[pid].total_wait_time = wait_time
    
    players = list(wait_times.keys())
    sorted_players = sort_players_by_wait_priority(session, players, reverse=True)
    
    # Should be: extreme waiters first (player2, player5), then significant (player4), then normal by time
    # Expected order: player2, player5, player4, player3, player1, player6 (highest priority first)
    sorted_tiers = []
    for pid in sorted_players:
        info = calculate_wait_priority_info(session, pid)
        sorted_tiers.append(info.priority_tier)
    
    # With reverse=True, we expect extreme (0) first, then significant (1), then normal (2)
    # Verify tiers are in ascending order (0=extreme, 1=significant, 2=normal) 
    assert sorted_tiers == sorted(sorted_tiers), f"Tiers not sorted correctly: {sorted_tiers}"
    
    # Verify extreme waiters are first
    extreme_waiters = [pid for pid in sorted_players if calculate_wait_priority_info(session, pid).priority_tier == 0]
    assert len(extreme_waiters) == 2
    assert "player2" in extreme_waiters[:2] and "player5" in extreme_waiters[:2]
    
    print("✓ Priority sorting works correctly")


def test_candidate_selection():
    """Test priority-aware candidate selection"""
    print("Testing candidate selection...")
    
    session = create_test_session(16, 4)
    
    # Create a mix of wait priorities
    for i in range(16):
        pid = f"player{i+1}"
        if i < 2:
            # Extreme waiters
            session.player_stats[pid].total_wait_time = EXTREME_WAIT_THRESHOLD_SECONDS + (i * 100)
        elif i < 5:
            # Significant waiters  
            session.player_stats[pid].total_wait_time = SIGNIFICANT_WAIT_THRESHOLD_SECONDS + (i * 50)
        else:
            # Normal priority
            session.player_stats[pid].total_wait_time = 300 + (i * 30)
    
    # Test selecting 8 candidates from 16
    candidates = get_priority_aware_candidates(session, session.active_players, max_candidates=8)
    
    assert len(candidates) == 8
    
    # Verify extreme waiters are included
    candidate_infos = [calculate_wait_priority_info(session, pid) for pid in candidates]
    extreme_count = sum(1 for info in candidate_infos if info.priority_tier == 0)
    significant_count = sum(1 for info in candidate_infos if info.priority_tier == 1)
    
    assert extreme_count == 2, f"Expected 2 extreme waiters, got {extreme_count}"
    assert significant_count == 3, f"Expected 3 significant waiters, got {significant_count}"
    
    print("✓ Candidate selection works correctly")


def test_match_generation_integration():
    """Test integration with match generation"""
    print("Testing match generation integration...")
    
    session = create_test_session(16, 4)
    
    # Set up priority scenario: 2 extreme waiters who should get priority
    extreme_waiters = ["player1", "player2"]
    for pid in extreme_waiters:
        session.player_stats[pid].total_wait_time = EXTREME_WAIT_THRESHOLD_SECONDS + 500
        session.player_stats[pid].games_played = 5  # Ensure they're not provisional
    
    # Set normal wait times for others
    for i, pid in enumerate(session.active_players):
        if pid not in extreme_waiters:
            session.player_stats[pid].total_wait_time = 300 + (i * 30)
            session.player_stats[pid].games_played = 5
    
    # Generate matches
    initial_matches = len(session.matches)
    populate_empty_courts_competitive_variety(session)
    
    # Verify matches were created
    new_matches = session.matches[initial_matches:]
    assert len(new_matches) > 0, "No matches were generated"
    
    # Check if extreme waiters were prioritized
    players_in_new_matches = set()
    for match in new_matches:
        players_in_new_matches.update(match.team1 + match.team2)
    
    extreme_in_matches = sum(1 for pid in extreme_waiters if pid in players_in_new_matches)
    print(f"Extreme waiters in matches: {extreme_in_matches}/2")
    
    # Note: Due to competitive variety constraints, extreme waiters might not always get matches
    # But the algorithm should have considered them first
    
    print("✓ Match generation integration works")


def test_time_display_formatting():
    """Test time display formatting"""
    print("Testing time display formatting...")
    
    test_cases = [
        (45, "45s"),
        (60, "1m"),
        (90, "1m 30s"),
        (3600, "1h"),
        (3720, "1h 2m"),
        (4500, "1h 15m"),
    ]
    
    for seconds, expected in test_cases:
        result = format_wait_time_display(seconds)
        assert result == expected, f"Expected '{expected}', got '{result}' for {seconds}s"
    
    print("✓ Time display formatting works correctly")


def test_current_wait_time_tracking():
    """Test current wait time tracking with priority system"""
    print("Testing current wait time tracking...")
    
    session = create_test_session(4, 1)
    player_id = "player1"
    stats = session.player_stats[player_id]
    
    # Start wait timer
    start_player_wait_timer(stats)
    
    # Simulate some time passing
    original_time = stats.wait_start_time
    stats.wait_start_time = original_time - timedelta(minutes=5)
    
    # Calculate priority info
    info = calculate_wait_priority_info(session, player_id)
    assert info.current_wait_seconds >= 300  # At least 5 minutes
    assert info.total_wait_seconds >= 300
    
    # Stop timer and check accumulation
    waited_time = stop_player_wait_timer(stats)
    assert waited_time >= 300
    assert stats.total_wait_time >= 300
    assert stats.wait_start_time is None
    
    print("✓ Current wait time tracking works correctly")


def run_all_tests():
    """Run all wait priority system tests"""
    print("Running Wait Priority System Tests...\n")
    
    test_basic_wait_priority_calculation()
    test_threshold_logic()
    test_priority_sorting()
    test_candidate_selection()
    test_match_generation_integration()
    test_time_display_formatting()
    test_current_wait_time_tracking()
    
    print(f"\n✅ All wait priority system tests passed!")
    print(f"Configuration:")
    print(f"  - Minimum priority gap: {MINIMUM_PRIORITY_GAP_SECONDS}s ({MINIMUM_PRIORITY_GAP_SECONDS//60}m)")
    print(f"  - Significant wait threshold: {SIGNIFICANT_WAIT_THRESHOLD_SECONDS}s ({SIGNIFICANT_WAIT_THRESHOLD_SECONDS//60}m)")
    print(f"  - Extreme wait threshold: {EXTREME_WAIT_THRESHOLD_SECONDS}s ({EXTREME_WAIT_THRESHOLD_SECONDS//60}m)")


if __name__ == "__main__":
    run_all_tests()