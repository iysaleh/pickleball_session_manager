#!/usr/bin/env python3

"""
Debug test to reproduce the waitlist rotation issue seen in the session file.
The issue: After everyone has waited once, the rotation is going back to the same players
instead of continuing the fair rotation cycle.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'python'))

from pickleball_types import Session, Match, Player
from kingofcourt import apply_king_of_court_advancement, apply_waitlist_rotation, select_players_for_fair_rotation

def setup_debug_session():
    """
    Set up a session that mimics the state when the bug occurs.
    Based on the session file, we have 16 players and 3 courts (12 playing, 4 waiting).
    """
    session = Session()
    session.game_mode = 'King of Court'
    session.court_names = {1: 'Court 1', 2: 'Court 2', 3: 'Court 3'}
    session.king_of_court_ordering = [1, 2, 3]  # Court 1 = Kings, Court 3 = Bottom
    
    # Set up players (using names from session file)
    players = [
        'Ibraheem Saleh', 'Leah A', 'William Minton', 'Greg Mcafee', 'Skyler Hensley',
        'Brenda Rea', 'Brock Trejo', 'Jo Campbell', 'Kimberly Conant', 'Jeremy Estrada',
        'Grey Trejo', 'David Laforest', 'Daniel Conant', 'Ron Rea', 'Allison Monroe', 'Patrick Carroll'
    ]
    
    for name in players:
        player = Player(id=name, name=name)
        session.players[name] = player
    
    # Simulate the state where everyone has waited exactly once
    # Based on the waitlist history from session file:
    waitlist_history_order = [
        'William Minton', 'David Laforest', 'Brenda Rea', 'Brock Trejo', 'Kimberly Conant', 
        'Skyler Hensley', 'Jeremy Estrada', 'Greg Mcafee', 'Jo Campbell', 'Grey Trejo', 
        'Daniel Conant', 'Ron Rea', 'Allison Monroe', 'Patrick Carroll'
    ]
    
    # Set initial wait counts - most have waited once, some haven't waited yet
    session.king_of_court_wait_counts = {}
    for player in players:
        if player in waitlist_history_order:
            session.king_of_court_wait_counts[player] = 1  # Has waited once
        else:
            session.king_of_court_wait_counts[player] = 1  # Ibraheem and Leah have also waited once based on session
    
    # Set up waitlist history
    session.king_of_court_waitlist_history = waitlist_history_order.copy()
    
    # Set rotation index to simulate the state when the bug occurs
    # In the session, it shows index 8, which points to 'Jo Campbell'
    session.king_of_court_waitlist_rotation_index = 8
    
    # Set current court positions (12 players on courts, 4 waiting)
    session.king_of_court_player_positions = {
        # Court 1 (Kings)
        'Ibraheem Saleh': 1, 'Leah A': 1, 'William Minton': 1, 'Greg Mcafee': 1,
        # Court 2 (Middle)  
        'Skyler Hensley': 2, 'Brenda Rea': 2, 'Brock Trejo': 2, 'Jo Campbell': 2,
        # Court 3 (Bottom)
        'Kimberly Conant': 3, 'Jeremy Estrada': 3, 'Grey Trejo': 3, 'David Laforest': 3
    }
    
    # Set current waiters
    session.waiting_players = ['Daniel Conant', 'Ron Rea', 'Allison Monroe', 'Patrick Carroll']
    
    return session

def test_fair_rotation_selection():
    """
    Test the select_players_for_fair_rotation function directly to understand the bug.
    """
    session = setup_debug_session()
    
    print("=== DEBUGGING WAITLIST ROTATION SELECTION ===")
    print(f"Waitlist history: {session.king_of_court_waitlist_history}")
    print(f"Current rotation index: {session.king_of_court_waitlist_rotation_index}")
    print(f"Current waiters: {session.waiting_players}")
    
    # All active players (12 on courts + 4 waiting)
    all_active_players = list(session.players.keys())
    print(f"All active players ({len(all_active_players)}): {all_active_players}")
    
    # Test selecting 4 players for waiting (excess_players = 4)
    excess_players = 4
    
    print(f"\n--- Selecting {excess_players} players for fair rotation ---")
    players_to_wait = select_players_for_fair_rotation(session, all_active_players, excess_players)
    
    print(f"Selected players: {players_to_wait}")
    print(f"New rotation index: {session.king_of_court_waitlist_rotation_index}")
    
    # Check which players should be selected based on rotation index 8
    active_history_players = [p for p in session.king_of_court_waitlist_history if p in all_active_players]
    print(f"\nActive history players: {active_history_players}")
    print(f"Starting from index 8: {active_history_players[8:]}")
    print(f"Expected selection: {active_history_players[8:8+4]}")
    
    # Verify the selection is correct
    expected_players = []
    for i in range(excess_players):
        player_index = (8 + i) % len(active_history_players)
        expected_players.append(active_history_players[player_index])
    
    print(f"Expected (calculated): {expected_players}")
    
    if players_to_wait == expected_players:
        print("✅ Selection is correct according to fair rotation!")
    else:
        print("❌ Selection does not match expected fair rotation!")
        
    return players_to_wait, expected_players

def test_full_waitlist_rotation():
    """
    Test the full waitlist rotation process that happens during King of Court advancement.
    """
    session = setup_debug_session()
    
    print("\n=== TESTING FULL WAITLIST ROTATION PROCESS ===")
    print("Simulating court assignments after King of Court movement...")
    
    # Simulate court assignments after movement (before waitlist rotation)
    court_assignments = {
        1: ['Ibraheem Saleh', 'Leah A', 'William Minton', 'Greg Mcafee'],
        2: ['Skyler Hensley', 'Brenda Rea', 'Brock Trejo', 'Jo Campbell'], 
        3: ['Kimberly Conant', 'Jeremy Estrada', 'Grey Trejo', 'David Laforest']
    }
    
    print(f"Court assignments before waitlist rotation:")
    for court, players in court_assignments.items():
        print(f"  Court {court}: {players}")
    
    print(f"Current waiters: {session.waiting_players}")
    
    # Apply waitlist rotation
    final_assignments = apply_waitlist_rotation(
        session, 
        court_assignments, 
        session.king_of_court_ordering,
        4  # players_per_court
    )
    
    print(f"\nAfter waitlist rotation:")
    print(f"New waiters: {session.waiting_players}")
    print(f"Court assignments after rotation:")
    for court in session.king_of_court_ordering:
        if court in final_assignments:
            print(f"  Court {court}: {final_assignments[court]}")
    
    # Check wait counts
    print(f"\nWait count distribution:")
    wait_counts = {}
    for player_id in session.players.keys():
        count = session.king_of_court_wait_counts.get(player_id, 0)
        if count not in wait_counts:
            wait_counts[count] = []
        wait_counts[count].append(player_id)
    
    for count in sorted(wait_counts.keys()):
        print(f"  Waited {count} times: {wait_counts[count]} ({len(wait_counts[count])} players)")

if __name__ == "__main__":
    print("🐛 DEBUGGING WAITLIST ROTATION ISSUE")
    print("=====================================")
    
    selected, expected = test_fair_rotation_selection()
    
    test_full_waitlist_rotation()
    
    print("\n🔍 ANALYSIS:")
    print("- If the rotation selection is correct but wrong players are waiting,")
    print("  the bug is in how court assignments or wait counts are handled.")
    print("- If the rotation selection is wrong, the bug is in select_players_for_fair_rotation.")