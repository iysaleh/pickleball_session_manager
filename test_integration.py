"""
Integration test for manual court management features
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from python.types import Player, Session, SessionConfig, Match
from python.session import create_session, create_manual_match, update_match_teams, complete_match
from python.queue_manager import get_empty_courts, get_waiting_players, get_match_for_court
from datetime import datetime


def test_make_court_workflow():
    """Test the complete 'Make Court' workflow"""
    print("Testing 'Make Court' workflow...")
    
    # Create session
    players = [
        Player(id=f"p{i}", name=f"Player {i}")
        for i in range(1, 13)
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=3
    )
    
    session = create_session(config)
    
    # Get empty courts
    empty_courts = get_empty_courts(session)
    assert len(empty_courts) == 3, "Should have 3 empty courts initially"
    
    # Create a court manually
    success = create_manual_match(
        session,
        court_number=1,
        team1_ids=["p1", "p2"],
        team2_ids=["p3", "p4"]
    )
    assert success, "Should create match on court 1"
    
    # Check that court 1 is now occupied
    empty_courts = get_empty_courts(session)
    assert len(empty_courts) == 2, "Should have 2 empty courts after creating match"
    assert 1 not in empty_courts, "Court 1 should be occupied"
    
    # Make another court
    success = create_manual_match(
        session,
        court_number=2,
        team1_ids=["p5", "p6"],
        team2_ids=["p7", "p8"]
    )
    assert success, "Should create match on court 2"
    
    # Verify courts are occupied
    empty_courts = get_empty_courts(session)
    assert len(empty_courts) == 1, "Should have 1 empty court"
    assert 3 in empty_courts, "Court 3 should be the only empty court"
    
    print("  [PASS] Make Court workflow successful")


def test_edit_court_workflow():
    """Test the complete 'Edit Court' workflow"""
    print("Testing 'Edit Court' workflow...")
    
    # Create session
    players = [
        Player(id=f"p{i}", name=f"Player {i}")
        for i in range(1, 9)
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
    assert set(match.team1) == {"p1", "p2"}, "Initial team1 correct"
    assert set(match.team2) == {"p3", "p4"}, "Initial team2 correct"
    
    # Edit the court - swap team members
    success = update_match_teams(
        session,
        match_id=match.id,
        team1_ids=["p1", "p3"],
        team2_ids=["p2", "p4"]
    )
    assert success, "Should successfully edit match"
    
    # Verify edit
    updated_match = get_match_for_court(session, 1)
    assert set(updated_match.team1) == {"p1", "p3"}, "Team1 should be updated"
    assert set(updated_match.team2) == {"p2", "p4"}, "Team2 should be updated"
    
    # Edit again - swap teams completely
    success = update_match_teams(
        session,
        match_id=updated_match.id,
        team1_ids=["p5", "p6"],
        team2_ids=["p7", "p8"]
    )
    assert success, "Should successfully swap different players"
    
    # Verify final state
    final_match = get_match_for_court(session, 1)
    assert set(final_match.team1) == {"p5", "p6"}, "Final team1 correct"
    assert set(final_match.team2) == {"p7", "p8"}, "Final team2 correct"
    
    print("  [PASS] Edit Court workflow successful")


def test_manual_court_with_algorithms():
    """Test that Round Robin and Competitive Variety algorithms work after manual court creation"""
    print("Testing manual courts with algorithms...")
    
    for mode in ['round-robin', 'competitive-variety']:
        players = [
            Player(id=f"p{i}", name=f"Player {i}")
            for i in range(1, 9)
        ]
        
        config = SessionConfig(
            mode=mode,
            session_type='doubles',
            players=players,
            courts=2
        )
        
        session = create_session(config)
        
        # Create a manual match
        create_manual_match(
            session,
            court_number=1,
            team1_ids=["p1", "p2"],
            team2_ids=["p3", "p4"]
        )
        
        # Complete the match
        match = get_match_for_court(session, 1)
        complete_match(session, match.id, 11, 5)
        
        # Verify the match was completed
        assert match.status == 'completed', f"Match should be completed in {mode} mode"
        assert match.score == {'team1_score': 11, 'team2_score': 5}, "Score should be recorded"
        
        # Verify player stats were updated
        p1_stats = session.player_stats["p1"]
        assert p1_stats.games_played == 1, "Player should have 1 game played"
        assert p1_stats.wins == 1, "Player should have 1 win"
        assert p1_stats.opponents_played == {"p3", "p4"}, "Should track opponents"
        assert p1_stats.partners_played == {"p2"}, "Should track partners"
        
        # Verify algorithm can still work
        from python.queue_manager import populate_empty_courts
        from python.competitive_variety import populate_empty_courts_competitive_variety
        
        # Try to populate empty courts
        if mode == 'round-robin':
            populate_empty_courts(session)
        elif mode == 'competitive-variety':
            populate_empty_courts_competitive_variety(session)
        
        print(f"  [PASS] {mode} mode works after manual court creation")
    
    print("  [PASS] Algorithms work correctly with manual courts")


def test_manual_court_in_all_modes():
    """Test manual court creation in all game modes"""
    print("Testing manual courts in all game modes...")
    
    for mode in ['round-robin', 'king-of-court', 'competitive-variety']:
        for session_type in ['doubles', 'singles']:
            players = [
                Player(id=f"p{i}", name=f"Player {i}")
                for i in range(1, (5 if session_type == 'doubles' else 3))
            ]
            
            config = SessionConfig(
                mode=mode,
                session_type=session_type,
                players=players,
                courts=2
            )
            
            session = create_session(config)
            
            # Determine team sizes based on session type
            team_size = 2 if session_type == 'doubles' else 1
            
            # Create manual match
            team1_ids = [f"p{i}" for i in range(1, team_size + 1)]
            team2_ids = [f"p{i}" for i in range(team_size + 1, 2 * team_size + 1)]
            
            success = create_manual_match(
                session,
                court_number=1,
                team1_ids=team1_ids,
                team2_ids=team2_ids
            )
            
            assert success, f"Should create manual match in {mode}/{session_type}"
            
            match = get_match_for_court(session, 1)
            assert match is not None, f"Match should exist in {mode}/{session_type}"
            assert len(match.team1) == team_size, f"Team1 should have {team_size} players"
            assert len(match.team2) == team_size, f"Team2 should have {team_size} players"
            
            print(f"  [PASS] {mode} / {session_type}")


def test_manual_court_and_auto_populate():
    """Test that manually created courts don't interfere with auto-population"""
    print("Testing manual courts with auto-population...")
    
    players = [
        Player(id=f"p{i}", name=f"Player {i}")
        for i in range(1, 13)
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Manually create a match on court 1
    create_manual_match(
        session,
        court_number=1,
        team1_ids=["p1", "p2"],
        team2_ids=["p3", "p4"]
    )
    
    # Get empty courts
    empty_before = get_empty_courts(session)
    assert len(empty_before) == 3, "Should have 3 empty courts"
    
    # Try to auto-populate
    from python.queue_manager import populate_empty_courts
    populate_empty_courts(session)
    
    # Check that some courts were populated (since we have a queue)
    empty_after = get_empty_courts(session)
    # We might have some empty courts depending on queue availability
    assert len(empty_after) < 3, "Some courts should be populated"
    
    # Court 1 should still have our manual match
    match = get_match_for_court(session, 1)
    assert match is not None, "Manual match should still exist on court 1"
    assert set(match.team1) == {"p1", "p2"}, "Team1 should be unchanged"
    
    print("  [PASS] Manual courts work with auto-population")


if __name__ == '__main__':
    test_make_court_workflow()
    test_edit_court_workflow()
    test_manual_court_with_algorithms()
    test_manual_court_in_all_modes()
    test_manual_court_and_auto_populate()
    print("\n[ALL PASS] All integration tests passed!")
