#!/usr/bin/env python3
"""
Test to demonstrate the specific scenario where adaptive constraints help:
When repetition constraints prevent ANY match generation, forcing courts to stay empty.
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    can_play_with_player, populate_empty_courts_competitive_variety,
    apply_adaptive_constraints, get_adaptive_constraints
)
from python.utils import generate_id

def test_constraint_deadlock_scenario():
    """Test scenario where strict repetition constraints create match generation deadlock"""
    
    print("CONSTRAINT DEADLOCK TEST: When Strict Rules Prevent Match Generation")
    print("=" * 75)
    
    initialize_time_manager(test_mode=False)
    
    # 8 players - simpler scenario to create deadlock
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Set up mixed skill levels
    for i in range(1, 9):
        player_id = f'p{i}'
        stats = session.player_stats[player_id]
        
        if i <= 3:  # Strong players
            stats.games_played = 8
            stats.wins = 7
            stats.total_points_for = 105
            stats.total_points_against = 75
        elif i <= 6:  # Medium players
            stats.games_played = 8
            stats.wins = 4
            stats.total_points_for = 85
            stats.total_points_against = 85
        else:  # Weak players
            stats.games_played = 8
            stats.wins = 1
            stats.total_points_for = 75
            stats.total_points_against = 105
    
    # Create extensive partnership/opponent history to trigger constraints
    historical_partnerships = [
        # Round 1
        (['p1', 'p2'], ['p3', 'p4']),
        (['p5', 'p6'], ['p7', 'p8']),
        # Round 2  
        (['p1', 'p3'], ['p2', 'p4']),
        (['p5', 'p7'], ['p6', 'p8']),
        # Round 3
        (['p1', 'p4'], ['p2', 'p3']),
        (['p5', 'p8'], ['p6', 'p7']),
        # Round 4
        (['p2', 'p5'], ['p1', 'p6']),
        (['p3', 'p7'], ['p4', 'p8']),
        # Round 5
        (['p2', 'p6'], ['p1', 'p5']),
        (['p3', 'p8'], ['p4', 'p7']),
    ]
    
    print("Building extensive match history to create constraint deadlock...")
    
    match_id_counter = 0
    for team1, team2 in historical_partnerships:
        match_id_counter += 1
        match = Match(
            id=f"hist_{match_id_counter}",
            court_number=1,
            team1=team1,
            team2=team2,
            status='completed',
            start_time=None,
            end_time=None
        )
        session.matches.append(match)
        
        # Update player histories properly
        for p1 in team1:
            # Record partnerships
            for p2 in team1:
                if p1 != p2:
                    if p2 not in session.player_stats[p1].partners_played:
                        session.player_stats[p1].partners_played[p2] = []
                    session.player_stats[p1].partners_played[p2].append(match.id)
            
            # Record opponents
            for p2 in team2:
                if p2 not in session.player_stats[p1].opponents_played:
                    session.player_stats[p1].opponents_played[p2] = []
                session.player_stats[p1].opponents_played[p2].append(match.id)
        
        # Same for team2
        for p1 in team2:
            # Record partnerships
            for p2 in team2:
                if p1 != p2:
                    if p2 not in session.player_stats[p1].partners_played:
                        session.player_stats[p1].partners_played[p2] = []
                    session.player_stats[p1].partners_played[p2].append(match.id)
    
    print(f"Created {len(historical_partnerships)} historical matches")
    
    # Now test constraint compatibility
    print(f"\nChecking partnership possibilities with STRICT constraints:")
    
    # Set strict constraints
    session.competitive_variety_partner_repetition_limit = 3
    session.competitive_variety_opponent_repetition_limit = 2
    session.competitive_variety_roaming_range_percent = 0.65
    
    available_players = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8']
    valid_partnerships = 0
    total_partnerships = 0
    
    for i, p1 in enumerate(available_players):
        for p2 in available_players[i+1:]:
            total_partnerships += 1
            can_partner = can_play_with_player(session, p1, p2, 'partner')
            if can_partner:
                valid_partnerships += 1
                print(f"  ✓ {p1}-{p2} can partner")
            else:
                print(f"  ✗ {p1}-{p2} blocked by constraints")
    
    print(f"\nStrict Constraints Result: {valid_partnerships}/{total_partnerships} partnerships allowed")
    
    # Try to generate matches with strict constraints
    print(f"\nGenerating matches with STRICT constraints...")
    session_strict = create_session(config)
    session_strict.matches = session.matches.copy()
    session_strict.player_stats = session.player_stats.copy()
    session_strict.competitive_variety_partner_repetition_limit = 3
    session_strict.competitive_variety_opponent_repetition_limit = 2
    
    populate_empty_courts_competitive_variety(session_strict)
    strict_new_matches = [m for m in session_strict.matches if m.status == 'waiting']
    
    print(f"Strict constraints generated: {len(strict_new_matches)} matches")
    for match in strict_new_matches:
        print(f"  Court {match.court_number}: {match.team1} vs {match.team2}")
    
    # Now test with adaptive (relaxed) constraints
    print(f"\nChecking partnership possibilities with ADAPTIVE constraints:")
    
    # Apply adaptive constraints (simulate late session)
    for i in range(50):  # Add fake matches to trigger late session
        fake_match = Match(
            id=f"fake_{i}", court_number=1, team1=['p1', 'p2'], team2=['p3', 'p4'],
            status='completed', start_time=None, end_time=None
        )
        session.matches.append(fake_match)
    
    adaptive_constraints = get_adaptive_constraints(session)
    apply_adaptive_constraints(session)
    
    print(f"Adaptive constraints: Partner={adaptive_constraints['partner_repetition']}, Opponent={adaptive_constraints['opponent_repetition']}")
    
    valid_adaptive_partnerships = 0
    for i, p1 in enumerate(available_players):
        for p2 in available_players[i+1:]:
            can_partner = can_play_with_player(session, p1, p2, 'partner')
            if can_partner:
                valid_adaptive_partnerships += 1
    
    print(f"Adaptive Constraints Result: {valid_adaptive_partnerships}/{total_partnerships} partnerships allowed")
    
    # Generate matches with adaptive constraints
    print(f"\nGenerating matches with ADAPTIVE constraints...")
    session_adaptive = create_session(config)
    session_adaptive.matches = session.matches.copy()
    session_adaptive.player_stats = session.player_stats.copy()
    apply_adaptive_constraints(session_adaptive)
    
    populate_empty_courts_competitive_variety(session_adaptive)
    adaptive_new_matches = [m for m in session_adaptive.matches if m.status == 'waiting']
    
    print(f"Adaptive constraints generated: {len(adaptive_new_matches)} matches")
    for match in adaptive_new_matches:
        print(f"  Court {match.court_number}: {match.team1} vs {match.team2}")
    
    # Compare results
    print(f"\n" + "=" * 75)
    print("DEADLOCK RESOLUTION COMPARISON:")
    print("=" * 75)
    print(f"Strict Constraints:")
    print(f"  Valid partnerships: {valid_partnerships}/{total_partnerships}")
    print(f"  Matches generated: {len(strict_new_matches)}")
    print(f"  Courts filled: {len(strict_new_matches)}/2")
    
    print(f"\nAdaptive Constraints:")
    print(f"  Valid partnerships: {valid_adaptive_partnerships}/{total_partnerships}")
    print(f"  Matches generated: {len(adaptive_new_matches)}")
    print(f"  Courts filled: {len(adaptive_new_matches)}/2")
    
    improvement = len(adaptive_new_matches) - len(strict_new_matches)
    partnership_improvement = valid_adaptive_partnerships - valid_partnerships
    
    print(f"\nImprovement:")
    print(f"  Additional partnerships available: +{partnership_improvement}")
    print(f"  Additional matches generated: +{improvement}")
    
    if improvement > 0:
        print("✅ ADAPTIVE CONSTRAINTS RESOLVE DEADLOCK!")
        print("   By relaxing repetition constraints, courts can be filled when")
        print("   strict constraints would leave them empty.")
    elif improvement == 0:
        print("➖ NO DIFFERENCE in match generation")
    else:
        print("❌ UNEXPECTED RESULT")
    
    return improvement > 0

if __name__ == "__main__":
    test_constraint_deadlock_scenario()