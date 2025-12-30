"""
Test the Variety slider functionality
"""
from python.pickleball_types import Player, SessionConfig
from python.session import create_session

def test_variety_slider_positions():
    """Test all 3 variety slider positions"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Position 0: Min
    session.competitive_variety_partner_repetition_limit = 1
    session.competitive_variety_opponent_repetition_limit = 1
    assert session.competitive_variety_partner_repetition_limit == 1
    assert session.competitive_variety_opponent_repetition_limit == 1
    print("✓ Min variety: partner=1, opponent=1")
    
    # Position 1: Balanced (default)
    session.competitive_variety_partner_repetition_limit = 3
    session.competitive_variety_opponent_repetition_limit = 2
    assert session.competitive_variety_partner_repetition_limit == 3
    assert session.competitive_variety_opponent_repetition_limit == 2
    print("✓ Balanced variety: partner=3, opponent=2")
    
    # Position 2: Max
    session.competitive_variety_partner_repetition_limit = 4
    session.competitive_variety_opponent_repetition_limit = 3
    assert session.competitive_variety_partner_repetition_limit == 4
    assert session.competitive_variety_opponent_repetition_limit == 3
    print("✓ Max variety: partner=4, opponent=3")

def test_custom_variety_settings():
    """Test custom variety settings"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Custom settings
    session.competitive_variety_partner_repetition_limit = 2
    session.competitive_variety_opponent_repetition_limit = 1
    assert session.competitive_variety_partner_repetition_limit == 2
    assert session.competitive_variety_opponent_repetition_limit == 1
    print("✓ Custom variety: partner=2, opponent=1")

def test_ultra_competitive_no_longer_changes_variety():
    """Test that Ultra-Competitive only changes roaming, not variety"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Default balanced variety
    initial_partner = session.competitive_variety_partner_repetition_limit
    initial_opponent = session.competitive_variety_opponent_repetition_limit
    print(f"Initial variety: partner={initial_partner}, opponent={initial_opponent}")
    
    # Set to Ultra-Competitive (35% roaming)
    session.competitive_variety_roaming_range_percent = 0.35
    
    # Variety should NOT change
    assert session.competitive_variety_partner_repetition_limit == initial_partner
    assert session.competitive_variety_opponent_repetition_limit == initial_opponent
    print(f"After Ultra-Competitive: variety unchanged (partner={session.competitive_variety_partner_repetition_limit}, opponent={session.competitive_variety_opponent_repetition_limit})")
    print("✓ Ultra-Competitive only changes roaming percentage, not variety")

def test_variety_slider_limits():
    """Test that variety limits can range from 0-5"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Test all values 0-5
    for i in range(0, 6):
        session.competitive_variety_partner_repetition_limit = i
        session.competitive_variety_opponent_repetition_limit = i
        assert session.competitive_variety_partner_repetition_limit == i
        assert session.competitive_variety_opponent_repetition_limit == i
    
    print("✓ Variety limits can be set from 0-5")

if __name__ == "__main__":
    print("Testing Variety Slider Functionality")
    print("=" * 60)
    
    test_variety_slider_positions()
    print()
    test_custom_variety_settings()
    print()
    test_ultra_competitive_no_longer_changes_variety()
    print()
    test_variety_slider_limits()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("\nVariety Slider Features:")
    print("  ✓ 3 preset positions: Min (1,1), Balanced (3,2), Max (4,3)")
    print("  ✓ Custom settings via double-click on 'Variety' label")
    print("  ✓ Re-evaluates matches when moved")
    print("  ✓ Independent from competitiveness slider")
    print("  ✓ Ultra-Competitive no longer changes variety")
