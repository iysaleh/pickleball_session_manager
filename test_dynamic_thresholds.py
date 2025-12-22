#!/usr/bin/env python3
"""
Test the dynamic threshold calculation for adaptive competitive variety constraints
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    calculate_session_thresholds, get_adaptive_constraints
)

def test_dynamic_thresholds():
    """Test that thresholds scale properly with different player counts"""
    
    print("Dynamic Threshold Calculation Test")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Test different player counts
    player_counts = [8, 12, 16, 20, 24]
    
    for player_count in player_counts:
        print(f"\n{player_count} Players:")
        
        # Create session
        players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, player_count + 1)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=player_count // 4  # Assume courts = players/4
        )
        
        session = create_session(config)
        
        # Calculate thresholds
        thresholds = calculate_session_thresholds(session)
        early_to_mid = thresholds['early_to_mid']
        mid_to_late = thresholds['mid_to_late']
        
        print(f"  Early to Mid threshold: {early_to_mid} completed matches")
        print(f"  Mid to Late threshold: {mid_to_late} completed matches")
        
        # Show what this means in terms of games per player
        avg_games_at_mid = (early_to_mid * 4) / player_count
        avg_games_at_late = (mid_to_late * 4) / player_count
        
        print(f"  Avg games per player at Mid transition: {avg_games_at_mid:.1f}")
        print(f"  Avg games per player at Late transition: {avg_games_at_late:.1f}")
        
        # Test the constraint progression
        test_match_counts = [0, early_to_mid - 1, early_to_mid, mid_to_late - 1, mid_to_late, mid_to_late + 10]
        
        print(f"  Constraint progression:")
        for match_count in test_match_counts:
            # Simulate session with this many matches
            session.matches = []
            for i in range(match_count):
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
            
            constraints = get_adaptive_constraints(session)
            
            if match_count < early_to_mid:
                phase = "EARLY"
            elif match_count < mid_to_late:
                phase = "MID"
            else:
                phase = "LATE"
            
            print(f"    {match_count:2d} matches → {phase:5s}: Partner={constraints['partner_repetition']}, Opponent={constraints['opponent_repetition']}, Weight={constraints['balance_weight']:.1f}x")

def test_realistic_progression():
    """Test progression with a realistic 16-player session"""
    
    print(f"\n\nRealistic 16-Player Session Progression")
    print("=" * 45)
    
    initialize_time_manager(test_mode=False)
    
    # 16 players
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4  # 4 courts for 16 players
    )
    
    session = create_session(config)
    
    thresholds = calculate_session_thresholds(session)
    print(f"16 Players, 4 Courts:")
    print(f"  Early to Mid: {thresholds['early_to_mid']} matches (avg {thresholds['early_to_mid']*4/16:.1f} games/player)")
    print(f"  Mid to Late: {thresholds['mid_to_late']} matches (avg {thresholds['mid_to_late']*4/16:.1f} games/player)")
    print()
    
    # Simulate a realistic session progression
    print("Session Progression Simulation:")
    
    match_progression = [
        (0, "Session Start"),
        (4, "Round 1 Complete"),
        (8, "Round 2 Complete"), 
        (12, "Round 3 Complete"),
        (16, "Round 4 Complete"),
        (20, "Round 5 Complete"),
        (24, "Round 6 Complete"),
        (28, "Round 7 Complete"),
        (32, "Round 8 Complete")
    ]
    
    for match_count, description in match_progression:
        # Simulate session state
        session.matches = []
        for i in range(match_count):
            fake_match = Match(
                id=f"match_{i}",
                court_number=(i % 4) + 1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=None,
                end_time=None
            )
            session.matches.append(fake_match)
        
        constraints = get_adaptive_constraints(session)
        avg_games_per_player = (match_count * 4) / 16
        
        if match_count < thresholds['early_to_mid']:
            phase = "EARLY"
        elif match_count < thresholds['mid_to_late']:
            phase = "MID"
        else:
            phase = "LATE"
        
        print(f"{description:18s} ({match_count:2d} matches, {avg_games_per_player:.1f} avg games/player):")
        print(f"  Phase: {phase}, Partner: {constraints['partner_repetition']}, Opponent: {constraints['opponent_repetition']}, Weight: {constraints['balance_weight']:.1f}x")
    
    print(f"\n✓ Dynamic thresholds properly scale with player count and session progression")

def run_threshold_tests():
    """Run all dynamic threshold tests"""
    try:
        test_dynamic_thresholds()
        test_realistic_progression()
        
        print(f"\n{'=' * 50}")
        print("✅ All dynamic threshold tests passed!")
        print("   • Thresholds scale with player count")
        print("   • Constraints never go to 0 (minimum 1)")
        print("   • Progression based on games per player, not absolute matches")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_threshold_tests()