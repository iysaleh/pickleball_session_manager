#!/usr/bin/env python3
"""
Quick test to make sure the round robin function still works with the new signature
"""

from python.pickleball_types import Player
from python.roundrobin import generate_round_robin_queue

def test_basic_round_robin():
    """Test basic round robin generation without first bye"""
    print("Testing basic round robin generation...")
    
    # Create some players
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(8)]
    
    # Test doubles
    queue_doubles = generate_round_robin_queue(
        players=players,
        session_type='doubles',
        banned_pairs=[],
        max_matches=10
    )
    
    print(f"Doubles queue: {len(queue_doubles)} matches")
    for i, match in enumerate(queue_doubles[:3]):
        print(f"  Match {i+1}: {match.team1} vs {match.team2}")
    
    # Test singles
    queue_singles = generate_round_robin_queue(
        players=players,
        session_type='singles', 
        banned_pairs=[],
        max_matches=10
    )
    
    print(f"Singles queue: {len(queue_singles)} matches")
    for i, match in enumerate(queue_singles[:3]):
        print(f"  Match {i+1}: {match.team1} vs {match.team2}")
    
    return len(queue_doubles) > 0 and len(queue_singles) > 0

def test_with_first_bye():
    """Test round robin with first bye players"""
    print("\nTesting round robin with first bye...")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(8)]
    
    # Test with first bye
    queue_with_bye = generate_round_robin_queue(
        players=players,
        session_type='doubles',
        banned_pairs=[],
        max_matches=10,
        first_bye_players=['p0', 'p1']
    )
    
    print(f"With first bye: {len(queue_with_bye)} matches")
    for i, match in enumerate(queue_with_bye[:3]):
        print(f"  Match {i+1}: {match.team1} vs {match.team2}")
    
    # Check that p0 and p1 are not in any match
    first_bye_in_matches = False
    for match in queue_with_bye:
        all_players = match.team1 + match.team2
        if 'p0' in all_players or 'p1' in all_players:
            first_bye_in_matches = True
            break
    
    print(f"First bye players in matches: {first_bye_in_matches}")
    return not first_bye_in_matches


if __name__ == '__main__':
    print("=" * 50)
    print("TESTING ROUND ROBIN FUNCTION SIGNATURE")
    print("=" * 50)
    
    test1 = test_basic_round_robin()
    test2 = test_with_first_bye()
    
    if test1 and test2:
        print("\n✅ All round robin tests passed!")
    else:
        print("\n❌ Some tests failed!")
        print(f"Basic: {test1}, First bye: {test2}")