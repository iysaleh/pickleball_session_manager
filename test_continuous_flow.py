#!/usr/bin/env python3
"""
Test continuous flow for Competitive Round Robin scheduling.

Verifies that when any match finishes, exactly one follow-up match can start immediately.
"""

import json
import sys
from python.competitive_round_robin import generate_initial_schedule
from python.pickleball_types import Session, SessionConfig, Player, CompetitiveRoundRobinConfig


def test_continuous_flow():
    """Test that continuous flow is achieved."""
    # Load player data
    with open('players.json', 'r') as f:
        data = json.load(f)
    
    players_list = data['players'][:20]
    players = [Player(id=p['name'], name=p['name'], skill_rating=p.get('skill_rating', 4.0)) 
               for p in players_list]
    
    crr_config = CompetitiveRoundRobinConfig(games_per_player=8)
    config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        courts=4,
        players=players,
        competitive_round_robin_config=crr_config
    )
    session = Session(id='test', config=config)
    for p in players:
        session.player_stats[p.id] = type('PS', (), {
            'current_skill': p.skill_rating,
            'wins': 0, 'losses': 0, 'total_points': 0, 'games_played': 0
        })()
    
    result = generate_initial_schedule(session, crr_config)
    
    print(f"Generated {len(result)} matches for {len(players)} players")
    print()
    
    # Test Wave 0 -> Wave 1 continuity
    print("=== COURT CONTINUITY ===")
    continuity_scores = []
    for court_idx in range(4):
        w0_idx = court_idx
        w1_idx = court_idx + 4
        w0_players = set(result[w0_idx].team1 + result[w0_idx].team2)
        w1_players = set(result[w1_idx].team1 + result[w1_idx].team2)
        overlap = len(w0_players & w1_players)
        continuity_scores.append(overlap)
        status = "✓" if overlap >= 3 else "✗"
        print(f"  Court {court_idx}: M{w0_idx+1}->M{w1_idx+1}: {overlap}/4 players retained {status}")
    
    avg_continuity = sum(continuity_scores) / len(continuity_scores)
    print(f"\n  Average continuity: {avg_continuity:.1f}/4")
    
    # Test continuous flow - each Wave 0 match should enable exactly one Wave 1 match
    print("\n=== CONTINUOUS FLOW ===")
    
    # Identify waiter players (not in Wave 0)
    waiter_ids = set()
    for p in players:
        in_wave0 = any(p.id in set(result[i].team1 + result[i].team2) for i in range(4))
        if not in_wave0:
            waiter_ids.add(p.id)
    
    perfect_flow = True
    for w0_idx in range(4):
        w0_players = set(result[w0_idx].team1 + result[w0_idx].team2)
        available = w0_players | waiter_ids
        
        # Which Wave 1 matches can start?
        startable = []
        for w1_idx in range(4, 8):
            w1_players = set(result[w1_idx].team1 + result[w1_idx].team2)
            if w1_players <= available:
                startable.append(w1_idx + 1)
        
        expected_match = w0_idx + 5  # M1->M5, M2->M6, etc.
        if len(startable) == 1 and startable[0] == expected_match:
            print(f"  M{w0_idx+1} finishes -> M{startable[0]} starts ✓")
        else:
            print(f"  M{w0_idx+1} finishes -> {startable} (expected [M{expected_match}]) ✗")
            perfect_flow = False
    
    print()
    if avg_continuity >= 3.0 and perfect_flow:
        print("✅ PASS: Continuous flow achieved!")
        print("   - Each match retains 3/4 players from same court")
        print("   - When any match finishes, exactly 1 follow-up starts")
        return True
    else:
        print("❌ FAIL: Continuous flow not achieved")
        return False


def test_wave_dependencies():
    """Test that Wave 1 matches have minimal dependencies."""
    with open('players.json', 'r') as f:
        data = json.load(f)
    
    players_list = data['players'][:20]
    players = [Player(id=p['name'], name=p['name'], skill_rating=p.get('skill_rating', 4.0)) 
               for p in players_list]
    
    crr_config = CompetitiveRoundRobinConfig(games_per_player=8)
    config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        courts=4,
        players=players,
        competitive_round_robin_config=crr_config
    )
    session = Session(id='test', config=config)
    for p in players:
        session.player_stats[p.id] = type('PS', (), {
            'current_skill': p.skill_rating,
            'wins': 0, 'losses': 0, 'total_points': 0, 'games_played': 0
        })()
    
    result = generate_initial_schedule(session, crr_config)
    
    print("\n=== DEPENDENCY ANALYSIS ===")
    
    all_single_dep = True
    for w1_idx in range(4, 8):
        w1_players = set(result[w1_idx].team1 + result[w1_idx].team2)
        
        # Find which Wave 0 matches these players came from
        deps = []
        for w0_idx in range(4):
            w0_players = set(result[w0_idx].team1 + result[w0_idx].team2)
            if w1_players & w0_players:
                deps.append(w0_idx + 1)
        
        status = "✓" if len(deps) == 1 else "✗"
        print(f"  M{w1_idx+1}: depends on {deps} {status}")
        if len(deps) != 1:
            all_single_dep = False
    
    if all_single_dep:
        print("\n✅ PASS: All Wave 1 matches have single dependency!")
        return True
    else:
        print("\n❌ FAIL: Some matches have multiple dependencies")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("CONTINUOUS FLOW TESTS FOR COMPETITIVE ROUND ROBIN")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    if test_continuous_flow():
        passed += 1
    else:
        failed += 1
    
    if test_wave_dependencies():
        passed += 1
    else:
        failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
