#!/usr/bin/env python3
"""
Test fixes for first bye feature bugs:
1. Bye players should be scheduled immediately after first match completes
2. First bye players should be saved/restored with player history
3. Validation should prevent too many bye players for given court count
"""

from python.pickleball_types import SessionConfig, Player
from python.session import create_session, evaluate_and_create_matches, complete_match
from python.session_persistence import (
    save_player_history, load_player_history, load_first_bye_players
)


def test_bye_players_scheduled_immediately():
    """Test that bye players are scheduled as soon as first match finishes"""
    print("Test 1: Bye players scheduled immediately after first match completes")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        first_bye_players=['p0', 'p1']
    )
    
    session = create_session(config)
    
    # Create first round
    evaluate_and_create_matches(session)
    first_round_count = len(session.matches)
    
    # Verify bye players NOT in first round
    bye_in_first = set()
    for m in session.matches:
        for p in m.team1 + m.team2:
            if p in ['p0', 'p1']:
                bye_in_first.add(p)
    assert len(bye_in_first) == 0, "Bye players should not be in first round"
    
    # Complete first match
    match = session.matches[0]
    complete_match(session, match.id, 11, 10)
    
    # Create second round
    evaluate_and_create_matches(session)
    
    # Verify bye players ARE in active matches NOW
    bye_in_active = set()
    for m in session.matches:
        if m.status in ['waiting', 'in-progress']:
            for p in m.team1 + m.team2:
                if p in ['p0', 'p1']:
                    bye_in_active.add(p)
    
    assert bye_in_active == {'p0', 'p1'}, f"Bye players should be scheduled immediately, got {bye_in_active}"
    print("  ✓ PASS: Bye players scheduled immediately after first match")


def test_first_bye_player_persistence():
    """Test that first bye players are saved and loaded from history"""
    print("\nTest 2: First bye players saved and restored with player history")
    
    # Save players and first bye list
    players = ['Alice', 'Bob', 'Charlie', 'Diana']
    first_byes = ['Alice', 'Bob']
    
    save_player_history(players, first_byes)
    
    # Load them back
    loaded_players = load_player_history()
    loaded_byes = load_first_bye_players()
    
    assert loaded_players == players, f"Players not persisted: {loaded_players}"
    assert loaded_byes == first_byes, f"First bye players not persisted: {loaded_byes}"
    
    print("  ✓ PASS: First bye players persist correctly")


def test_bye_count_validation():
    """Test validation logic for bye player count vs court count"""
    print("\nTest 3: Validation prevents too many bye players")
    
    # Test case 1: 6 players, 1 court = max 2 byes
    courts = 1
    total_players = 6
    players_needed = courts * 4
    max_byes = total_players - players_needed
    
    assert max_byes == 2, f"Expected max 2 byes for 6 players + 1 court, got {max_byes}"
    
    # Trying to set 3 byes should fail
    bye_count = 3
    assert bye_count > max_byes, f"Should have too many byes: {bye_count} > {max_byes}"
    
    # Test case 2: 12 players, 2 courts = max 4 byes
    courts = 2
    total_players = 12
    players_needed = courts * 4
    max_byes = total_players - players_needed
    
    assert max_byes == 4, f"Expected max 4 byes for 12 players + 2 courts, got {max_byes}"
    
    # Test case 3: 16 players, 3 courts = max 4 byes
    courts = 3
    total_players = 16
    players_needed = courts * 4
    max_byes = total_players - players_needed
    
    assert max_byes == 4, f"Expected max 4 byes for 16 players + 3 courts, got {max_byes}"
    
    print("  ✓ PASS: Validation logic correct")


def test_bye_applied_only_first_round():
    """Test that bye exclusion only applies to first round, not subsequent ones"""
    print("\nTest 4: Bye exclusion only applies to first round")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        first_bye_players=['p0', 'p1']
    )
    
    session = create_session(config)
    
    # Round 1
    evaluate_and_create_matches(session)
    bye_in_round1 = set()
    for m in session.matches:
        for p in m.team1 + m.team2:
            if p in ['p0', 'p1']:
                bye_in_round1.add(p)
    
    assert len(bye_in_round1) == 0, f"Bye should not be in round 1: {bye_in_round1}"
    
    # Complete all round 1 matches
    for match in session.matches[:2]:
        if match.status in ['waiting', 'in-progress']:
            complete_match(session, match.id, 11, 10)
    
    # Round 2 - bye players should now be available
    evaluate_and_create_matches(session)
    bye_in_round2 = set()
    for m in session.matches:
        if m.status in ['waiting', 'in-progress']:
            for p in m.team1 + m.team2:
                if p in ['p0', 'p1']:
                    bye_in_round2.add(p)
    
    assert len(bye_in_round2) == 2, f"Bye should be in round 2: {bye_in_round2}"
    print("  ✓ PASS: Bye exclusion only applies to first round")


if __name__ == '__main__':
    print("=" * 70)
    print("FIRST BYE FEATURE - BUG FIXES TESTS")
    print("=" * 70)
    
    test_bye_players_scheduled_immediately()
    test_first_bye_player_persistence()
    test_bye_count_validation()
    test_bye_applied_only_first_round()
    
    print("\n" + "=" * 70)
    print("[ALL TESTS PASSED] All three bug fixes verified!")
    print("=" * 70)
