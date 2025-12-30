#!/usr/bin/env python3
"""
Test for team balancing bug fix.

The issue was that when 4 players were selected for a match, the algorithm would
use the first valid team configuration instead of evaluating all configurations
and picking the most balanced one.

Example from bug report:
- Ibraheem (ELO 1850) + Carol (ELO 1812) vs Alisha (ELO 1206) + Kimberly (ELO 1531)
- Team totals: 3662 vs 2737 (difference: 925 ELO - very imbalanced!)
- Should be: Ibraheem + Alisha vs Carol + Kimberly (difference: ~300 ELO - much better)
"""

from python.session import create_session
from python.pickleball_types import SessionConfig, Player, PlayerStats
from python.competitive_variety import (
    populate_empty_courts_competitive_variety, 
    calculate_elo_rating, 
    score_potential_match
)


def set_player_stats(session, player_id, games, wins, points_for, points_against):
    """Helper to set player stats for testing"""
    session.player_stats[player_id].games_played = games
    session.player_stats[player_id].wins = wins
    session.player_stats[player_id].total_points_for = points_for
    session.player_stats[player_id].total_points_against = points_against


def test_team_balancing_fix():
    """Test that team configurations are balanced properly"""
    
    print("Testing team balancing fix...")
    
    # Create players similar to the bug report
    players = [
        Player(id='ibraheem', name='Ibraheem Saleh'),
        Player(id='carol', name='Carol Ritter'),  
        Player(id='alisha', name='Alisha Crebbin'),
        Player(id='kimberly', name='Kimberly Conant'),
    ]

    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )

    session = create_session(config)

    # Set up player stats to create a clear ELO spread (high, high-med, med-low, low)
    set_player_stats(session, 'ibraheem', 5, 4, 52, 32)   # High skill
    set_player_stats(session, 'carol', 6, 4, 55, 37)     # High-medium skill  
    set_player_stats(session, 'alisha', 5, 0, 28, 56)    # Low skill
    set_player_stats(session, 'kimberly', 6, 2, 47, 56)  # Medium-low skill

    # Calculate actual ELO ratings
    elos = {}
    for player_id in ['ibraheem', 'carol', 'alisha', 'kimberly']:
        elos[player_id] = calculate_elo_rating(session.player_stats[player_id])

    print(f"  Player ELOs: Ibraheem={elos['ibraheem']:.0f}, Carol={elos['carol']:.0f}, "
          f"Alisha={elos['alisha']:.0f}, Kimberly={elos['kimberly']:.0f}")

    # Generate the match
    populate_empty_courts_competitive_variety(session)

    if not session.matches:
        print("  ✗ FAIL: No match was generated")
        return False

    match = session.matches[0]
    team1_elos = [elos[p] for p in match.team1]
    team2_elos = [elos[p] for p in match.team2]
    team1_total = sum(team1_elos)
    team2_total = sum(team2_elos)
    elo_diff = abs(team1_total - team2_total)

    print(f"  Generated match:")
    print(f"    Team 1: {match.team1[0]}/{match.team1[1]} (Total ELO: {team1_total:.0f})")
    print(f"    Team 2: {match.team2[0]}/{match.team2[1]} (Total ELO: {team2_total:.0f})")
    print(f"    ELO difference: {elo_diff:.0f}")

    # The worst case would be high+high vs low+low (difference ~925)
    # A good balance should be much better (difference ~300-400)
    if elo_diff > 600:
        print(f"  ✗ FAIL: Teams are poorly balanced (difference {elo_diff:.0f} > 600)")
        return False
    else:
        print(f"  ✓ PASS: Teams are well balanced (difference {elo_diff:.0f} <= 600)")
        return True


def test_all_configurations_evaluated():
    """Test that the algorithm evaluates all 3 team configurations"""
    
    print("\nTesting that all configurations are evaluated...")
    
    # Create a scenario where configuration order matters for balance
    players = [
        Player(id='high1', name='High Player 1'),    # ELO ~1800
        Player(id='high2', name='High Player 2'),    # ELO ~1750  
        Player(id='low1', name='Low Player 1'),      # ELO ~1300
        Player(id='low2', name='Low Player 2'),      # ELO ~1250
    ]

    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )

    session = create_session(config)

    # Create a clear skill gradient
    set_player_stats(session, 'high1', 4, 3, 44, 28)   # ~1800 ELO
    set_player_stats(session, 'high2', 4, 3, 40, 32)   # ~1750 ELO
    set_player_stats(session, 'low1', 4, 1, 30, 42)    # ~1300 ELO  
    set_player_stats(session, 'low2', 4, 1, 26, 44)    # ~1250 ELO

    elos = {}
    for player_id in ['high1', 'high2', 'low1', 'low2']:
        elos[player_id] = calculate_elo_rating(session.player_stats[player_id])

    print(f"  Player ELOs: High1={elos['high1']:.0f}, High2={elos['high2']:.0f}, "
          f"Low1={elos['low1']:.0f}, Low2={elos['low2']:.0f}")

    # Test all 3 possible configurations manually to see which should be best
    configs = [
        (['high1', 'high2'], ['low1', 'low2']),   # Worst: high+high vs low+low
        (['high1', 'low1'], ['high2', 'low2']),   # Better: high+low vs high+low  
        (['high1', 'low2'], ['high2', 'low1']),   # Similar to config 2
    ]
    
    best_balance = float('inf')
    best_config_idx = -1
    
    for i, (team1, team2) in enumerate(configs):
        team1_total = sum(elos[p] for p in team1)
        team2_total = sum(elos[p] for p in team2)
        diff = abs(team1_total - team2_total)
        
        print(f"    Config {i+1}: {team1[0]}/{team1[1]} vs {team2[0]}/{team2[1]} "
              f"(diff: {diff:.0f})")
        
        if diff < best_balance:
            best_balance = diff
            best_config_idx = i

    print(f"  Best configuration should be #{best_config_idx + 1} (difference: {best_balance:.0f})")

    # Generate actual match
    populate_empty_courts_competitive_variety(session)
    
    if not session.matches:
        print("  ✗ FAIL: No match generated")
        return False

    match = session.matches[0]
    actual_team1_total = sum(elos[p] for p in match.team1)
    actual_team2_total = sum(elos[p] for p in match.team2)
    actual_diff = abs(actual_team1_total - actual_team2_total)

    print(f"  Generated: {match.team1[0]}/{match.team1[1]} vs {match.team2[0]}/{match.team2[1]} "
          f"(diff: {actual_diff:.0f})")

    # The algorithm should pick one of the better configurations (not config 1)
    if actual_diff <= best_balance * 1.1:  # Allow small tolerance
        print("  ✓ PASS: Algorithm chose a well-balanced configuration")
        return True
    else:
        print(f"  ✗ FAIL: Algorithm chose poorly balanced configuration "
              f"(diff {actual_diff:.0f} > expected ~{best_balance:.0f})")
        return False


def test_edge_case_equal_players():
    """Test balancing when all players have similar skill"""
    
    print("\nTesting edge case with equally skilled players...")
    
    players = [
        Player(id='p1', name='Player 1'),
        Player(id='p2', name='Player 2'),
        Player(id='p3', name='Player 3'),
        Player(id='p4', name='Player 4'),
    ]

    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )

    session = create_session(config)

    # Give all players similar stats (should result in similar ELOs)
    for player_id in ['p1', 'p2', 'p3', 'p4']:
        set_player_stats(session, player_id, 4, 2, 35, 35)  # 50% win rate, even points

    populate_empty_courts_competitive_variety(session)
    
    if not session.matches:
        print("  ✗ FAIL: No match generated")
        return False

    # With equal players, any configuration should be balanced
    match = session.matches[0]
    elos = {p: calculate_elo_rating(session.player_stats[p]) for p in ['p1', 'p2', 'p3', 'p4']}
    
    team1_total = sum(elos[p] for p in match.team1)
    team2_total = sum(elos[p] for p in match.team2)
    diff = abs(team1_total - team2_total)

    print(f"  All players have similar ELO (~{list(elos.values())[0]:.0f})")
    print(f"  Generated match difference: {diff:.0f}")
    
    if diff < 50:  # Should be very close with equal players
        print("  ✓ PASS: Equal players result in balanced teams")
        return True
    else:
        print("  ✗ FAIL: Even equal players resulted in imbalanced teams")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("TEAM BALANCING BUG FIX VERIFICATION")
    print("=" * 70)
    
    tests = [
        test_team_balancing_fix,
        test_all_configurations_evaluated,
        test_edge_case_equal_players,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[ALL TESTS PASSED] {passed}/{total} tests passed - Team balancing works correctly!")
    else:
        print(f"[SOME TESTS FAILED] {passed}/{total} tests passed - Team balancing needs more work!")
        exit(1)