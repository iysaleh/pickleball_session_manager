#!/usr/bin/env python3
"""
Realistic test showing how repetition constraints cause imbalanced matches
and how adaptive constraints solve it.
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    calculate_elo_rating, populate_empty_courts_competitive_variety,
    get_adaptive_constraints, apply_adaptive_constraints
)
from python.utils import generate_id
from datetime import datetime

def test_realistic_imbalance_scenario():
    """Test a realistic scenario where repetition constraints cause imbalanced matches"""
    
    print("REALISTIC IMBALANCE TEST: Repetition Constraints vs Balance")
    print("=" * 65)
    
    initialize_time_manager(test_mode=False)
    
    # 12 players with clear skill tiers
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3  # 3 courts = 12 players exactly
    )
    
    session = create_session(config)
    
    # Create 3 distinct skill tiers
    for i in range(1, 13):
        player_id = f'p{i}'
        stats = session.player_stats[player_id]
        
        if 1 <= i <= 4:  # Elite players (p1-p4)
            stats.games_played = 10
            stats.wins = 9
            stats.total_points_for = 110
            stats.total_points_against = 70
        elif 5 <= i <= 8:  # Average players (p5-p8) 
            stats.games_played = 10
            stats.wins = 5
            stats.total_points_for = 90
            stats.total_points_against = 90
        else:  # Weak players (p9-p12)
            stats.games_played = 10
            stats.wins = 1
            stats.total_points_for = 70
            stats.total_points_against = 110
    
    # Show skill tiers
    print("Player Skill Tiers:")
    for i in range(1, 13):
        player_id = f'p{i}'
        rating = calculate_elo_rating(session.player_stats[player_id])
        tier = "Elite" if i <= 4 else "Average" if i <= 8 else "Weak"
        print(f"  {player_id}: {rating:.0f} ({tier})")
    
    print()
    
    # Simulate several rounds that create repetition constraints
    print("Simulating Early Rounds to Create Repetition History:")
    
    # Round 1: Balanced within tiers
    round1_matches = [
        (['p1', 'p2'], ['p3', 'p4']),   # Elite vs Elite
        (['p5', 'p6'], ['p7', 'p8']),   # Average vs Average  
        (['p9', 'p10'], ['p11', 'p12']) # Weak vs Weak
    ]
    
    # Round 2: Mix things up but stay within reasonable bounds
    round2_matches = [
        (['p1', 'p3'], ['p2', 'p4']),   # Elite vs Elite
        (['p5', 'p7'], ['p6', 'p8']),   # Average vs Average
        (['p9', 'p11'], ['p10', 'p12']) # Weak vs Weak
    ]
    
    # Round 3: Create more repetition constraints
    round3_matches = [
        (['p2', 'p3'], ['p1', 'p4']),   # Elite vs Elite
        (['p6', 'p7'], ['p5', 'p8']),   # Average vs Average
        (['p10', 'p11'], ['p9', 'p12']) # Weak vs Weak
    ]
    
    all_historical_matches = [round1_matches, round2_matches, round3_matches]
    
    for round_num, round_matches in enumerate(all_historical_matches, 1):
        print(f"  Round {round_num}:")
        for court_num, (team1, team2) in enumerate(round_matches, 1):
            match = Match(
                id=generate_id(),
                court_number=court_num,
                team1=team1,
                team2=team2,
                status='completed',
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            session.matches.append(match)
            
            # Update player histories
            for p1 in team1:
                for p2 in team1:
                    if p1 != p2:
                        if p2 not in session.player_stats[p1].partners_played:
                            session.player_stats[p1].partners_played[p2] = []
                        session.player_stats[p1].partners_played[p2].append(match.id)
                
                for p2 in team2:
                    if p2 not in session.player_stats[p1].opponents_played:
                        session.player_stats[p1].opponents_played[p2] = []
                    session.player_stats[p1].opponents_played[p2].append(match.id)
            
            for p1 in team2:
                for p2 in team2:
                    if p1 != p2:
                        if p2 not in session.player_stats[p1].partners_played:
                            session.player_stats[p1].partners_played[p2] = []
                        session.player_stats[p1].partners_played[p2].append(match.id)
            
            team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
            team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
            imbalance = abs(team1_rating - team2_rating)
            print(f"    Court {court_num}: {team1} vs {team2} - Imbalance: {imbalance:.0f}")
    
    # Now test Round 4 with strict constraints vs adaptive constraints
    print(f"\n" + "=" * 65)
    print("ROUND 4 COMPARISON: Strict vs Adaptive Constraints")
    print("=" * 65)
    
    # Test with strict constraints (early session)
    print("\nSTRICT CONSTRAINTS (Early Session Rules):")
    session_strict = create_session(config)
    session_strict.matches = session.matches.copy()  # Copy match history
    session_strict.player_stats = session.player_stats.copy()  # Copy player stats
    
    # Force strict constraints
    session_strict.competitive_variety_roaming_range_percent = 0.65
    session_strict.competitive_variety_partner_repetition_limit = 3
    session_strict.competitive_variety_opponent_repetition_limit = 2
    session_strict.adaptive_balance_weight = 1.0
    
    populate_empty_courts_competitive_variety(session_strict)
    strict_matches = [m for m in session_strict.matches if m.status == 'waiting']
    
    strict_total_imbalance = 0
    for i, match in enumerate(strict_matches):
        team1_rating = sum(calculate_elo_rating(session_strict.player_stats[p]) for p in match.team1)
        team2_rating = sum(calculate_elo_rating(session_strict.player_stats[p]) for p in match.team2)
        imbalance = abs(team1_rating - team2_rating)
        strict_total_imbalance += imbalance
        print(f"  Court {match.court_number}: {match.team1} vs {match.team2} - Imbalance: {imbalance:.0f}")
    
    strict_avg_imbalance = strict_total_imbalance / len(strict_matches) if strict_matches else 0
    print(f"  Average Imbalance: {strict_avg_imbalance:.0f}")
    
    # Test with adaptive constraints (late session)
    print(f"\nADAPTIVE CONSTRAINTS (Late Session Rules):")
    session_adaptive = create_session(config)
    session_adaptive.matches = session.matches.copy()  # Copy match history
    session_adaptive.player_stats = session.player_stats.copy()  # Copy player stats
    
    # Simulate late session by adding fake completed matches
    for i in range(50):  # Trigger "very late" session
        fake_match = Match(
            id=f"fake_{i}",
            court_number=1,
            team1=['p1', 'p2'],
            team2=['p3', 'p4'],
            status='completed',
            start_time=None,
            end_time=None
        )
        session_adaptive.matches.append(fake_match)
    
    populate_empty_courts_competitive_variety(session_adaptive)
    adaptive_matches = [m for m in session_adaptive.matches if m.status == 'waiting']
    
    adaptive_total_imbalance = 0
    for i, match in enumerate(adaptive_matches):
        team1_rating = sum(calculate_elo_rating(session_adaptive.player_stats[p]) for p in match.team1)
        team2_rating = sum(calculate_elo_rating(session_adaptive.player_stats[p]) for p in match.team2)
        imbalance = abs(team1_rating - team2_rating)
        adaptive_total_imbalance += imbalance
        print(f"  Court {match.court_number}: {match.team1} vs {match.team2} - Imbalance: {imbalance:.0f}")
    
    adaptive_avg_imbalance = adaptive_total_imbalance / len(adaptive_matches) if adaptive_matches else 0
    print(f"  Average Imbalance: {adaptive_avg_imbalance:.0f}")
    
    # Compare results
    print(f"\n" + "=" * 65)
    print("RESULTS COMPARISON:")
    print("=" * 65)
    print(f"Strict Constraints Average Imbalance: {strict_avg_imbalance:.0f}")
    print(f"Adaptive Constraints Average Imbalance: {adaptive_avg_imbalance:.0f}")
    
    improvement = strict_avg_imbalance - adaptive_avg_imbalance
    print(f"Improvement: {improvement:.0f} rating points")
    
    if improvement > 0:
        print("✅ ADAPTIVE CONSTRAINTS IMPROVE BALANCE!")
        print(f"   By relaxing repetition constraints, more balanced matches are possible")
    elif improvement == 0:
        print("➖ NO DIFFERENCE - both approaches yield similar balance")
    else:
        print("❌ ADAPTIVE CONSTRAINTS WORSEN BALANCE")
        print(f"   This suggests the test scenario needs adjustment")
    
    # Show constraint differences
    print(f"\nConstraint Analysis:")
    strict_constraints = {
        'roaming_range': 0.65,
        'partner_repetition': 3,
        'opponent_repetition': 2,
        'balance_weight': 1.0
    }
    adaptive_constraints = get_adaptive_constraints(session_adaptive)
    
    print(f"Strict:   Roaming={strict_constraints['roaming_range']*100:.0f}%, Partner={strict_constraints['partner_repetition']}, Opponent={strict_constraints['opponent_repetition']}, Weight={strict_constraints['balance_weight']:.1f}x")
    print(f"Adaptive: Roaming={adaptive_constraints['roaming_range']*100:.0f}%, Partner={adaptive_constraints['partner_repetition']}, Opponent={adaptive_constraints['opponent_repetition']}, Weight={adaptive_constraints['balance_weight']:.1f}x")

if __name__ == "__main__":
    test_realistic_imbalance_scenario()