#!/usr/bin/env python3
"""
Demonstration of Enhanced Balance Constraints in Action - CORRECTED VERSION

This shows a realistic session where the old system would create imbalanced matches
but the new enhanced balance constraints system prevents them while encouraging
HOMOGENEOUS partnerships (Elite+Elite, Strong+Strong, etc.)
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    calculate_elo_rating, populate_empty_courts_competitive_variety,
    apply_adaptive_constraints, get_adaptive_constraints
)
from datetime import datetime

def demonstrate_corrected_balance_improvement():
    """Show how enhanced balance constraints improve match quality with CORRECT strategy"""
    
    print("ENHANCED BALANCE CONSTRAINTS DEMONSTRATION - CORRECTED")
    print("=" * 60)
    print()
    print("As a staff-level expert with years of observing pickleball sessions,")
    print("here's the CORRECT smart balance strategy we implement:")
    print()
    print("✅ GOOD: Elite vs Elite, Strong vs Strong, Average vs Average")
    print("❌ BAD: Elite+Weak partnerships (creates 'carry' dynamic)")
    print()
    
    initialize_time_manager(test_mode=False)
    
    # Create realistic 12-player session with mixed skills
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles', 
        players=players,
        courts=3
    )
    
    session = create_session(config)
    
    # Set up realistic skill distribution
    skill_setup = [
        # Elite players (4.5+ level)
        (1, 2, 15, 13, 150, 80),
        # Strong players (4.0 level)  
        (3, 5, 12, 9, 125, 95),
        # Average players (3.5 level)
        (6, 8, 10, 6, 105, 105),
        # Developing players (3.0 level)
        (9, 11, 8, 3, 85, 125),
        # Beginner player (2.5 level)
        (12, 12, 6, 1, 70, 140)
    ]
    
    print("🎾 REALISTIC PLAYER SKILL DISTRIBUTION:")
    for start, end, games, wins, points_for, points_against in skill_setup:
        for i in range(start, end + 1):
            player_id = f'p{i}'
            stats = session.player_stats[player_id]
            stats.games_played = games
            stats.wins = wins
            stats.total_points_for = points_for
            stats.total_points_against = points_against
    
    # Show actual ratings
    for i in range(1, 13):
        player_id = f'p{i}'
        rating = calculate_elo_rating(session.player_stats[player_id])
        level = ("Elite (4.5+)" if i <= 2 else 
                "Strong (4.0)" if i <= 5 else
                "Average (3.5)" if i <= 8 else
                "Developing (3.0)" if i <= 11 else
                "Beginner (2.5)")
        print(f"  {player_id}: {rating:.0f} ELO - {level}")
    print()
    
    # Show what NOT to do (mismatched partnerships)
    print("❌ PROBLEMATIC MATCHES (what we want to AVOID):")
    
    bad_matches = [
        (["p1", "p12"], ["p2", "p11"], "Elite+Beginner partnerships"),   # Creates 'carry' dynamic
        (["p3", "p10"], ["p4", "p9"], "Strong+Developing partnerships"), # Imbalanced within teams
        (["p1", "p2"], ["p11", "p12"], "Elite vs Beginners"),           # Severe skill gap
    ]
    
    # Simulate late session for maximum balance constraints
    session.matches = []
    for i in range(25):
        fake_match = Match(
            id=f"sim_{i}",
            court_number=1,
            team1=['p1', 'p2'],
            team2=['p3', 'p4'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    apply_adaptive_constraints(session)
    constraints = get_adaptive_constraints(session)
    
    from python.competitive_variety import score_potential_match, meets_balance_constraints
    
    for team1, team2, description in bad_matches:
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        imbalance = abs(team1_rating - team2_rating)
        
        meets_threshold = meets_balance_constraints(session, team1, team2)
        score = score_potential_match(session, team1, team2)
        
        print(f"   {description}: {team1} vs {team2}")
        print(f"   Team ratings: {team1_rating:.0f} vs {team2_rating:.0f} (imbalance: {imbalance:.0f})")
        print(f"   Meets threshold: {meets_threshold} | Score: {score:.0f} ({'BLOCKED' if score <= -5000 else 'ALLOWED'})")
        print()
    
    # Show what TO do (homogeneous partnerships)
    print("✅ ENHANCED BALANCE CONSTRAINTS SOLUTION:")
    print()
    
    print(f"🎯 CURRENT SESSION STATE (Late Phase):")
    print(f"   Balance weight: {constraints['balance_weight']:.1f}x (balance highly prioritized)")
    print(f"   Partner constraints: {constraints['partner_repetition']} games")
    print(f"   Opponent constraints: {constraints['opponent_repetition']} games")
    print()
    
    # Show preferred matches
    good_matches = [
        (["p1", "p2"], ["p3", "p4"], "Elite vs Strong (homogeneous partnerships)"),
        (["p5", "p6"], ["p7", "p8"], "Strong vs Average (homogeneous partnerships)"),
        (["p9", "p10"], ["p11", "p12"], "Developing vs Beginner (homogeneous partnerships)"),
    ]
    
    print("🚀 PREFERRED MATCHES (homogeneous partnerships):")
    for team1, team2, description in good_matches:
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        imbalance = abs(team1_rating - team2_rating)
        
        meets_threshold = meets_balance_constraints(session, team1, team2)
        score = score_potential_match(session, team1, team2)
        
        # Check partnership homogeneity
        team1_ratings = [calculate_elo_rating(session.player_stats[p]) for p in team1]
        team2_ratings = [calculate_elo_rating(session.player_stats[p]) for p in team2]
        team1_range = max(team1_ratings) - min(team1_ratings)
        team2_range = max(team2_ratings) - min(team2_ratings)
        
        print(f"   {description}: {team1} vs {team2}")
        print(f"   Team ratings: {team1_rating:.0f} vs {team2_rating:.0f} (imbalance: {imbalance:.0f})")
        print(f"   Partnership skill ranges: {team1_range:.0f}, {team2_range:.0f}")
        print(f"   Score: {score:.0f} ({'HIGH SCORE - PREFERRED' if score > 0 else 'NEUTRAL'})")
        print()
    
    print("💡 KEY IMPROVEMENTS IMPLEMENTED:")
    print()
    print("1. 🎯 HARD BALANCE THRESHOLDS:")
    print("   • Early session: ≤400 rating points team difference allowed")
    print("   • Mid session:   ≤300 rating points difference allowed") 
    print("   • Late session:  ≤200 rating points difference allowed")
    print("   • Severely imbalanced matches automatically rejected")
    print()
    print("2. 🤝 HOMOGENEOUS PARTNERSHIP BONUS:")
    print("   • Rewards Elite+Elite, Strong+Strong partnerships")
    print("   • Penalties for Elite+Weak 'carry' partnerships")
    print("   • Creates fair competition at appropriate skill levels")
    print()
    print("3. 📈 SKILL TIER MATCHING BONUS:")
    print("   • Elite vs Elite gets highest scores")
    print("   • Strong vs Strong, Average vs Average preferred")
    print("   • Cross-tier matches (Elite vs Weak) heavily penalized")
    print()
    print("4. ⚖️ SMART TRADEOFF MANAGEMENT:")
    print("   • Early: Allow variety exploration across skill levels")
    print("   • Mid: Balance variety with homogeneous partnerships")
    print("   • Late: Prioritize similar-skill partnerships and fair competition")
    print()
    print("🏆 RESULT: Competitive matches at appropriate skill levels!")
    print("   • Elite players get challenging Elite opponents")
    print("   • Developing players get appropriate competition")
    print("   • No more 'carry' partnerships that frustrate both partners")

if __name__ == "__main__":
    demonstrate_corrected_balance_improvement()