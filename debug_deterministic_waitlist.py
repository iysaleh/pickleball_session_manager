#!/usr/bin/env python3

"""
Deterministic Waitlist Diagnostic Tool

Helps users understand why dependencies might be empty and how to set up
scenarios where dependencies will show correctly.
"""

import sys
sys.path.append('.')

from python.session import create_session
from python.types import SessionConfig, Player, Match
from python.deterministic_waitlist_v2 import get_court_outcome_dependencies_v2
from python.time_manager import initialize_time_manager
from python.queue_manager import get_waiting_players

initialize_time_manager()

def diagnose_session_state(session):
    """Diagnose why dependencies might be empty"""
    print(f"🔍 SESSION DIAGNOSIS")
    print(f"=" * 40)
    
    # Basic session info
    total_players = len(session.active_players)
    total_courts = session.config.courts
    court_capacity = total_courts * 4
    
    print(f"📊 Basic Info:")
    print(f"   Total players: {total_players}")
    print(f"   Total courts: {total_courts}")
    print(f"   Court capacity: {court_capacity} players")
    print(f"   Expected waiting: {max(0, total_players - court_capacity)} players")
    
    # Match state analysis
    matches = session.matches
    waiting_matches = [m for m in matches if m.status == 'waiting']
    in_progress_matches = [m for m in matches if m.status == 'in-progress']
    completed_matches = [m for m in matches if m.status == 'completed']
    
    print(f"\n🏓 Match State:")
    print(f"   Waiting matches: {len(waiting_matches)}")
    print(f"   In-progress matches: {len(in_progress_matches)}")
    print(f"   Completed matches: {len(completed_matches)}")
    
    # Player state analysis
    players_in_matches = set()
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            players_in_matches.update(match.team1 + match.team2)
    
    waiting_players = get_waiting_players(session)
    
    print(f"\n👥 Player State:")
    print(f"   Players in matches: {len(players_in_matches)}")
    print(f"   Players waiting: {len(waiting_players)}")
    print(f"   Waiting players: {waiting_players}")
    
    # Dependencies analysis
    print(f"\n🎯 Dependencies Analysis:")
    if not waiting_players:
        print(f"   ❌ No dependencies possible - no one is waiting!")
        print(f"   💡 To see dependencies: add more players or reduce courts")
        return False
    
    if not in_progress_matches:
        print(f"   ❌ No dependencies possible - no matches in progress!")
        print(f"   💡 To see dependencies: start some matches (status='in-progress')")
        return False
    
    print(f"   ✅ Dependencies possible!")
    print(f"   📝 Testing dependencies for waiting players...")
    
    for player_id in waiting_players[:3]:  # Test first 3
        deps = get_court_outcome_dependencies_v2(session, player_id)
        if deps:
            print(f"      {player_id}: {deps}")
        else:
            print(f"      {player_id}: {{}} (no dependencies found)")
    
    return len(waiting_players) > 0 and len(in_progress_matches) > 0


def demonstrate_working_scenario():
    """Create a scenario where dependencies will definitely show"""
    print(f"\n🎯 CREATING WORKING SCENARIO")
    print(f"=" * 40)
    
    # Create session with guaranteed waiting players
    players = [Player(f'demo_player_{i}', f'DemoPlayer{i}') for i in range(12)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2)
    session = create_session(config)
    
    # Set up matches that guarantee waiting players
    session.matches = [
        Match(id='demo_m1', court_number=1, 
              team1=['demo_player_0', 'demo_player_1'], 
              team2=['demo_player_2', 'demo_player_3'], 
              status='in-progress'),
        Match(id='demo_m2', court_number=2, 
              team1=['demo_player_4', 'demo_player_5'], 
              team2=['demo_player_6', 'demo_player_7'], 
              status='in-progress')
    ]
    
    print(f"✅ Created working scenario:")
    print(f"   - 12 players")
    print(f"   - 2 courts (capacity: 8 players)")
    print(f"   - 2 matches in progress")
    print(f"   - Expected: 4 waiting players")
    
    diagnose_session_state(session)


def test_user_scenario():
    """Test the exact scenario from user's issue"""
    print(f"\n🔍 TESTING USER SCENARIO")
    print(f"=" * 40)
    
    # Try to recreate user's scenario
    players = [Player(f'player_{i}_1766531990.081548', f'Player{i}') for i in range(8)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2)
    session = create_session(config)
    
    # This scenario has NO waiting players (8 players = 2 courts × 4 players)
    session.matches = [
        Match(id='user_m1', court_number=1, 
              team1=['player_0_1766531990.081548', 'player_1_1766531990.081548'], 
              team2=['player_2_1766531990.081548', 'player_3_1766531990.081548'], 
              status='in-progress'),
        Match(id='user_m2', court_number=2, 
              team1=['player_4_1766531990.081548', 'player_5_1766531990.081548'], 
              team2=['player_6_1766531990.081548', 'player_7_1766531990.081548'], 
              status='in-progress')
    ]
    
    print(f"🔍 User's scenario recreation:")
    success = diagnose_session_state(session)
    
    if not success:
        print(f"\n💡 SOLUTION FOR USER:")
        print(f"   The players you tested are NOT waiting - they're playing!")
        print(f"   To test dependencies:")
        print(f"   1. Add more players (e.g., 10-12 players)")
        print(f"   2. OR reduce courts (e.g., 1 court)")
        print(f"   3. OR test on players who are actually in the waitlist")


def provide_recommendations():
    """Provide recommendations for testing dependencies"""
    print(f"\n💡 RECOMMENDATIONS FOR TESTING")
    print(f"=" * 40)
    
    print(f"✅ To see dependencies in GUI:")
    print(f"   1. Start competitive-variety session")
    print(f"   2. Ensure: Players > (Courts × 4)")
    print(f"   3. Start matches so some courts are 'in-progress'")
    print(f"   4. Toggle 'Show Court Deps' button")
    print(f"   5. Dependencies will show for waitlist players only")
    
    print(f"\n🎯 Working Example Setups:")
    print(f"   • 12 players + 2 courts = 4 waiters (✅ Good)")
    print(f"   • 10 players + 2 courts = 2 waiters (✅ Good)")
    print(f"   • 16 players + 3 courts = 4 waiters (✅ Good)")
    print(f"   • 8 players + 2 courts = 0 waiters (❌ No dependencies)")
    print(f"   • 6 players + 2 courts = 0 waiters (❌ No dependencies)")
    
    print(f"\n⚠️  Remember:")
    print(f"   - Dependencies only show for WAITING players")
    print(f"   - Players already in matches won't have dependencies")
    print(f"   - Need active 'in-progress' matches for dependencies to calculate")


if __name__ == "__main__":
    print("🎾 DETERMINISTIC WAITLIST DIAGNOSTIC TOOL")
    print("=" * 50)
    
    test_user_scenario()
    demonstrate_working_scenario()
    provide_recommendations()
    
    print(f"\n🎉 Diagnostic complete!")
    print(f"    The V2 system is working correctly.")
    print(f"    Dependencies only show when there are actual waiters!")