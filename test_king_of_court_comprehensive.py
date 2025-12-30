#!/usr/bin/env python3

"""
Comprehensive King of Court Validation Test

This test validates 6 rounds of 19-player King of Court to ensure:
1. Winners move up and split correctly
2. Losers move down and split correctly  
3. Court ordering is strictly respected
4. Wait list rotation works properly (nobody waits twice until everyone waits once)
5. Partnership constraints are secondary to court movement rules
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from python.pickleball_types import Player, SessionConfig, KingOfCourtConfig
from python.session import create_session
from python.kingofcourt import advance_round
from python.time_manager import initialize_time_manager, now
from typing import Dict, List, Set


def create_test_players(count: int) -> List[Player]:
    """Create test players with incrementing names"""
    return [Player(f"player_{i:02d}", f"Player {i:02d}") for i in range(1, count + 1)]


def print_round_state(session, round_num: int):
    """Print current round state for debugging"""
    print(f"\n=== ROUND {round_num} STATE ===")
    
    # Print court assignments
    print("Court Assignments:")
    for court_num in session.config.king_of_court_config.court_ordering:
        players_on_court = []
        for player_id, court in session.king_of_court_player_positions.items():
            if court == court_num:
                players_on_court.append(player_id)
        if players_on_court:
            print(f"  Court {court_num}: {players_on_court}")
    
    # Print waitlist
    if session.waiting_players:
        print(f"Waitlist: {session.waiting_players}")
        
    # Print wait counts
    wait_counts = {}
    for player_id in session.active_players:
        count = session.king_of_court_wait_counts.get(player_id, 0)
        if count not in wait_counts:
            wait_counts[count] = []
        wait_counts[count].append(player_id)
    
    print("Wait Count Distribution:")
    for count, players in sorted(wait_counts.items()):
        print(f"  Waited {count} times: {len(players)} players")


def get_court_players(session, court_num: int) -> List[str]:
    """Get players currently assigned to a specific court"""
    return [player_id for player_id, court in session.king_of_court_player_positions.items() 
            if court == court_num]


def validate_round_movement(session, prev_matches: List, round_num: int) -> List[str]:
    """
    Validate that winners/losers moved correctly according to King of Court rules.
    Returns list of validation errors.
    """
    errors = []
    court_ordering = session.config.king_of_court_config.court_ordering
    
    # Build expected movements based on previous round results
    expected_movements = {}
    
    for match in prev_matches:
        if match.status != 'completed':
            continue
            
        match_court = match.court_number
        court_index = court_ordering.index(match_court)
        
        # Determine winners and losers
        if match.score and match.score['team1_score'] > match.score['team2_score']:
            winners = match.team1
            losers = match.team2
        elif match.score:
            winners = match.team2
            losers = match.team1
        else:
            continue  # Skip matches without scores
        
        # Winners should move up one court (or stay at top)
        if court_index > 0:  # Not already at top court
            target_court = court_ordering[court_index - 1]
            for winner in winners:
                expected_movements[winner] = f"winner_to_court_{target_court}"
        else:  # Already at top court - stay
            target_court = court_ordering[0]
            for winner in winners:
                expected_movements[winner] = f"winner_stay_court_{target_court}"
        
        # Losers should move down one court (or stay at bottom)
        if court_index < len(court_ordering) - 1:  # Not already at bottom
            target_court = court_ordering[court_index + 1]
            for loser in losers:
                expected_movements[loser] = f"loser_to_court_{target_court}"
        else:  # Already at bottom - stay
            target_court = court_ordering[-1]
            for loser in losers:
                expected_movements[loser] = f"loser_stay_court_{target_court}"
    
    # Check if movements happened correctly
    print(f"Expected movements for Round {round_num}:")
    for player_id, expected_movement in expected_movements.items():
        current_court = session.king_of_court_player_positions.get(player_id)
        print(f"  {player_id}: {expected_movement} -> actual court {current_court}")
        
        # Extract expected court from movement description
        expected_court = int(expected_movement.split('_')[-1])
        
        # Skip validation for players who are currently waiting (they should have no court)
        if player_id in session.waiting_players:
            continue
        
        if current_court != expected_court:
            errors.append(f"Round {round_num}: {player_id} should be on court {expected_court}, but is on court {current_court}")
    
    return errors


def validate_team_splitting(session, prev_matches: List, round_num: int) -> List[str]:
    """
    Validate that all teams from previous round split (no partnerships preserved).
    Returns list of validation errors.
    """
    errors = []
    
    # Get all previous partnerships
    prev_partnerships = set()
    for match in prev_matches:
        if match.status == 'completed':
            prev_partnerships.add(tuple(sorted(match.team1)))
            prev_partnerships.add(tuple(sorted(match.team2)))
    
    # Check current matches for preserved partnerships
    for match in session.matches:
        if match.status == 'waiting':
            current_team1 = tuple(sorted(match.team1))
            current_team2 = tuple(sorted(match.team2))
            
            if current_team1 in prev_partnerships:
                errors.append(f"Round {round_num}: Team {current_team1} was preserved from previous round - should have split")
            
            if current_team2 in prev_partnerships:
                errors.append(f"Round {round_num}: Team {current_team2} was preserved from previous round - should have split")
    
    return errors


def validate_wait_rotation(session, round_num: int, total_rounds: int) -> List[str]:
    """
    Validate wait rotation follows King of Court rules.
    Returns list of validation errors.
    """
    errors = []
    
    # Check wait count distribution
    wait_counts = {}
    for player_id in session.active_players:
        count = session.king_of_court_wait_counts.get(player_id, 0)
        if count not in wait_counts:
            wait_counts[count] = []
        wait_counts[count].append(player_id)
    
    # King of Court rule: Nobody waits twice until everyone has waited once
    max_wait_count = max(wait_counts.keys()) if wait_counts else 0
    min_wait_count = min(wait_counts.keys()) if wait_counts else 0
    
    if max_wait_count - min_wait_count > 1:
        errors.append(f"Round {round_num}: Wait count spread too large - some players have waited {max_wait_count} times while others only {min_wait_count} times")
    
    # For 6 rounds with 19 players (4 courts = 16 playing, 3 waiting each round)
    # Total wait slots = 6 rounds * 3 waiters = 18 slots
    # With 19 players, we should have 18 players with 1 wait and 1 player with 0 waits by end
    if round_num == total_rounds:
        expected_wait_distribution = {0: 1, 1: 18}  # 1 player never waited, 18 waited once
        
        for expected_count, expected_players in expected_wait_distribution.items():
            actual_players = len(wait_counts.get(expected_count, []))
            if actual_players != expected_players:
                errors.append(f"Final Round: Expected {expected_players} players with {expected_count} waits, but got {actual_players}")
    
    return errors


def validate_court_ordering(session, round_num: int) -> List[str]:
    """
    Validate that court ordering is being respected.
    Returns list of validation errors.
    """
    errors = []
    court_ordering = session.config.king_of_court_config.court_ordering
    
    # Check that all courts in ordering are populated
    for court_num in court_ordering:
        players_on_court = get_court_players(session, court_num)
        if len(players_on_court) != 4:  # Should have exactly 4 players per court
            errors.append(f"Round {round_num}: Court {court_num} has {len(players_on_court)} players, expected 4")
    
    return errors


def complete_all_matches_in_round(session, round_num: int):
    """Complete all active matches with deterministic scores"""
    completed_matches = []
    
    for match in session.matches:
        if match.status == 'waiting':
            # Use deterministic scores based on court hierarchy
            # Higher courts (lower numbers) tend to have closer games
            court_index = session.config.king_of_court_config.court_ordering.index(match.court_number)
            
            if court_index == 0:  # Kings court - closest games
                team1_score, team2_score = 11, 9
            elif court_index == 1:  # Second court
                team1_score, team2_score = 11, 7
            elif court_index == 2:  # Third court  
                team1_score, team2_score = 11, 5
            else:  # Bottom courts
                team1_score, team2_score = 11, 3
            
            # Complete the match
            match.status = 'completed'
            match.score = {'team1_score': team1_score, 'team2_score': team2_score}
            match.end_time = now()
            completed_matches.append(match)
            
            print(f"Round {round_num} - Court {match.court_number}: {match.team1} {team1_score}-{team2_score} {match.team2}")
    
    return completed_matches


def test_king_of_court_comprehensive():
    """Test 6 rounds of 19-player King of Court with comprehensive validation"""
    initialize_time_manager()
    
    print("🏓 Testing Comprehensive King of Court Algorithm")
    print("=" * 60)
    
    # Create 19-player session
    players = create_test_players(19)
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2, 3, 4]  # Court 1 = Kings, Court 4 = Bottom
    )
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=4,
        king_of_court_config=koc_config
    )
    session = create_session(config)
    
    print(f"Setup: 19 players, 4 courts ({len(session.config.king_of_court_config.court_ordering)} courts)")
    print(f"Court ordering: {session.config.king_of_court_config.court_ordering}")
    print(f"Expected: 16 playing, 3 waiting each round")
    
    all_errors = []
    total_rounds = 6
    
    # Initial round setup
    print_round_state(session, 1)
    
    for round_num in range(1, total_rounds + 1):
        print(f"\n{'='*20} ROUND {round_num} {'='*20}")
        
        # Complete all matches in current round
        completed_matches = complete_all_matches_in_round(session, round_num)
        
        if round_num < total_rounds:
            # Advance to next round (except on last round)
            print(f"\nAdvancing to Round {round_num + 1}...")
            advance_round(session)
            
            # Validate the advancement
            print(f"\nValidating Round {round_num + 1} setup...")
            
            # Validate court movement
            movement_errors = validate_round_movement(session, completed_matches, round_num + 1)
            all_errors.extend(movement_errors)
            
            # Validate team splitting  
            splitting_errors = validate_team_splitting(session, completed_matches, round_num + 1)
            all_errors.extend(splitting_errors)
            
            # Validate court ordering
            ordering_errors = validate_court_ordering(session, round_num + 1)
            all_errors.extend(ordering_errors)
            
            # Validate wait rotation
            wait_errors = validate_wait_rotation(session, round_num + 1, total_rounds)
            all_errors.extend(wait_errors)
            
            # Print next round state
            print_round_state(session, round_num + 1)
            
            if movement_errors or splitting_errors or ordering_errors or wait_errors:
                print(f"❌ Round {round_num + 1} has validation errors!")
                for error in movement_errors + splitting_errors + ordering_errors + wait_errors:
                    print(f"   {error}")
            else:
                print(f"✅ Round {round_num + 1} validation passed")
    
    # Final validation
    print(f"\n{'='*20} FINAL VALIDATION {'='*20}")
    
    final_wait_errors = validate_wait_rotation(session, total_rounds, total_rounds)
    all_errors.extend(final_wait_errors)
    
    if all_errors:
        print(f"\n❌ COMPREHENSIVE TEST FAILED - {len(all_errors)} errors found:")
        for error in all_errors:
            print(f"   {error}")
        return False
    else:
        print(f"\n✅ COMPREHENSIVE TEST PASSED")
        print("✅ All court movements followed King of Court rules")
        print("✅ All teams split correctly between rounds")
        print("✅ Court ordering was respected throughout")
        print("✅ Wait rotation followed fair distribution rules")
        return True


if __name__ == "__main__":
    success = test_king_of_court_comprehensive()
    if not success:
        sys.exit(1)
    print("\n🎉 King of Court algorithm working perfectly!")