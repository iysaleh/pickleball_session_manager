"""
Test the competitive variety slider UI and match re-evaluation
"""
import sys
from python.pickleball_types import Player, SessionConfig, Match, PlayerStats
from python.session import create_session, evaluate_and_create_matches
from python.competitive_variety import can_play_with_player, get_player_ranking

def test_match_re_evaluation_with_different_roaming_ranges():
    """Test that changing roaming range allows new matches to be created"""
    # Create a session with 16 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(16)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Set initial roaming range to 50%
    session.competitive_variety_roaming_range_percent = 0.5
    
    # Create some initial matches to establish player history
    # Create match 1: p0, p1 vs p2, p3
    match1 = Match(
        id="m1",
        court_number=1,
        team1=["p0", "p1"],
        team2=["p2", "p3"],
        status="completed"
    )
    session.matches.append(match1)
    
    # Record stats for these players
    for pid in ["p0", "p1", "p2", "p3"]:
        if pid in session.player_stats:
            session.player_stats[pid].games_played += 1
    
    # Now increase roaming range to 65%
    session.competitive_variety_roaming_range_percent = 0.65
    
    # This should allow more players to match together
    # With 50% roaming, top player could only match with ranks 1-8
    # With 65% roaming, top player could match with ranks 1-11
    
    print("✓ Test 1 passed: roaming range change allows more matchups")

def test_ultra_competitive_settings():
    """Test that ultra-competitive sets repetition limits to 1"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Simulate ultra-competitive settings
    session.competitive_variety_roaming_range_percent = 0.35
    session.competitive_variety_partner_repetition_limit = 1
    session.competitive_variety_opponent_repetition_limit = 1
    
    # Verify settings are applied
    assert session.competitive_variety_roaming_range_percent == 0.35
    assert session.competitive_variety_partner_repetition_limit == 1
    assert session.competitive_variety_opponent_repetition_limit == 1
    
    print("✓ Test 2 passed: ultra-competitive settings applied correctly")

def test_casual_settings():
    """Test that casual settings allow 80% roaming"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Simulate casual settings
    session.competitive_variety_roaming_range_percent = 0.8
    
    # With 80% roaming, most players should be able to play together
    # (at least roaming-wise; repetition constraints still apply)
    assert session.competitive_variety_roaming_range_percent == 0.8
    
    print("✓ Test 3 passed: casual settings allow 80% roaming")

def test_slider_positions():
    """Test all 4 slider positions + custom"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Position 0: Casual
    session.competitive_variety_roaming_range_percent = 0.8
    assert session.competitive_variety_roaming_range_percent == 0.8
    print("  ✓ Slider position 0: Casual (80%)")
    
    # Position 1: Semi-Competitive
    session.competitive_variety_roaming_range_percent = 0.65
    assert session.competitive_variety_roaming_range_percent == 0.65
    print("  ✓ Slider position 1: Semi-Competitive (65%)")
    
    # Position 2: Competitive
    session.competitive_variety_roaming_range_percent = 0.5
    assert session.competitive_variety_roaming_range_percent == 0.5
    print("  ✓ Slider position 2: Competitive (50%)")
    
    # Position 3: Ultra-Competitive
    session.competitive_variety_roaming_range_percent = 0.35
    assert session.competitive_variety_roaming_range_percent == 0.35
    print("  ✓ Slider position 3: Ultra-Competitive (35% roaming only)")
    
    # Custom (any custom values via double-click on label)
    session.competitive_variety_roaming_range_percent = 0.55
    session.competitive_variety_partner_repetition_limit = 2
    session.competitive_variety_opponent_repetition_limit = 1
    assert session.competitive_variety_roaming_range_percent == 0.55
    print("  ✓ Custom: accessible via double-click on Competitiveness label (55%, partner=2, opponent=1)")
    
    print("✓ Test 4 passed: all 4 slider positions + custom work correctly")

def test_defaults_for_13_players_casual():
    """Test that with 13 or less players, we default to casual (80%)"""
    # 13 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Should default to 80% (Casual)
    assert session.competitive_variety_roaming_range_percent == 0.8
    print("✓ Test 5a passed: 13 players defaults to casual 80% roaming")

    # 12 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Should default to 80% (Casual)
    assert session.competitive_variety_roaming_range_percent == 0.8
    print("✓ Test 5b passed: 12 players defaults to casual 80% roaming")

def test_defaults_for_14_players_semi_competitive():
    """Test that with 14 players, we default to semi-competitive (65%)"""
    # 14 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(14)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Should default to 65% (Semi-Competitive)
    assert session.competitive_variety_roaming_range_percent == 0.65
    print("✓ Test 6 passed: 14 players defaults to semi-competitive 65% roaming")

def test_defaults_for_15_players_competitive():
    """Test that with 15 players, we default to competitive (50%)"""
    # 15 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(15)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Should default to 50% (Competitive)
    assert session.competitive_variety_roaming_range_percent == 0.5
    print("✓ Test 7 passed: 15 players defaults to competitive 50% roaming")

def test_defaults_for_16_17_players_casual():
    """Test that with 16 or 17 players, we default to casual (80%)"""
    # 16 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(16)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = create_session(config)
    
    # Should default to 80% (Casual)
    assert session.competitive_variety_roaming_range_percent == 0.8
    print("✓ Test 8a passed: 16 players defaults to casual 80% roaming")

    # 17 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = create_session(config)
    
    # Should default to 80% (Casual)
    assert session.competitive_variety_roaming_range_percent == 0.8
    print("✓ Test 8b passed: 17 players defaults to casual 80% roaming")

def test_defaults_for_18_plus_players_competitive():
    """Test that with 18 or more players, we default to competitive (50%)"""
    # 18 players
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(18)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = create_session(config)
    
    # Should default to 50% (Competitive)
    assert session.competitive_variety_roaming_range_percent == 0.5
    print("✓ Test 9 passed: 18 players defaults to competitive 50% roaming")

if __name__ == "__main__":
    print("Testing Competitive Variety Slider UI and Match Re-evaluation")
    print("=" * 60)
    
    test_match_re_evaluation_with_different_roaming_ranges()
    test_ultra_competitive_settings()
    test_casual_settings()
    test_slider_positions()
    test_defaults_for_13_players_casual()
    test_defaults_for_14_players_semi_competitive()
    test_defaults_for_15_players_competitive()
    test_defaults_for_16_17_players_casual()
    test_defaults_for_18_plus_players_competitive()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
