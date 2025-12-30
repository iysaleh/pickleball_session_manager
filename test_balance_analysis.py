#!/usr/bin/env python3
"""
Test the new balance analysis function for manual match creation.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session, analyze_match_balance
from python.pickleball_types import SessionConfig, PlayerStats, Player

def create_test_session():
    """Create a session with the problematic players."""
    
    # Players from the problematic session
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
    
    # Update player stats
    for name, expected_elo, wins, losses, pts_for, pts_against in players_data:
        stats = session.player_stats[name]
        stats.wins = wins
        stats.games_played = wins + losses
        stats.total_points_for = pts_for
        stats.total_points_against = pts_against
    
    return session

def test_balance_analysis():
    """Test the balance analysis function."""
    session = create_test_session()
    
    print("Balance Analysis Test")
    print("=" * 60)
    
    # Test the problematic match: Ibraheem + Patrick vs Robert + SKyler
    print("\n1. Testing problematic match (Ibraheem + Patrick vs Robert + SKyler):")
    analysis = analyze_match_balance(session, 
                                   ['Ibraheem Saleh', 'Patrick Carroll'], 
                                   ['Robert Dillon', 'SKyler Hensley'])
    
    print(f"   Team Ratings: {analysis['team1_rating']:.0f} vs {analysis['team2_rating']:.0f}")
    print(f"   Rating Difference: {analysis['rating_difference']:.0f}")
    print(f"   Balance Quality: {analysis['balance_quality']}")
    print(f"   Is Imbalanced: {analysis['is_imbalanced']}")
    print(f"   Constraints Violated: {len(analysis['constraints_violated'])}")
    print(f"   Alternative Configs: {len(analysis['alternative_configs'])}")
    
    if analysis['alternative_configs']:
        print("   Suggested Alternatives:")
        for i, alt in enumerate(analysis['alternative_configs']):
            print(f"      {i+1}. {alt['team1']} vs {alt['team2']}")
            print(f"         Rating Diff: {alt['rating_difference']:.0f}, Valid: {alt['valid']}")
    
    # Test a balanced match
    print("\n2. Testing balanced match (Ibraheem + Sheila vs David + Ellie):")
    analysis2 = analyze_match_balance(session,
                                    ['Ibraheem Saleh', 'Sheila B.'],
                                    ['David Laforest', 'Ellie Farias'])
    
    print(f"   Team Ratings: {analysis2['team1_rating']:.0f} vs {analysis2['team2_rating']:.0f}")
    print(f"   Rating Difference: {analysis2['rating_difference']:.0f}")
    print(f"   Balance Quality: {analysis2['balance_quality']}")
    print(f"   Is Imbalanced: {analysis2['is_imbalanced']}")
    
    # Test with 4 players to see all alternatives
    print("\n3. Testing with 4 imbalanced players to see alternatives:")
    analysis3 = analyze_match_balance(session,
                                    ['Ibraheem Saleh', 'David Laforest'],
                                    ['Ellie Farias', 'Sheila B.'])
    
    print(f"   Original: Rating Diff: {analysis3['rating_difference']:.0f}, Quality: {analysis3['balance_quality']}")
    
    if analysis3['alternative_configs']:
        print("   Alternatives found:")
        for i, alt in enumerate(analysis3['alternative_configs']):
            print(f"      {i+1}. {alt['team1']} vs {alt['team2']}")
            print(f"         Rating Diff: {alt['rating_difference']:.0f} (vs {analysis3['rating_difference']:.0f} original)")
            print(f"         Valid: {alt['valid']}")

if __name__ == "__main__":
    test_balance_analysis()