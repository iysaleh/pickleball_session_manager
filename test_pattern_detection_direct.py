#!/usr/bin/env python3
"""
Direct test of the player-specific pattern detection logic
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import check_partner_opponent_partner_pattern, apply_adaptive_constraints
from datetime import datetime

def test_player_specific_pattern_detection():
    """Test pattern detection using player-specific match histories"""
    
    print("PLAYER-SPECIFIC PATTERN DETECTION TEST")
    print("=" * 45)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session with 6 players to show the difference
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 7)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session = create_session(config)
    
    # Add matches to trigger late session
    for i in range(20):
        fake_match = Match(
            id=f"trigger_{i}",
            court_number=1,
            team1=['p5', 'p6'],
            team2=['p3', 'p4'],
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(fake_match)
    
    apply_adaptive_constraints(session)
    
    # Clear trigger matches for clean test
    session.matches = session.matches[-10:]  # Keep some to stay in late session
    
    print("Creating specific match sequence to test player-specific history:")
    print()
    
    # Match 1: p1 & p2 are PARTNERS (other match also happening)
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
    
    # Match 2: p1 sits out, p2 plays with others (breaks the sequence globally but not for p1)
    match2 = Match(
        id="match2",
        court_number=1,
        team1=['p2', 'p5'],  # p1 not playing
        team2=['p3', 'p6'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match2)
    print("Match 2: p2 & p5 vs p3 & p6 (p1 sits out)")
    
    # Match 3: p1 & p2 are OPPONENTS
    match3 = Match(
        id="match3",
        court_number=1,
        team1=['p1', 'p5'],  # p1 with p5
        team2=['p2', 'p6'],  # p2 with p6 (p1 vs p2!)
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match3)
    print("Match 3: p1 & p5 vs p2 & p6 (p1 & p2 now OPPONENTS)")
    print()
    
    # Test pattern detection from p1's perspective
    print("PLAYER-SPECIFIC ANALYSIS:")
    print()
    
    # Get p1's match history
    p1_matches = []
    for match in session.matches[-3:]:  # Last 3 matches we added
        if 'p1' in match.team1 or 'p1' in match.team2:
            p1_matches.append(match)
    
    print("p1's personal match history:")
    for i, match in enumerate(p1_matches, 1):
        if 'p1' in match.team1:
            p1_team = match.team1
            other_team = match.team2
        else:
            p1_team = match.team2
            other_team = match.team1
        
        if 'p2' in p1_team:
            relationship = "PARTNERS"
        elif 'p2' in other_team:
            relationship = "OPPONENTS"
        else:
            relationship = "No p2"
        
        print(f"  Match {i}: {match.team1} vs {match.team2} → p1 & p2 are {relationship}")
    
    # Test pattern detection
    pattern_detected = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"\nPattern detected (p1 & p2): {pattern_detected}")
    print("Expected: True (p1's history shows Partners → Opponents sequence)")
    
    # Test from p2's perspective (should be same result)
    pattern_detected_p2 = check_partner_opponent_partner_pattern(session, 'p2', 'p1')
    print(f"Pattern detected (p2 & p1): {pattern_detected_p2}")
    print("Expected: True (p2's history also shows Partners → Opponents sequence)")
    
    # Test control case - players who haven't had this pattern
    pattern_p1_p3 = check_partner_opponent_partner_pattern(session, 'p1', 'p3')
    print(f"Pattern detected (p1 & p3): {pattern_p1_p3}")
    print("Expected: False (no Partner → Opponent sequence)")
    
    print()
    print("🔍 KEY INSIGHT: Player-Specific History")
    print("   • Each player's personal match history is analyzed")
    print("   • Pattern detected based on their individual experience")
    print("   • Global matches that don't involve the player are ignored")
    print("   • More accurate social dynamic tracking")

def test_global_vs_player_specific_difference():
    """Demonstrate the difference between global and player-specific pattern detection"""
    
    print("\n\nGLOBAL vs PLAYER-SPECIFIC COMPARISON")
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
    for i in range(15):
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
    
    print("Creating scenario where global vs player-specific matters:")
    print()
    
    # Create interleaved matches where p1 & p2 have pattern but it's not obvious globally
    matches = [
        (["p1", "p2"], ["p3", "p4"], "p1&p2 PARTNERS"),
        (["p5", "p6"], ["p7", "p8"], "Other match"),  
        (["p3", "p5"], ["p7", "p1"], "Other match (p1 plays)"),
        (["p2", "p6"], ["p4", "p8"], "Other match (p2 plays)"),
        (["p1", "p5"], ["p2", "p6"], "p1&p2 OPPONENTS"),
    ]
    
    for team1, team2, description in matches:
        match = Match(
            id=f"test_{len(session.matches)}",
            court_number=1,
            team1=team1,
            team2=team2,
            status='completed',
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        session.matches.append(match)
        print(f"Match {len(session.matches)-15}: {description}")
    
    print()
    
    # Show p1's specific history with p2
    p1_matches = [m for m in session.matches[-5:] if 'p1' in m.team1 or 'p1' in m.team2]
    print("p1's personal matches involving p2:")
    
    p1_p2_relationships = []
    for match in p1_matches:
        if 'p2' in match.team1 or 'p2' in match.team2:
            if ('p1' in match.team1 and 'p2' in match.team1) or ('p1' in match.team2 and 'p2' in match.team2):
                p1_p2_relationships.append("PARTNERS")
                print(f"  {match.team1} vs {match.team2} → PARTNERS")
            elif ('p1' in match.team1 and 'p2' in match.team2) or ('p1' in match.team2 and 'p2' in match.team1):
                p1_p2_relationships.append("OPPONENTS") 
                print(f"  {match.team1} vs {match.team2} → OPPONENTS")
    
    print(f"Relationship sequence: {' → '.join(p1_p2_relationships)}")
    
    # Test detection
    pattern_detected = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Pattern detected: {pattern_detected}")
    
    if pattern_detected and len(p1_p2_relationships) >= 2 and 'PARTNERS' in p1_p2_relationships and 'OPPONENTS' in p1_p2_relationships:
        print("✅ SUCCESS: Player-specific detection working correctly")
        print("   Detected Partners → Opponents sequence in personal history")
    else:
        print("❌ Issue with pattern detection")

def run_player_specific_tests():
    """Run all player-specific pattern detection tests"""
    try:
        test_player_specific_pattern_detection()
        test_global_vs_player_specific_difference()
        
        print(f"\n{'=' * 70}")
        print("✅ PLAYER-SPECIFIC PATTERN DETECTION TESTS COMPLETED!")
        print()
        print("🎯 KEY IMPROVEMENTS:")
        print("   • Uses player-specific match histories (not global)")
        print("   • More accurate tracking of individual player relationships")
        print("   • Properly ignores matches where player wasn't involved")
        print("   • Better social dynamic detection and prevention")
        print()
        print("🧠 ALGORITHM LOGIC:")
        print("   1. Get player1's personal match history")
        print("   2. Track relationships with player2 in chronological order")
        print("   3. Look for Partners → Opponents sequence")
        print("   4. Block if they're trying to be partners again")
        print()
        print("📈 BENEFIT:")
        print("   • More precise social constraint enforcement")
        print("   • Avoids false positives from unrelated matches") 
        print("   • Better player experience through accurate relationship tracking")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_player_specific_tests()