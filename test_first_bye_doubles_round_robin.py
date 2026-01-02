#!/usr/bin/env python3
"""
Test first bye feature specifically for doubles round robin mode.
"""

from python.pickleball_types import SessionConfig, Player
from python.session import create_session, evaluate_and_create_matches
from python.time_manager import initialize_time_manager


def test_doubles_round_robin_first_bye():
    """Test that first bye works in doubles round robin mode"""
    print("Testing doubles round robin with first bye...")
    
    # Initialize time manager
    initialize_time_manager()
    
    # Create 12 players so we have 8 playing (2 courts) and 4 waiting
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    
    # Test with first bye (p0, p1 should sit out first round)
    config_with_bye = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=2,  # 2 courts = 8 players playing, 4 waiting
        first_bye_players=['p0', 'p1']
    )
    
    session_with_bye = create_session(config_with_bye)
    evaluate_and_create_matches(session_with_bye)
    
    print(f"With first bye (p0, p1): {len(session_with_bye.matches)} matches created")
    all_players_in_matches = set()
    for match in session_with_bye.matches:
        print(f"  Match: {match.team1} vs {match.team2}")
        all_players_in_matches.update(match.team1 + match.team2)
    
    # Check if p0 and p1 are in any match (should not be)
    p0_in_matches = 'p0' in all_players_in_matches
    p1_in_matches = 'p1' in all_players_in_matches
    
    print(f"p0 in matches: {p0_in_matches}")
    print(f"p1 in matches: {p1_in_matches}")
    
    if p0_in_matches or p1_in_matches:
        print("❌ FAILED: First bye players are playing in first round!")
        return False
    else:
        print("✅ PASSED: First bye players are correctly sitting out first round!")
        return True


if __name__ == '__main__':
    print("=" * 60)
    print("TESTING FIRST BYE IN DOUBLES ROUND ROBIN")
    print("=" * 60)
    
    success = test_doubles_round_robin_first_bye()
    
    if success:
        print("\n✅ Doubles round robin first bye test completed successfully!")
    else:
        print("\n❌ Doubles round robin first bye test failed!")