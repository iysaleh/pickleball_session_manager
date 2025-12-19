#!/usr/bin/env python3
"""
Debug test to understand why balanced configurations might be rejected
by repetition constraints.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from python.session import create_session
from python.types import SessionConfig, PlayerStats, Player
from python.competitive_variety import can_play_with_player, score_potential_match

def create_session_with_history():
    """Create a session with match history that might cause constraint violations."""
    
    # Players from the problematic session
    players_data = [
        ('Ibraheem Saleh', 1871, 5, 1, 63, 33),
        ('David Laforest', 1844, 5, 1, 61, 46),
        ('Sheila B.', 1543, 2, 4, 44, 50),
        ('Ellie Farias', 1539, 2, 4, 45, 52),
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
    
    # Simulate previous matches that could create constraints
    # From the session file, we can see:
    # "Ibraheem Saleh, David Laforest: 11 beat Ellie Farias, Sheila B.: 5"
    # This means they've already played together recently!
    
    # Add some match history to simulate constraints
    # Game 1: Ibraheem + David vs Sheila + Ellie (the actual match from history)
    session.player_stats['Ibraheem Saleh'].partner_last_game['David Laforest'] = 1
    session.player_stats['David Laforest'].partner_last_game['Ibraheem Saleh'] = 1
    
    session.player_stats['Ibraheem Saleh'].opponent_last_game['Sheila B.'] = 1
    session.player_stats['Ibraheem Saleh'].opponent_last_game['Ellie Farias'] = 1
    session.player_stats['David Laforest'].opponent_last_game['Sheila B.'] = 1
    session.player_stats['David Laforest'].opponent_last_game['Ellie Farias'] = 1
    
    session.player_stats['Sheila B.'].partner_last_game['Ellie Farias'] = 1
    session.player_stats['Ellie Farias'].partner_last_game['Sheila B.'] = 1
    
    session.player_stats['Sheila B.'].opponent_last_game['Ibraheem Saleh'] = 1
    session.player_stats['Sheila B.'].opponent_last_game['David Laforest'] = 1
    session.player_stats['Ellie Farias'].opponent_last_game['Ibraheem Saleh'] = 1
    session.player_stats['Ellie Farias'].opponent_last_game['David Laforest'] = 1
    
    # Simulate we're now at game 2 (not enough gap for partner repetition)
    # Update games_played to simulate passage of time
    for name, _, _, _, _, _ in players_data:
        session.player_stats[name].games_played = 2  # Now at game 2
    
    return session

def debug_constraints():
    """Debug which constraints are blocking balanced configurations."""
    session = create_session_with_history()
    
    players = ['Ibraheem Saleh', 'David Laforest', 'Ellie Farias', 'Sheila B.']
    
    # Test all 3 possible configurations
    configs = [
        (['Ibraheem Saleh', 'David Laforest'], ['Ellie Farias', 'Sheila B.']),  # Unbalanced (was recent)
        (['Ibraheem Saleh', 'Ellie Farias'], ['David Laforest', 'Sheila B.']),  # Balanced option 1
        (['Ibraheem Saleh', 'Sheila B.'], ['David Laforest', 'Ellie Farias']),  # Balanced option 2
    ]
    
    print("Constraint Analysis:")
    print("=" * 80)
    
    for i, (team1, team2) in enumerate(configs):
        print(f"\nConfig {i+1}: {team1} vs {team2}")
        
        # Calculate balance score
        score = score_potential_match(session, team1, team2)
        print(f"  Balance Score: {score:.2f}")
        
        # Check partner constraints
        valid = True
        
        # Check team1 partners
        partner1_valid = can_play_with_player(session, team1[0], team1[1], 'partner')
        print(f"  Team1 Partners ({team1[0]} + {team1[1]}): {'✓' if partner1_valid else '✗'}")
        if not partner1_valid:
            valid = False
        
        # Check team2 partners  
        partner2_valid = can_play_with_player(session, team2[0], team2[1], 'partner')
        print(f"  Team2 Partners ({team2[0]} + {team2[1]}): {'✓' if partner2_valid else '✗'}")
        if not partner2_valid:
            valid = False
        
        # Check opponent constraints
        opponent_valid = True
        for p1 in team1:
            for p2 in team2:
                opp_ok = can_play_with_player(session, p1, p2, 'opponent')
                if not opp_ok:
                    print(f"    Opponent constraint violated: {p1} vs {p2}")
                    opponent_valid = False
        
        print(f"  All Opponents: {'✓' if opponent_valid else '✗'}")
        if not opponent_valid:
            valid = False
        
        print(f"  Overall Valid: {'✓' if valid else '✗'}")

if __name__ == "__main__":
    print("Constraints Debug Test")
    print("=" * 50)
    
    debug_constraints()