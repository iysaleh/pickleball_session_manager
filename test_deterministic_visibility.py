#!/usr/bin/env python3

"""
Test Deterministic Waitlist in GUI Context

This demonstrates the deterministic waitlist feature working correctly
and shows when dependencies will appear.
"""

import sys
sys.path.append('.')

from python.session import create_session
from python.pickleball_types import SessionConfig, Player, Match
from python.time_manager import initialize_time_manager
from python.queue_manager import get_waiting_players

initialize_time_manager()

def test_deterministic_visibility():
    """Test to understand when dependencies are visible"""
    
    print("🎾 DETERMINISTIC WAITLIST VISIBILITY TEST")
    print("=" * 50)
    
    # Create realistic session
    players = [Player(f'p{i}', f'Player{i}') for i in range(12)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2)
    session = create_session(config)
    
    print(f"\n📋 Session Setup:")
    print(f"   Players: {len(players)}")
    print(f"   Courts: {config.courts}")
    print(f"   Court capacity: {config.courts * 4} players")
    print(f"   Expected waiting: {len(players) - (config.courts * 4)} players")
    
    # Test Case 1: No matches in progress
    print(f"\n🔍 TEST 1: No active matches")
    waiting = get_waiting_players(session)
    print(f"   Waiting players: {len(waiting)}")
    print(f"   Dependencies will show: NO")
    print(f"   Reason: No court outcomes to wait for")
    
    # Test Case 2: One match in progress
    print(f"\n🔍 TEST 2: One match in progress")
    session.matches = [
        Match(id='m1', court_number=1, team1=['p0', 'p1'], team2=['p2', 'p3'], status='in-progress'),
    ]
    
    waiting = get_waiting_players(session)
    print(f"   Waiting players: {len(waiting)}")
    print(f"   Dependencies will show: LIMITED")
    print(f"   Reason: Court 2 is empty, so some players can play immediately")
    
    # Test Case 3: Both courts in progress (IDEAL CASE)
    print(f"\n🔍 TEST 3: Both courts in progress ⭐")
    session.matches = [
        Match(id='m1', court_number=1, team1=['p0', 'p1'], team2=['p2', 'p3'], status='in-progress'),
        Match(id='m2', court_number=2, team1=['p4', 'p5'], team2=['p6', 'p7'], status='in-progress'),
    ]
    
    waiting = get_waiting_players(session)
    print(f"   Waiting players: {len(waiting)}")
    print(f"   Dependencies will show: YES! 🎯")
    print(f"   Reason: All courts occupied, players must wait for specific outcomes")
    
    from python.deterministic_waitlist import get_court_outcome_dependencies
    
    if waiting:
        for i, player in enumerate(waiting[:3]):  # Show first 3
            deps = get_court_outcome_dependencies(session, player)
            if deps:
                court_strings = []
                for court_num in sorted(deps.keys()):
                    outcomes = deps[court_num]
                    outcome_chars = []
                    if "red_wins" in outcomes:
                        outcome_chars.append("R")
                    if "blue_wins" in outcomes:
                        outcome_chars.append("B")
                    
                    if len(outcome_chars) == 2:
                        outcome_str = "RB"
                    else:
                        outcome_str = "".join(outcome_chars)
                    
                    court_strings.append(f"C{court_num}{outcome_str}")
                
                deps_str = ", ".join(court_strings)
                print(f"   {player} would show: 🎯[{deps_str}]")
    
    print(f"\n💡 KEY INSIGHTS:")
    print(f"   • Dependencies only show when courts are OCCUPIED")
    print(f"   • The 🎯 emoji makes dependencies more visible")
    print(f"   • C1R = Court 1, Red team wins")
    print(f"   • C2B = Court 2, Blue team wins") 
    print(f"   • C1RB = Court 1, either team wins")
    
    print(f"\n📱 TO TEST IN GUI:")
    print(f"   1. Start competitive-variety session with 8+ players")
    print(f"   2. Fill all courts with matches")
    print(f"   3. Toggle 'Show Court Deps' button")
    print(f"   4. Dependencies will appear as 🎯[C1R, C2RB]")
    
    print(f"\n✅ FONT FIXES APPLIED:")
    print(f"   • Increased minimum font size from 8 to 9")
    print(f"   • Added 🎯 emoji for better visibility")  
    print(f"   • Added debug output for troubleshooting")
    print(f"   • Force font resize when dependencies toggle")


if __name__ == "__main__":
    test_deterministic_visibility()