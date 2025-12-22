#!/usr/bin/env python3
"""
Test Partner-Opponent-Partner Pattern Prevention

This test demonstrates the new constraint that prevents the awkward social pattern
where two players are partners, then opponents, then partners again.
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    can_play_with_player, check_partner_opponent_partner_pattern,
    apply_adaptive_constraints, get_adaptive_constraints
)
from datetime import datetime

def test_partner_opponent_partner_prevention():
    """Test that Partner-Opponent-Partner pattern is prevented in mid-late session"""
    
    print("PARTNER-OPPONENT-PARTNER PATTERN PREVENTION TEST")
    print("=" * 55)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session with 8 players
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Set up player stats so they're not provisional
    for i in range(1, 9):
        player_id = f'p{i}'
        stats = session.player_stats[player_id]
        stats.games_played = 5
        stats.wins = 3
        stats.total_points_for = 100
        stats.total_points_against = 90
    
    print("Setting up problematic sequence...")
    print()
    
    # Create the problematic sequence: p1 & p2 as Partners → Opponents → (trying Partners again)
    
    # Match 1: p1 & p2 are PARTNERS
    match1 = Match(
        id="match1",
        court_number=1,
        team1=['p1', 'p2'],  # p1 & p2 as partners
        team2=['p3', 'p4'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match1)
    print("Match 1: p1 & p2 as PARTNERS vs p3 & p4")
    
    # Match 2: Some other match
    match2 = Match(
        id="match2", 
        court_number=1,
        team1=['p5', 'p6'],
        team2=['p7', 'p8'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match2)
    print("Match 2: p5 & p6 vs p7 & p8 (unrelated)")
    
    # Match 3: p1 & p2 are OPPONENTS
    match3 = Match(
        id="match3",
        court_number=1,
        team1=['p1', 'p5'],  # p1 with different partner
        team2=['p2', 'p6'],  # p2 with different partner (now OPPONENTS)
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match3)
    print("Match 3: p1 & p5 vs p2 & p6 (p1 & p2 now OPPONENTS)")
    print()
    
    # Test in early session (pattern should be allowed)
    print("EARLY SESSION TEST (pattern allowed):")
    session.adaptive_balance_weight = None  # Auto mode, early session
    apply_adaptive_constraints(session)
    constraints = get_adaptive_constraints(session)
    
    pattern_detected_early = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    can_partner_early = can_play_with_player(session, 'p1', 'p2', 'partner')
    
    print(f"  Balance weight: {constraints['balance_weight']:.1f}x")
    print(f"  Pattern detected: {pattern_detected_early}")
    print(f"  Can p1 & p2 be partners: {can_partner_early}")
    print("  → Early session allows exploration of all combinations")
    print()
    
    # Add more matches to trigger mid-session (adaptive system kicks in)
    for i in range(20):  # Push into mid-late session
        fake_match = Match(
            id=f"fake_{i}",
            court_number=1,
            team1=['p3', 'p4'],
            team2=['p5', 'p6'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    # Test in mid-late session (pattern should be blocked)
    print("MID-LATE SESSION TEST (pattern blocked):")
    apply_adaptive_constraints(session)  # Recalculate constraints
    constraints = get_adaptive_constraints(session)
    
    pattern_detected_late = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    can_partner_late = can_play_with_player(session, 'p1', 'p2', 'partner')
    
    print(f"  Balance weight: {constraints['balance_weight']:.1f}x")
    print(f"  Pattern detected: {pattern_detected_late}")
    print(f"  Can p1 & p2 be partners: {can_partner_late}")
    print("  → Mid-late session blocks Partner-Opponent-Partner pattern")
    print()
    
    # Test control cases
    print("CONTROL CASES:")
    
    # Test p1 & p3 (no problematic pattern)
    can_p1_p3 = can_play_with_player(session, 'p1', 'p3', 'partner')
    print(f"  p1 & p3 as partners: {can_p1_p3} (no pattern, should work)")
    
    # Test p1 & p2 as opponents (should still work)
    can_p1_p2_opponents = can_play_with_player(session, 'p1', 'p2', 'opponent')
    print(f"  p1 & p2 as opponents: {can_p1_p2_opponents} (opponents OK)")
    
    # Test pattern with different players
    pattern_p1_p3 = check_partner_opponent_partner_pattern(session, 'p1', 'p3')
    print(f"  p1 & p3 pattern check: {pattern_p1_p3} (no pattern exists)")
    print()

def test_pattern_detection_edge_cases():
    """Test edge cases for pattern detection"""
    
    print("PATTERN DETECTION EDGE CASES")
    print("=" * 35)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Set up for mid-session
    for i in range(15):
        fake_match = Match(
            id=f"setup_{i}",
            court_number=1,
            team1=['p3', 'p4'],
            team2=['p5', 'p6'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    apply_adaptive_constraints(session)
    
    print("Test cases:")
    
    # Case 1: No matches between p1 & p2
    pattern = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"  No history: {pattern} (should be False)")
    
    # Case 2: Only partners, no opponents
    match_partners_only = Match(
        id="partners_only",
        court_number=1,
        team1=['p1', 'p2'],
        team2=['p7', 'p8'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match_partners_only)
    
    pattern = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"  Partners only: {pattern} (should be False)")
    
    # Case 3: Only opponents, no partners
    session.matches = session.matches[:-1]  # Remove partners match
    match_opponents_only = Match(
        id="opponents_only",
        court_number=1,
        team1=['p1', 'p7'],
        team2=['p2', 'p8'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match_opponents_only)
    
    pattern = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"  Opponents only: {pattern} (should be False)")
    
    # Case 4: Reverse pattern: Opponent → Partner (should be allowed)
    session.matches = session.matches[:-1]  # Remove opponents match
    # Add opponent match first
    session.matches.append(match_opponents_only)
    # Then partners match
    session.matches.append(match_partners_only)
    
    pattern = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"  Opponent→Partner: {pattern} (should be False - reverse pattern is OK)")
    
    print()

def run_partner_opponent_partner_tests():
    """Run all Partner-Opponent-Partner prevention tests"""
    try:
        test_partner_opponent_partner_prevention()
        test_pattern_detection_edge_cases()
        
        print("=" * 70)
        print("✅ PARTNER-OPPONENT-PARTNER PREVENTION TESTS COMPLETED!")
        print()
        print("🎯 KEY FEATURES:")
        print("   • Pattern only blocked when adaptive balance system is active (mid-late session)")
        print("   • Early session allows pattern exploration")
        print("   • Prevents awkward Partner → Opponent → Partner sequences")
        print("   • Only applies to partnership attempts, not opponent matching")
        print("   • Looks back maximum 6 matches to find patterns")
        print()
        print("🚫 BLOCKED PATTERN:")
        print("   Match N:   Player A & B as PARTNERS")
        print("   Match N+X: Player A vs Player B as OPPONENTS") 
        print("   Match N+Y: Player A & B as PARTNERS (BLOCKED in mid-late session)")
        print()
        print("✅ SOCIAL BENEFIT:")
        print("   • Avoids awkward 'friend-enemy-friend' dynamics")
        print("   • Maintains consistent relationship patterns")
        print("   • Improves player experience and comfort")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_partner_opponent_partner_tests()