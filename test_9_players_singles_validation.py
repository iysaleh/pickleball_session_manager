#!/usr/bin/env python3
"""
Test that validates the total number of matches generated for 9 players in singles round robin.
This reproduces the bug where first bye implementation reduced the total match count.
"""

from python.pickleball_types import SessionConfig, Player
from python.session import create_session, evaluate_and_create_matches
from python.time_manager import initialize_time_manager
import math

def calculate_expected_singles_matches(num_players):
    """Calculate expected number of matches for singles round robin"""
    # In singles round robin, each player plays every other player once
    # Total matches = C(n,2) = n*(n-1)/2
    return (num_players * (num_players - 1)) // 2

def test_9_players_singles_round_robin():
    """Test that 9 players generate exactly 36 matches in singles round robin"""
    print("Testing 9 players singles round robin total match count...")
    
    initialize_time_manager()
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(9)]
    expected_matches = calculate_expected_singles_matches(9)
    print(f"Expected total matches for 9 players: {expected_matches}")
    
    # Test without first bye
    config_no_bye = SessionConfig(
        mode='round-robin',
        session_type='singles',
        players=players,
        courts=4,
        first_bye_players=[]
    )
    
    session_no_bye = create_session(config_no_bye)
    evaluate_and_create_matches(session_no_bye)
    
    total_matches_no_bye = len(session_no_bye.matches) + len(session_no_bye.match_queue)
    print(f"Without first bye: {len(session_no_bye.matches)} on courts + {len(session_no_bye.match_queue)} queued = {total_matches_no_bye} total")
    
    # Test with first bye
    config_with_bye = SessionConfig(
        mode='round-robin',
        session_type='singles',
        players=players,
        courts=4,
        first_bye_players=['p0']
    )
    
    session_with_bye = create_session(config_with_bye)
    evaluate_and_create_matches(session_with_bye)
    
    total_matches_with_bye = len(session_with_bye.matches) + len(session_with_bye.match_queue)
    print(f"With first bye (p0): {len(session_with_bye.matches)} on courts + {len(session_with_bye.match_queue)} queued = {total_matches_with_bye} total")
    
    print(f"\nWaiting players without bye: {session_no_bye.waiting_players}")
    print(f"Waiting players with bye: {session_with_bye.waiting_players}")
    
    # Check results
    success = True
    if total_matches_no_bye != expected_matches:
        print(f"❌ FAILED: Without first bye should have {expected_matches} matches, got {total_matches_no_bye}")
        success = False
    else:
        print(f"✅ PASSED: Without first bye has correct {expected_matches} matches")
    
    if total_matches_with_bye != expected_matches:
        print(f"❌ FAILED: With first bye should have {expected_matches} matches, got {total_matches_with_bye}")
        success = False
    else:
        print(f"✅ PASSED: With first bye has correct {expected_matches} matches")
    
    return success

def test_check_queue_contents():
    """Check what's in the queue to debug the issue"""
    print("\n" + "="*60)
    print("DEBUGGING QUEUE CONTENTS")
    print("="*60)
    
    initialize_time_manager()
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(9)]
    
    config_with_bye = SessionConfig(
        mode='round-robin',
        session_type='singles',
        players=players,
        courts=4,
        first_bye_players=['p0']
    )
    
    session = create_session(config_with_bye)
    
    print("Match queue contents:")
    for i, match in enumerate(session.match_queue):
        print(f"  {i+1}: {match.team1[0]} vs {match.team2[0]}")
    
    print(f"\nTotal queue size: {len(session.match_queue)}")
    
    # Check which players are in the queue
    players_in_queue = set()
    for match in session.match_queue:
        players_in_queue.update(match.team1 + match.team2)
    
    print(f"Players in queue: {sorted(players_in_queue)}")
    print(f"Players NOT in queue: {sorted(set([f'p{i}' for i in range(9)]) - players_in_queue)}")

if __name__ == '__main__':
    print("=" * 70)
    print("TESTING 9 PLAYERS SINGLES ROUND ROBIN MATCH COUNT")
    print("=" * 70)
    
    success = test_9_players_singles_round_robin()
    test_check_queue_contents()
    
    if success:
        print("\n✅ All match count tests passed!")
    else:
        print("\n❌ Match count tests failed - bug detected!")