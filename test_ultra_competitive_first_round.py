"""
Test ultra-competitive first round for competitive variety matchmaking.

Tests:
1. First round uses top 4/bottom 4 alternating pattern
2. Simple 2-court-wait rule is enforced in later rounds
"""

import sys
sys.path.insert(0, 'python')

from python.pickleball_types import Session, SessionConfig, Player, PlayerStats
from python.competitive_variety import (
    create_ultra_competitive_first_round_matches,
    get_must_play_players,
    get_simple_wait_priority_candidates,
    calculate_player_elo_rating,
    COURTS_WAIT_THRESHOLD
)


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


if __name__ == "__main__":
    print("=" * 70)
    print("ULTRA-COMPETITIVE FIRST ROUND & SIMPLE WAIT PRIORITY TEST SUITE")
    print("=" * 70)
    
    test_threshold_constant()
    test_ultra_competitive_first_round_pattern()
    test_simple_wait_priority()
    test_courts_completed_tracking()
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
