"""
Tests for must-play balance relaxation and SESSION WINNERS non-seeded ranking.

When must-play players (waited 2+ courts) would create badly imbalanced matches
due to strict variety constraints, the algorithm should relax constraints to
prioritize balance (only enforcing back-to-back prevention, locked teams, banned pairs).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.pickleball_types import Session, SessionConfig, Player, Match, PlayerStats
from python.competitive_variety import (
    _can_play_relaxed,
    _find_relaxed_must_play_match,
    calculate_player_elo_rating,
    MUST_PLAY_BALANCE_THRESHOLD,
    COURTS_WAIT_THRESHOLD,
    get_must_play_players,
    populate_empty_courts_competitive_variety,
    calculate_elo_rating_unseeded,
)
from python.session import create_session
from python.time_manager import initialize_time_manager, now

initialize_time_manager(test_mode=False)


def make_session_with_history():
    """
    Create a session that mimics the real-world scenario from the export:
    - Players with pre-seeded ratings (skill levels 3.0 to 4.5)
    - Some completed matches that create partner repetition constraints
    - Must-play players who waited 2+ courts
    Returns session with the problematic state.
    """
    players = [
        Player(id='p1', name='Ibraheem', skill_rating=4.5),  # ~2100
        Player(id='p2', name='Amanda', skill_rating=4.0),    # ~1800
        Player(id='p3', name='Blaize', skill_rating=3.5),    # ~1500
        Player(id='p4', name='Leslie', skill_rating=3.0),    # ~1200
        Player(id='p5', name='Niaz', skill_rating=4.0),      # ~1800
        Player(id='p6', name='Cory', skill_rating=3.5),      # ~1500
        Player(id='p7', name='Caleb', skill_rating=3.5),     # ~1500
        Player(id='p8', name='John', skill_rating=3.0),      # ~1200
        Player(id='p9', name='Mike', skill_rating=3.5),      # ~1500
        Player(id='p10', name='Sarah', skill_rating=3.0),    # ~1200
    ]
    
    config = SessionConfig(
        mode='competitive-variety',
        courts=2,
        players=players,
        pre_seeded_ratings=True,
        session_type='doubles',
    )
    
    session = create_session(config)
    
    # Simulate completed matches to create variety constraints
    # Match 1: Amanda+Blaize partners (on court 1)
    m1 = Match(
        id='m1', court_number=1,
        team1=['p2', 'p3'],  # Amanda, Blaize
        team2=['p5', 'p6'],  # Niaz, Cory
        status='completed',
        start_time=now(),
        score={'team1_score': 11, 'team2_score': 9}
    )
    
    # Match 2: Different players (on court 2)
    m2 = Match(
        id='m2', court_number=2,
        team1=['p1', 'p4'],  # Ibraheem, Leslie
        team2=['p7', 'p8'],  # Caleb, John
        status='completed',
        start_time=now(),
        score={'team1_score': 11, 'team2_score': 5}
    )
    
    # Match 3: More matches to advance court completions
    m3 = Match(
        id='m3', court_number=1,
        team1=['p5', 'p7'],  # Niaz, Caleb
        team2=['p6', 'p9'],  # Cory, Mike
        status='completed',
        start_time=now(),
        score={'team1_score': 11, 'team2_score': 8}
    )
    
    # Match 4: Another match
    m4 = Match(
        id='m4', court_number=2,
        team1=['p1', 'p10'], # Ibraheem, Sarah
        team2=['p8', 'p4'],  # John, Leslie
        status='completed',
        start_time=now(),
        score={'team1_score': 11, 'team2_score': 3}
    )
    
    session.matches = [m1, m2, m3, m4]
    
    # Update stats
    for pid in session.active_players:
        if pid not in session.player_stats:
            session.player_stats[pid] = PlayerStats(player_id=pid)
    
    for m in session.matches:
        t1_score = m.score['team1_score'] if m.score else 0
        t2_score = m.score['team2_score'] if m.score else 0
        for pid in m.team1 + m.team2:
            session.player_stats[pid].games_played += 1
            if pid in m.team1:
                if t1_score > t2_score:
                    session.player_stats[pid].wins += 1
                else:
                    session.player_stats[pid].losses += 1
                session.player_stats[pid].total_points_for += t1_score
                session.player_stats[pid].total_points_against += t2_score
            else:
                if t2_score > t1_score:
                    session.player_stats[pid].wins += 1
                else:
                    session.player_stats[pid].losses += 1
                session.player_stats[pid].total_points_for += t2_score
                session.player_stats[pid].total_points_against += t1_score
    
    # Set wait counts: p2 (Amanda) and p3 (Blaize) waited 2 courts (must-play)
    session.player_stats['p2'].courts_completed_since_last_play = 2
    session.player_stats['p3'].courts_completed_since_last_play = 2
    
    return session


def test_relaxed_allows_recent_partners():
    """Test that _can_play_relaxed allows players who were partners 2 games ago."""
    session = make_session_with_history()
    
    # Amanda (p2) and Blaize (p3) were partners in match 1 (2 matches ago for both)
    # Normal constraints: PARTNER_REPETITION_GAMES_REQUIRED=3, so they can't partner
    # Relaxed constraints: only back-to-back prevention, so they CAN partner (gap=1+)
    
    result = _can_play_relaxed(session, 'p2', 'p3', 'partner')
    assert result, "Relaxed constraints should allow partners who played together 2+ games ago"
    print("[PASS] test_relaxed_allows_recent_partners")


def test_relaxed_blocks_back_to_back():
    """Test that _can_play_relaxed still blocks back-to-back partnerships."""
    session = make_session_with_history()
    
    # John (p8) and Leslie (p4) were PARTNERS in the LAST match (m4, team2)
    # They are back-to-back partners, so they should be blocked as partners
    result = _can_play_relaxed(session, 'p8', 'p4', 'partner')
    assert not result, "Relaxed constraints should still block back-to-back partners"
    
    # Ibraheem (p1) and Sarah (p10) were partners in the LAST match (m4, team1)
    result = _can_play_relaxed(session, 'p1', 'p10', 'partner')
    assert not result, "Relaxed constraints should still block back-to-back partners"
    
    # p1 (team1) and p8 (team2) were opponents in the LAST match (m4)
    result = _can_play_relaxed(session, 'p1', 'p8', 'opponent')
    assert not result, "Relaxed constraints should still block back-to-back opponents"
    print("[PASS] test_relaxed_blocks_back_to_back")


def test_relaxed_respects_banned_pairs():
    """Test that _can_play_relaxed respects banned pairs."""
    session = make_session_with_history()
    session.config.banned_pairs = [['p2', 'p3']]
    
    result = _can_play_relaxed(session, 'p2', 'p3', 'partner')
    assert not result, "Relaxed constraints should still respect banned pairs"
    print("[PASS] test_relaxed_respects_banned_pairs")


def test_relaxed_respects_locked_teams():
    """Test that _can_play_relaxed respects locked teams."""
    session = make_session_with_history()
    session.config.locked_teams = [['p1', 'p5']]
    
    # p1 must partner with p5
    result = _can_play_relaxed(session, 'p1', 'p2', 'partner')
    assert not result, "p1 is locked with p5, so can't partner with p2"
    
    result = _can_play_relaxed(session, 'p1', 'p5', 'partner')
    assert result, "Locked pair should always be allowed as partners"
    
    # Locked partners can't be opponents
    result = _can_play_relaxed(session, 'p1', 'p5', 'opponent')
    assert not result, "Locked partners can't be opponents"
    print("[PASS] test_relaxed_respects_locked_teams")


def test_find_relaxed_must_play_match():
    """Test that relaxed search finds a more balanced match than strict constraints."""
    session = make_session_with_history()
    
    must_play = get_must_play_players(session, list(session.active_players))
    assert 'p2' in must_play, "Amanda should be must-play"
    assert 'p3' in must_play, "Blaize should be must-play"
    
    # Get available players (not in active matches)
    players_in_matches = set()
    for m in session.matches:
        if m.status == 'waiting':
            players_in_matches.update(m.team1 + m.team2)
    
    available = [p for p in session.active_players if p not in players_in_matches]
    
    result = _find_relaxed_must_play_match(session, available, must_play, len(available))
    assert result is not None, "Relaxed search should find a match"
    
    team1, team2 = result
    # Must include at least one must-play player
    all_players = set(team1 + team2)
    assert any(p in must_play for p in all_players), "Relaxed match must include must-play players"
    
    # Check balance
    t1_rating = sum(calculate_player_elo_rating(session, p) for p in team1)
    t2_rating = sum(calculate_player_elo_rating(session, p) for p in team2)
    diff = abs(t1_rating - t2_rating)
    
    print(f"  Relaxed match: {team1} vs {team2}, balance diff: {diff:.0f}")
    # The relaxed search should find something reasonably balanced
    assert diff < 500, f"Relaxed match should be reasonably balanced, got diff={diff}"
    print("[PASS] test_find_relaxed_must_play_match")


def test_must_play_balance_threshold_constant():
    """Verify the MUST_PLAY_BALANCE_THRESHOLD constant is set."""
    assert MUST_PLAY_BALANCE_THRESHOLD == 300, \
        f"Expected threshold 300, got {MUST_PLAY_BALANCE_THRESHOLD}"
    print("[PASS] test_must_play_balance_threshold_constant")


def test_unseeded_elo_for_session_winners():
    """
    Verify that unseeded ELO produces different rankings than seeded
    when pre-seeded ratings are used, ensuring SESSION WINNERS
    uses performance-based rankings.
    """
    session = make_session_with_history()
    
    # Calculate both seeded and unseeded for all players with games
    seeded_rankings = []
    unseeded_rankings = []
    
    for pid in session.active_players:
        stats = session.player_stats.get(pid)
        if stats and stats.games_played > 0:
            player = next(p for p in session.config.players if p.id == pid)
            seeded_elo = calculate_player_elo_rating(session, pid)
            unseeded_elo = calculate_elo_rating_unseeded(stats)
            seeded_rankings.append((player.name, seeded_elo, pid))
            unseeded_rankings.append((player.name, unseeded_elo, pid))
    
    seeded_rankings.sort(key=lambda x: x[1], reverse=True)
    unseeded_rankings.sort(key=lambda x: x[1], reverse=True)
    
    seeded_order = [r[2] for r in seeded_rankings]
    unseeded_order = [r[2] for r in unseeded_rankings]
    
    print(f"  Seeded top 3:   {[r[0] for r in seeded_rankings[:3]]}")
    print(f"  Unseeded top 3: {[r[0] for r in unseeded_rankings[:3]]}")
    
    # Rankings should differ since seeds give advantage to higher-rated players
    assert seeded_order != unseeded_order, \
        "Seeded and unseeded rankings should differ when pre-seeded ratings are used"
    print("[PASS] test_unseeded_elo_for_session_winners")


if __name__ == '__main__':
    print("=" * 60)
    print("MUST-PLAY BALANCE RELAXATION & SESSION WINNERS TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_relaxed_allows_recent_partners,
        test_relaxed_blocks_back_to_back,
        test_relaxed_respects_banned_pairs,
        test_relaxed_respects_locked_teams,
        test_find_relaxed_must_play_match,
        test_must_play_balance_threshold_constant,
        test_unseeded_elo_for_session_winners,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    if failed == 0:
        print(f"✅ All {passed} tests passed!")
    else:
        print(f"❌ {failed}/{passed+failed} tests failed")
    
    sys.exit(1 if failed else 0)
