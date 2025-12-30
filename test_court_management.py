"""
Test suite for manual court management and export features
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from python.pickleball_types import Player, Session, SessionConfig, GameMode, SessionType
from python.session import create_session, create_manual_match, update_match_teams
from python.queue_manager import get_empty_courts, get_waiting_players, get_match_for_court
from python.competitive_variety import calculate_elo_rating
from python.kingofcourt import calculate_player_rating


def test_create_manual_match_doubles():
    """Test creating a manual match on an empty court (doubles)"""
    # Setup
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana"),
        Player(id="p5", name="Eve"),
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Verify court is empty
    empty_courts = get_empty_courts(session)
    assert len(empty_courts) == 2, "Should have 2 empty courts"
    
    # Create a match on court 1
    success = create_manual_match(
        session, 
        court_number=1,
        team1_ids=["p1", "p2"],
        team2_ids=["p3", "p4"]
    )
    
    assert success, "Should successfully create manual match"
    
    # Verify match was created
    match = get_match_for_court(session, 1)
    assert match is not None, "Match should exist on court 1"
    assert match.court_number == 1, "Match should be on court 1"
    assert set(match.team1) == {"p1", "p2"}, "Team 1 should be p1 and p2"
    assert set(match.team2) == {"p3", "p4"}, "Team 2 should be p3 and p4"
    assert match.status == 'waiting', "Match should be in waiting status"
    
    # Verify court 1 is now occupied
    empty_courts = get_empty_courts(session)
    assert len(empty_courts) == 1, "Should have 1 empty court"
    assert 1 not in empty_courts, "Court 1 should not be empty"
    assert 2 in empty_courts, "Court 2 should still be empty"
    
    print("[PASS] test_create_manual_match_doubles")


def test_create_manual_match_singles():
    """Test creating a manual match for singles"""
    # Setup
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='singles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Create a singles match (1v1)
    success = create_manual_match(
        session,
        court_number=1,
        team1_ids=["p1"],
        team2_ids=["p2"]
    )
    
    assert success, "Should successfully create singles match"
    
    # Verify match
    match = get_match_for_court(session, 1)
    assert match is not None, "Match should exist"
    assert len(match.team1) == 1, "Team 1 should have 1 player"
    assert len(match.team2) == 1, "Team 2 should have 1 player"
    
    print("[PASS] test_create_manual_match_singles")


def test_invalid_manual_match():
    """Test that invalid manual matches are rejected"""
    # Setup
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Try to create match with overlapping players
    success = create_manual_match(
        session,
        court_number=1,
        team1_ids=["p1", "p2"],
        team2_ids=["p2", "p3"]  # p2 is in both teams!
    )
    
    assert not success, "Should reject match with overlapping players"
    
    # Try invalid court number
    success = create_manual_match(
        session,
        court_number=99,
        team1_ids=["p1", "p2"],
        team2_ids=["p3", "p1"]
    )
    
    assert not success, "Should reject invalid court number"
    
    # Try with inactive player
    session.active_players.discard("p3")
    success = create_manual_match(
        session,
        court_number=1,
        team1_ids=["p1", "p3"],
        team2_ids=["p2", "p3"]
    )
    
    assert not success, "Should reject match with inactive player"
    
    print("[PASS] test_invalid_manual_match")


def test_update_match_teams():
    """Test updating an existing match's teams"""
    # Setup
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana"),
        Player(id="p5", name="Eve"),
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Create initial match
    create_manual_match(
        session,
        court_number=1,
        team1_ids=["p1", "p2"],
        team2_ids=["p3", "p4"]
    )
    
    match = get_match_for_court(session, 1)
    match_id = match.id
    
    # Update the teams
    success = update_match_teams(
        session,
        match_id=match_id,
        team1_ids=["p1", "p3"],
        team2_ids=["p2", "p5"]
    )
    
    assert success, "Should successfully update match teams"
    
    # Verify update
    updated_match = get_match_for_court(session, 1)
    assert set(updated_match.team1) == {"p1", "p3"}, "Team 1 should be updated"
    assert set(updated_match.team2) == {"p2", "p5"}, "Team 2 should be updated"
    
    print("[PASS] test_update_match_teams")


def test_elo_calculation():
    """Test ELO rating calculation"""
    from python.pickleball_types import PlayerStats
    
    # New player
    new_player = PlayerStats(player_id="p1", games_played=0, wins=0)
    elo = calculate_elo_rating(new_player)
    assert elo == 1500, "New player should have 1500 ELO"
    
    # Player with perfect record
    perfect_player = PlayerStats(player_id="p2", games_played=10, wins=10)
    elo = calculate_elo_rating(perfect_player)
    assert elo > 1500, "Undefeated player should have ELO > 1500"
    
    # Player with terrible record
    poor_player = PlayerStats(player_id="p3", games_played=10, wins=0)
    elo = calculate_elo_rating(poor_player)
    assert elo < 1500, "0-win player should have ELO < 1500"
    
    # 50-50 player
    average_player = PlayerStats(player_id="p4", games_played=10, wins=5)
    elo = calculate_elo_rating(average_player)
    assert elo > 1500, "50-50 player should have ELO above 1500 due to games_played bonus"
    
    print("[PASS] test_elo_calculation")


def test_elo_with_point_differential():
    """Test ELO calculation with point differential"""
    from python.pickleball_types import PlayerStats
    
    # High point differential
    high_diff = PlayerStats(
        player_id="p1",
        games_played=5,
        wins=5,
        total_points_for=100,
        total_points_against=50
    )
    elo_high = calculate_elo_rating(high_diff)
    
    # Same record but low point differential
    low_diff = PlayerStats(
        player_id="p2",
        games_played=5,
        wins=5,
        total_points_for=56,
        total_points_against=50
    )
    elo_low = calculate_elo_rating(low_diff)
    
    assert elo_high > elo_low, "Higher point differential should give higher ELO"
    
    print("[PASS] test_elo_with_point_differential")


def test_manual_match_all_modes():
    """Test manual match creation works in all game modes"""
    for mode in ['round-robin', 'king-of-court', 'competitive-variety']:
        players = [
            Player(id="p1", name="Alice"),
            Player(id="p2", name="Bob"),
            Player(id="p3", name="Charlie"),
            Player(id="p4", name="Diana"),
        ]
        
        config = SessionConfig(
            mode=mode,
            session_type='doubles',
            players=players,
            courts=2
        )
        
        session = create_session(config)
        
        # Create manual match
        success = create_manual_match(
            session,
            court_number=1,
            team1_ids=["p1", "p2"],
            team2_ids=["p3", "p4"]
        )
        
        assert success, f"Should create manual match in {mode} mode"
        
        match = get_match_for_court(session, 1)
        assert match is not None, f"Match should exist in {mode} mode"
        assert match.status == 'waiting', f"Match should be waiting in {mode} mode"
    
    print("[PASS] test_manual_match_all_modes")


if __name__ == '__main__':
    test_create_manual_match_doubles()
    test_create_manual_match_singles()
    test_invalid_manual_match()
    test_update_match_teams()
    test_elo_calculation()
    test_elo_with_point_differential()
    test_manual_match_all_modes()
    print("\n[ALL PASS] All tests passed!")
