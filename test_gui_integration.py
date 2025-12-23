#!/usr/bin/env python3
"""
Quick test of GUI pre-seeded functionality (without actually running GUI)
"""

import sys
from python.types import Player, SessionConfig
from python.session import create_session
from python.time_manager import initialize_time_manager


def test_gui_integration():
    """Test the GUI-related functionality without starting the actual GUI"""
    print("Testing GUI Integration for Pre-seeded Ratings")
    print("=" * 50)
    
    initialize_time_manager()
    
    # Test 1: SessionConfig with pre_seeded_ratings flag
    print("\n1. Testing SessionConfig with pre_seeded_ratings flag...")
    
    players = [
        Player(id="p1", name="Alice", skill_rating=4.0),
        Player(id="p2", name="Bob", skill_rating=3.5),
        Player(id="p3", name="Charlie", skill_rating=3.25),
        Player(id="p4", name="Diana", skill_rating=4.25),
    ]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1,
        pre_seeded_ratings=True  # This should work
    )
    
    print(f"✓ SessionConfig created with pre_seeded_ratings: {config.pre_seeded_ratings}")
    
    # Test 2: Session creation with pre-seeded config
    print("\n2. Testing Session creation with pre-seeded config...")
    session = create_session(config)
    print(f"✓ Session created successfully")
    print(f"✓ Session config pre_seeded_ratings: {session.config.pre_seeded_ratings}")
    
    # Test 3: ELO calculations with pre-seeded ratings
    print("\n3. Testing ELO calculations...")
    from python.competitive_variety import calculate_player_elo_rating
    
    for player in players:
        elo = calculate_player_elo_rating(session, player.id)
        expected_base = 1200 + (player.skill_rating - 3.0) * 600
        print(f"  {player.name} (skill: {player.skill_rating}) -> ELO: {elo:.0f} (expected: {expected_base:.0f})")
        
        # Verify the ELO matches the expected base rating (since no games played yet)
        if abs(elo - expected_base) < 1:
            print(f"    ✓ ELO calculation correct")
        else:
            print(f"    ✗ ELO calculation incorrect")
    
    # Test 4: Session persistence integration
    print("\n4. Testing session persistence...")
    from python.session_persistence import save_player_history, load_player_history_with_ratings
    
    # Save player history with pre-seeded ratings
    player_names = [p.name for p in players]
    save_player_history(
        player_names, 
        first_bye_players=[],
        players_with_ratings=players,
        pre_seeded=True
    )
    print("✓ Player history saved with pre-seeded ratings")
    
    # Load player history back
    loaded_history = load_player_history_with_ratings()
    print(f"✓ Player history loaded: pre_seeded={loaded_history['pre_seeded']}")
    print(f"✓ Player ratings loaded: {loaded_history['player_ratings']}")
    
    # Verify the loaded ratings match what we saved
    all_ratings_correct = True
    for player in players:
        if player.name in loaded_history['player_ratings']:
            saved_rating = loaded_history['player_ratings'][player.name]
            if abs(saved_rating - player.skill_rating) < 0.01:
                print(f"    ✓ {player.name}: {saved_rating} (correct)")
            else:
                print(f"    ✗ {player.name}: {saved_rating} != {player.skill_rating}")
                all_ratings_correct = False
        else:
            print(f"    ✗ {player.name}: rating not found in saved data")
            all_ratings_correct = False
    
    if all_ratings_correct:
        print("✓ All player ratings saved and loaded correctly")
    else:
        print("✗ Some player ratings were not saved/loaded correctly")
    
    print("\n" + "=" * 50)
    print("GUI Integration Test Complete!")


if __name__ == "__main__":
    test_gui_integration()