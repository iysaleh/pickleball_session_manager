#!/usr/bin/env python3

"""
Test exact waitlist rotation scenario from pickleball_session_20251230_150938.txt

The problem: When everyone has waited exactly once, the fair rotation should start from
the beginning of the waitlist history (oldest waiters first), not continue from some
arbitrary rotation index.

Expected behavior: 
- Waitlist history: William -> David -> Brenda -> Brock -> Kimberly -> Skyler -> Jeremy -> Greg -> Jo -> Grey -> Daniel -> Ron -> Allison -> Patrick -> Jake -> Leah
- When everyone has 1 wait, next to wait should be: William, David, Brenda, Brock (in that order)
- NOT: Leah, Daniel, David, Sheila (which is what was happening)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.pickleball_types import Session, SessionConfig, SessionType, Match
from python.kingofcourt import select_players_for_fair_rotation

def test_exact_rotation_scenario():
    """Test the exact scenario from the session file"""
    
    # Create session with King of Court configuration
    session = Session(
        id="test",
        config=SessionConfig(
            mode='king-of-court',
            session_type='doubles',
            players=[],  # Empty for test
            courts=4
        )
    )
    
    # Set up the exact waitlist history from the session file
    session.king_of_court_waitlist_history = [
        'William Minton', 'David Laforest', 'Brenda Rea', 'Brock Trejo', 
        'Kimberly Conant', 'Skyler Hensley', 'Jeremy Estrada', 'Greg Mcafee', 
        'Jo Campbell', 'Grey Trejo', 'Daniel Conant', 'Ron Rea', 
        'Allison Monroe', 'Patrick Carroll', 'Jake', 'Leah A'
    ]
    
    # Rotation index from session file was 8 (pointing to Jo Campbell)
    session.king_of_court_waitlist_rotation_index = 8
    
    # Set up wait counts - everyone has waited exactly 1 time (the transition point)
    for player in session.king_of_court_waitlist_history:
        session.king_of_court_wait_counts[player] = 1
    
    # Add Ibraheem and Lia who also had 1 wait but aren't in current active players
    session.king_of_court_wait_counts['Ibraheem Saleh'] = 1
    session.king_of_court_wait_counts['Lia Adamson'] = 1
    session.king_of_court_wait_counts['Sheila B.'] = 1
    session.king_of_court_wait_counts['Lisa Kochenderfer'] = 1
    
    # Active players (all 20 from session file)
    all_active_players = [
        'William Minton', 'David Laforest', 'Brenda Rea', 'Brock Trejo', 
        'Kimberly Conant', 'Skyler Hensley', 'Jeremy Estrada', 'Greg Mcafee', 
        'Jo Campbell', 'Grey Trejo', 'Daniel Conant', 'Ron Rea', 
        'Allison Monroe', 'Patrick Carroll', 'Jake', 'Leah A',
        'Ibraheem Saleh', 'Lia Adamson', 'Sheila B.', 'Lisa Kochenderfer'
    ]
    
    # Test: Need 4 players to wait (20 players - 16 court spots = 4 waiters)
    excess_players = 4
    
    print("BEFORE fix test:")
    print(f"Waitlist history: {session.king_of_court_waitlist_history}")
    print(f"Current rotation index: {session.king_of_court_waitlist_rotation_index}")
    print(f"All players have wait count = 1: {all(session.king_of_court_wait_counts.get(p, 0) == 1 for p in all_active_players)}")
    
    # Call the selection function
    selected_waiters = select_players_for_fair_rotation(session, all_active_players, excess_players)
    
    print(f"\nSELECTED WAITERS: {selected_waiters}")
    print(f"New rotation index: {session.king_of_court_waitlist_rotation_index}")
    
    # Expected: Should start from beginning of waitlist history when everyone has waited once
    expected_waiters = ['William Minton', 'David Laforest', 'Brenda Rea', 'Brock Trejo']
    
    print(f"\nEXPECTED: {expected_waiters}")
    print(f"ACTUAL:   {selected_waiters}")
    
    if selected_waiters == expected_waiters:
        print("✅ SUCCESS: Fair rotation is working correctly!")
        print("   Players who waited LONGEST AGO are selected first")
    else:
        print("❌ FAILED: Fair rotation is NOT working correctly!")
        print("   Algorithm should prioritize players who waited longest ago")
        
    # Test that rotation index was reset to 0 when transitioning to fair rotation
    if session.king_of_court_waitlist_rotation_index == 4:  # Should advance by 4 from reset 0
        print("✅ SUCCESS: Rotation index was properly reset to start from beginning")
    else:
        print(f"❌ FAILED: Rotation index should be 4, but got {session.king_of_court_waitlist_rotation_index}")
    
    return selected_waiters == expected_waiters

def test_subsequent_fair_rotation():
    """Test that subsequent rotations continue correctly"""
    
    # Set up session for second round of fair rotation  
    session = Session(
        id="test2",
        config=SessionConfig(
            mode='king-of-court',
            session_type='doubles',
            players=[],  # Empty for test
            courts=4
        )
    )
    
    session.king_of_court_waitlist_history = [
        'William Minton', 'David Laforest', 'Brenda Rea', 'Brock Trejo', 
        'Kimberly Conant', 'Skyler Hensley', 'Jeremy Estrada', 'Greg Mcafee', 
        'Jo Campbell', 'Grey Trejo', 'Daniel Conant', 'Ron Rea', 
        'Allison Monroe', 'Patrick Carroll', 'Jake', 'Leah A'
    ]
    
    # Set rotation index as if we just selected the first 4 players  
    session.king_of_court_waitlist_rotation_index = 4
    
    # Set up wait counts - first 4 have waited 2 times, rest have 1 time
    wait_counts = {
        'William Minton': 2, 'David Laforest': 2, 'Brenda Rea': 2, 'Brock Trejo': 2,
        'Kimberly Conant': 1, 'Skyler Hensley': 1, 'Jeremy Estrada': 1, 'Greg Mcafee': 1,
        'Jo Campbell': 1, 'Grey Trejo': 1, 'Daniel Conant': 1, 'Ron Rea': 1,
        'Allison Monroe': 1, 'Patrick Carroll': 1, 'Jake': 1, 'Leah A': 1
    }
    session.king_of_court_wait_counts = wait_counts
    
    all_active_players = list(wait_counts.keys())
    
    # Select next 4 waiters
    selected_waiters = select_players_for_fair_rotation(session, all_active_players, 4)
    
    # Expected: Should continue from index 4 in waitlist history
    expected_waiters = ['Kimberly Conant', 'Skyler Hensley', 'Jeremy Estrada', 'Greg Mcafee']
    
    print(f"\nSUBSEQUENT ROTATION TEST:")
    print(f"EXPECTED: {expected_waiters}")
    print(f"ACTUAL:   {selected_waiters}")
    
    if selected_waiters == expected_waiters:
        print("✅ SUCCESS: Subsequent fair rotation works correctly!")
        return True
    else:
        print("❌ FAILED: Subsequent fair rotation is broken!")
        return False

if __name__ == "__main__":
    print("Testing exact waitlist rotation scenario from session file...")
    print("=" * 70)
    
    test1_passed = test_exact_rotation_scenario()
    test2_passed = test_subsequent_fair_rotation()
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! Waitlist fair rotation is working correctly.")
    else:
        print("\n💥 TESTS FAILED! Waitlist rotation needs fixing.")
        sys.exit(1)