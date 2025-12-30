#!/usr/bin/env python3
"""
Test the corrected Partner-Opponent-Partner pattern logic

This test shows that we allow Partners → Opponents → Other Game → Partners
but block Partners → Opponents → Partners (immediate sequence)
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import check_partner_opponent_partner_pattern, apply_adaptive_constraints
from datetime import datetime

def test_immediate_vs_gapped_patterns():
    """Test that immediate patterns are blocked but gapped patterns are allowed"""
    
    print("IMMEDIATE vs GAPPED PARTNER-OPPONENT-PARTNER TEST")
    print("=" * 55)
    
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
    
    # Set up late session
    for i in range(20):
        fake_match = Match(
            id=f"setup_{i}",
            court_number=1,
            team1=['p7', 'p8'],
            team2=['p5', 'p6'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    apply_adaptive_constraints(session)
    session.matches = session.matches[-10:]  # Clean slate for test
    
    print("=== SCENARIO 1: IMMEDIATE PATTERN (should be blocked) ===")
    print()
    
    # Create immediate Partners → Opponents → Partners sequence
    match1 = Match(
        id="immediate_1",
        court_number=1,
        team1=['p1', 'p2'],  # p1 & p2 PARTNERS
        team2=['p3', 'p4'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match1)
    print("Match 1: p1 & p2 as PARTNERS vs p3 & p4")
    
    match2 = Match(
        id="immediate_2",
        court_number=1,
        team1=['p1', 'p5'],  # p1 & p2 OPPONENTS
        team2=['p2', 'p6'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match2)
    print("Match 2: p1 & p5 vs p2 & p6 (p1 & p2 OPPONENTS)")
    
    # Test if immediate partnership is blocked
    pattern_immediate = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Immediate pattern detected: {pattern_immediate}")
    print("Expected: True (should block immediate Partners after Opponents)")
    print()
    
    print("=== SCENARIO 2: GAPPED PATTERN (should be allowed) ===")
    print()
    
    # Clear session for new test
    session.matches = session.matches[:-2]  # Remove the immediate test matches
    
    # Create gapped Partners → Opponents → Other Game → Partners sequence
    match1_gap = Match(
        id="gap_1",
        court_number=1,
        team1=['p1', 'p2'],  # p1 & p2 PARTNERS
        team2=['p3', 'p4'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match1_gap)
    print("Match 1: p1 & p2 as PARTNERS vs p3 & p4")
    
    match2_gap = Match(
        id="gap_2",
        court_number=1,
        team1=['p1', 'p5'],  # p1 & p2 OPPONENTS
        team2=['p2', 'p6'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match2_gap)
    print("Match 2: p1 & p5 vs p2 & p6 (p1 & p2 OPPONENTS)")
    
    match3_gap = Match(
        id="gap_3",
        court_number=1,
        team1=['p1', 'p7'],  # p1 plays with someone else (gap game)
        team2=['p3', 'p8'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match3_gap)
    print("Match 3: p1 & p7 vs p3 & p8 (p1 plays other game, p2 not involved)")
    
    # Test if partnership is now allowed after gap
    pattern_gapped = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Gapped pattern detected: {pattern_gapped}")
    print("Expected: False (should allow Partners after gap game)")
    print()
    
    print("=== SCENARIO 3: NO PRIOR PARTNERSHIP (should be allowed) ===")
    print()
    
    # Test players who were only opponents (no prior partnership)
    pattern_no_prior = check_partner_opponent_partner_pattern(session, 'p1', 'p5')
    print("Testing p1 & p5 (they were only opponents, never partners)")
    print(f"Pattern detected: {pattern_no_prior}")
    print("Expected: False (no prior partnership, so no pattern)")
    print()
    
    # Summary
    print("=== SUMMARY ===")
    print()
    print("✅ ALLOWED patterns:")
    print("   • Partners → Opponents → Other Games → Partners")
    print("   • Players who were never partners before")
    print("   • Any partnership in early session")
    print()
    print("🚫 BLOCKED patterns:")
    print("   • Partners → Opponents → Partners (immediate sequence)")
    print("   • Only in mid-late session when adaptive balance active")
    print()
    
    if pattern_immediate and not pattern_gapped and not pattern_no_prior:
        print("🎯 SUCCESS: Constraint working exactly as intended!")
        print("   Blocks immediate awkward sequences")
        print("   Allows natural progression with gaps")
    else:
        print("❌ Issue: Pattern detection not working as expected")
        print(f"   Immediate: {pattern_immediate} (should be True)")
        print(f"   Gapped: {pattern_gapped} (should be False)")
        print(f"   No prior: {pattern_no_prior} (should be False)")

if __name__ == "__main__":
    test_immediate_vs_gapped_patterns()