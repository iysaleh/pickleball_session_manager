#!/usr/bin/env python3
"""
Test to analyze the scoring balance between ELO difference penalty and variety bonus.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session
from python.types import SessionConfig, PlayerStats, Player
from python.competitive_variety import score_potential_match, calculate_elo_rating

def create_test_session():
    """Create a session with varying ELO players."""
    
    players_data = [
        ('High1', 1900, 10, 2, 120, 80),     # Very high ELO
        ('High2', 1850, 9, 3, 115, 85),      # High ELO
        ('Mid1', 1600, 6, 6, 100, 100),      # Medium ELO
        ('Mid2', 1550, 5, 7, 95, 105),       # Medium-low ELO
        ('Low1', 1300, 3, 9, 80, 120),       # Low ELO
        ('Low2', 1250, 2, 10, 75, 125),      # Very low ELO
    ]
    
    players = []
    for name, _, _, _, _, _ in players_data:
        players.append(Player(id=name, name=name))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Update player stats
    for name, expected_elo, wins, losses, pts_for, pts_against in players_data:
        stats = session.player_stats[name]
        stats.wins = wins
        stats.games_played = wins + losses
        stats.total_points_for = pts_for
        stats.total_points_against = pts_against
        
        # Verify ELO calculation
        actual_elo = calculate_elo_rating(stats)
        print(f"{name}: {actual_elo:.0f}")
    
    return session

def test_scoring_weights():
    """Test how ELO balance vs variety affects scoring."""
    session = create_test_session()
    
    print("\nScoring Balance Analysis")
    print("=" * 60)
    
    # Test scenarios with different balance vs variety tradeoffs
    scenarios = [
        # (team1, team2, description)
        (['High1', 'High2'], ['Low1', 'Low2'], "Terrible Balance (both high vs both low)"),
        (['High1', 'Low1'], ['High2', 'Low2'], "Perfect Balance (high+low vs high+low)"),
        (['High1', 'Mid1'], ['High2', 'Mid2'], "Good Balance (high+mid vs high+mid)"),
        (['High1', 'Low2'], ['Mid1', 'Mid2'], "Fair Balance (mixed teams)"),
    ]
    
    for team1, team2, description in scenarios:
        score = score_potential_match(session, team1, team2)
        
        # Calculate components manually
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        rating_diff = abs(team1_rating - team2_rating)
        balance_penalty = -rating_diff * 2
        
        # Calculate variety bonus (simplified - assume all new opponents)
        variety_bonus = len(team1) * len(team2) * 10  # 4 opponent pairs × 10 = 40
        
        total_score = balance_penalty + variety_bonus
        
        print(f"\n{description}:")
        print(f"  Teams: {team1} vs {team2}")
        print(f"  Team ratings: {team1_rating:.0f} vs {team2_rating:.0f}")
        print(f"  Rating difference: {rating_diff:.0f}")
        print(f"  Balance penalty: {balance_penalty:.0f}")
        print(f"  Variety bonus (max): +{variety_bonus}")
        print(f"  Expected total: {total_score:.0f}")
        print(f"  Actual score: {score:.0f}")

def demonstrate_variety_overwhelm():
    """Show how variety bonus is overwhelmed by balance penalty."""
    print("\nVariety vs Balance Weight Analysis")
    print("=" * 50)
    
    rating_differences = [50, 100, 200, 500, 1000, 1500]
    max_variety_bonus = 4 * 10  # 4 opponent pairs × 10 points = 40
    
    print("Rating Diff | Balance Penalty | Max Variety | Net Score")
    print("-" * 55)
    
    for diff in rating_differences:
        balance_penalty = -diff * 2
        net_score = balance_penalty + max_variety_bonus
        print(f"{diff:10} | {balance_penalty:14} | {max_variety_bonus:11} | {net_score:8}")

if __name__ == "__main__":
    print("Scoring Balance Analysis Test")
    print("=" * 50)
    
    session = create_test_session()
    test_scoring_weights()
    demonstrate_variety_overwhelm()