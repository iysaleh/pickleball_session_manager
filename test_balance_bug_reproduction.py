#!/usr/bin/env python3
"""
Test to reproduce the balance bug where highly skilled players are paired together
against low skilled players instead of being balanced across teams.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from python.session import Session
from python.types import SessionConfig, PlayerStats
from python.competitive_variety import populate_empty_courts_competitive_variety, score_potential_match

def create_test_session():
    """Create a session that reproduces the balance bug."""
    from python.types import Player
    from python.session import create_session
    
    # Add players with exact ELOs from the problematic session
    players_data = [
        ('Patrick Carroll', 1879, 6, 1, 73, 40),
        ('Ibraheem Saleh', 1871, 5, 1, 63, 33),
        ('David Laforest', 1844, 5, 1, 61, 46),
        ('Sheila B.', 1543, 2, 4, 44, 50),
        ('Ellie Farias', 1539, 2, 4, 45, 52),
        ('Robert Dillon', 1196, 0, 7, 28, 77),
        ('SKyler Hensley', 1477, 2, 5, 45, 71),
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
    
    # Update player stats with exact data from the session
    for name, expected_elo, wins, losses, pts_for, pts_against in players_data:
        stats = session.player_stats[name]
        stats.wins = wins
        stats.games_played = wins + losses
        stats.total_points_for = pts_for
        stats.total_points_against = pts_against
        
        # Verify ELO calculation
        from python.competitive_variety import calculate_elo_rating
        actual_elo = calculate_elo_rating(stats)
        print(f"{name}: Expected {expected_elo}, Actual {actual_elo:.1f}")
    
    return session

def test_balance_scenarios():
    """Test different team configurations to see which scores highest."""
    session = create_test_session()
    
    # The problematic players from the session
    players = ['Ibraheem Saleh', 'David Laforest', 'Ellie Farias', 'Sheila B.']
    
    # Test all 3 possible configurations
    configs = [
        (['Ibraheem Saleh', 'David Laforest'], ['Ellie Farias', 'Sheila B.']),  # Actual (bad)
        (['Ibraheem Saleh', 'Ellie Farias'], ['David Laforest', 'Sheila B.']),  
        (['Ibraheem Saleh', 'Sheila B.'], ['David Laforest', 'Ellie Farias']),  # Should be best
    ]
    
    print("\nTesting team configurations:")
    print("=" * 80)
    
    for i, (team1, team2) in enumerate(configs):
        score = score_potential_match(session, team1, team2)
        
        # Calculate team ratings
        from python.competitive_variety import calculate_elo_rating
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        rating_diff = abs(team1_rating - team2_rating)
        
        print(f"Config {i+1}: {team1[0]} + {team1[1]} vs {team2[0]} + {team2[1]}")
        print(f"  Team ratings: {team1_rating:.1f} vs {team2_rating:.1f} (diff: {rating_diff:.1f})")
        print(f"  Score: {score:.2f}")
        print()

def test_actual_matching():
    """Test what the actual matching algorithm produces."""
    session = create_test_session()
    
    print("\nTesting actual matching algorithm:")
    print("=" * 50)
    
    # Clear any existing matches
    session.matches.clear()
    
    # Run the matching algorithm
    populate_empty_courts_competitive_variety(session)
    
    # Show what matches were created
    for i, match in enumerate(session.matches):
        team1, team2 = match.team1, match.team2
        print(f"Match {i+1}: {team1} vs {team2}")
        
        # Calculate balance
        from python.competitive_variety import calculate_elo_rating
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        rating_diff = abs(team1_rating - team2_rating)
        
        print(f"  Team ratings: {team1_rating:.1f} vs {team2_rating:.1f} (diff: {rating_diff:.1f})")

if __name__ == "__main__":
    print("Balance Bug Reproduction Test")
    print("=" * 50)
    
    session = create_test_session()
    test_balance_scenarios()
    test_actual_matching()