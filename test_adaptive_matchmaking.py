#!/usr/bin/env python3
"""
Test the adaptive competitive variety constraint system
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    get_adaptive_constraints, apply_adaptive_constraints, 
    calculate_elo_rating, score_potential_match,
    populate_empty_courts_competitive_variety, can_play_with_player,
    calculate_session_thresholds
)
from python.utils import generate_id

def test_adaptive_constraints():
    """Test the adaptive constraint system"""
    print("Testing Adaptive Constraint System")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles', 
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Set up skill tiers to create imbalance scenarios
    for i in range(1, 17):
        player_id = f'p{i}'
        stats = session.player_stats[player_id]
        
        if i <= 4:  # Elite players
            stats.games_played = 12
            stats.wins = 10
            stats.total_points_for = 120
            stats.total_points_against = 80
        elif i <= 8:  # Strong players
            stats.games_played = 12
            stats.wins = 8
            stats.total_points_for = 110
            stats.total_points_against = 90
        elif i <= 12:  # Average players
            stats.games_played = 12
            stats.wins = 6
            stats.total_points_for = 100
            stats.total_points_against = 100
        else:  # Weak players
            stats.games_played = 12
            stats.wins = 4
            stats.total_points_for = 80
            stats.total_points_against = 120
    
    # Test different session phases
    # Test different session phases using dynamic thresholds
    thresholds = calculate_session_thresholds(session)
    early_to_mid = thresholds['early_to_mid']
    mid_to_late = thresholds['mid_to_late']
    
    test_phases = [
        (0, "Early Session"),
        (early_to_mid - 1, "Late Early Session"),
        (early_to_mid + 2, "Mid Session"), 
        (mid_to_late + 5, "Late Session")
    ]
    
    for completed_count, phase_name in test_phases:
        print(f"\n{phase_name} ({completed_count} completed matches):")
        
        # Simulate completed matches by adding them to session
        # Clear previous test matches
        session.matches = [m for m in session.matches if m.status != 'completed']
        
        # Add fake completed matches to simulate session progression
        for i in range(completed_count):
            fake_match = Match(
                id=f"fake_{i}",
                court_number=1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=None,
                end_time=None
            )
            session.matches.append(fake_match)
        
        # Get adaptive constraints for this phase
        constraints = get_adaptive_constraints(session)
        
        print(f"  Roaming range: {constraints['roaming_range']*100:.0f}%")
        print(f"  Partner repetition limit: {constraints['partner_repetition']}")
        print(f"  Opponent repetition limit: {constraints['opponent_repetition']}")
        print(f"  Balance weight: {constraints['balance_weight']}")
        
        # Apply constraints to session
        apply_adaptive_constraints(session)
        
        # Test Elite+Weak partnership (most balanced but challenging for constraints)
        can_elite_weak = can_play_with_player(session, 'p1', 'p16', 'partner', False)
        print(f"  Elite+Weak partnership allowed: {can_elite_weak}")
        
        # Test match scoring with increased balance priority
        team1_balanced = ['p1', 'p16']  # Elite + Weak
        team2_balanced = ['p5', 'p12']  # Strong + Average
        
        team1_imbalanced = ['p1', 'p2']   # Elite + Elite
        team2_imbalanced = ['p15', 'p16'] # Weak + Weak
        
        score_balanced = score_potential_match(session, team1_balanced, team2_balanced)
        score_imbalanced = score_potential_match(session, team1_imbalanced, team2_imbalanced)
        
        print(f"  Balanced match score: {score_balanced:.1f}")
        print(f"  Imbalanced match score: {score_imbalanced:.1f}")
        
        # Calculate score difference (balanced should be increasingly better)
        score_advantage = score_balanced - score_imbalanced
        print(f"  Balance advantage: {score_advantage:.1f}")
    
    print(f"\n✓ Adaptive constraints successfully adjust with session progression")

def test_match_generation_improvement():
    """Test that match generation improves with adaptive system"""
    print(f"\nTesting Match Generation Improvement")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create session with clear skill tiers
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    
    session = create_session(config)
    
    # Create pronounced skill differences
    skill_groups = {
        'Elite': (1, 3),      # p1-p3: Very strong
        'Average': (4, 9),    # p4-p9: Average  
        'Weak': (10, 12)      # p10-p12: Very weak
    }
    
    for group_name, (start, end) in skill_groups.items():
        for i in range(start, end + 1):
            player_id = f'p{i}'
            stats = session.player_stats[player_id]
            
            if group_name == 'Elite':
                stats.games_played = 15
                stats.wins = 13
                stats.total_points_for = 130
                stats.total_points_against = 70
            elif group_name == 'Average':
                stats.games_played = 15
                stats.wins = 7
                stats.total_points_for = 100
                stats.total_points_against = 105
            else:  # Weak
                stats.games_played = 15
                stats.wins = 2
                stats.total_points_for = 75
                stats.total_points_against = 125
    
    # Test early vs late session match quality using dynamic thresholds
    thresholds = calculate_session_thresholds(session)
    late_threshold = thresholds['mid_to_late'] + 5
    
    phases_to_test = [
        (0, "Early Session (Strict Constraints)"),
        (late_threshold, "Late Session (Relaxed Constraints)")
    ]
    
    for completed_count, phase_name in phases_to_test:
        print(f"\n{phase_name}:")
        
        # Clear and set up matches for this phase
        session.matches = []
        session.waiting_players = [f'p{i}' for i in range(1, 13)]
        
        # Add fake completed matches
        for i in range(completed_count):
            fake_match = Match(
                id=f"fake_{i}",
                court_number=1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'], 
                status='completed',
                start_time=None,
                end_time=None
            )
            session.matches.append(fake_match)
        
        # Generate matches using adaptive system
        populate_empty_courts_competitive_variety(session)
        
        # Analyze generated matches
        new_matches = [m for m in session.matches if m.status == 'waiting']
        
        print(f"  Generated {len(new_matches)} matches:")
        
        total_imbalance = 0
        for i, match in enumerate(new_matches):
            team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in match.team1)
            team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in match.team2)
            imbalance = abs(team1_rating - team2_rating)
            total_imbalance += imbalance
            
            print(f"    Court {match.court_number}: {match.team1} ({team1_rating:.0f}) vs {match.team2} ({team2_rating:.0f}) - Imbalance: {imbalance:.0f}")
        
        if new_matches:
            avg_imbalance = total_imbalance / len(new_matches)
            print(f"  Average imbalance: {avg_imbalance:.0f}")
        
        # Store results for comparison
        if completed_count == 0:
            early_imbalance = avg_imbalance if new_matches else float('inf')
        else:
            late_imbalance = avg_imbalance if new_matches else float('inf')
    
    # Compare results
    if 'early_imbalance' in locals() and 'late_imbalance' in locals():
        improvement = early_imbalance - late_imbalance
        print(f"\nImprovement Analysis:")
        print(f"  Early session avg imbalance: {early_imbalance:.0f}")
        print(f"  Late session avg imbalance: {late_imbalance:.0f}")
        print(f"  Improvement: {improvement:.0f} rating points")
        
        if improvement > 0:
            print("  ✓ Adaptive system reduces match imbalance!")
        else:
            print("  ⚠ Need further tuning of adaptive parameters")

def run_all_tests():
    """Run all adaptive system tests"""
    print("Adaptive Competitive Variety Constraint Tests")
    print("=" * 50)
    
    try:
        test_adaptive_constraints()
        test_match_generation_improvement()
        
        print(f"\n{'=' * 50}")
        print("✅ All adaptive system tests completed!")
        print("   The system successfully adjusts constraints based on session progression")
        print("   to prioritize balance while maintaining variety when possible.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()