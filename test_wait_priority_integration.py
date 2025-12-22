#!/usr/bin/env python3

"""
Integration test for the new wait priority system with existing matchmaking.

This test validates that the sophisticated wait time priority system works
correctly with the competitive variety algorithm while maintaining backward
compatibility with the legacy games_waited counter.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from python.session import Session, create_session, complete_match
from python.types import SessionConfig, Player, PlayerStats, Match
from python.wait_priority import (
    calculate_wait_priority_info, 
    calculate_relative_wait_priority_infos,
    get_priority_aware_candidates,
    sort_players_by_wait_priority,
    SIGNIFICANT_GAP_SECONDS,
    EXTREME_GAP_SECONDS
)
from python.competitive_variety import populate_empty_courts_competitive_variety
from python.utils import start_player_wait_timer, stop_player_wait_timer, generate_id

def create_realistic_test_session():
    """Create a realistic test session with mixed wait scenarios"""
    # Initialize time manager for tests
    from python.time_manager import initialize_time_manager
    initialize_time_manager(test_mode=False)
    
    players = [Player(id=f"player{i+1}", name=f"Player {i+1}") for i in range(16)]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        courts=4,
        players=players
    )
    
    session = create_session(config)
    return session


def simulate_real_session_with_wait_priority():
    """Simulate a real session where some players wait much longer than others"""
    print("Simulating realistic session with varied wait times...")
    
    session = create_realistic_test_session()
    
    # Simulate session history: some players played many games, others waited
    players = list(session.active_players)
    
    # Create some completed matches to establish history
    match_id = 1
    for i in range(5):  # 5 completed matches
        # Pick 4 players for match (rotate to create variety)
        start_idx = (i * 2) % len(players)
        match_players = players[start_idx:start_idx+4]
        if len(match_players) < 4:
            match_players.extend(players[:4-len(match_players)])
        
        # Create and complete match
        match = Match(
            id=f"match{match_id}",
            court_number=1,
            team1=match_players[:2],
            team2=match_players[2:4],
            status='completed',
            start_time=datetime.now() - timedelta(minutes=30-i*5)
        )
        # Add scoring manually after creation
        match.end_time = datetime.now() - timedelta(minutes=25-i*5)
        match.score = {'team1_score': 11, 'team2_score': 8}
        match.winner = 'team1'
        session.matches.append(match)
        match_id += 1
        
        # Update player stats
        for player_id in match_players:
            if player_id not in session.player_stats:
                session.player_stats[player_id] = PlayerStats(player_id=player_id)
            
            stats = session.player_stats[player_id]
            stats.games_played += 1
            
            if player_id in match.team1:
                if match.winner == 'team1':
                    stats.wins += 1
                else:
                    stats.losses += 1
            else:
                if match.winner == 'team2':
                    stats.wins += 1
                else:
                    stats.losses += 1
    
    # Now simulate different wait scenarios
    current_time = datetime.now()
    
    # The base_wait will be determined by the shortest actual waiter (recent players)
    # So we don't need to explicitly set it here
    
    # Group 1: Extreme waiters (2 players) - 20+ minutes longer than shortest
    # Assuming min will be ~60s, extreme threshold = 60s + 1200s = 1260s, so use 1400s+
    extreme_waiters = ["player1", "player2"]
    for i, pid in enumerate(extreme_waiters):
        stats = session.player_stats.setdefault(pid, PlayerStats(player_id=pid))
        stats.total_wait_time = 1400 + (i * 200)  # ~23-26 minutes (20+ min gap from 60s base)
        stats.games_waited = 8 + i  # High legacy counter
        # Start current wait session  
        stats.wait_start_time = current_time - timedelta(minutes=5+i)
    
    # Group 2: Significant waiters (3 players) - 12+ minutes longer than shortest  
    # Assuming min ~60s, significant threshold = 60s + 720s = 780s, so use 800-1000s
    significant_waiters = ["player3", "player4", "player5"] 
    for i, pid in enumerate(significant_waiters):
        stats = session.player_stats.setdefault(pid, PlayerStats(player_id=pid))
        stats.total_wait_time = 800 + (i * 100)  # ~13-18 minutes (12+ min gap from 60s base)
        stats.games_waited = 5 + i  # Medium legacy counter
        stats.wait_start_time = current_time - timedelta(minutes=2+i)  # Shorter current waits
    
    # Group 3: Normal waiters (4 players) - between recent and significant
    normal_waiters = ["player6", "player7", "player8", "player9"]  
    for i, pid in enumerate(normal_waiters):
        stats = session.player_stats.setdefault(pid, PlayerStats(player_id=pid))
        # Between recent players (~60-95s) and significant threshold (will be ~180-240s based on min)
        stats.total_wait_time = 120 + (i * 20)  # 120-180s range
        stats.games_waited = 2 + i  # Low legacy counter
        stats.wait_start_time = current_time - timedelta(minutes=1+i)  # Shorter current waits
    
    # Group 4: Recently played (remaining players) - shortest wait times (these set the base)
    recent_players = [pid for pid in players if pid not in extreme_waiters + significant_waiters + normal_waiters]
    for i, pid in enumerate(recent_players):
        stats = session.player_stats.setdefault(pid, PlayerStats(player_id=pid))
        stats.total_wait_time = 60 + (i * 5)  # Very short waits (60-95s range)
        stats.games_waited = 0  # No wait count
        stats.games_played = 5  # Just played
    
    return session, extreme_waiters, significant_waiters, normal_waiters, recent_players


def test_priority_calculation_integration():
    """Test that relative priority calculation integrates correctly with existing system"""
    print("Testing priority calculation integration...")
    
    session, extreme_waiters, significant_waiters, normal_waiters, recent_players = simulate_real_session_with_wait_priority()
    
    # Get relative priority calculation for all active players
    all_player_ids = extreme_waiters + significant_waiters + normal_waiters + recent_players
    relative_infos = calculate_relative_wait_priority_infos(session, all_player_ids)
    info_by_player = {info.player_id: info for info in relative_infos}
    
    # Test that the relative system creates a meaningful priority hierarchy
    
    # Test that players with much longer wait times get higher priority
    long_waiters = [pid for pid in extreme_waiters + significant_waiters]
    short_waiters = recent_players
    
    for long_pid in long_waiters:
        long_info = info_by_player[long_pid]
        for short_pid in short_waiters:
            short_info = info_by_player[short_pid]
            # Long waiters should have lower tier numbers (higher priority) than short waiters
            assert long_info.priority_tier <= short_info.priority_tier, \
                f"Long waiter {long_pid} (tier {long_info.priority_tier}) should have higher priority than short waiter {short_pid} (tier {short_info.priority_tier})"
    
    # Test that the system creates different tiers when there are significant gaps
    unique_tiers = set(info.priority_tier for info in relative_infos)
    assert len(unique_tiers) >= 2, f"Should have multiple priority tiers, got {unique_tiers}"
    
    print("✓ Relative priority calculation integration works correctly")


def test_candidate_selection_prioritizes_waiters():
    """Test that candidate selection prioritizes long waiters"""
    print("Testing candidate selection prioritization...")
    
    session, extreme_waiters, significant_waiters, normal_waiters, recent_players = simulate_real_session_with_wait_priority()
    
    # Get all available players
    available_players = list(session.active_players)
    
    # Select top 8 candidates
    candidates = get_priority_aware_candidates(session, available_players, max_candidates=8)
    
    # Verify extreme waiters are included
    extreme_in_candidates = sum(1 for pid in extreme_waiters if pid in candidates)
    assert extreme_in_candidates == len(extreme_waiters), f"Expected all {len(extreme_waiters)} extreme waiters, got {extreme_in_candidates}"
    
    # Verify significant waiters are prioritized
    significant_in_candidates = sum(1 for pid in significant_waiters if pid in candidates)
    assert significant_in_candidates >= 2, f"Expected at least 2 significant waiters, got {significant_in_candidates}"
    
    # Verify recent players are deprioritized
    recent_in_candidates = sum(1 for pid in recent_players if pid in candidates)
    expected_recent = max(0, 8 - len(extreme_waiters) - len(significant_waiters) - len(normal_waiters))
    assert recent_in_candidates <= expected_recent + 1, f"Too many recent players selected: {recent_in_candidates}"
    
    print(f"✓ Candidate selection works: {extreme_in_candidates} extreme, {significant_in_candidates} significant, {recent_in_candidates} recent")


def test_match_generation_respects_wait_priority():
    """Test that match generation respects wait time priority"""
    print("Testing match generation with wait priority...")
    
    session, extreme_waiters, significant_waiters, normal_waiters, recent_players = simulate_real_session_with_wait_priority()
    
    # Ensure all players have some games to avoid provisional status
    for pid in session.active_players:
        stats = session.player_stats.setdefault(pid, PlayerStats(player_id=pid))
        if stats.games_played < 2:
            stats.games_played = 3
    
    # Clear any existing active matches
    session.matches = [m for m in session.matches if m.status == 'completed']
    
    # Generate matches
    initial_match_count = len(session.matches)
    populate_empty_courts_competitive_variety(session)
    new_match_count = len(session.matches) - initial_match_count
    
    assert new_match_count > 0, "No matches were generated"
    
    # Check which players got into matches
    players_in_matches = set()
    for match in session.matches[initial_match_count:]:
        if match.status in ['waiting', 'in-progress']:
            players_in_matches.update(match.team1 + match.team2)
    
    extreme_in_matches = sum(1 for pid in extreme_waiters if pid in players_in_matches)
    significant_in_matches = sum(1 for pid in significant_waiters if pid in players_in_matches)
    normal_in_matches = sum(1 for pid in normal_waiters if pid in players_in_matches)
    recent_in_matches = sum(1 for pid in recent_players if pid in players_in_matches)
    
    print(f"Players in matches: {extreme_in_matches} extreme, {significant_in_matches} significant, {normal_in_matches} normal, {recent_in_matches} recent")
    
    # Extreme waiters should be prioritized for matches
    assert extreme_in_matches >= 1, "At least one extreme waiter should get a match"
    
    print("✓ Match generation respects wait priority")


def test_backward_compatibility():
    """Test that legacy games_waited counter still works"""
    print("Testing backward compatibility with legacy system...")
    
    session = create_realistic_test_session()
    
    # Simulate old-style priority (games_waited based)
    players = list(session.active_players)[:6]
    
    # Set up legacy-style wait counters
    for i, pid in enumerate(players):
        stats = session.player_stats.setdefault(pid, PlayerStats(player_id=pid))
        stats.games_waited = i * 2  # 0, 2, 4, 6, 8, 10
        stats.total_wait_time = 300  # All same total wait time
    
    # Test that sorting still considers games_waited as fallback
    sorted_players = sort_players_by_wait_priority(session, players, reverse=True)
    
    # When total wait times are equal, games_waited should be used as tiebreaker
    # Higher games_waited should come first
    for i in range(len(sorted_players) - 1):
        curr_stats = session.player_stats[sorted_players[i]]
        next_stats = session.player_stats[sorted_players[i+1]]
        
        # Since total wait times are equal, games_waited should be descending
        assert curr_stats.games_waited >= next_stats.games_waited, \
            f"Legacy fallback failed: {curr_stats.games_waited} < {next_stats.games_waited}"
    
    print("✓ Backward compatibility maintained")


def test_mixed_priority_scenarios():
    """Test complex scenarios with mixed priorities using gap-based system"""
    print("Testing complex mixed priority scenarios...")
    
    session = create_realistic_test_session()
    
    # Scenario: Player with high games_waited but low total_wait_time vs 
    # player with low games_waited but high total_wait_time
    
    player1_id = "player1"  # High legacy counter, low total wait (will be shortest)
    player2_id = "player2"  # Low legacy counter, high total wait (12+ min gap)
    
    stats1 = session.player_stats.setdefault(player1_id, PlayerStats(player_id=player1_id))
    stats1.games_waited = 10  # High legacy count
    stats1.total_wait_time = 300  # 5 minutes total (shortest)
    
    stats2 = session.player_stats.setdefault(player2_id, PlayerStats(player_id=player2_id))  
    stats2.games_waited = 2   # Low legacy count
    stats2.total_wait_time = 300 + SIGNIFICANT_GAP_SECONDS + 120  # 5 + 12 + 2 = 19 minutes (significant gap)
    
    # Use relative calculation to compare them properly
    relative_infos = calculate_relative_wait_priority_infos(session, [player1_id, player2_id])
    info1 = next(info for info in relative_infos if info.player_id == player1_id)
    info2 = next(info for info in relative_infos if info.player_id == player2_id)
    
    # Player2 should be prioritized despite lower games_waited
    sorted_players = sort_players_by_wait_priority(session, [player1_id, player2_id], reverse=True)
    assert sorted_players[0] == player2_id, f"Player with higher total wait should be first, got {sorted_players}"
    
    # Player2 should have higher priority (lower tier number)
    assert info2.priority_tier < info1.priority_tier, f"Player2 (tier {info2.priority_tier}) should have higher priority than Player1 (tier {info1.priority_tier})"
    
    print("✓ Mixed priority scenarios handled correctly")


def test_time_accumulation():
    """Test that wait time accumulates correctly across sessions"""
    print("Testing wait time accumulation...")
    
    session = create_realistic_test_session()
    player_id = "player1"
    
    stats = session.player_stats.setdefault(player_id, PlayerStats(player_id=player_id))
    
    # Start with some accumulated wait time
    stats.total_wait_time = 600  # 10 minutes previous
    
    # Start waiting
    start_player_wait_timer(stats)
    original_start = stats.wait_start_time
    
    # Simulate 5 minutes passing
    stats.wait_start_time = original_start - timedelta(minutes=5)
    
    # Get priority info (should include current wait)
    info = calculate_wait_priority_info(session, player_id)
    assert info.total_wait_seconds >= 900, f"Expected at least 900s total, got {info.total_wait_seconds}"  # 10 + 5 minutes
    assert info.current_wait_seconds >= 300, f"Expected at least 300s current, got {info.current_wait_seconds}"  # 5 minutes
    
    # Stop timer and verify accumulation
    waited_duration = stop_player_wait_timer(stats)
    assert waited_duration >= 300, f"Expected at least 300s duration, got {waited_duration}"
    assert stats.total_wait_time >= 900, f"Expected at least 900s accumulated, got {stats.total_wait_time}"
    assert stats.wait_start_time is None, "Wait timer should be stopped"
    
    print("✓ Wait time accumulation works correctly")


def run_integration_tests():
    """Run all integration tests"""
    print("Running Wait Priority Integration Tests...\n")
    
    test_priority_calculation_integration()
    test_candidate_selection_prioritizes_waiters() 
    test_match_generation_respects_wait_priority()
    test_backward_compatibility()
    test_mixed_priority_scenarios()
    test_time_accumulation()
    
    print(f"\n✅ All wait priority integration tests passed!")
    print("The new wait time priority system is fully integrated and working correctly.")


if __name__ == "__main__":
    run_integration_tests()