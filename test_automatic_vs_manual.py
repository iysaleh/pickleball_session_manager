#!/usr/bin/env python3
"""
Test what the automatic algorithm produces vs manual match creation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session
from python.pickleball_types import SessionConfig, PlayerStats, Player
from python.competitive_variety import populate_empty_courts_competitive_variety

def create_problematic_session():
    """Create session with the exact players from the problematic session."""
    
    # All players from the session with their exact ELOs
    players_data = [
        ('Patrick Carroll', 1879, 6, 1, 73, 40),
        ('Ibraheem Saleh', 1871, 5, 1, 63, 33), 
        ('David Laforest', 1844, 5, 1, 61, 46),
        ('Brandon S.', 1827, 5, 2, 66, 46),
        ('Niaz Ahmad', 1799, 5, 3, 72, 54),
        ('Ron Rea', 1773, 4, 2, 56, 51),
        ('Jeremy Estrada', 1635, 4, 4, 69, 70),
        ('Sheila B.', 1543, 2, 4, 44, 50),
        ('Ellie Farias', 1539, 2, 4, 45, 52),
        ('Brenda Rea', 1528, 2, 4, 46, 56),
        ('SKyler Hensley', 1477, 2, 5, 45, 71),
        ('Cleo Burgett', 1398, 1, 5, 35, 62),
        ('Robert Dillon', 1196, 0, 7, 28, 77),
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
    
    # Set 100% roaming range (as mentioned in the original issue)
    session.competitive_variety_roaming_range_percent = 1.0  # 100%
    
    # Update player stats with exact data
    for name, expected_elo, wins, losses, pts_for, pts_against in players_data:
        stats = session.player_stats[name]
        stats.wins = wins
        stats.games_played = wins + losses
        stats.total_points_for = pts_for
        stats.total_points_against = pts_against
    
    return session

def test_automatic_algorithm():
    """Test what matches the automatic algorithm would create."""
    session = create_problematic_session()
    
    print("Automatic Algorithm Test")
    print("=" * 50)
    print(f"Total players: {len(session.active_players)}")
    print(f"Roaming range: {session.competitive_variety_roaming_range_percent * 100}%")
    print()
    
    # Run the automatic algorithm
    populate_empty_courts_competitive_variety(session)
    
    print("Matches created by automatic algorithm:")
    print("-" * 40)
    
    from python.competitive_variety import calculate_elo_rating
    
    total_imbalance = 0
    for i, match in enumerate(session.matches):
        team1, team2 = match.team1, match.team2
        
        # Calculate team ratings
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        rating_diff = abs(team1_rating - team2_rating)
        total_imbalance += rating_diff
        
        print(f"Court {match.court_number}: {team1} vs {team2}")
        print(f"  Team ratings: {team1_rating:.0f} vs {team2_rating:.0f} (diff: {rating_diff:.0f})")
        
        # Classify balance
        if rating_diff < 50:
            balance = "Excellent"
        elif rating_diff < 150:
            balance = "Good"
        elif rating_diff < 300:
            balance = "Fair"
        elif rating_diff < 500:
            balance = "Poor"
        else:
            balance = "Terrible"
        
        print(f"  Balance: {balance}")
        print()
    
    if session.matches:
        avg_imbalance = total_imbalance / len(session.matches)
        print(f"Average imbalance: {avg_imbalance:.0f} points")
    else:
        print("No matches created!")
        print("Checking available players...")
        print(f"Available players: {session.waiting_players}")

def compare_with_problematic_matches():
    """Compare with the problematic matches from the session file."""
    print("\nComparison with Problematic Session")
    print("=" * 50)
    
    # The problematic matches from the session
    problematic_matches = [
        (['Ibraheem Saleh', 'Patrick Carroll'], ['Robert Dillon', 'SKyler Hensley']),
        (['Ibraheem Saleh', 'David Laforest'], ['Ellie Farias', 'Sheila B.']),
    ]
    
    session = create_problematic_session()
    from python.competitive_variety import calculate_elo_rating, score_potential_match
    
    print("Problematic matches from session file:")
    print("-" * 40)
    
    for i, (team1, team2) in enumerate(problematic_matches, 1):
        team1_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team1)
        team2_rating = sum(calculate_elo_rating(session.player_stats[p]) for p in team2)
        rating_diff = abs(team1_rating - team2_rating)
        
        score = score_potential_match(session, team1, team2)
        
        print(f"Match {i}: {team1} vs {team2}")
        print(f"  Team ratings: {team1_rating:.0f} vs {team2_rating:.0f} (diff: {rating_diff:.0f})")
        print(f"  Algorithm score: {score:.0f}")
        print()

if __name__ == "__main__":
    print("Automatic vs Manual Match Creation Test")
    print("=" * 60)
    
    test_automatic_algorithm()
    compare_with_problematic_matches()