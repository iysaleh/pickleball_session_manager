"""
Test that unseeded ELO export produces rankings based purely on session performance,
ignoring pre-seeded skill ratings.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.pickleball_types import Player, Session, SessionConfig, Match, PlayerStats
from python.session import create_session, complete_match
from python.competitive_variety import (
    calculate_player_elo_rating, calculate_elo_rating_unseeded,
    calculate_elo_rating, BASE_RATING
)
from python.time_manager import initialize_time_manager
from datetime import datetime

initialize_time_manager(test_mode=False)


def _create_preseeded_session():
    """Helper to create a competitive-variety session with pre-seeded ratings."""
    players = [
        Player(id="p1", name="Alice", skill_rating=4.5),   # High seed
        Player(id="p2", name="Bob", skill_rating=4.0),     # Mid-high seed
        Player(id="p3", name="Charlie", skill_rating=3.0), # Low seed
        Player(id="p4", name="Diana", skill_rating=3.5),   # Mid-low seed
        Player(id="p5", name="Eve", skill_rating=2.5),     # Very low seed
        Player(id="p6", name="Frank", skill_rating=5.0),   # Highest seed
        Player(id="p7", name="Grace", skill_rating=3.0),   # Low seed
        Player(id="p8", name="Hank", skill_rating=3.5),    # Mid-low seed
    ]

    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
        pre_seeded_ratings=True
    )

    session = create_session(config)
    return session


def test_unseeded_elo_ignores_seed():
    """Unseeded ELO should use BASE_RATING (1500) regardless of seed, seeded should differ."""
    session = _create_preseeded_session()

    # Complete a match: Alice (4.5 seed) + Bob (4.0) vs Charlie (3.0) + Diana (3.5)
    # Charlie's team wins — the underdogs upset
    match1 = Match(
        id="m1", court_number=1,
        team1=["p1", "p2"], team2=["p3", "p4"],
        status='in_progress'
    )
    session.matches.append(match1)
    complete_match(session, "m1", 5, 11)

    # Complete another match: Eve (2.5) + Frank (5.0) vs Grace (3.0) + Hank (3.5)
    # Eve + Frank win
    match2 = Match(
        id="m2", court_number=2,
        team1=["p5", "p6"], team2=["p7", "p8"],
        status='in_progress'
    )
    session.matches.append(match2)
    complete_match(session, "m2", 11, 7)

    # Now check seeded vs unseeded for Charlie (low seed, 1 win) vs Frank (high seed, 1 win)
    charlie_stats = session.player_stats["p3"]
    frank_stats = session.player_stats["p6"]

    # Both have 1 win, 0 losses
    assert charlie_stats.wins == 1 and charlie_stats.losses == 0
    assert frank_stats.wins == 1 and frank_stats.losses == 0

    # Seeded ELO: Frank should be much higher (5.0 seed base) than Charlie (3.0 seed base)
    charlie_seeded = calculate_player_elo_rating(session, "p3")
    frank_seeded = calculate_player_elo_rating(session, "p6")
    print(f"Charlie seeded ELO: {charlie_seeded:.0f} (seed 3.0)")
    print(f"Frank seeded ELO:   {frank_seeded:.0f} (seed 5.0)")
    assert frank_seeded > charlie_seeded + 100, \
        f"Seeded: Frank ({frank_seeded:.0f}) should be much higher than Charlie ({charlie_seeded:.0f})"

    # Unseeded ELO: Both should be very similar (same record, similar point differentials)
    charlie_unseeded = calculate_elo_rating_unseeded(charlie_stats)
    frank_unseeded = calculate_elo_rating_unseeded(frank_stats)
    print(f"Charlie unseeded ELO: {charlie_unseeded:.0f}")
    print(f"Frank unseeded ELO:   {frank_unseeded:.0f}")

    # Frank had +4 pt diff, Charlie had +6 pt diff — Charlie should actually be slightly higher unseeded
    assert charlie_unseeded > frank_unseeded, \
        f"Unseeded: Charlie ({charlie_unseeded:.0f}) should be >= Frank ({frank_unseeded:.0f}) due to better pt diff"

    print("\n[PASS] test_unseeded_elo_ignores_seed")


def test_unseeded_elo_base_rating_for_zero_games():
    """Players with no games should get BASE_RATING (1500) regardless of seed."""
    session = _create_preseeded_session()

    alice_stats = session.player_stats["p1"]
    assert alice_stats.games_played == 0

    # Seeded ELO should reflect the seed
    seeded = calculate_player_elo_rating(session, "p1")
    unseeded = calculate_elo_rating_unseeded(alice_stats)

    print(f"Alice (4.5 seed, 0 games) seeded ELO: {seeded:.0f}")
    print(f"Alice (4.5 seed, 0 games) unseeded ELO: {unseeded:.0f}")

    assert unseeded == BASE_RATING, f"Unseeded ELO for 0 games should be {BASE_RATING}, got {unseeded:.0f}"
    assert seeded > BASE_RATING, f"Seeded ELO should reflect seed (> {BASE_RATING}), got {seeded:.0f}"

    print("\n[PASS] test_unseeded_elo_base_rating_for_zero_games")


def test_unseeded_ranking_differs_from_seeded():
    """
    Demonstrate that unseeded rankings can differ from seeded rankings.
    A low-seeded player who performs well should rank higher unseeded than seeded.
    """
    session = _create_preseeded_session()

    # Match 1: Charlie (3.0 seed) + Eve (2.5 seed) beat Alice (4.5) + Frank (5.0)
    m1 = Match(id="m1", court_number=1, team1=["p3", "p5"], team2=["p1", "p6"], status='in_progress')
    session.matches.append(m1)
    complete_match(session, "m1", 11, 3)

    # Match 2: Bob (4.0) + Diana (3.5) beat Grace (3.0) + Hank (3.5)
    m2 = Match(id="m2", court_number=2, team1=["p2", "p4"], team2=["p7", "p8"], status='in_progress')
    session.matches.append(m2)
    complete_match(session, "m2", 11, 9)

    # Seeded rankings
    seeded_rankings = []
    for p in session.config.players:
        if p.id in session.active_players:
            elo = calculate_player_elo_rating(session, p.id)
            seeded_rankings.append((p.name, p.id, elo))
    seeded_rankings.sort(key=lambda x: x[2], reverse=True)

    # Unseeded rankings
    unseeded_rankings = []
    for p in session.config.players:
        if p.id in session.active_players:
            stats = session.player_stats[p.id]
            elo = calculate_elo_rating_unseeded(stats)
            unseeded_rankings.append((p.name, p.id, elo))
    unseeded_rankings.sort(key=lambda x: x[2], reverse=True)

    print("Seeded rankings:")
    for rank, (name, pid, elo) in enumerate(seeded_rankings, 1):
        print(f"  #{rank} {name}: {elo:.0f}")

    print("\nUnseeded rankings:")
    for rank, (name, pid, elo) in enumerate(unseeded_rankings, 1):
        print(f"  #{rank} {name}: {elo:.0f}")

    seeded_order = [r[1] for r in seeded_rankings]
    unseeded_order = [r[1] for r in unseeded_rankings]

    # Rankings should differ because seeds influence the seeded order
    assert seeded_order != unseeded_order, \
        "Seeded and unseeded rankings should differ when low-seeded players outperform"

    # In unseeded: Charlie/Eve (won 11-3) should be top — they had the best performance
    unseeded_top2 = {unseeded_rankings[0][1], unseeded_rankings[1][1]}
    assert "p3" in unseeded_top2 or "p5" in unseeded_top2, \
        "Charlie or Eve should be in top 2 unseeded (they won 11-3)"

    print("\n[PASS] test_unseeded_ranking_differs_from_seeded")


def test_unseeded_function_matches_legacy_no_seed():
    """Unseeded function should produce same results as legacy calculate_elo_rating with no seed."""
    stats = PlayerStats(player_id="test")
    stats.games_played = 5
    stats.wins = 3
    stats.losses = 2
    stats.total_points_for = 50
    stats.total_points_against = 40

    unseeded = calculate_elo_rating_unseeded(stats)
    legacy_no_seed = calculate_elo_rating(stats, pre_seeded_rating=None)

    print(f"Unseeded ELO: {unseeded:.2f}")
    print(f"Legacy (no seed) ELO: {legacy_no_seed:.2f}")

    assert abs(unseeded - legacy_no_seed) < 0.01, \
        f"Unseeded ({unseeded:.2f}) should match legacy no-seed ({legacy_no_seed:.2f})"

    print("\n[PASS] test_unseeded_function_matches_legacy_no_seed")


if __name__ == '__main__':
    test_unseeded_elo_ignores_seed()
    print()
    test_unseeded_elo_base_rating_for_zero_games()
    print()
    test_unseeded_ranking_differs_from_seeded()
    print()
    test_unseeded_function_matches_legacy_no_seed()
    print("\n✅ All unseeded export tests passed!")
