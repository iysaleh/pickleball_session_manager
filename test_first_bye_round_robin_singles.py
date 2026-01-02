#!/usr/bin/env python3
"""
Test first bye feature specifically for singles round robin mode.
The issue: Singles round robin doesn't respect first bye players.
"""

from python.pickleball_types import SessionConfig, Player
from python.session import create_session, evaluate_and_create_matches
from python.time_manager import initialize_time_manager
from python.roundrobin import generate_round_robin_queue


def test_singles_round_robin_first_bye():
    """Test that first bye works in singles round robin mode"""
    print("Testing singles round robin with first bye...")
    
    # Initialize time manager
    initialize_time_manager()
    
    # Create 7 players (odd number) so someone has to wait
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(7)]
    
    # Test 1: Without first bye (baseline)
    config_no_bye = SessionConfig(
        mode='round-robin',
        session_type='singles',
        players=players,
        courts=3,  # 3 courts = 6 players playing, 1 waiting
        first_bye_players=[]
    )
    
    session_no_bye = create_session(config_no_bye)
    evaluate_and_create_matches(session_no_bye)
    
    print(f"Without first bye: {len(session_no_bye.matches)} matches created")
    print("Players in matches:", [match.team1[0] + " vs " + match.team2[0] for match in session_no_bye.matches])
    
    # Test 2: With first bye (p0 should sit out first round)
    config_with_bye = SessionConfig(
        mode='round-robin',
        session_type='singles',
        players=players,
        courts=3,  # 3 courts = 6 players playing, 1 waiting
        first_bye_players=['p0']
    )
    
    session_with_bye = create_session(config_with_bye)
    evaluate_and_create_matches(session_with_bye)
    
    print(f"\nWith first bye (p0): {len(session_with_bye.matches)} matches created")
    print("Players in matches:", [match.team1[0] + " vs " + match.team2[0] for match in session_with_bye.matches])
    
    # Check if p0 is in any match (should not be)
    p0_in_matches = False
    for match in session_with_bye.matches:
        if 'p0' in match.team1 or 'p0' in match.team2:
            p0_in_matches = True
            break
    
    print(f"p0 in matches: {p0_in_matches}")
    
    if p0_in_matches:
        print("❌ FAILED: p0 (first bye) is playing in first round!")
        return False
    else:
        print("✅ PASSED: p0 (first bye) is correctly sitting out first round!")
        return True


def test_round_robin_queue_generation_with_first_bye():
    """Test the round robin queue generation directly"""
    print("\n" + "="*50)
    print("Testing round robin queue generation with first bye...")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(7)]
    
    # Test direct queue generation
    queue_no_bye = generate_round_robin_queue(
        players=players,
        session_type='singles',
        banned_pairs=[],
        max_matches=10
    )
    
    print(f"Queue without first bye filtering: {len(queue_no_bye)} matches")
    for i, match in enumerate(queue_no_bye[:5]):  # Show first 5
        print(f"  Match {i+1}: {match.team1[0]} vs {match.team2[0]}")
    
    # The issue is likely that round robin queue generation doesn't 
    # take first_bye_players into account at all!
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("TESTING FIRST BYE IN SINGLES ROUND ROBIN")
    print("=" * 60)
    
    success1 = test_singles_round_robin_first_bye()
    success2 = test_round_robin_queue_generation_with_first_bye()
    
    if success1 and success2:
        print("\n✅ All tests completed!")
    else:
        print("\n❌ Some tests failed - first bye not working in singles round robin")