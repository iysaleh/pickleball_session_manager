#!/usr/bin/env python3
"""
Test the both-sided gap requirement for Partner-Opponent-Partner pattern

This test shows that BOTH players must have played other games before
they can be partners again after being opponents.
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import check_partner_opponent_partner_pattern, apply_adaptive_constraints
from datetime import datetime

def test_both_sided_gap_requirement():
    """Test that both players must have gap games before re-partnering"""
    
    print("BOTH-SIDED GAP REQUIREMENT TEST")
    print("=" * 40)
    
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
    session.matches = session.matches[-10:]  # Clean slate
    
    print("=== BASE SEQUENCE ===")
    print()
    
    # Step 1: Partners
    match1 = Match(
        id="base_1",
        court_number=1,
        team1=['p1', 'p2'],  # p1 & p2 PARTNERS
        team2=['p3', 'p4'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match1)
    print("Match 1: p1 & p2 as PARTNERS vs p3 & p4")
    
    # Step 2: Opponents
    match2 = Match(
        id="base_2",
        court_number=1,
        team1=['p1', 'p5'],  # p1 & p2 OPPONENTS
        team2=['p2', 'p6'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match2)
    print("Match 2: p1 & p5 vs p2 & p6 (p1 & p2 OPPONENTS)")
    print()
    
    # Test immediate re-partnering (should be blocked)
    print("=== SCENARIO 1: IMMEDIATE RE-PARTNERING (should be blocked) ===")
    pattern_immediate = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Immediate pattern detected: {pattern_immediate}")
    print("Expected: True (should block - no gap games yet)")
    print()
    
    # Test one-sided gap (should still be blocked)
    print("=== SCENARIO 2: ONE-SIDED GAP (should be blocked) ===")
    
    match3_one_sided = Match(
        id="one_sided",
        court_number=1,
        team1=['p1', 'p7'],  # Only p1 plays
        team2=['p3', 'p8'],  # p2 doesn't play
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match3_one_sided)
    print("Match 3: p1 & p7 vs p3 & p8 (only p1 plays, p2 sits out)")
    
    pattern_one_sided = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"One-sided gap pattern detected: {pattern_one_sided}")
    print("Expected: True (should block - p2 didn't have gap game)")
    print()
    
    # Test both-sided gap (should be allowed)
    print("=== SCENARIO 3: BOTH-SIDED GAP (should be allowed) ===")
    
    match4_other_side = Match(
        id="other_side",
        court_number=1,
        team1=['p2', 'p4'],  # Now p2 plays too
        team2=['p5', 'p6'],  # p1 doesn't play this one
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match4_other_side)
    print("Match 4: p2 & p4 vs p5 & p6 (now p2 plays, p1 sits out)")
    print("→ Both players have now played other games since being opponents")
    
    pattern_both_sided = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Both-sided gap pattern detected: {pattern_both_sided}")
    print("Expected: False (should allow - both players had gap games)")
    print()
    
    print("=== SCENARIO 4: DIFFERENT ORDER TEST ===")
    print()
    
    # Clear session for new test
    session.matches = session.matches[:-4]  # Remove test matches
    
    # Create sequence with different gap order
    matches = [
        (['p1', 'p2'], ['p3', 'p4'], "p1 & p2 PARTNERS"),
        (['p1', 'p5'], ['p2', 'p6'], "p1 & p2 OPPONENTS"),
        (['p2', 'p7'], ['p3', 'p8'], "p2 plays gap game"),
        (['p1', 'p4'], ['p5', 'p7'], "p1 plays gap game"),
    ]
    
    for team1, team2, description in matches:
        match = Match(
            id=f"order_{len(session.matches)}",
            court_number=1,
            team1=team1,
            team2=team2,
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(match)
        print(f"Match: {description}")
    
    pattern_different_order = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Different order pattern detected: {pattern_different_order}")
    print("Expected: False (should allow - both had gap games, different order)")
    print()
    
    # Summary
    print("=== SUMMARY ===")
    print()
    print("✅ ALLOWED: Partners → Opponents → [Both players play other games] → Partners")
    print("🚫 BLOCKED: Partners → Opponents → [Only one or neither plays] → Partners")
    print()
    print(f"Results:")
    print(f"  Immediate: {pattern_immediate} (should be True)")
    print(f"  One-sided: {pattern_one_sided} (should be True)") 
    print(f"  Both-sided: {pattern_both_sided} (should be False)")
    print(f"  Different order: {pattern_different_order} (should be False)")
    print()
    
    if pattern_immediate and pattern_one_sided and not pattern_both_sided and not pattern_different_order:
        print("🎯 SUCCESS: Both-sided gap requirement working correctly!")
        print("   • Blocks immediate re-partnering")
        print("   • Blocks one-sided gaps") 
        print("   • Allows both-sided gaps")
        print("   • Works regardless of gap game order")
    else:
        print("❌ Issue with both-sided gap logic")

def test_edge_cases():
    """Test edge cases for the both-sided gap requirement"""
    
    print("\n\nEDGE CASES TEST")
    print("=" * 20)
    
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
            id=f"edge_{i}",
            court_number=1,
            team1=['p7', 'p8'],
            team2=['p5', 'p6'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    apply_adaptive_constraints(session)
    session.matches = session.matches[-10:]
    
    # Edge case 1: Multiple gap games
    print("Edge case 1: Multiple gap games")
    matches = [
        (['p1', 'p2'], ['p3', 'p4'], "Partners"),
        (['p1', 'p5'], ['p2', 'p6'], "Opponents"), 
        (['p1', 'p7'], ['p3', 'p8'], "p1 gap 1"),
        (['p2', 'p4'], ['p5', 'p7'], "p2 gap 1"),
        (['p1', 'p3'], ['p4', 'p8'], "p1 gap 2"),
        (['p2', 'p5'], ['p6', 'p7'], "p2 gap 2"),
    ]
    
    for team1, team2, desc in matches:
        match = Match(
            id=f"multi_{len(session.matches)}",
            court_number=1,
            team1=team1,
            team2=team2,
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(match)
    
    pattern = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Multiple gaps pattern: {pattern} (should be False)")
    
    # Edge case 2: No prior partnership
    pattern_no_prior = check_partner_opponent_partner_pattern(session, 'p1', 'p3')
    print(f"No prior partnership: {pattern_no_prior} (should be False)")

def run_both_sided_gap_tests():
    """Run all both-sided gap requirement tests"""
    try:
        test_both_sided_gap_requirement()
        test_edge_cases()
        
        print(f"\n{'=' * 70}")
        print("✅ BOTH-SIDED GAP REQUIREMENT TESTS COMPLETED!")
        print()
        print("🎯 CORRECTED CONSTRAINT LOGIC:")
        print("   • Partners → Opponents → Partners (BLOCKED - immediate)")
        print("   • Partners → Opponents → [One plays] → Partners (BLOCKED - one-sided gap)")
        print("   • Partners → Opponents → [Both play] → Partners (ALLOWED - both-sided gap)")
        print()
        print("🧠 ALGORITHM:")
        print("   1. Find last game where both players played together")
        print("   2. If they were opponents, check for prior partnership")
        print("   3. Count games since opponents match for EACH player")
        print("   4. Block unless BOTH players have played at least one game since")
        print()
        print("⚖️ BENEFIT:")
        print("   • Prevents one player from 'waiting out' on bench")
        print("   • Ensures both players have had social/competitive break")
        print("   • More fair and balanced constraint application")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_both_sided_gap_tests()