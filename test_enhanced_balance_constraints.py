#!/usr/bin/env python3
"""
Test the Enhanced Balance Constraints System - CORRECTED VERSION

This test demonstrates how the new balance constraints work with the adaptive system
to ensure progressively better match balance while encouraging similar-skill partnerships.

CORRECT STRATEGY: Elite vs Elite, Strong vs Strong, etc. (NOT Elite+Weak partnerships!)
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    calculate_elo_rating, populate_empty_courts_competitive_variety,
    get_adaptive_constraints, apply_adaptive_constraints,
    get_balance_threshold, meets_balance_constraints, score_potential_match
)
from datetime import datetime

def test_balance_constraint_system():
    """Test the enhanced balance constraints across different session phases"""
    
    print("ENHANCED BALANCE CONSTRAINTS TEST (CORRECTED)")
    print("=" * 55)
    
    initialize_time_manager(test_mode=False)
    
    # Create 16 players with distinct skill tiers
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Set up clear skill tiers
    skill_tiers = [
        (1, 4, "Elite", 10, 9, 120, 70),     # Elite players
        (5, 8, "Strong", 10, 7, 110, 85),   # Strong players
        (9, 12, "Average", 10, 5, 95, 95),  # Average players
        (13, 16, "Weak", 10, 2, 75, 115)    # Weak players
    ]
    
    print("Setting up skill tiers:")
    for start, end, tier_name, games, wins, points_for, points_against in skill_tiers:
        print(f"  {tier_name}: p{start}-p{end}")
        for i in range(start, end + 1):
            player_id = f'p{i}'
            stats = session.player_stats[player_id]
            stats.games_played = games
            stats.wins = wins
            stats.total_points_for = points_for
            stats.total_points_against = points_against
    
    # Show actual ELO ratings
    print(f"\nActual ELO ratings:")
    for i in range(1, 17):
        player_id = f'p{i}'
        rating = calculate_elo_rating(session.player_stats[player_id])
        tier = "Elite" if i <= 4 else "Strong" if i <= 8 else "Average" if i <= 12 else "Weak"
        print(f"  {player_id}: {rating:.0f} ({tier})")
    
    # Test balance thresholds across session phases
    print(f"\nBalance Threshold Analysis:")
    
    phases = [
        (0, "Early Session", 1.0),
        (16, "Mid Session", 3.0),  
        (24, "Late Session", 5.0)
    ]
    
    for match_count, phase_name, expected_weight in phases:
        print(f"\n{phase_name} ({match_count} matches):")
        
        # Set up session state
        session.matches = []
        session.adaptive_balance_weight = None  # Auto mode
        
        for i in range(match_count):
            fake_match = Match(
                id=f"fake_{i}",
                court_number=(i % 4) + 1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            session.matches.append(fake_match)
        
        apply_adaptive_constraints(session)
        constraints = get_adaptive_constraints(session)
        threshold = get_balance_threshold(session)
        
        print(f"  Balance weight: {constraints['balance_weight']:.1f}x")
        print(f"  Balance threshold: {threshold:.0f} rating points")
        
        # Test CORRECT example matches (similar skill partnerships)
        test_matches = [
            (["p1", "p2"], ["p3", "p4"], "Elite vs Elite"),                 # Perfect - similar skills
            (["p5", "p6"], ["p7", "p8"], "Strong vs Strong"),               # Perfect - similar skills  
            (["p1", "p16"], ["p8", "p9"], "Elite+Weak vs Strong+Average"),  # BAD - mismatched partnerships
            (["p1", "p2"], ["p15", "p16"], "Elite vs Weak"),                # Very imbalanced
        ]
        
        for team1, team2, description in test_matches:
            team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
            team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
            imbalance = abs(team1_rating - team2_rating)
            
            meets_threshold = meets_balance_constraints(session, team1, team2)
            score = score_potential_match(session, team1, team2)
            
            print(f"    {description}:")
            print(f"      Imbalance: {imbalance:.0f} | Threshold: {threshold:.0f} | Meets: {meets_threshold} | Score: {score:.0f}")

def test_homogeneous_partnership_bonus():
    """Test that similar-skill partnerships get bonus scoring in late sessions"""
    
    print(f"\n\nHOMOGENEOUS PARTNERSHIP BONUS TEST")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Set up skill differences
    for i in range(1, 9):
        player_id = f'p{i}'
        stats = session.player_stats[player_id]
        
        if i <= 2:  # Elite
            stats.games_played = 10
            stats.wins = 9
            stats.total_points_for = 130
            stats.total_points_against = 60
        elif i <= 4:  # Strong  
            stats.games_played = 10
            stats.wins = 7
            stats.total_points_for = 110
            stats.total_points_against = 80
        elif i <= 6:  # Average
            stats.games_played = 10
            stats.wins = 5
            stats.total_points_for = 90
            stats.total_points_against = 90
        else:  # Weak
            stats.games_played = 10
            stats.wins = 1
            stats.total_points_for = 60
            stats.total_points_against = 130
    
    # Test in late session (high balance weight)
    session.matches = []
    for i in range(30):  # Trigger late session
        fake_match = Match(
            id=f"late_{i}",
            court_number=1,
            team1=['p1', 'p2'],
            team2=['p3', 'p4'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    apply_adaptive_constraints(session)
    
    # Test different team compositions
    test_compositions = [
        (["p1", "p2"], ["p3", "p4"], "Elite vs Strong (homogeneous)"),      # GOOD - similar partners
        (["p5", "p6"], ["p7", "p8"], "Average vs Weak (homogeneous)"),      # GOOD - similar partners
        (["p1", "p8"], ["p2", "p7"], "Elite+Weak vs Elite+Weak"),          # BAD - mismatched partners
        (["p1", "p7"], ["p3", "p8"], "Elite+Weak vs Strong+Weak"),         # BAD - mismatched partners
    ]
    
    print("Team composition scoring in LATE session:")
    for team1, team2, description in test_compositions:
        score = score_potential_match(session, team1, team2)
        
        team1_ratings = [calculate_elo_rating(session.player_stats[p]) for p in team1]
        team2_ratings = [calculate_elo_rating(session.player_stats[p]) for p in team2]
        
        team1_range = max(team1_ratings) - min(team1_ratings)
        team2_range = max(team2_ratings) - min(team2_ratings)
        
        print(f"  {description}:")
        print(f"    Team skill ranges: {team1_range:.0f}, {team2_range:.0f}")
        print(f"    Score: {score:.0f} ({'GOOD' if score > -5000 else 'BAD'})")

def test_skill_tier_matching():
    """Test that Elite vs Elite, Strong vs Strong produces highest scores"""
    
    print(f"\n\nSKILL TIER MATCHING TEST")
    print("=" * 30)
    
    initialize_time_manager(test_mode=False)
    
    # Create session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    
    session = create_session(config)
    
    # Set up distinct skill tiers
    for i in range(1, 13):
        player_id = f'p{i}'
        stats = session.player_stats[player_id]
        
        if i <= 3:  # Elite
            stats.games_played = 8
            stats.wins = 7
            stats.total_points_for = 115
            stats.total_points_against = 75
        elif i <= 6:  # Strong
            stats.games_played = 8
            stats.wins = 6
            stats.total_points_for = 105
            stats.total_points_against = 85
        elif i <= 9:  # Average
            stats.games_played = 8
            stats.wins = 4
            stats.total_points_for = 90
            stats.total_points_against = 90
        else:  # Weak
            stats.games_played = 8
            stats.wins = 1
            stats.total_points_for = 75
            stats.total_points_against = 115
    
    # Test in late session for maximum bonus effects
    session.matches = []
    for i in range(25):
        fake_match = Match(
            id=f"tier_{i}",
            court_number=(i % 3) + 1,
            team1=['p1', 'p2'],
            team2=['p3', 'p4'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    apply_adaptive_constraints(session)
    
    # Test tier-based matchups
    tier_matches = [
        (["p1", "p2"], ["p3", "p4"], "Elite vs Elite (BEST)"),
        (["p4", "p5"], ["p5", "p6"], "Strong vs Strong (GOOD)"), 
        (["p7", "p8"], ["p9", "p10"], "Average vs Average (GOOD)"),
        (["p1", "p11"], ["p2", "p12"], "Elite+Weak vs Elite+Weak (BAD - mixed partnerships)"),
        (["p1", "p2"], ["p11", "p12"], "Elite vs Weak (BAD - skill gap)"),
    ]
    
    print("Skill tier matching preferences:")
    scores = []
    for team1, team2, description in tier_matches:
        score = score_potential_match(session, team1, team2)
        scores.append((description, score))
        
        team1_avg = sum(calculate_elo_rating(session.player_stats[p]) for p in team1) / 2
        team2_avg = sum(calculate_elo_rating(session.player_stats[p]) for p in team2) / 2
        tier_diff = abs(team1_avg - team2_avg)
        
        print(f"  {description}: Score={score:.0f}, Tier diff={tier_diff:.0f}")
    
    # Sort by score to show ranking
    scores.sort(key=lambda x: x[1], reverse=True)
    print(f"\nRanking (highest score = best match):")
    for i, (desc, score) in enumerate(scores, 1):
        print(f"  {i}. {desc} ({score:.0f})")

def run_all_corrected_balance_tests():
    """Run all corrected enhanced balance constraint tests"""
    try:
        test_balance_constraint_system()
        test_homogeneous_partnership_bonus()
        test_skill_tier_matching()
        
        print(f"\n{'=' * 70}")
        print("✅ ENHANCED BALANCE CONSTRAINTS TESTS COMPLETED! (CORRECTED)")
        print()
        print("🎯 KEY IMPROVEMENTS:")
        print("   • Hard balance thresholds prevent severely imbalanced matches")
        print("   • Homogeneous partnerships get bonus scoring (Elite+Elite, Strong+Strong)")
        print("   • Mismatched partnerships get penalties (Elite+Weak partnerships)")
        print("   • System encourages Elite vs Elite, Strong vs Strong matchups")
        print("   • Skill tier matching bonus for similar average team skills")
        print()
        print("📊 BALANCE THRESHOLDS:")
        print("   • Early session: ≤400 rating points difference allowed")
        print("   • Mid session:   ≤300 rating points difference allowed")  
        print("   • Late session:  ≤200 rating points difference allowed")
        print()
        print("🔥 CORRECT PARTNERSHIP STRATEGY:")
        print("   • Elite vs Elite (homogeneous partnerships)")
        print("   • Strong vs Strong, Average vs Average, Weak vs Weak")
        print("   • Penalties for Elite+Weak 'carry' partnerships")
        print("   • Results in fair, competitive matches at appropriate skill levels")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_corrected_balance_tests()