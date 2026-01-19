"""
Test ultra-competitive first round for competitive variety matchmaking.

Tests:
1. First round uses top 4/bottom 4 alternating pattern
2. Simple 2-court-wait rule is enforced in later rounds
3. Player swap behavior correctly resets wait counters
"""

import sys
sys.path.insert(0, 'python')

from python.pickleball_types import Session, SessionConfig, Player, PlayerStats, Match
from python.competitive_variety import (
    create_ultra_competitive_first_round_matches,
    get_must_play_players,
    get_simple_wait_priority_candidates,
    calculate_player_elo_rating,
    COURTS_WAIT_THRESHOLD
)
from python.session import add_player_to_session, create_manual_match, update_match_teams
from python.utils import generate_id


def create_test_session(num_players: int, num_courts: int = 4) -> Session:
    """Create a test session with players having varied skill ratings."""
    players = []
    for i in range(num_players):
        # Assign skill ratings: higher index = higher skill (3.0 to 4.5 range)
        skill = 3.0 + (i / num_players) * 1.5
        players.append(Player(id=f"p{i+1}", name=f"Player {i+1}", skill_rating=skill))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        courts=num_courts,
        players=players,
        pre_seeded_ratings=True
    )
    
    session = Session(
        id="test_session",
        config=config,
        active_players=set(p.id for p in players),
        player_stats={p.id: PlayerStats(player_id=p.id) for p in players}
    )
    
    return session


def test_ultra_competitive_first_round_pattern():
    """Test that first round uses top 4/bottom 4 alternating pattern."""
    print("\n=== Test: Ultra-Competitive First Round Pattern ===")
    
    # Create session with 16 players, 4 courts
    session = create_test_session(16, 4)
    available_players = list(session.active_players)
    
    # Get player ratings sorted highest to lowest
    player_ratings = [(p, calculate_player_elo_rating(session, p)) for p in available_players]
    player_ratings.sort(key=lambda x: x[1], reverse=True)
    sorted_by_skill = [p[0] for p in player_ratings]
    
    print(f"Players sorted by skill (highest first):")
    for i, (pid, rating) in enumerate(player_ratings):
        print(f"  {i+1}. {pid}: {rating:.0f}")
    
    # Generate first round matches
    matches = create_ultra_competitive_first_round_matches(session, available_players, 4)
    
    print(f"\nGenerated {len(matches)} matches:")
    
    # Track which players are in each match
    all_used = set()
    for i, match in enumerate(matches):
        match_players = set(match.team1 + match.team2)
        all_used.update(match_players)
        
        # Get ratings for match players
        match_ratings = [calculate_player_elo_rating(session, p) for p in match.team1 + match.team2]
        avg_rating = sum(match_ratings) / 4
        spread = max(match_ratings) - min(match_ratings)
        
        print(f"\n  Match {i+1} (Court {i+1}):")
        print(f"    Team 1: {match.team1}")
        print(f"    Team 2: {match.team2}")
        print(f"    Avg rating: {avg_rating:.0f}, Spread: {spread:.0f}")
        
        # Check that this court has similar-skill players (low spread)
        # Top/bottom courts should have tight spreads
        if i < 2:  # First two courts (top and bottom skill groups)
            assert spread < 400, f"Court {i+1} has too high spread: {spread}"
            print(f"    ✓ Homogeneous skill group (spread < 400)")
    
    # Verify all courts got 4 different players
    assert len(all_used) == 16, f"Expected 16 unique players, got {len(all_used)}"
    print(f"\n✓ All 16 players assigned to exactly 4 courts")
    
    # Check court 1 has top players, court 2 has bottom players (alternating pattern)
    court1_players = set(matches[0].team1 + matches[0].team2)
    court2_players = set(matches[1].team1 + matches[1].team2)
    
    top_4 = set(sorted_by_skill[:4])
    bottom_4 = set(sorted_by_skill[-4:])
    
    # Court 1 should be top 4
    court1_overlap_top = len(court1_players & top_4)
    print(f"\nCourt 1 overlap with top 4: {court1_overlap_top}/4")
    assert court1_overlap_top == 4, f"Court 1 should have top 4 players"
    
    # Court 2 should be bottom 4
    court2_overlap_bottom = len(court2_players & bottom_4)
    print(f"Court 2 overlap with bottom 4: {court2_overlap_bottom}/4")
    assert court2_overlap_bottom == 4, f"Court 2 should have bottom 4 players"
    
    print("\n✓ Ultra-competitive pattern verified: top 4 → bottom 4 → ... alternating")


def test_simple_wait_priority():
    """Test simple 2-court-wait priority system."""
    print("\n=== Test: Simple 2-Court-Wait Priority ===")
    
    session = create_test_session(12, 2)
    
    # Simulate some players waiting different amounts
    session.player_stats["p1"].courts_completed_since_last_play = 0  # Just played
    session.player_stats["p2"].courts_completed_since_last_play = 1  # Waited 1 court
    session.player_stats["p3"].courts_completed_since_last_play = 2  # Waited 2 courts - MUST PLAY
    session.player_stats["p4"].courts_completed_since_last_play = 3  # Waited 3 courts - MUST PLAY
    session.player_stats["p5"].courts_completed_since_last_play = 0  # Just played
    session.player_stats["p6"].courts_completed_since_last_play = 2  # Waited 2 courts - MUST PLAY
    
    available = ["p1", "p2", "p3", "p4", "p5", "p6"]
    
    # Get must-play players
    must_play = get_must_play_players(session, available)
    print(f"\nPlayers who MUST play (waited >= {COURTS_WAIT_THRESHOLD} courts):")
    for p in must_play:
        waited = session.player_stats[p].courts_completed_since_last_play
        print(f"  {p}: waited {waited} courts")
    
    assert set(must_play) == {"p3", "p4", "p6"}, f"Expected p3, p4, p6 as must-play, got {must_play}"
    print("✓ Must-play players correctly identified")
    
    # Get priority-sorted candidates
    candidates = get_simple_wait_priority_candidates(session, available)
    print(f"\nPriority-sorted candidates (highest wait first):")
    for p in candidates:
        waited = session.player_stats[p].courts_completed_since_last_play
        print(f"  {p}: waited {waited} courts")
    
    # Verify sorting: p4 (3) > p3 (2) = p6 (2) > p2 (1) > p1 (0) = p5 (0)
    # First should be p4 (waited 3 courts)
    assert candidates[0] == "p4", f"Expected p4 first, got {candidates[0]}"
    
    # p3 and p6 should be next (both waited 2)
    assert set(candidates[1:3]) == {"p3", "p6"}, f"Expected p3, p6 in positions 1-2"
    
    # p2 should be after that (waited 1)
    assert candidates[3] == "p2", f"Expected p2 in position 3, got {candidates[3]}"
    
    # p1 and p5 last (both waited 0)
    assert set(candidates[4:6]) == {"p1", "p5"}, f"Expected p1, p5 in positions 4-5"
    
    print("✓ Priority sorting works correctly")


def test_courts_completed_tracking():
    """Test that courts_completed_since_last_play is properly tracked."""
    print("\n=== Test: Courts Completed Tracking ===")
    
    session = create_test_session(8, 2)
    
    # All players start at 0
    for p in session.active_players:
        assert session.player_stats[p].courts_completed_since_last_play == 0, \
            f"Player {p} should start at 0"
    
    print("✓ All players start with 0 courts_completed_since_last_play")
    
    # Simulate a match completion - players in match reset to 0, others increment
    players_in_match = {"p1", "p2", "p3", "p4"}
    players_waiting = {"p5", "p6", "p7", "p8"}
    
    # Increment for waiting players
    for p in players_waiting:
        session.player_stats[p].courts_completed_since_last_play += 1
    
    # Reset for playing players
    for p in players_in_match:
        session.player_stats[p].courts_completed_since_last_play = 0
    
    # Verify
    for p in players_in_match:
        assert session.player_stats[p].courts_completed_since_last_play == 0
    for p in players_waiting:
        assert session.player_stats[p].courts_completed_since_last_play == 1
    
    print("✓ Tracking updates correctly after match completion")


def test_threshold_constant():
    """Verify the threshold constant is set correctly."""
    print("\n=== Test: Threshold Constant ===")
    
    assert COURTS_WAIT_THRESHOLD == 2, f"Expected threshold of 2, got {COURTS_WAIT_THRESHOLD}"
    print(f"✓ COURTS_WAIT_THRESHOLD = {COURTS_WAIT_THRESHOLD}")


def test_player_swap_resets_wait_count():
    """Test that swapping players in/out of matches correctly resets their wait counters."""
    print("\n=== Test: Player Swap Resets Wait Count ===")
    
    # Create session with 12 players, 2 courts
    session = create_test_session(12, 2)
    
    # Simulate some players having waited different amounts
    session.player_stats["p1"].courts_completed_since_last_play = 3
    session.player_stats["p2"].courts_completed_since_last_play = 2
    session.player_stats["p3"].courts_completed_since_last_play = 1
    session.player_stats["p4"].courts_completed_since_last_play = 0
    session.player_stats["p9"].courts_completed_since_last_play = 5  # Long waiter on bench
    session.player_stats["p10"].courts_completed_since_last_play = 4  # Long waiter on bench
    
    # Create a match with p1, p2, p3, p4 on court 1
    from python.time_manager import now
    match = Match(
        id="test_match_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='waiting',
        start_time=now()
    )
    session.matches.append(match)
    
    print(f"Before swap - p1 wait count: {session.player_stats['p1'].courts_completed_since_last_play}")
    print(f"Before swap - p9 wait count: {session.player_stats['p9'].courts_completed_since_last_play}")
    
    # Now use create_manual_match to swap p1 out and p9 in
    result = create_manual_match(session, 1, ["p9", "p2"], ["p3", "p4"])
    
    assert result['success'], f"create_manual_match failed: {result['error']}"
    
    # p9 was swapped IN - should have wait count reset to 0
    assert session.player_stats["p9"].courts_completed_since_last_play == 0, \
        f"p9 (swapped IN) should have wait count 0, got {session.player_stats['p9'].courts_completed_since_last_play}"
    print(f"✓ Player swapped INTO match (p9) has wait count reset to 0")
    
    # p1 was swapped OUT - should have wait count reset to 0 (they just played/were about to play)
    assert session.player_stats["p1"].courts_completed_since_last_play == 0, \
        f"p1 (swapped OUT) should have wait count 0, got {session.player_stats['p1'].courts_completed_since_last_play}"
    print(f"✓ Player swapped OUT of match (p1) has wait count reset to 0")
    
    # p2, p3, p4 stayed in match - should also have 0
    for p in ["p2", "p3", "p4"]:
        assert session.player_stats[p].courts_completed_since_last_play == 0, \
            f"{p} (stayed in match) should have wait count 0"
    print(f"✓ Players who stayed in match have wait count 0")


def test_add_player_gets_priority():
    """Test that a newly added player gets priority in the wait system."""
    print("\n=== Test: Added Player Gets Wait Priority ===")
    
    session = create_test_session(8, 2)
    
    # Simulate some wait counts
    session.player_stats["p1"].courts_completed_since_last_play = 2
    session.player_stats["p2"].courts_completed_since_last_play = 1
    session.player_stats["p3"].courts_completed_since_last_play = 3
    
    max_wait = max(s.courts_completed_since_last_play for s in session.player_stats.values())
    print(f"Max current wait count: {max_wait}")
    
    # Add a new player
    new_player = Player(id="p_new", name="New Player", skill_rating=3.5)
    add_player_to_session(session, new_player)
    
    # New player should have wait count = max + 1 for priority
    new_stats = session.player_stats["p_new"]
    expected_wait = max_wait + 1
    assert new_stats.courts_completed_since_last_play == expected_wait, \
        f"New player should have wait count {expected_wait}, got {new_stats.courts_completed_since_last_play}"
    
    print(f"✓ New player added with courts_completed_since_last_play = {new_stats.courts_completed_since_last_play}")
    print(f"✓ This gives them priority to play in the next match")


def test_update_match_teams_resets_wait_count():
    """Test that updating match teams correctly resets wait counters."""
    print("\n=== Test: Update Match Teams Resets Wait Count ===")
    
    session = create_test_session(12, 2)
    
    # Set up wait counts
    session.player_stats["p5"].courts_completed_since_last_play = 4  # On waitlist, long wait
    session.player_stats["p6"].courts_completed_since_last_play = 3  # On waitlist
    
    # Create a match
    from python.time_manager import now
    match = Match(
        id="test_match_update",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='waiting',
        start_time=now()
    )
    session.matches.append(match)
    
    print(f"Before update - p5 wait count: {session.player_stats['p5'].courts_completed_since_last_play}")
    print(f"Before update - p1 wait count: {session.player_stats['p1'].courts_completed_since_last_play}")
    
    # Update match to swap p1 and p2 out, p5 and p6 in
    success = update_match_teams(session, "test_match_update", ["p5", "p6"], ["p3", "p4"])
    
    assert success, "update_match_teams should succeed"
    
    # p5 and p6 swapped IN - should have wait count 0
    assert session.player_stats["p5"].courts_completed_since_last_play == 0
    assert session.player_stats["p6"].courts_completed_since_last_play == 0
    print(f"✓ Players swapped IN (p5, p6) have wait count reset to 0")
    
    # p1 and p2 swapped OUT - should have wait count 0
    assert session.player_stats["p1"].courts_completed_since_last_play == 0
    assert session.player_stats["p2"].courts_completed_since_last_play == 0
    print(f"✓ Players swapped OUT (p1, p2) have wait count reset to 0")


def test_first_bye_player_gets_priority():
    """Test that first bye players get priority to play after first round."""
    print("\n=== Test: First Bye Player Gets Priority ===")
    
    from python.session import create_session
    from python.competitive_variety import COURTS_WAIT_THRESHOLD
    from python.time_manager import initialize_time_manager
    
    # Initialize time manager (required for session creation)
    initialize_time_manager()
    
    # Create session with first bye player
    players = []
    for i in range(19):  # 19 players, 4 courts = 16 playing + 3 waiting
        skill = 3.0 + (i / 19) * 1.5
        players.append(Player(id=f"p{i+1}", name=f"Player {i+1}", skill_rating=skill))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        courts=4,
        players=players,
        pre_seeded_ratings=True,
        first_bye_players=["p10"]  # p10 is explicitly first bye
    )
    
    session = create_session(config)
    
    # First bye player should start with courts_completed_since_last_play = num_courts
    first_bye_wait = session.player_stats["p10"].courts_completed_since_last_play
    print(f"First bye player (p10) initial wait count: {first_bye_wait}")
    
    # Should be set to number of courts (4) to ensure priority after first round
    assert first_bye_wait == 4, \
        f"First bye player should start with wait count = num_courts (4), got {first_bye_wait}"
    print(f"✓ First bye player starts with courts_completed_since_last_play = {first_bye_wait}")
    
    # Non-first-bye players should start at 0
    for p in ["p1", "p2", "p3", "p5"]:
        non_bye_wait = session.player_stats[p].courts_completed_since_last_play
        assert non_bye_wait == 0, \
            f"Non-first-bye player {p} should start with wait count 0, got {non_bye_wait}"
    print(f"✓ Non-first-bye players start with courts_completed_since_last_play = 0")
    
    # First bye player should already exceed the threshold (4 >= 2)
    assert first_bye_wait >= COURTS_WAIT_THRESHOLD, \
        f"First bye player should exceed threshold {COURTS_WAIT_THRESHOLD}"
    print(f"✓ First bye player already exceeds threshold ({first_bye_wait} >= {COURTS_WAIT_THRESHOLD})")
    
    # Check that first bye player is in the must_play list
    from python.competitive_variety import get_must_play_players
    available_players = list(session.active_players)
    must_play = get_must_play_players(session, available_players)
    
    assert "p10" in must_play, f"First bye player should be in must_play list, got {must_play}"
    print(f"✓ First bye player (p10) is in the must_play list")


def test_preseeded_session_respects_must_play_priority():
    """
    Test that pre-seeded sessions respect the 2-court-wait must-play priority.
    
    This reproduces a bug where create_skill_based_matches_for_pre_seeded() 
    only sorts by ELO rating and ignores players who have waited 2+ courts.
    
    Scenario from pickleball_session_20260118_200913.txt:
    - 19 players, 4 courts
    - First bye player (mid-level rating) is Ibraheem
    - After 3 matches complete, Ibraheem is STILL on the waitlist (bug!)
    - Expected: First-bye player should play after at most 2 courts complete
    """
    print("\n=== Test: Pre-seeded Session Respects Must-Play Priority ===")
    
    from python.session import create_session, complete_match
    from python.competitive_variety import (
        COURTS_WAIT_THRESHOLD,
        get_must_play_players,
        create_skill_based_matches_for_pre_seeded,
        populate_empty_courts_competitive_variety
    )
    from python.time_manager import initialize_time_manager
    
    # Initialize time manager
    initialize_time_manager()
    
    # Create session matching the real scenario: 19 players, mid-level first-bye player
    players = []
    # Use actual ELO-like skill ratings similar to the session file
    skill_ratings = [
        ("p1", 4.5),   # Top tier
        ("p2", 4.4),
        ("p3", 4.3),
        ("p4", 4.2),
        ("p5", 4.0),
        ("p6", 3.9),
        ("p7", 3.8),
        ("p8", 3.7),
        ("p9", 3.6),   # Mid tier
        ("p10_ibraheem", 3.5),  # MID-LEVEL FIRST BYE PLAYER - like Ibraheem at ELO 1800
        ("p11", 3.4),
        ("p12", 3.3),
        ("p13", 3.2),
        ("p14", 3.0),
        ("p15", 2.8),  # Lower tier
        ("p16", 2.6),
        ("p17", 2.4),
        ("p18", 2.2),
        ("p19", 2.0),
    ]
    
    for pid, skill in skill_ratings:
        players.append(Player(id=pid, name=pid, skill_rating=skill))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        courts=4,
        players=players,
        pre_seeded_ratings=True,
        first_bye_players=["p10_ibraheem"]  # Mid-level player as first bye
    )
    
    session = create_session(config)
    
    # Verify first-bye player starts with correct wait count
    first_bye_wait = session.player_stats["p10_ibraheem"].courts_completed_since_last_play
    print(f"First bye player (p10_ibraheem) initial wait count: {first_bye_wait}")
    assert first_bye_wait == 4, f"First bye should start with wait=4, got {first_bye_wait}"
    
    # Fill courts for first round
    populate_empty_courts_competitive_variety(session)
    
    # Verify first round created (4 matches)
    active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
    print(f"First round: {len(active_matches)} matches created")
    assert len(active_matches) == 4, f"Expected 4 matches in first round, got {len(active_matches)}"
    
    # First-bye player should NOT be in any first-round match
    players_in_matches = set()
    for m in active_matches:
        players_in_matches.update(m.team1 + m.team2)
    
    print(f"Players in first round: {sorted(players_in_matches)}")
    assert "p10_ibraheem" not in players_in_matches, "First-bye player should sit out first round"
    print("✓ First-bye player correctly sits out first round")
    
    # Complete first match
    first_match = active_matches[0]
    first_match.status = 'in-progress'
    complete_match(session, first_match.id, 11, 5)
    
    # First-bye player's wait count should increase by 1 (now 5)
    first_bye_wait_after = session.player_stats["p10_ibraheem"].courts_completed_since_last_play
    print(f"After 1 match completes, first-bye wait count: {first_bye_wait_after}")
    
    # Now fill empty court - THIS IS WHERE THE BUG MANIFESTS
    # The first-bye player should be in the must_play list and included in match creation
    
    # Get available players (not in active matches)
    players_in_active = set()
    for m in session.matches:
        if m.status in ['waiting', 'in-progress']:
            players_in_active.update(m.team1 + m.team2)
    available = [p for p in session.active_players if p not in players_in_active]
    
    # Check must_play list
    must_play = get_must_play_players(session, available)
    print(f"Must-play players: {must_play}")
    assert "p10_ibraheem" in must_play, f"First-bye player should be in must_play list!"
    
    # Now test create_skill_based_matches_for_pre_seeded - IT SHOULD INCLUDE MUST-PLAY PLAYERS
    # This is the core bug - the function ignores must-play players
    new_matches = create_skill_based_matches_for_pre_seeded(session, available, 1)
    
    if new_matches:
        new_match_players = set(new_matches[0].team1 + new_matches[0].team2)
        print(f"Players in new match: {new_match_players}")
        
        # BUG CHECK: First-bye player MUST be in the new match
        # If they're not, the bug exists!
        if "p10_ibraheem" not in new_match_players:
            print(f"❌ BUG REPRODUCED: First-bye player NOT in new match!")
            print(f"   Must-play players: {must_play}")
            print(f"   Players chosen: {new_match_players}")
            # After fix, this should not happen
            assert "p10_ibraheem" in new_match_players, \
                f"First-bye player (must-play) should be in new match, but got {new_match_players}"
        else:
            print(f"✓ First-bye player correctly included in new match")
    else:
        print(f"❌ No match created - available players: {available}")
        assert False, "Should have created a match"
    
    print("✓ Pre-seeded session correctly respects must-play priority")


if __name__ == "__main__":
    print("=" * 70)
    print("ULTRA-COMPETITIVE FIRST ROUND & SIMPLE WAIT PRIORITY TEST SUITE")
    print("=" * 70)
    
    test_threshold_constant()
    test_ultra_competitive_first_round_pattern()
    test_simple_wait_priority()
    test_courts_completed_tracking()
    test_player_swap_resets_wait_count()
    test_add_player_gets_priority()
    test_update_match_teams_resets_wait_count()
    test_first_bye_player_gets_priority()
    test_preseeded_session_respects_must_play_priority()
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
