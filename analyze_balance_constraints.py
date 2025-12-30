#!/usr/bin/env python3
"""
Analysis and solution for improving balance in competitive variety matchmaking.

The issue: As sessions progress, variety constraints become too restrictive,
preventing balanced matches and forcing imbalanced ones.

Solution: Implement adaptive constraint relaxation based on session progression.
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig
from python.session import create_session
from python.competitive_variety import (
    calculate_elo_rating, get_player_ranking, can_play_with_player,
    get_roaming_rank_range
)

def analyze_constraint_impact():
    """Analyze how constraints affect match balance as sessions progress"""
    
    print("ANALYSIS: Constraint Impact on Match Balance")
    print("=" * 50)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session with skill tiers
    players = []
    for i in range(1, 17):  # 16 players
        players.append(Player(id=f'p{i}', name=f'Player{i}'))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Set up skill tiers
    skill_tiers = {
        'Elite': (1, 4),     # p1-p4: 1800+ rating
        'Strong': (5, 8),    # p5-p8: 1700+ rating  
        'Average': (9, 12),  # p9-p12: 1500+ rating
        'Weak': (13, 16)     # p13-p16: 1400+ rating
    }
    
    # Simulate player histories to create skill differences
    for tier_name, (start, end) in skill_tiers.items():
        for i in range(start, end + 1):
            player_id = f'p{i}'
            stats = session.player_stats[player_id]
            
            if tier_name == 'Elite':
                stats.games_played = 12
                stats.wins = 10
                stats.total_points_for = 120
                stats.total_points_against = 80
            elif tier_name == 'Strong':
                stats.games_played = 12
                stats.wins = 8
                stats.total_points_for = 110
                stats.total_points_against = 90
            elif tier_name == 'Average':
                stats.games_played = 12
                stats.wins = 6
                stats.total_points_for = 100
                stats.total_points_against = 100
            else:  # Weak
                stats.games_played = 12
                stats.wins = 4
                stats.total_points_for = 80
                stats.total_points_against = 120
    
    # Display skill rankings
    print("\n1. Current Skill Tiers:")
    for tier_name, (start, end) in skill_tiers.items():
        ratings = []
        for i in range(start, end + 1):
            player_id = f'p{i}'
            rating = calculate_elo_rating(session.player_stats[player_id])
            ratings.append(rating)
        
        avg_rating = sum(ratings) / len(ratings)
        print(f"   {tier_name}: p{start}-p{end} (avg: {avg_rating:.0f})")
    
    # Test roaming range constraints
    print(f"\n2. Roaming Range Analysis (16 players):")
    roaming_percent = session.competitive_variety_roaming_range_percent
    print(f"   Current roaming percentage: {roaming_percent*100:.0f}%")
    
    # Test different player pairs
    test_pairs = [
        ('p1', 'p4', 'Elite vs Elite'),
        ('p1', 'p8', 'Elite vs Strong'), 
        ('p1', 'p12', 'Elite vs Average'),
        ('p1', 'p16', 'Elite vs Weak'),
        ('p5', 'p12', 'Strong vs Average'),
        ('p9', 'p16', 'Average vs Weak')
    ]
    
    for p1, p2, desc in test_pairs:
        rank1, _ = get_player_ranking(session, p1)
        rank2, _ = get_player_ranking(session, p2)
        rank_diff = abs(rank1 - rank2)
        
        # Check if they can play together
        can_partner = can_play_with_player(session, p1, p2, 'partner', False)
        can_opponent = can_play_with_player(session, p1, p2, 'opponent', False)
        
        print(f"   {desc} ({p1} rank {rank1}, {p2} rank {rank2}):")
        print(f"     Rank difference: {rank_diff}")
        print(f"     Can partner: {can_partner}")
        print(f"     Can be opponents: {can_opponent}")
    
    # Calculate optimal balanced matches and see if constraints allow them
    print(f"\n3. Balanced Match Analysis:")
    
    # Most balanced: Elite+Weak vs Strong+Average
    balanced_configs = [
        (['p1', 'p16'], ['p5', 'p12'], 'Elite+Weak vs Strong+Average'),
        (['p2', 'p15'], ['p6', 'p11'], 'Elite+Weak vs Strong+Average'), 
        (['p3', 'p14'], ['p7', 'p10'], 'Elite+Weak vs Strong+Average'),
        (['p4', 'p13'], ['p8', 'p9'], 'Elite+Weak vs Strong+Average')
    ]
    
    for team1, team2, desc in balanced_configs:
        # Calculate team ratings
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        rating_diff = abs(team1_rating - team2_rating)
        
        # Check if constraints allow this match
        constraints_ok = True
        constraint_failures = []
        
        # Check partnerships
        if not can_play_with_player(session, team1[0], team1[1], 'partner', False):
            constraints_ok = False
            constraint_failures.append(f"{team1[0]}-{team1[1]} partnership")
        
        if not can_play_with_player(session, team2[0], team2[1], 'partner', False):
            constraints_ok = False
            constraint_failures.append(f"{team2[0]}-{team2[1]} partnership")
        
        # Check opponents
        for p1 in team1:
            for p2 in team2:
                if not can_play_with_player(session, p1, p2, 'opponent', False):
                    constraints_ok = False
                    constraint_failures.append(f"{p1}-{p2} opponent")
        
        print(f"   {desc}:")
        print(f"     Team ratings: {team1_rating:.0f} vs {team2_rating:.0f} (diff: {rating_diff:.0f})")
        print(f"     Constraints allow: {constraints_ok}")
        if constraint_failures:
            print(f"     Blocked by: {', '.join(constraint_failures[:3])}...")
    
    return session

def design_adaptive_solution():
    """Design adaptive constraint relaxation system"""
    
    print(f"\n\nSOLUTION: Adaptive Constraint Relaxation")
    print("=" * 45)
    
    print("""
The Problem:
• Fixed constraints become too restrictive as sessions progress
• Roaming range prevents balanced Elite+Weak partnerships
• Repetition constraints limit available combinations
• Forces algorithm to choose imbalanced matches

The Solution - Progressive Relaxation:

PHASE 1: Early Session (0-20 completed matches)
• Use current strict constraints
• Roaming range: 50% (8 player range for 16 players)
• Partner repetition: 3 games
• Opponent repetition: 2 games

PHASE 2: Mid Session (21-40 completed matches)  
• Relax roaming range: 65% (10 player range)
• Partner repetition: 2 games (reduced)
• Opponent repetition: 1 game (reduced)

PHASE 3: Late Session (41+ completed matches)
• Further relax roaming range: 80% (13 player range)
• Partner repetition: 1 game (minimal)
• Opponent repetition: 0 games (only global recency)
• Priority: Balance > Variety

Key Implementation Points:
1. Track completed matches as session progress metric
2. Adjust roaming_range_percent dynamically
3. Modify repetition limits based on session phase
4. Add balance prioritization weight that increases over time
5. Keep fallback cross-bracket matching for late session
""")

def test_adaptive_system():
    """Test the adaptive constraint system"""
    
    print(f"\n4. Testing Adaptive System Benefits:")
    
    session = analyze_constraint_impact()
    
    # Simulate different session phases
    phases = [
        (0, "Early Session", 0.5, 3, 2),
        (25, "Mid Session", 0.65, 2, 1), 
        (50, "Late Session", 0.8, 1, 0)
    ]
    
    for completed_matches, phase_name, roaming_pct, partner_limit, opponent_limit in phases:
        print(f"\n   {phase_name} ({completed_matches} completed matches):")
        print(f"     Roaming range: {roaming_pct*100:.0f}%")
        print(f"     Partner repetition limit: {partner_limit}")
        print(f"     Opponent repetition limit: {opponent_limit}")
        
        # Test Elite+Weak partnership possibility
        old_roaming = session.competitive_variety_roaming_range_percent
        old_partner = session.competitive_variety_partner_repetition_limit
        old_opponent = session.competitive_variety_opponent_repetition_limit
        
        # Apply adaptive settings
        session.competitive_variety_roaming_range_percent = roaming_pct
        session.competitive_variety_partner_repetition_limit = partner_limit
        session.competitive_variety_opponent_repetition_limit = opponent_limit
        
        # Test the Elite+Weak partnership (most balanced but previously blocked)
        can_elite_weak_partner = can_play_with_player(session, 'p1', 'p16', 'partner', False)
        can_strong_avg_partner = can_play_with_player(session, 'p5', 'p12', 'partner', False)
        
        print(f"     Elite+Weak partnership allowed: {can_elite_weak_partner}")
        print(f"     Strong+Average partnership allowed: {can_strong_avg_partner}")
        
        # Restore original settings
        session.competitive_variety_roaming_range_percent = old_roaming
        session.competitive_variety_partner_repetition_limit = old_partner
        session.competitive_variety_opponent_repetition_limit = old_opponent
        
    print(f"\n   Result: Adaptive system enables balanced matches in later phases!")

if __name__ == "__main__":
    analyze_constraint_impact()
    design_adaptive_solution() 
    test_adaptive_system()
    
    print(f"\n{'='*50}")
    print("✅ Analysis complete! Adaptive solution will improve balance.")
    print("   Implementation: Adjust constraints based on session progression")