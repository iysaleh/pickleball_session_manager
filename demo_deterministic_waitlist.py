#!/usr/bin/env python3

"""
Demonstration of the Deterministic Waitlist System

This demonstration shows how the advanced waitlist prediction system works
in practice, displaying exactly which court outcomes waiting players depend on.
"""

import sys
sys.path.append('.')

from python.session import create_session, complete_match
from python.types import SessionConfig, Player, Match
from python.deterministic_waitlist import get_deterministic_waitlist_display
from python.time_manager import initialize_time_manager
from python.queue_manager import get_waiting_players, advance_session
from python.session import get_player_name
import time

initialize_time_manager()

def print_session_state(session, title="Session State"):
    """Print current session state including matches and waitlist"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    # Show active matches
    print("\n🏟️  ACTIVE COURTS:")
    active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
    if not active_matches:
        print("  No active matches")
    else:
        for match in active_matches:
            status_icon = "⏳" if match.status == 'waiting' else "🏓"
            team1_names = [get_player_name(session, pid) for pid in match.team1]
            team2_names = [get_player_name(session, pid) for pid in match.team2]
            team1_str = " + ".join(team1_names)
            team2_str = " + ".join(team2_names)
            print(f"  Court {match.court_number}: {status_icon} {team1_str} vs {team2_str}")
    
    # Show waiting players with deterministic predictions
    waiting = get_waiting_players(session)
    if waiting:
        print(f"\n⏳ WAITLIST ({len(waiting)} players):")
        display = get_deterministic_waitlist_display(session)
        for line in display:
            print(f"  {line}")
    else:
        print(f"\n⏳ WAITLIST: Empty")


def demonstrate_deterministic_waitlist():
    """Main demonstration of the deterministic waitlist system"""
    print("🎾 DETERMINISTIC WAITLIST SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This system shows waiting players exactly which court outcomes")
    print("will get them into their next match!")
    print()
    print("Legend:")
    print("  [C1R] = Court 1, Red team wins")  
    print("  [C2B] = Court 2, Blue team wins")
    print("  [C1RB] = Court 1, either team wins")
    
    # Create session with 12 players, 2 courts
    players = []
    skill_levels = [4.5, 4.2, 4.0, 3.8, 3.6, 3.4, 3.2, 3.0, 2.8, 2.6, 2.4, 2.2]
    for i, skill in enumerate(skill_levels):
        players.append(Player(f"p{i}", f"Player{i}", skill))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles', 
        players=players,
        courts=2,
        pre_seeded_ratings=True
    )
    
    session = create_session(config)
    
    print(f"\n📋 Created session with {len(players)} players and {config.courts} courts")
    print(f"   Court capacity: {config.courts * 4} players")
    print(f"   Expected waiting: {len(players) - (config.courts * 4)} players")
    
    # Set up initial matches manually for demonstration
    session.matches = [
        Match(
            id="demo_match1",
            court_number=1,
            team1=["p0", "p3"],  # Top + 4th = balanced
            team2=["p1", "p2"],  # 2nd + 3rd = balanced
            status="in-progress"
        ),
        Match(
            id="demo_match2", 
            court_number=2,
            team1=["p4", "p7"],  # 5th + 8th = balanced
            team2=["p5", "p6"],  # 6th + 7th = balanced
            status="in-progress"
        )
    ]
    
    print_session_state(session, "INITIAL SETUP")
    
    print("\n🔍 PREDICTION ANALYSIS:")
    print("   - All waiting players show [C1RB, C2RB] because:")
    print("     1. Any court finishing frees up 4 spots")
    print("     2. With only 4 waiters, they can all play regardless of winner")
    print("     3. Skill balance allows flexible team formations")
    
    # Demonstrate what happens when court 1 finishes
    print(f"\n⚡ SIMULATION: Court 1 finishes (Red team wins)")
    print("   Completing match with score 11-8...")
    
    # Complete the match
    success, slides = complete_match(session, "demo_match1", 11, 8)
    if success:
        print("   ✅ Match completed successfully")
        
        # Advance session to populate courts
        advance_session(session)
        print_session_state(session, "AFTER COURT 1 COMPLETION")
        
        # Check if predictions were accurate
        waiting = get_waiting_players(session)
        if len(waiting) == 0:
            print("\n🎯 PREDICTION ACCURACY: Perfect!")
            print("   All previously waiting players were assigned to courts as predicted")
        else:
            print(f"\n🎯 PREDICTION ACCURACY: {4-len(waiting)}/4 players assigned")
    
    # Demonstrate different scenario - mid-game state
    print(f"\n" + "="*60)
    print("SCENARIO 2: More Complex Waitlist Dependencies")
    print("="*60)
    
    # Create session with uneven skill distribution
    players2 = []
    # Create 14 players with varied skills to create more complex dependencies
    skills = [4.8, 4.5, 4.2, 3.9, 3.6, 3.3, 3.0, 4.6, 4.1, 3.8, 3.5, 3.2, 2.9, 2.6]
    for i, skill in enumerate(skills):
        players2.append(Player(f"q{i}", f"Qplayer{i}", skill))
    
    config2 = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players2,
        courts=3,  # 3 courts = 12 player capacity
        pre_seeded_ratings=True  
    )
    
    session2 = create_session(config2)
    
    # Set up matches with different skill balances to create dependencies
    session2.matches = [
        Match(
            id="complex_match1",
            court_number=1,
            team1=["q0", "q6"],  # Elite + weak = imbalanced
            team2=["q2", "q4"],  # Good + good = balanced
            status="in-progress"
        ),
        Match(
            id="complex_match2",
            court_number=2,
            team1=["q1", "q5"],  # Elite + average = somewhat balanced
            team2=["q3", "q7"],  # Strong + elite = balanced
            status="in-progress"
        ),
        Match(
            id="complex_match3",
            court_number=3,
            team1=["q8", "q11"], # Good + average = balanced
            team2=["q9", "q10"], # Strong + good = balanced
            status="in-progress"
        )
    ]
    
    print_session_state(session2, "COMPLEX SCENARIO SETUP")
    
    print("\n🔍 COMPLEX PREDICTION ANALYSIS:")
    print("   - Different players may depend on different court outcomes")
    print("   - Some players might need specific winners for skill balance")
    print("   - Higher-skill players might have fewer opportunities")
    
    print("\n🎯 KEY INSIGHTS:")
    print("   1. Players can see exactly which courts to watch")
    print("   2. Red/Blue indicators show if specific outcomes matter")
    print("   3. System accounts for skill balance and variety constraints")
    print("   4. Wait time is more predictable and less frustrating")
    
    print(f"\n✨ BENEFITS OF DETERMINISTIC WAITLIST:")
    print("   • Players know exactly what they're waiting for")
    print("   • Reduces anxiety about uncertain wait times") 
    print("   • Enables strategic bathroom/water breaks")
    print("   • Makes session management more transparent")
    print("   • Helps predict optimal court count for groups")


if __name__ == "__main__":
    demonstrate_deterministic_waitlist()
    print(f"\n🎉 Demonstration complete!")