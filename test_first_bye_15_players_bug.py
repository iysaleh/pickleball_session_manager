#!/usr/bin/env python3
"""
Test for specific bug: 15 players, 4 courts, 2 first bye players
Only 1 of 2 first bye players was actually waiting in first round.

This test reproduces the exact scenario reported by the user.
"""

from python.session import create_session
from python.pickleball_types import SessionConfig, Player
from python.competitive_variety import populate_empty_courts_competitive_variety


def test_15_players_4_courts_2_byes_bug():
    """Reproduce and verify fix for the specific reported bug"""
    print("Testing: 15 players, 4 courts, 2 first bye players")
    
    # Create exact scenario from bug report
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 16)]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4,
        first_bye_players=['p1', 'p2']  # 2 players should be on first bye
    )
    
    session = create_session(config)
    
    # Populate courts (this is where the bug occurred)
    populate_empty_courts_competitive_variety(session)
    
    # Analyze results
    players_on_courts = set()
    for match in session.matches:
        players_on_courts.update(match.team1 + match.team2)
    
    waiting_players = set(session.active_players) - players_on_courts
    bye_players_waiting = set(['p1', 'p2']).intersection(waiting_players)
    bye_players_on_courts = set(['p1', 'p2']).intersection(players_on_courts)
    
    print(f"  Total players: {len(session.active_players)}")
    print(f"  Courts used: {len(session.matches)}/4")
    print(f"  Players on courts: {len(players_on_courts)}")
    print(f"  Players waiting: {len(waiting_players)}")
    print(f"  Bye players waiting: {len(bye_players_waiting)}/2 - {sorted(bye_players_waiting)}")
    print(f"  Bye players on courts: {len(bye_players_on_courts)}/2 - {sorted(bye_players_on_courts)}")
    
    # Verify the fix
    assert len(bye_players_waiting) == 2, f"Expected 2 bye players waiting, got {len(bye_players_waiting)}"
    assert len(bye_players_on_courts) == 0, f"Expected 0 bye players on courts, got {len(bye_players_on_courts)}"
    assert len(session.matches) == 3, f"Expected 3 courts used (15-2=13 players → 3 courts), got {len(session.matches)}"
    assert len(waiting_players) == 3, f"Expected 3 players waiting (1 regular + 2 bye), got {len(waiting_players)}"
    
    print("  ✓ PASS: Both first bye players are waiting as expected")
    print("  ✓ PASS: Correct number of courts used (3/4)")
    print("  ✓ PASS: Correct total waiting players (3)")


if __name__ == "__main__":
    print("=" * 70)
    print("FIRST BYE BUG FIX VERIFICATION")
    print("=" * 70)
    
    test_15_players_4_courts_2_byes_bug()
    
    print("=" * 70) 
    print("[TEST PASSED] Bug fix verified successfully!")
    print("=" * 70)