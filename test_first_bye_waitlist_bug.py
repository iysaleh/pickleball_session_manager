#!/usr/bin/env python3
"""
Test to reproduce the bug where first bye players get stuck on the waitlist.
"""

from python.pickleball_types import SessionConfig, Player
from python.session import create_session, evaluate_and_create_matches, complete_match
from python.time_manager import initialize_time_manager

def test_first_bye_waitlist_bug():
    """Test that first bye players don't get stuck on waitlist"""
    print("Testing first bye waitlist behavior...")
    
    initialize_time_manager()
    
    # Create 9 players for singles
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(9)]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='singles',
        players=players,
        courts=4,  # 4 courts = 8 players playing, 1 waiting
        first_bye_players=['p0']  # p0 should sit out first round
    )
    
    session = create_session(config)
    evaluate_and_create_matches(session)
    
    print(f"Initial state:")
    print(f"  Players on courts: {len([p for match in session.matches for p in match.team1 + match.team2])}")
    print(f"  Players waiting: {len(session.waiting_players)}")
    print(f"  Waiting players: {session.waiting_players}")
    print(f"  Matches on courts: {len(session.matches)}")
    print(f"  Matches in queue: {len(session.match_queue)}")
    
    # Show first few matches in queue
    print(f"\nFirst 10 matches in queue:")
    for i, match in enumerate(session.match_queue[:10]):
        if session.config.session_type == 'singles':
            print(f"  {i+1}: {match.team1[0]} vs {match.team2[0]}")
        else:
            print(f"  {i+1}: {match.team1} vs {match.team2}")
    
    # Check if p0 is in any of the first 8 matches (those that should be on courts initially)
    p0_in_initial_matches = False
    for match in session.matches:
        if 'p0' in match.team1 + match.team2:
            p0_in_initial_matches = True
            break
    
    print(f"\np0 in initial matches on courts: {p0_in_initial_matches}")
    print(f"p0 on waitlist: {'p0' in session.waiting_players}")
    
    # Complete a match and see what happens
    if session.matches:
        print(f"\n--- Completing first match ---")
        first_match = session.matches[0]
        print(f"Completing match: {first_match.team1} vs {first_match.team2}")
        
        # Complete with a score
        complete_match(session, first_match.id, 11, 5)
        evaluate_and_create_matches(session)
        
        print(f"\nAfter completing first match:")
        print(f"  Players on courts: {len([p for match in session.matches for p in match.team1 + match.team2])}")
        print(f"  Players waiting: {len(session.waiting_players)}")
        print(f"  Waiting players: {session.waiting_players}")
        print(f"  Matches on courts: {len(session.matches)}")
        print(f"  Matches in queue: {len(session.match_queue)}")
        
        # Check if p0 is still stuck on waitlist
        p0_still_waiting = 'p0' in session.waiting_players
        
        # Check if p0 got a match
        p0_now_playing = False
        for match in session.matches:
            if 'p0' in match.team1 + match.team2:
                p0_now_playing = True
                print(f"  p0 is now playing: {match.team1} vs {match.team2}")
                break
        
        print(f"p0 still on waitlist: {p0_still_waiting}")
        print(f"p0 now playing: {p0_now_playing}")
        
        return not p0_still_waiting or p0_now_playing
    
    return True

if __name__ == '__main__':
    print("=" * 70)
    print("TESTING FIRST BYE WAITLIST BUG")
    print("=" * 70)
    
    success = test_first_bye_waitlist_bug()
    
    if success:
        print("\n✅ First bye waitlist test passed!")
    else:
        print("\n❌ First bye waitlist bug detected!")