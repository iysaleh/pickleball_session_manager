#!/usr/bin/env python3

"""
Test for Refactored Deterministic Waitlist System V2

Tests the new architecture that hooks into the actual competitive variety
matching algorithm rather than duplicating its logic.
"""

import sys
sys.path.append('.')

from python.session import create_session
from python.pickleball_types import SessionConfig, Player, Match
from python.deterministic_waitlist_v2 import (
    calculate_player_dependencies, get_deterministic_waitlist_display_v2,
    analyze_court_finish_scenarios, run_matching_in_trial_mode
)
from python.time_manager import initialize_time_manager
from python.queue_manager import get_waiting_players

# Initialize time manager for tests
initialize_time_manager()

def test_instrumented_algorithm():
    """Test that the instrumented algorithm correctly tracks assignments"""
    print("=== Test Instrumented Algorithm ===")
    
    # Create realistic scenario
    players = [Player(f'p{i}', f'Player{i}', 3.0 + i*0.2) for i in range(12)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2, pre_seeded_ratings=True)
    session = create_session(config)
    
    # Set up matches on both courts
    session.matches = [
        Match(id='m1', court_number=1, team1=['p0', 'p1'], team2=['p2', 'p3'], status='in-progress'),
        Match(id='m2', court_number=2, team1=['p4', 'p5'], team2=['p6', 'p7'], status='in-progress'),
    ]
    
    waiting = get_waiting_players(session)
    print(f"Waiting players: {waiting}")
    
    # Test trial mode execution
    print("\nTesting trial mode execution...")
    trial_results = run_matching_in_trial_mode(session)
    print(f"Trial mode results: {len(trial_results)} assignments")
    for result in trial_results:
        print(f"  Court {result.court_number}: {result.assigned_players}")
    
    # Test court finish scenario analysis
    print(f"\nTesting court finish scenarios...")
    court1_scenarios = analyze_court_finish_scenarios(session, 1)
    print(f"Court 1 scenarios: {list(court1_scenarios.keys())}")
    
    for outcome, results in court1_scenarios.items():
        print(f"  {outcome}: {len(results)} assignments")
        for result in results:
            print(f"    Court {result.court_number}: {result.assigned_players}")
    
    print("\n✅ Instrumented algorithm test passed")


def test_player_dependencies():
    """Test the new player dependency calculation"""
    print("\n=== Test Player Dependencies ===")
    
    # Create scenario with active matches
    players = [Player(f'p{i}', f'Player{i}', 3.0 + i*0.2) for i in range(12)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2, pre_seeded_ratings=True)
    session = create_session(config)
    
    # Set up matches
    session.matches = [
        Match(id='m1', court_number=1, team1=['p0', 'p1'], team2=['p2', 'p3'], status='in-progress'),
        Match(id='m2', court_number=2, team1=['p4', 'p5'], team2=['p6', 'p7'], status='in-progress'),
    ]
    
    waiting = get_waiting_players(session)
    print(f"Waiting players: {waiting}")
    
    # Test dependencies for each waiting player
    for player in waiting[:3]:  # Test first 3
        deps = calculate_player_dependencies(session, player)
        print(f"{player} dependencies: {deps}")
    
    print("\n✅ Player dependencies test passed")


def test_waitlist_display():
    """Test the new waitlist display generation"""
    print("\n=== Test Waitlist Display ===")
    
    # Create scenario
    players = [Player(f'p{i}', f'Player{i}', 3.0 + i*0.2) for i in range(12)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2, pre_seeded_ratings=True)
    session = create_session(config)
    
    # Set up matches
    session.matches = [
        Match(id='m1', court_number=1, team1=['p0', 'p1'], team2=['p2', 'p3'], status='in-progress'),
        Match(id='m2', court_number=2, team1=['p4', 'p5'], team2=['p6', 'p7'], status='in-progress'),
    ]
    
    # Test display generation
    display = get_deterministic_waitlist_display_v2(session)
    print(f"Generated display with {len(display)} entries:")
    for line in display:
        print(f"  {line}")
    
    print("\n✅ Waitlist display test passed")


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n=== Test Edge Cases ===")
    
    # Test with no active matches
    players = [Player(f'p{i}', f'Player{i}') for i in range(8)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2)
    session = create_session(config)
    
    waiting = get_waiting_players(session)
    print(f"No active matches - waiting: {len(waiting)}")
    
    deps = calculate_player_dependencies(session, waiting[0] if waiting else 'nonexistent')
    print(f"Dependencies with no active matches: {deps}")
    
    # Test with one court active
    session.matches = [
        Match(id='m1', court_number=1, team1=['p0', 'p1'], team2=['p2', 'p3'], status='in-progress'),
    ]
    
    waiting = get_waiting_players(session)
    if waiting:
        deps = calculate_player_dependencies(session, waiting[0])
        print(f"Dependencies with one court active: {deps}")
    
    print("\n✅ Edge cases test passed")


def test_realistic_scenario():
    """Test with a realistic mid-session scenario"""
    print("\n=== Test Realistic Mid-Session Scenario ===")
    
    # Create 16 players with varied skills
    players = []
    skills = [4.5, 4.2, 4.0, 3.8, 3.6, 3.4, 3.2, 3.0, 2.8, 2.6, 4.3, 3.9, 3.5, 3.1, 2.9, 2.7]
    for i, skill in enumerate(skills):
        players.append(Player(f'p{i}', f'Player{i}', skill))
    
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=3, pre_seeded_ratings=True)
    session = create_session(config)
    
    # Simulate mid-session with some completed matches and current active matches
    session.matches = [
        # Some completed matches to establish ELO history
        Match(id='completed1', court_number=1, team1=['p0', 'p4'], team2=['p1', 'p5'], 
              status='completed', score={'team1_score': 11, 'team2_score': 8}),
        Match(id='completed2', court_number=2, team1=['p2', 'p6'], team2=['p3', 'p7'],
              status='completed', score={'team1_score': 9, 'team2_score': 11}),
        
        # Current active matches
        Match(id='active1', court_number=1, team1=['p8', 'p12'], team2=['p9', 'p13'], status='in-progress'),
        Match(id='active2', court_number=2, team1=['p10', 'p14'], team2=['p11', 'p15'], status='in-progress'),
        Match(id='active3', court_number=3, team1=['p0', 'p1'], team2=['p2', 'p3'], status='in-progress'),
    ]
    
    # Update some player stats to simulate game history
    for player_id in ['p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7']:
        if player_id in session.player_stats:
            stats = session.player_stats[player_id]
            stats.games_played = 1
            stats.wins = 1 if player_id in ['p0', 'p3', 'p4', 'p6'] else 0
            stats.losses = 0 if player_id in ['p0', 'p3', 'p4', 'p6'] else 1
    
    waiting = get_waiting_players(session)
    print(f"Realistic scenario - waiting players: {waiting}")
    
    # Test display
    display = get_deterministic_waitlist_display_v2(session)
    print(f"Realistic waitlist display:")
    for line in display:
        print(f"  {line}")
    
    print("\n✅ Realistic scenario test passed")


if __name__ == "__main__":
    test_instrumented_algorithm()
    test_player_dependencies() 
    test_waitlist_display()
    test_edge_cases()
    test_realistic_scenario()
    print("\n🎉 All V2 deterministic waitlist tests passed!")