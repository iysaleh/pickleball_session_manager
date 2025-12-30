#!/usr/bin/env python3

"""
Test to validate the fixed King of Court waitlist rotation logic.
Ensures players cycle fairly through the waitlist after everyone has waited once.
"""

import sys
import random
from python.session import Session
from python.pickleball_types import Player, SessionConfig, KingOfCourtConfig
from python.kingofcourt import advance_round
from python.utils import generate_id

def create_test_session(num_players=19):
    """Create a test session with specified number of players"""
    
    players = []
    for i in range(num_players):
        players.append(Player(
            id=f"player_{i}",
            name=f"Player {i+1}"
        ))
    
    config = SessionConfig(
        players=players,
        mode="King-Of-Court",
        session_type="doubles",
        courts=4,
        king_of_court_config=KingOfCourtConfig(
            court_ordering=[1, 2, 3, 4]
        )
    )
    
    session = Session(
        id=generate_id(),
        config=config,
        active_players=[p.id for p in players]
    )
    
    return session

def simulate_round_with_random_winners(session):
    """Simulate a round by advancing with random winners"""
    
    # Create fake completed matches for current round
    active_matches = [m for m in session.matches if m.status == 'active']
    
    if not active_matches:
        print("No active matches to complete")
        return False
    
    # Randomly determine winners and complete matches
    for match in active_matches:
        # Random winner
        if random.choice([True, False]):
            match.team1_score = 11
            match.team2_score = random.randint(0, 10)
            match.winner = 'team1'
        else:
            match.team2_score = 11
            match.team1_score = random.randint(0, 10)
            match.winner = 'team2'
        
        match.status = 'completed'
    
    # Advance to next round
    advance_round(session)
    return True

def test_waitlist_rotation_fairness():
    """Test that waitlist rotation ensures fair distribution"""
    
    print("Testing King of Court waitlist rotation fairness...")
    print("=" * 60)
    
    # Test with 19 players, 4 courts (16 playing, 3 waiting)
    session = create_test_session(19)
    
    # Start the first round
    advance_round(session)
    
    # Track wait counts for validation
    total_rounds = 8  # Test 8 rounds
    
    for round_num in range(1, total_rounds + 1):
        print(f"\nRound {round_num}:")
        print(f"  Active matches: {len([m for m in session.matches if m.status == 'active'])}")
        print(f"  Waiting players: {len(session.waiting_players)}")
        
        # Show current waiters
        if session.waiting_players:
            waiter_names = [f"Player {int(p.split('_')[1]) + 1}" for p in session.waiting_players]
            print(f"  Current waiters: {', '.join(waiter_names)}")
        
        # Show wait counts
        wait_counts = {}
        for player_id in session.active_players:
            count = session.king_of_court_wait_counts.get(player_id, 0)
            wait_counts[count] = wait_counts.get(count, 0) + 1
        
        print(f"  Wait count distribution: {wait_counts}")
        
        # Show waitlist history and rotation index
        if session.king_of_court_waitlist_history:
            history_size = len(session.king_of_court_waitlist_history)
            rotation_index = getattr(session, 'king_of_court_waitlist_rotation_index', 0)
            print(f"  Waitlist history size: {history_size}, rotation index: {rotation_index}")
        
        # Validate fairness after round 3 (when everyone should have waited once)
        if round_num >= 3:
            max_waits = max(session.king_of_court_wait_counts.values()) if session.king_of_court_wait_counts else 0
            min_waits = min(session.king_of_court_wait_counts.get(p, 0) for p in session.active_players)
            
            print(f"  Wait range: {min_waits} to {max_waits}")
            
            # After round 3, no one should wait more than 1 more time than others
            if max_waits - min_waits > 1:
                print(f"  ❌ FAIRNESS VIOLATION: Wait difference is {max_waits - min_waits}")
                
                # Show detailed breakdown
                for player_id in session.active_players:
                    count = session.king_of_court_wait_counts.get(player_id, 0)
                    name = f"Player {int(player_id.split('_')[1]) + 1}"
                    print(f"    {name}: {count} waits")
                
                return False
            else:
                print(f"  ✅ Wait distribution is fair")
        
        # Simulate completing this round and advancing
        if round_num < total_rounds:
            if not simulate_round_with_random_winners(session):
                break
    
    # Final validation
    print(f"\nFinal Results after {total_rounds} rounds:")
    print("-" * 40)
    
    wait_counts = {}
    for player_id in session.active_players:
        count = session.king_of_court_wait_counts.get(player_id, 0)
        wait_counts[count] = wait_counts.get(count, 0) + 1
    
    print(f"Final wait count distribution: {wait_counts}")
    
    max_waits = max(session.king_of_court_wait_counts.values()) if session.king_of_court_wait_counts else 0
    min_waits = min(session.king_of_court_wait_counts.get(p, 0) for p in session.active_players)
    
    print(f"Final wait range: {min_waits} to {max_waits}")
    
    if max_waits - min_waits <= 1:
        print("✅ SUCCESS: Waitlist rotation is fair!")
        return True
    else:
        print("❌ FAILURE: Waitlist rotation is unfair!")
        return False

def test_rotation_index_behavior():
    """Test that rotation index advances correctly"""
    
    print("\n\nTesting rotation index behavior...")
    print("=" * 40)
    
    session = create_test_session(10)  # Smaller test for clarity
    
    # Manually set up a waitlist history (simulate everyone has waited once)
    session.king_of_court_waitlist_history = [f"player_{i}" for i in range(10)]
    session.king_of_court_waitlist_rotation_index = 0
    
    # Test selecting 3 players for waitlist
    from python.kingofcourt import select_players_for_fair_rotation
    
    # First selection
    players_to_wait = select_players_for_fair_rotation(session, session.active_players, 3)
    expected_first = [f"player_{i}" for i in range(3)]  # Should be first 3
    
    print(f"First selection: {players_to_wait}")
    print(f"Expected: {expected_first}")
    print(f"Rotation index after: {session.king_of_court_waitlist_rotation_index}")
    
    if players_to_wait == expected_first and session.king_of_court_waitlist_rotation_index == 3:
        print("✅ First selection correct")
    else:
        print("❌ First selection incorrect")
        return False
    
    # Second selection
    players_to_wait = select_players_for_fair_rotation(session, session.active_players, 3)
    expected_second = [f"player_{i}" for i in range(3, 6)]  # Should be next 3
    
    print(f"Second selection: {players_to_wait}")
    print(f"Expected: {expected_second}")
    print(f"Rotation index after: {session.king_of_court_waitlist_rotation_index}")
    
    if players_to_wait == expected_second and session.king_of_court_waitlist_rotation_index == 6:
        print("✅ Second selection correct")
    else:
        print("❌ Second selection incorrect")
        return False
    
    # Third selection (should wrap around)
    players_to_wait = select_players_for_fair_rotation(session, session.active_players, 3)
    expected_third = [f"player_{i}" for i in range(6, 9)]  # Should be next 3
    
    print(f"Third selection: {players_to_wait}")
    print(f"Expected: {expected_third}")
    print(f"Rotation index after: {session.king_of_court_waitlist_rotation_index}")
    
    if players_to_wait == expected_third and session.king_of_court_waitlist_rotation_index == 9:
        print("✅ Third selection correct")
    else:
        print("❌ Third selection incorrect")
        return False
    
    # Fourth selection (should wrap around)
    players_to_wait = select_players_for_fair_rotation(session, session.active_players, 3)
    expected_fourth = ["player_9", "player_0", "player_1"]  # Should wrap to beginning
    
    print(f"Fourth selection: {players_to_wait}")
    print(f"Expected: {expected_fourth}")
    print(f"Rotation index after: {session.king_of_court_waitlist_rotation_index}")
    
    if players_to_wait == expected_fourth and session.king_of_court_waitlist_rotation_index == 2:
        print("✅ Fourth selection correct (wraparound)")
        return True
    else:
        print("❌ Fourth selection incorrect")
        return False

if __name__ == "__main__":
    # Set seed for reproducible test results
    random.seed(42)
    
    success1 = test_rotation_index_behavior()
    success2 = test_waitlist_rotation_fairness()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED! Waitlist rotation is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED! Waitlist rotation needs more fixes.")
        sys.exit(1)