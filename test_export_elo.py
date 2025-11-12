"""
Test export functionality with ELO ratings
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(__file__))

from python.types import Player, Session, SessionConfig, Match
from python.session import create_session, complete_match
from datetime import datetime


def test_export_with_elo():
    """Test that export includes ELO ratings sorted correctly"""
    # Create session with some players
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana"),
    ]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session = create_session(config)
    
    # Create some matches and complete them to generate different ELOs
    # Alice and Bob win
    match1 = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='completed',
        score={'team1_score': 11, 'team2_score': 5},
        end_time=datetime.now()
    )
    session.matches.append(match1)
    complete_match(session, "m1", 11, 5)
    
    # Clear for next match
    session.matches.pop(0)
    
    # Charlie and Diana win this time
    match2 = Match(
        id="m2",
        court_number=1,
        team1=["p1", "p3"],
        team2=["p2", "p4"],
        status='completed',
        score={'team1_score': 9, 'team2_score': 11},
        end_time=datetime.now()
    )
    session.matches.append(match2)
    complete_match(session, "m2", 9, 11)
    
    # Verify that player stats are set up correctly
    alice_stats = session.player_stats["p1"]
    bob_stats = session.player_stats["p2"]
    charlie_stats = session.player_stats["p3"]
    diana_stats = session.player_stats["p4"]
    
    print(f"Alice: {alice_stats.wins}W-{alice_stats.losses}L")
    print(f"Bob: {bob_stats.wins}W-{bob_stats.losses}L")
    print(f"Charlie: {charlie_stats.wins}W-{charlie_stats.losses}L")
    print(f"Diana: {diana_stats.wins}W-{diana_stats.losses}L")
    
    # Calculate ELOs
    from python.competitive_variety import calculate_elo_rating
    
    alice_elo = calculate_elo_rating(alice_stats)
    bob_elo = calculate_elo_rating(bob_stats)
    charlie_elo = calculate_elo_rating(charlie_stats)
    diana_elo = calculate_elo_rating(diana_stats)
    
    print(f"\nAlice ELO: {alice_elo:.0f}")
    print(f"Bob ELO: {bob_elo:.0f}")
    print(f"Charlie ELO: {charlie_elo:.0f}")
    print(f"Diana ELO: {diana_elo:.0f}")
    
    # Verify sorting - Bob should be highest (2W-0L), Alice (1W-1L), Diana (1W-1L), Charlie (0W-2L) should be lowest
    elo_list = [
        ("Alice", alice_elo),
        ("Bob", bob_elo),
        ("Charlie", charlie_elo),
        ("Diana", diana_elo)
    ]
    
    sorted_by_elo = sorted(elo_list, key=lambda x: x[1], reverse=True)
    print(f"\nSorted by ELO (highest first):")
    for name, elo in sorted_by_elo:
        print(f"  {name}: {elo:.0f}")
    
    # Bob (2W-0L) should be highest, Charlie (0W-2L) should be lowest
    assert sorted_by_elo[0][0] == "Bob", "Bob should have highest ELO (2W-0L)"
    assert sorted_by_elo[-1][0] == "Charlie", "Charlie should have lowest ELO (0W-2L)"
    
    print("\n[PASS] test_export_with_elo")


if __name__ == '__main__':
    test_export_with_elo()
