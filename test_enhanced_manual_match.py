#!/usr/bin/env python3
"""
Test the enhanced manual match creation with balance analysis.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session, create_manual_match
from python.types import SessionConfig, PlayerStats, Player

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

def test_enhanced_manual_match():
    """Test the enhanced manual match creation."""
    session = create_test_session()
    
    print("Enhanced Manual Match Creation Test")
    print("=" * 60)
    
    # Test 1: Create the problematic imbalanced match
    print("\n1. Creating problematic match (Ibraheem + Patrick vs Robert + SKyler):")
    result = create_manual_match(session, 1, 
                               ['Ibraheem Saleh', 'Patrick Carroll'], 
                               ['Robert Dillon', 'SKyler Hensley'])
    
    print(f"   Success: {result['success']}")
    if result['success']:
        analysis = result['balance_analysis']
        print(f"   Balance Quality: {analysis['balance_quality']}")
        print(f"   Rating Difference: {analysis['rating_difference']:.0f}")
        print(f"   Is Imbalanced: {analysis['is_imbalanced']}")
        
        if analysis['alternative_configs']:
            print(f"   {len(analysis['alternative_configs'])} better alternatives available:")
            for i, alt in enumerate(analysis['alternative_configs']):
                print(f"      {i+1}. {alt['team1']} vs {alt['team2']} (diff: {alt['rating_difference']:.0f})")
    
    # Test 2: Create a balanced match
    print("\n2. Creating balanced match (Ibraheem + Sheila vs David + Ellie):")
    result2 = create_manual_match(session, 2,
                                ['Ibraheem Saleh', 'Sheila B.'],
                                ['David Laforest', 'Ellie Farias'])
    
    print(f"   Success: {result2['success']}")
    if result2['success']:
        analysis2 = result2['balance_analysis']
        print(f"   Balance Quality: {analysis2['balance_quality']}")
        print(f"   Rating Difference: {analysis2['rating_difference']:.0f}")
        print(f"   Is Imbalanced: {analysis2['is_imbalanced']}")
    
    # Test 3: Try invalid match (duplicate player)
    print("\n3. Testing invalid match (duplicate player):")
    result3 = create_manual_match(session, 3,
                                ['Ibraheem Saleh', 'Ibraheem Saleh'],
                                ['David Laforest', 'Ellie Farias'])
    
    print(f"   Success: {result3['success']}")
    if not result3['success']:
        print(f"   Error: {result3['error']}")
    
    # Test 4: Check that matches were actually created
    print(f"\n4. Matches created in session: {len(session.matches)}")
    for i, match in enumerate(session.matches):
        print(f"   Match {i+1} on Court {match.court_number}: {match.team1} vs {match.team2}")

def test_balance_warnings():
    """Test that the system provides appropriate warnings for different balance levels."""
    session = create_test_session()
    
    print("\nBalance Warning Levels Test")
    print("=" * 50)
    
    test_matches = [
        # Excellent balance
        (['Ibraheem Saleh', 'Sheila B.'], ['David Laforest', 'Ellie Farias'], "Excellent"),
        # Terrible balance
        (['Ibraheem Saleh', 'Patrick Carroll'], ['Robert Dillon', 'SKyler Hensley'], "Terrible"),
        # Fair balance
        (['Patrick Carroll', 'Robert Dillon'], ['Ibraheem Saleh', 'SKyler Hensley'], "Fair"),
    ]
    
    for i, (team1, team2, expected_level) in enumerate(test_matches, 1):
        result = create_manual_match(session, i, team1, team2)
        if result['success']:
            analysis = result['balance_analysis']
            print(f"{i}. {team1} vs {team2}")
            print(f"   Expected: {expected_level}, Actual: {analysis['balance_quality'].title()}")
            print(f"   Rating Diff: {analysis['rating_difference']:.0f}")
            if analysis['alternative_configs']:
                print(f"   {len(analysis['alternative_configs'])} alternatives suggested")
            print()

if __name__ == "__main__":
    test_enhanced_manual_match()
    test_balance_warnings()