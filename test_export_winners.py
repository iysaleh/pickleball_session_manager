"""Test that session export includes SESSION WINNERS section for all game modes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.pickleball_types import Session, SessionConfig, Player, PlayerStats, Match


def create_test_session(mode='competitive-variety', num_players=8, num_courts=2):
    """Create a test session with completed matches for export testing."""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, num_players + 1)]
    
    config = SessionConfig(
        mode=mode,
        session_type='doubles',
        courts=num_courts,
        players=players,
    )
    
    session = Session(id='test-session', config=config)
    session.active_players = [p.id for p in players]
    
    # Initialize player stats
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)
    
    return session


def simulate_completed_matches(session):
    """Add some completed matches so players have stats."""
    # Give players varied stats so we get a clear ranking
    # Player 1: best (5-1, +20 pts)
    stats1 = session.player_stats["p1"]
    stats1.wins = 5
    stats1.losses = 1
    stats1.games_played = 6
    stats1.total_points_for = 66
    stats1.total_points_against = 46

    # Player 2: second (4-2, +10 pts)
    stats2 = session.player_stats["p2"]
    stats2.wins = 4
    stats2.losses = 2
    stats2.games_played = 6
    stats2.total_points_for = 60
    stats2.total_points_against = 50

    # Player 3: third (3-3, +5 pts)
    stats3 = session.player_stats["p3"]
    stats3.wins = 3
    stats3.losses = 3
    stats3.games_played = 6
    stats3.total_points_for = 55
    stats3.total_points_against = 50

    # Player 4: fourth (2-4, -5 pts)
    stats4 = session.player_stats["p4"]
    stats4.wins = 2
    stats4.losses = 4
    stats4.games_played = 6
    stats4.total_points_for = 50
    stats4.total_points_against = 55

    # Player 5: no games (should be skipped)
    stats5 = session.player_stats["p5"]
    stats5.wins = 0
    stats5.losses = 0
    stats5.games_played = 0

    # Create some completed match objects for the session
    for i in range(6):
        m = Match(
            id=f"m{i}",
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            court_number=1,
            status='completed',
            score={'team1_score': 11, 'team2_score': 9},
        )
        session.matches.append(m)


def build_export_lines(session):
    """
    Replicate the export logic from gui.py export_session to extract the 
    SESSION WINNERS section without needing the full GUI.
    """
    from python.utils import get_current_wait_time, format_duration
    
    export_lines = []
    
    # Collect player data with ELO ratings (same as gui.py)
    player_data = []
    for player in session.config.players:
        if player.id not in session.active_players:
            continue
        
        stats = session.player_stats[player.id]
        
        # Calculate ELO rating
        elo = 0
        try:
            if session.config.mode == 'competitive-variety':
                from python.competitive_variety import calculate_player_elo_rating
                elo = calculate_player_elo_rating(session, player.id)
            else:
                from python.kingofcourt import calculate_player_rating
                elo = calculate_player_rating(stats)
        except:
            elo = 1500 if stats.games_played == 0 else (1500 + (stats.wins - stats.losses) * 50)
        
        record = f"{stats.wins}-{stats.losses}"
        win_pct = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0
        
        current_wait = get_current_wait_time(stats)
        total_wait_seconds = stats.total_wait_time + current_wait
        
        avg_pt_diff = (stats.total_points_for - stats.total_points_against) / stats.games_played if stats.games_played > 0 else 0
        
        player_data.append((player.name, elo, record, stats.games_played, win_pct, total_wait_seconds, avg_pt_diff, stats.total_points_for, stats.total_points_against))
    
    # Sort by ELO descending
    player_data.sort(key=lambda x: x[1], reverse=True)
    
    # Session Winners (same logic as gui.py)
    if session.config.mode != 'pooled-continuous-rr' and player_data:
        export_lines.append("SESSION WINNERS:")
        export_lines.append("-" * 70)
        
        medals = ["🥇 GOLD", "🥈 SILVER", "🥉 BRONZE"]
        winner_count = 0
        for i, (player_name, elo, record, games_played, win_pct, total_wait_seconds, avg_pt_diff, pts_for, pts_against) in enumerate(player_data):
            if games_played == 0:
                continue
            if winner_count >= 3:
                break
            medal = medals[winner_count]
            pt_diff = pts_for - pts_against
            export_lines.append(f"{medal}: {player_name} - {record}, {pt_diff:+d} pts")
            winner_count += 1
        
        if winner_count == 0:
            export_lines.append("  (No completed games yet)")
        
        export_lines.append("")
    
    return export_lines, player_data


def test_competitive_variety_winners():
    """Test session winners export for competitive-variety mode."""
    print("Test: Competitive Variety mode winners...")
    session = create_test_session(mode='competitive-variety')
    simulate_completed_matches(session)
    
    export_lines, player_data = build_export_lines(session)
    
    # Should have SESSION WINNERS header
    assert "SESSION WINNERS:" in export_lines, "Missing SESSION WINNERS header"
    
    # Should have exactly 3 medal lines (players with 0 games skipped)
    medal_lines = [l for l in export_lines if any(m in l for m in ["🥇", "🥈", "🥉"])]
    assert len(medal_lines) == 3, f"Expected 3 medal lines, got {len(medal_lines)}: {medal_lines}"
    
    # Gold should be first (highest ELO)
    gold_line = medal_lines[0]
    assert "🥇 GOLD:" in gold_line, f"Gold line format wrong: {gold_line}"
    
    # Silver should be second
    silver_line = medal_lines[1]
    assert "🥈 SILVER:" in silver_line, f"Silver line format wrong: {silver_line}"
    
    # Bronze should be third
    bronze_line = medal_lines[2]
    assert "🥉 BRONZE:" in bronze_line, f"Bronze line format wrong: {bronze_line}"
    
    # Each line should have W-L record and point diff format
    for line in medal_lines:
        assert " - " in line, f"Missing ' - ' separator in: {line}"
        assert "pts" in line, f"Missing 'pts' in: {line}"
    
    # Verify the gold winner is the top ELO player
    top_player_name = player_data[0][0]
    assert top_player_name in gold_line, f"Expected {top_player_name} in gold line: {gold_line}"
    
    print(f"  ✅ PASSED - Winners section correctly generated")
    for line in export_lines:
        print(f"    {line}")


def test_king_of_court_winners():
    """Test session winners export for king-of-court mode."""
    print("Test: King of Court mode winners...")
    session = create_test_session(mode='king-of-court')
    simulate_completed_matches(session)
    session.king_of_court_round_number = 3
    
    export_lines, player_data = build_export_lines(session)
    
    assert "SESSION WINNERS:" in export_lines, "Missing SESSION WINNERS header"
    medal_lines = [l for l in export_lines if any(m in l for m in ["🥇", "🥈", "🥉"])]
    assert len(medal_lines) == 3, f"Expected 3 medal lines, got {len(medal_lines)}"
    
    print(f"  ✅ PASSED - KoC winners section correctly generated")
    for line in export_lines:
        print(f"    {line}")


def test_competitive_round_robin_winners():
    """Test session winners export for competitive-round-robin mode."""
    print("Test: Competitive Round Robin mode winners...")
    session = create_test_session(mode='competitive-round-robin')
    simulate_completed_matches(session)
    
    export_lines, player_data = build_export_lines(session)
    
    assert "SESSION WINNERS:" in export_lines, "Missing SESSION WINNERS header"
    medal_lines = [l for l in export_lines if any(m in l for m in ["🥇", "🥈", "🥉"])]
    assert len(medal_lines) == 3, f"Expected 3 medal lines, got {len(medal_lines)}"
    
    print(f"  ✅ PASSED - CRR winners section correctly generated")
    for line in export_lines:
        print(f"    {line}")


def test_no_games_played():
    """Test that no winners shown when nobody has played."""
    print("Test: No games played...")
    session = create_test_session(mode='competitive-variety')
    # Don't simulate any matches
    
    export_lines, _ = build_export_lines(session)
    
    assert "SESSION WINNERS:" in export_lines, "Missing SESSION WINNERS header"
    assert "  (No completed games yet)" in export_lines, "Missing no-games message"
    
    medal_lines = [l for l in export_lines if any(m in l for m in ["🥇", "🥈", "🥉"])]
    assert len(medal_lines) == 0, f"Should have no medal lines, got {len(medal_lines)}"
    
    print(f"  ✅ PASSED - No winners when no games played")


def test_fewer_than_3_players_with_games():
    """Test with only 2 players having completed games."""
    print("Test: Fewer than 3 players with games...")
    session = create_test_session(mode='competitive-variety', num_players=4)
    
    # Only give 2 players stats
    stats1 = session.player_stats["p1"]
    stats1.wins = 3
    stats1.losses = 1
    stats1.games_played = 4
    stats1.total_points_for = 44
    stats1.total_points_against = 36
    
    stats2 = session.player_stats["p2"]
    stats2.wins = 1
    stats2.losses = 3
    stats2.games_played = 4
    stats2.total_points_for = 36
    stats2.total_points_against = 44
    
    # Add completed matches to session
    for i in range(4):
        m = Match(id=f"m{i}", team1=["p1", "p3"], team2=["p2", "p4"],
                  court_number=1, status='completed', score={'team1_score': 11, 'team2_score': 9})
        session.matches.append(m)
    
    export_lines, _ = build_export_lines(session)
    
    medal_lines = [l for l in export_lines if any(m in l for m in ["🥇", "🥈", "🥉"])]
    assert len(medal_lines) == 2, f"Expected 2 medal lines (only 2 players with games), got {len(medal_lines)}"
    
    print(f"  ✅ PASSED - Shows only {len(medal_lines)} winners when {len(medal_lines)} players have games")


def test_point_diff_format():
    """Test that point differential is formatted correctly with +/- sign."""
    print("Test: Point diff format...")
    session = create_test_session(mode='competitive-variety')
    simulate_completed_matches(session)
    
    export_lines, _ = build_export_lines(session)
    medal_lines = [l for l in export_lines if any(m in l for m in ["🥇", "🥈", "🥉"])]
    
    # Gold player (p1) has pts_for=66, pts_against=46, diff=+20
    gold_line = medal_lines[0]
    assert "+20 pts" in gold_line, f"Expected '+20 pts' in gold line: {gold_line}"
    
    print(f"  ✅ PASSED - Point diff correctly formatted")


def test_pooled_mode_excluded():
    """Test that pooled-continuous-rr mode does NOT get the generic winners section."""
    print("Test: Pooled mode excluded from generic winners...")
    session = create_test_session(mode='pooled-continuous-rr')
    simulate_completed_matches(session)
    
    export_lines, _ = build_export_lines(session)
    
    # Should NOT have SESSION WINNERS for pooled mode (it has its own)
    assert "SESSION WINNERS:" not in export_lines, "Pooled mode should not have generic winners section"
    
    print(f"  ✅ PASSED - Pooled mode correctly excluded")


if __name__ == "__main__":
    print("=" * 70)
    print("Testing Session Winners Export")
    print("=" * 70)
    print()
    
    test_competitive_variety_winners()
    print()
    test_king_of_court_winners()
    print()
    test_competitive_round_robin_winners()
    print()
    test_no_games_played()
    print()
    test_fewer_than_3_players_with_games()
    print()
    test_point_diff_format()
    print()
    test_pooled_mode_excluded()
    
    print()
    print("=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
