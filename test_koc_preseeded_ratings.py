#!/usr/bin/env python3

"""
Test King of Court with pre-seeded skill ratings for seeding modes that require them
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from python.pickleball_types import Player, SessionConfig, KingOfCourtConfig
from python.session import create_session
from python.kingofcourt import calculate_player_rating
from python.time_manager import initialize_time_manager


def test_koc_with_preseeded_ratings():
    """Test King of Court seeding with pre-seeded skill ratings"""
    print("=== Testing King of Court with Pre-seeded Ratings ===")
    initialize_time_manager()
    
    # Create players with different skill ratings
    players = [
        Player("player_1", "Expert Player", skill_rating=4.5),
        Player("player_2", "Advanced Player", skill_rating=4.0),  
        Player("player_3", "Intermediate Player", skill_rating=3.5),
        Player("player_4", "Beginner Player", skill_rating=3.0),
        Player("player_5", "Expert Player 2", skill_rating=4.25),
        Player("player_6", "Advanced Player 2", skill_rating=3.75),
        Player("player_7", "Intermediate Player 2", skill_rating=3.25),
        Player("player_8", "Beginner Player 2", skill_rating=2.75),
    ]
    
    # Test highest to lowest seeding
    print("\n--- Testing Highest to Lowest Seeding ---")
    koc_config = KingOfCourtConfig(
        seeding_option='highest_to_lowest',
        court_ordering=[1, 2]
    )
    
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=2,
        pre_seeded_ratings=True,  # Enable pre-seeded ratings
        king_of_court_config=koc_config
    )
    
    session = create_session(config)
    
    # Analyze court assignments
    court_1_players = []
    court_2_players = []
    
    for match in session.matches:
        if match.court_number == 1:
            court_1_players.extend(match.team1 + match.team2)
        elif match.court_number == 2:
            court_2_players.extend(match.team1 + match.team2)
    
    print(f"Court 1 (Kings) players: {[p for p in players if p.id in court_1_players]}")
    print(f"Court 2 (Bottom) players: {[p for p in players if p.id in court_2_players]}")
    
    # Check that higher-rated players are on Court 1
    court_1_ratings = [p.skill_rating for p in players if p.id in court_1_players]
    court_2_ratings = [p.skill_rating for p in players if p.id in court_2_players]
    
    avg_court_1_rating = sum(court_1_ratings) / len(court_1_ratings)
    avg_court_2_rating = sum(court_2_ratings) / len(court_2_ratings)
    
    print(f"Court 1 average rating: {avg_court_1_rating:.2f}")
    print(f"Court 2 average rating: {avg_court_2_rating:.2f}")
    
    assert avg_court_1_rating > avg_court_2_rating, "Court 1 should have higher average rating"
    print("✓ Highest to lowest seeding working correctly")
    
    # Test lowest to highest seeding  
    print("\n--- Testing Lowest to Highest Seeding ---")
    koc_config_reverse = KingOfCourtConfig(
        seeding_option='lowest_to_highest',
        court_ordering=[1, 2]
    )
    
    config_reverse = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=2,
        pre_seeded_ratings=True,
        king_of_court_config=koc_config_reverse
    )
    
    session_reverse = create_session(config_reverse)
    
    # Analyze court assignments for reverse
    court_1_players_rev = []
    court_2_players_rev = []
    
    for match in session_reverse.matches:
        if match.court_number == 1:
            court_1_players_rev.extend(match.team1 + match.team2)
        elif match.court_number == 2:
            court_2_players_rev.extend(match.team1 + match.team2)
    
    print(f"Court 1 (Kings) players: {[p for p in players if p.id in court_1_players_rev]}")
    print(f"Court 2 (Bottom) players: {[p for p in players if p.id in court_2_players_rev]}")
    
    # Check that lower-rated players are on Court 1 (reverse seeding)
    court_1_ratings_rev = [p.skill_rating for p in players if p.id in court_1_players_rev]
    court_2_ratings_rev = [p.skill_rating for p in players if p.id in court_2_players_rev]
    
    avg_court_1_rating_rev = sum(court_1_ratings_rev) / len(court_1_ratings_rev)
    avg_court_2_rating_rev = sum(court_2_ratings_rev) / len(court_2_ratings_rev)
    
    print(f"Court 1 average rating: {avg_court_1_rating_rev:.2f}")
    print(f"Court 2 average rating: {avg_court_2_rating_rev:.2f}")
    
    assert avg_court_1_rating_rev < avg_court_2_rating_rev, "Court 1 should have lower average rating in reverse seeding"
    print("✓ Lowest to highest seeding working correctly")
    
    # Test that random seeding doesn't require pre-seeded ratings
    print("\n--- Testing Random Seeding (No Pre-seeded Ratings) ---")
    players_no_ratings = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    
    koc_config_random = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2]
    )
    
    config_random = SessionConfig(
        mode='king-of-court',
        session_type='doubles', 
        players=players_no_ratings,
        courts=2,
        pre_seeded_ratings=False,  # No pre-seeded ratings
        king_of_court_config=koc_config_random
    )
    
    session_random = create_session(config_random)
    assert len(session_random.matches) == 2, "Random seeding should work without skill ratings"
    print("✓ Random seeding works without pre-seeded ratings")


if __name__ == "__main__":
    test_koc_with_preseeded_ratings()
    print("\n🎉 All King of Court pre-seeded rating tests passed!")