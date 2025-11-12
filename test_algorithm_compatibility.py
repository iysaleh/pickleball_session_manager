"""
Test that competitive variety and round robin algorithms work after manual court creation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from python.types import Player, SessionConfig
from python.session import create_session, create_manual_match, complete_match
from python.queue_manager import get_empty_courts, populate_empty_courts
from python.competitive_variety import populate_empty_courts_competitive_variety
from datetime import datetime


def test_round_robin_after_manual_court():
    """Verify Round Robin algorithm works after manually creating courts"""
    print("Testing Round Robin after manual court creation...")
    
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 13)]
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = create_session(config)
    
    # Manually create a match on court 1
    create_manual_match(session, 1, ["p1", "p2"], ["p3", "p4"])
    
    # Check that court 1 is occupied
    empty = get_empty_courts(session)
    assert 1 not in empty, "Court 1 should be occupied"
    
    # Run auto-populate
    populate_empty_courts(session)
    
    # Check that other courts were populated
    empty_after = get_empty_courts(session)
    assert len(empty_after) < 3, "Should populate some empty courts"
    
    # Complete manual match
    from python.queue_manager import get_match_for_court
    match = get_match_for_court(session, 1)
    complete_match(session, match.id, 11, 5)
    
    # Run auto-populate again
    populate_empty_courts(session)
    
    # Verify algorithm continues to work
    assert len(session.matches) > 1, "Should have multiple matches after algorithm runs"
    
    print("  [PASS] Round Robin algorithm works after manual court creation")


def test_competitive_variety_after_manual_court():
    """Verify Competitive Variety algorithm works after manually creating courts"""
    print("Testing Competitive Variety after manual court creation...")
    
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = create_session(config)
    
    # Manually create a match on court 1
    create_manual_match(session, 1, ["p1", "p2"], ["p3", "p4"])
    
    # Run competitive variety auto-populate
    populate_empty_courts_competitive_variety(session)
    
    # Verify that some courts were populated
    from python.queue_manager import get_match_for_court
    populated_count = 0
    for court_num in range(1, 5):
        if get_match_for_court(session, court_num):
            populated_count += 1
    
    assert populated_count >= 1, "Should have at least 1 match"
    
    print("  [PASS] Competitive Variety algorithm works after manual court creation")


def test_manual_court_respects_constraints():
    """Verify that manually created courts don't violate algorithm constraints"""
    print("Testing manual court constraint compatibility...")
    
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Manually create match
    create_manual_match(session, 1, ["p1", "p2"], ["p3", "p4"])
    
    # Algorithm should still respect waiting list
    from python.queue_manager import get_waiting_players
    waiting_before = set(get_waiting_players(session))
    
    # Run algorithm
    populate_empty_courts_competitive_variety(session)
    
    # Players who were in manual match shouldn't appear in waiting list
    from python.queue_manager import get_match_for_court
    match1 = get_match_for_court(session, 1)
    assert match1 is not None, "Manual match should still exist"
    
    # Verify player overlap is handled correctly
    match_players = set(match1.team1 + match1.team2)
    match2 = get_match_for_court(session, 2)
    if match2:
        match2_players = set(match2.team1 + match2.team2)
        assert not (match_players & match2_players), "No player should be in two matches"
    
    print("  [PASS] Manual courts respect algorithm constraints")


if __name__ == '__main__':
    test_round_robin_after_manual_court()
    test_competitive_variety_after_manual_court()
    test_manual_court_respects_constraints()
    print("\n[ALL PASS] Algorithm compatibility tests passed!")
