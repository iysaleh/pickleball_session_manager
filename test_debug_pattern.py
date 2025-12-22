#!/usr/bin/env python3
"""
Debug the immediate vs gapped pattern logic
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import check_partner_opponent_partner_pattern, apply_adaptive_constraints
from datetime import datetime

def debug_pattern_detection():
    """Debug pattern detection step by step"""
    
    print("DEBUGGING PATTERN DETECTION")
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
    
    print("Creating gapped sequence:")
    print()
    
    # Step 1: Partners
    match1 = Match(
        id="gap_1",
        court_number=1,
        team1=['p1', 'p2'],  # p1 & p2 PARTNERS
        team2=['p3', 'p4'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match1)
    print("Match 1: p1 & p2 as PARTNERS")
    
    # Step 2: Opponents 
    match2 = Match(
        id="gap_2",
        court_number=1,
        team1=['p1', 'p5'],  # p1 & p2 OPPONENTS
        team2=['p2', 'p6'],
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match2)
    print("Match 2: p1 & p2 as OPPONENTS")
    
    # Step 3: Gap game where BOTH play but not together
    match3 = Match(
        id="gap_3",
        court_number=1,
        team1=['p1', 'p3'],  # p1 & p3 as partners
        team2=['p2', 'p4'],  # p2 & p4 as partners (p1 vs p2 as opponents again!)
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match3)
    print("Match 3: p1 & p3 vs p2 & p4 (both play, but as opponents again)")
    print()
    
    # Test pattern detection
    pattern_detected = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Pattern detected: {pattern_detected}")
    print("This should be True because last interaction was opponents")
    print()
    print("Let me try a TRUE gap game where they're not in the same match:")
    
    # Clear last match and try a different gap
    session.matches = session.matches[:-1]
    
    # Step 3b: True gap - different matches
    match3b = Match(
        id="gap_3b", 
        court_number=1,
        team1=['p1', 'p7'],  # p1 plays
        team2=['p3', 'p8'],  # p2 not in this match at all
        status='completed',
        start_time=datetime.now(),
        end_time=datetime.now()
    )
    session.matches.append(match3b)
    print("Match 3b: p1 & p7 vs p3 & p8 (p2 not involved)")
    
    pattern_detected = check_partner_opponent_partner_pattern(session, 'p1', 'p2')
    print(f"Pattern detected: {pattern_detected}")
    print()
    print("KEY INSIGHT: Since p2 didn't play in the gap game,")
    print("their 'last interaction' is still the opponents match.")
    print("The constraint should allow this - they had a break!")

if __name__ == "__main__":
    debug_pattern_detection()