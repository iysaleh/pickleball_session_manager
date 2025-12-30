#!/usr/bin/env python3
"""
Test the First Bye feature - allows users to specify players to sit out the first match.

The feature should:
1. Allow selecting players to sit out the first match via the GUI
2. Only apply bye if there will actually be waiting players
3. Persist first bye state across session saves/loads
4. Work with Competitive Variety matchmaking
"""

from python.pickleball_types import SessionConfig, Player
from python.session import create_session, evaluate_and_create_matches
from python.session_persistence import serialize_session, deserialize_session


def test_first_bye_basic():
    """Test basic first bye functionality"""
    print("Test 1: Basic first bye - should exclude bye players from first round")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        first_bye_players=['p0', 'p1']
    )
    
    session = create_session(config)
    evaluate_and_create_matches(session)
    
    # Check bye players are not in matches
    bye_players_in_matches = set()
    for match in session.matches:
        for player in match.team1 + match.team2:
            if player in session.config.first_bye_players:
                bye_players_in_matches.add(player)
    
    assert len(bye_players_in_matches) == 0, f"Bye players in matches: {bye_players_in_matches}"
    print("  ✓ PASS: Bye players excluded from first round")


def test_first_bye_not_applied_with_no_waiting():
    """Test that bye is not applied when all players will be playing"""
    print("\nTest 2: No bye when exactly filling courts")
    
    # 8 players exactly fills 2 courts (4 players per court * 2 courts)
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(8)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        first_bye_players=['p0', 'p1']
    )
    
    session = create_session(config)
    evaluate_and_create_matches(session)
    
    # Check bye players ARE in matches (because no one will be waiting)
    bye_players_in_matches = set()
    for match in session.matches:
        for player in match.team1 + match.team2:
            if player in session.config.first_bye_players:
                bye_players_in_matches.add(player)
    
    assert len(bye_players_in_matches) == 2, "Bye players should be in matches"
    print("  ✓ PASS: Bye not applied when no waiting players")


def test_first_bye_persistence():
    """Test that first bye data persists across save/load"""
    print("\nTest 3: Persistence of first bye data")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        first_bye_players=['p0', 'p1']
    )
    
    session = create_session(config)
    evaluate_and_create_matches(session)
    
    # Serialize and deserialize
    data = serialize_session(session)
    restored = deserialize_session(data)
    
    assert restored.config.first_bye_players == ['p0', 'p1'], \
        f"First bye players not preserved: {restored.config.first_bye_players}"
    assert restored.first_bye_used == session.first_bye_used, \
        "first_bye_used flag not preserved"
    print("  ✓ PASS: First bye data persists correctly")


def test_first_bye_empty():
    """Test with empty bye list (normal operation)"""
    print("\nTest 4: Empty bye list (normal operation)")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        first_bye_players=[]  # No bye players
    )
    
    session = create_session(config)
    evaluate_and_create_matches(session)
    
    # Should create normal matches without any bye logic
    assert len(session.matches) > 0, "Should create matches"
    assert not session.first_bye_used, "first_bye_used should be False"
    print("  ✓ PASS: Normal operation with empty bye list")


def test_first_bye_multiple_players():
    """Test with multiple bye players"""
    print("\nTest 5: Multiple bye players")
    
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(16)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3,
        first_bye_players=['p0', 'p1', 'p2', 'p3']  # 4 bye players
    )
    
    session = create_session(config)
    evaluate_and_create_matches(session)
    
    # Check all bye players are excluded
    bye_players_in_matches = set()
    for match in session.matches:
        for player in match.team1 + match.team2:
            if player in session.config.first_bye_players:
                bye_players_in_matches.add(player)
    
    assert len(bye_players_in_matches) == 0, f"Bye players in matches: {bye_players_in_matches}"
    print("  ✓ PASS: Multiple bye players work correctly")


if __name__ == '__main__':
    print("=" * 70)
    print("FIRST BYE FEATURE TESTS")
    print("=" * 70)
    
    test_first_bye_basic()
    test_first_bye_not_applied_with_no_waiting()
    test_first_bye_persistence()
    test_first_bye_empty()
    test_first_bye_multiple_players()
    
    print("\n" + "=" * 70)
    print("[ALL TESTS PASSED] First bye feature works correctly!")
    print("=" * 70)
