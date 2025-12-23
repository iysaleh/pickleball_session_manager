#!/usr/bin/env python3
"""
Test script for pre-seeded ratings feature
"""

import sys
import random
from python.types import Player, SessionConfig
from python.session import create_session
from python.competitive_variety import calculate_player_elo_rating, get_adaptive_constraints


def test_pre_seeded_ratings():
    """Test the pre-seeded ratings functionality"""
    print("Testing Pre-seeded Ratings Feature")
    print("=" * 50)
    
    # Initialize time manager
    from python.time_manager import initialize_time_manager
    initialize_time_manager()
    
    # Create players with pre-seeded ratings
    players = [
        Player(id="player_1", name="Alice Elite", skill_rating=4.5),
        Player(id="player_2", name="Bob Strong", skill_rating=4.0),
        Player(id="player_3", name="Charlie Good", skill_rating=3.5),
        Player(id="player_4", name="Diana Average", skill_rating=3.25),
        Player(id="player_5", name="Eve Beginner", skill_rating=3.0),
        Player(id="player_6", name="Frank Elite2", skill_rating=4.25),
        Player(id="player_7", name="Grace Strong2", skill_rating=4.0),
        Player(id="player_8", name="Henry Good2", skill_rating=3.5),
    ]
    
    # Test 1: Create session with pre-seeded ratings
    print("\n1. Creating session with pre-seeded ratings...")
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        pre_seeded_ratings=True
    )
    
    session = create_session(config)
    print(f"✓ Session created with {len(session.active_players)} players")
    print(f"✓ Pre-seeded ratings enabled: {session.config.pre_seeded_ratings}")
    
    # Test 2: Check ELO ratings based on pre-seeded values
    print("\n2. Testing ELO rating calculations...")
    for player in players:
        elo_rating = calculate_player_elo_rating(session, player.id)
        expected_base = 1200 + (player.skill_rating - 3.0) * 600
        print(f"  {player.name} (skill: {player.skill_rating}) -> ELO: {elo_rating:.0f} (expected base: {expected_base:.0f})")
    
    # Test 3: Check adaptive constraints activation timing
    print("\n3. Testing adaptive constraints timing...")
    
    # Debug: Check threshold calculation
    from python.competitive_variety import calculate_session_thresholds
    thresholds = calculate_session_thresholds(session)
    print(f"  Session thresholds: early_to_mid={thresholds['early_to_mid']}, mid_to_late={thresholds['mid_to_late']}")
    print(f"  Current completed matches: {len([m for m in session.matches if m.status == 'completed'])}")
    
    # For pre-seeded sessions, adaptive should activate earlier
    constraints_early = get_adaptive_constraints(session)
    print(f"  Early phase constraints: Partner={constraints_early['partner_repetition']}, Opponent={constraints_early['opponent_repetition']}, Balance={constraints_early['balance_weight']}")
    
    # Simulate some completed matches
    from python.types import Match
    from python.time_manager import now
    
    # Add 2 completed matches (should trigger adaptive constraints for pre-seeded)
    for i in range(2):
        match = Match(
            id=f"match_{i}",
            court_number=1,
            team1=[players[i*2].id, players[i*2+1].id],
            team2=[players[i*2+2].id, players[i*2+3].id],
            status='completed',
            start_time=now(),
            end_time=now()
        )
        session.matches.append(match)
    
    print(f"  After adding matches, completed count: {len([m for m in session.matches if m.status == 'completed'])}")
    
    constraints_mid = get_adaptive_constraints(session)
    print(f"  After 2 matches: Partner={constraints_mid['partner_repetition']}, Opponent={constraints_mid['opponent_repetition']}, Balance={constraints_mid['balance_weight']}")
    
    # Let's add more matches to trigger the transition
    for i in range(2, 4):  # Add 2 more matches
        match = Match(
            id=f"match_{i}",
            court_number=1,
            team1=[players[i*2 % 8].id, players[(i*2+1) % 8].id],
            team2=[players[(i*2+2) % 8].id, players[(i*2+3) % 8].id],
            status='completed',
            start_time=now(),
            end_time=now()
        )
        session.matches.append(match)
    
    print(f"  After 4 matches, completed count: {len([m for m in session.matches if m.status == 'completed'])}")
    constraints_later = get_adaptive_constraints(session)
    print(f"  After 4 matches: Partner={constraints_later['partner_repetition']}, Opponent={constraints_later['opponent_repetition']}, Balance={constraints_later['balance_weight']}")
    
    if constraints_later['balance_weight'] > constraints_early['balance_weight']:
        print("✓ Adaptive constraints activated for pre-seeded session")
    else:
        print("✗ Adaptive constraints did not activate as expected")
    
    # Test 4: Compare with non-pre-seeded session
    print("\n4. Comparing with non-pre-seeded session...")
    
    # Create similar players without pre-seeded ratings
    non_seeded_players = [
        Player(id=f"ns_player_{i}", name=f"Player{i}")
        for i in range(8)
    ]
    
    non_seeded_config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=non_seeded_players,
        courts=2,
        pre_seeded_ratings=False
    )
    
    non_seeded_session = create_session(non_seeded_config)
    
    # Add same number of matches
    for i in range(2):
        match = Match(
            id=f"ns_match_{i}",
            court_number=1,
            team1=[non_seeded_players[i*2].id, non_seeded_players[i*2+1].id],
            team2=[non_seeded_players[i*2+2].id, non_seeded_players[i*2+3].id],
            status='completed',
            start_time=now(),
            end_time=now()
        )
        non_seeded_session.matches.append(match)
    
    non_seeded_constraints = get_adaptive_constraints(non_seeded_session)
    print(f"  Non-seeded after 2 matches: Balance={non_seeded_constraints['balance_weight']}")
    
    if constraints_mid['balance_weight'] > non_seeded_constraints['balance_weight']:
        print("✓ Pre-seeded session has higher balance weight than non-seeded at same point")
    else:
        print("✗ Pre-seeded session balance weight not higher than expected")
    
    print("\n5. Testing skill rating to ELO conversion...")
    test_conversions = [
        (3.0, 1200),
        (3.5, 1500), 
        (4.0, 1800),
        (4.5, 2100),
        (5.0, 2200)
    ]
    
    for skill_rating, expected_elo in test_conversions:
        # Create a temp player to test conversion
        temp_player = Player(id="temp", name="Temp", skill_rating=skill_rating)
        temp_players = [temp_player]
        temp_config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=temp_players,
            courts=1,
            pre_seeded_ratings=True
        )
        temp_session = create_session(temp_config)
        actual_elo = calculate_player_elo_rating(temp_session, temp_player.id)
        
        print(f"  Skill {skill_rating} -> ELO {actual_elo:.0f} (expected {expected_elo})")
        
        if abs(actual_elo - expected_elo) <= 10:  # Allow small rounding differences
            print("    ✓ Conversion correct")
        else:
            print("    ✗ Conversion incorrect")
    
    print("\n" + "=" * 50)
    print("Pre-seeded Ratings Test Complete!")


if __name__ == "__main__":
    test_pre_seeded_ratings()