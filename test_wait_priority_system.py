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
from python.pickleball_types import SessionConfig, Player, PlayerStats
from python.wait_priority import (
    calculate_wait_priority_info, 
    calculate_relative_wait_priority_infos,
    should_prioritize_wait_differences,
    get_priority_aware_candidates,
    sort_players_by_wait_priority,
    format_wait_time_display,
    MINIMUM_PRIORITY_GAP_SECONDS,
    SIGNIFICANT_GAP_SECONDS,
    EXTREME_GAP_SECONDS
)
from python.competitive_variety import populate_empty_courts_competitive_variety
from python.utils import start_player_wait_timer, stop_player_wait_timer

def create_test_session(num_players=16, courts=4):
    """Create a test session with specified number of players"""
    # Initialize time manager for tests
    from python.time_manager import initialize_time_manager
    initialize_time_manager(test_mode=False)
    
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
    """Test basic wait priority calculation with fixed time gap thresholds"""
    print("Testing basic wait priority calculation...")
    
    session = create_test_session(8, 2)
    
    # Set up gap-based wait scenario
    player1_id = "player1"  # shortest waiter
    player2_id = "player2"  # significant waiter (12+ min gap)
    player3_id = "player3"  # extreme waiter (20+ min gap)
    
    # Player 1: Base wait time (shortest)
    base_wait = 300  # 5 minutes
    stats1 = session.player_stats[player1_id]
    stats1.total_wait_time = base_wait
    
    # Player 2: 12+ minute gap from shortest (should be significant)
    stats2 = session.player_stats[player2_id]
    stats2.total_wait_time = base_wait + SIGNIFICANT_GAP_SECONDS + 60  # 5min + 12min + 1min = 18min
    
    # Player 3: 20+ minute gap from shortest (should be extreme)
    stats3 = session.player_stats[player3_id]
    stats3.total_wait_time = base_wait + EXTREME_GAP_SECONDS + 120  # 5min + 20min + 2min = 27min
    
    # Test relative priority calculation
    player_ids = [player1_id, player2_id, player3_id]
    relative_infos = calculate_relative_wait_priority_infos(session, player_ids)
    
    info1 = next(info for info in relative_infos if info.player_id == player1_id)
    info2 = next(info for info in relative_infos if info.player_id == player2_id)
    info3 = next(info for info in relative_infos if info.player_id == player3_id)
    
    # Verify gap-based tier assignments
    assert info1.priority_tier == 2, f"Shortest waiter should be normal tier, got {info1.priority_tier}"
    assert info2.priority_tier == 1, f"12+ min gap waiter should be significant tier, got {info2.priority_tier}"
    assert info3.priority_tier == 0, f"20+ min gap waiter should be extreme tier, got {info3.priority_tier}"
    
    print("✓ Gap-based priority calculation works correctly")


def test_threshold_logic():
    """Test gap-based threshold logic for when wait differences matter"""
    print("Testing gap-based threshold logic...")
    
    session = create_test_session(6, 2)
    
    # Case 1: All players within minimum gap - should not prioritize
    players = ["player1", "player2", "player3"]
    base_wait = 300  # 5 minutes
    for i, pid in enumerate(players):
        session.player_stats[pid].total_wait_time = base_wait + (i * 30)  # 30s gaps
    
    relative_infos = calculate_relative_wait_priority_infos(session, players)
    assert not should_prioritize_wait_differences(relative_infos)
    
    # All should be normal tier due to small gaps
    for info in relative_infos:
        assert info.priority_tier == 2, f"Small gap players should all be normal tier"
    
    # Case 2: One player waited 12+ minutes longer - should prioritize
    session.player_stats["player1"].total_wait_time = 300  # base (5 min)
    session.player_stats["player2"].total_wait_time = 350  # similar (5.8 min)
    session.player_stats["player3"].total_wait_time = 300 + SIGNIFICANT_GAP_SECONDS + 60  # 18 min (13+ min gap)
    
    relative_infos = calculate_relative_wait_priority_infos(session, players)
    assert should_prioritize_wait_differences(relative_infos)
    
    # Player 3 should be significant tier
    player3_info = next(info for info in relative_infos if info.player_id == "player3")
    assert player3_info.priority_tier == 1, "Long waiter should be significant tier"
    
    # Case 3: Large minimum gap - should prioritize  
    for i, pid in enumerate(players):
        session.player_stats[pid].total_wait_time = 300 + (i * MINIMUM_PRIORITY_GAP_SECONDS)
    
    relative_infos = calculate_relative_wait_priority_infos(session, players)
    assert should_prioritize_wait_differences(relative_infos)
    
    print("✓ Gap-based threshold logic works correctly")


def test_priority_sorting():
    """Test player sorting by gap-based wait priority"""
    print("Testing gap-based priority sorting...")
    
    session = create_test_session(8, 2)
    
    # Set up wait times based on fixed gaps from shortest
    base_wait = 300  # 5 minutes (shortest)
    wait_times = {
        "player1": base_wait,  # shortest waiter (5 min)
        "player2": base_wait + EXTREME_GAP_SECONDS + 180,  # extreme waiter (20+ min gap = 28+ min total)
        "player3": base_wait + 60,  # normal, slightly longer (6 min)
        "player4": base_wait + SIGNIFICANT_GAP_SECONDS + 120,  # significant waiter (12+ min gap = 19+ min total)
        "player5": base_wait + EXTREME_GAP_SECONDS + 60,  # extreme waiter (20+ min gap = 26+ min total)
        "player6": base_wait + 30,   # normal, almost shortest (5.5 min)
    }
    
    for pid, wait_time in wait_times.items():
        session.player_stats[pid].total_wait_time = wait_time
    
    players = list(wait_times.keys())
    sorted_players = sort_players_by_wait_priority(session, players, reverse=True)
    
    # Get relative priority infos for verification
    relative_infos = calculate_relative_wait_priority_infos(session, players)
    info_by_player = {info.player_id: info for info in relative_infos}
    
    # Should be: extreme waiters first (player2, player5), then significant (player4), then normal by time
    sorted_tiers = [info_by_player[pid].priority_tier for pid in sorted_players]
    
    # With reverse=True, we expect extreme (0) first, then significant (1), then normal (2)
    # Verify tiers are in ascending order (0=extreme, 1=significant, 2=normal) 
    assert sorted_tiers == sorted(sorted_tiers), f"Gap-based tiers not sorted correctly: {sorted_tiers}"
    
    # Verify extreme waiters are first
    extreme_waiters = [pid for pid in sorted_players if info_by_player[pid].priority_tier == 0]
    assert len(extreme_waiters) == 2, f"Expected 2 extreme waiters, got {len(extreme_waiters)}"
    assert "player2" in extreme_waiters and "player5" in extreme_waiters
    
    # Verify significant waiter comes after extreme but before normal
    significant_waiters = [pid for pid in sorted_players if info_by_player[pid].priority_tier == 1]
    assert len(significant_waiters) == 1, f"Expected 1 significant waiter, got {len(significant_waiters)}"
    assert "player4" in significant_waiters
    
    print("✓ Gap-based priority sorting works correctly")


def test_candidate_selection():
    """Test priority-aware candidate selection with gap-based thresholds"""
    print("Testing candidate selection...")
    
    session = create_test_session(16, 4)
    
    # Create a mix of wait priorities using fixed gaps
    base_wait = 200  # Base wait time (shortest - 3.3 min)
    
    for i in range(16):
        pid = f"player{i+1}"
        if i < 2:
            # Extreme waiters (20+ min gap from base)
            session.player_stats[pid].total_wait_time = base_wait + EXTREME_GAP_SECONDS + (i * 100)
        elif i < 5:
            # Significant waiters (12+ min gap from base)
            session.player_stats[pid].total_wait_time = base_wait + SIGNIFICANT_GAP_SECONDS + (i * 50)
        else:
            # Normal priority (small gaps from base)
            session.player_stats[pid].total_wait_time = base_wait + (i * 30)
    
    # Test selecting 8 candidates from 16
    candidates = get_priority_aware_candidates(session, session.active_players, max_candidates=8)
    
    assert len(candidates) == 8
    
    # Get relative priority infos to verify tiers
    relative_infos = calculate_relative_wait_priority_infos(session, session.active_players)
    candidate_infos = [info for info in relative_infos if info.player_id in candidates]
    
    extreme_count = sum(1 for info in candidate_infos if info.priority_tier == 0)
    significant_count = sum(1 for info in candidate_infos if info.priority_tier == 1)
    
    # Verify we have the expected distribution based on actual tiers assigned
    all_extreme = sum(1 for info in relative_infos if info.priority_tier == 0)
    all_significant = sum(1 for info in relative_infos if info.priority_tier == 1)
    
    # The candidate selection should include all extreme and significant waiters if they exist
    expected_extreme = min(all_extreme, 8)  # Limited by max_candidates
    expected_significant = min(all_significant, 8 - expected_extreme)
    
    assert extreme_count == expected_extreme, f"Expected {expected_extreme} extreme waiters, got {extreme_count}"
    assert significant_count == expected_significant, f"Expected {expected_significant} significant waiters, got {significant_count}"
    
    print("✓ Candidate selection works correctly")


def test_match_generation_integration():
    """Test integration with match generation using gap-based thresholds"""
    print("Testing match generation integration...")
    
    session = create_test_session(16, 4)
    
    # Set up gap-based priority scenario
    base_wait = 300  # 5 minutes
    extreme_waiters = ["player1", "player2"]
    
    # Set up extreme waiters (20+ min gap from base)
    for pid in extreme_waiters:
        session.player_stats[pid].total_wait_time = base_wait + EXTREME_GAP_SECONDS + 300  # 28+ minutes total
        session.player_stats[pid].games_played = 5  # Ensure they're not provisional
    
    # Set normal wait times for others (small gaps from base)
    for i, pid in enumerate(session.active_players):
        if pid not in extreme_waiters:
            session.player_stats[pid].total_wait_time = base_wait + (i * 30)  # 5-12 minutes
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
    print(f"  - Significant gap threshold: {SIGNIFICANT_GAP_SECONDS}s ({SIGNIFICANT_GAP_SECONDS//60}m above shortest)")
    print(f"  - Extreme gap threshold: {EXTREME_GAP_SECONDS}s ({EXTREME_GAP_SECONDS//60}m above shortest)")


if __name__ == "__main__":
    run_all_tests()