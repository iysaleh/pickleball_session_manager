"""
Tests for Competitive Round Robin mode - rounds-based scheduling.

Key features to test:
1. All courts wait for round completion before starting next round
2. Fair waitlist rotation - nobody waits twice before all wait once
3. Pre-scheduled matches with approval workflow
4. Waiters are shown per round in UI
"""

import pytest
from typing import List
from python.pickleball_types import (
    Player, Session, SessionConfig, CompetitiveRoundRobinConfig,
    ScheduledMatch, Match
)
from python.session import create_session
from python.competitive_round_robin import (
    generate_initial_schedule,
    generate_rounds_based_schedule,
    populate_courts_from_schedule,
    compute_scheduled_waiters,
    get_round_info,
    swap_waiter_in_round
)
from python.time_manager import now, initialize_time_manager


def create_test_players(n: int) -> List[Player]:
    """Create n test players with skill ratings."""
    players = []
    for i in range(n):
        rating = 3.0 + (i % 7) * 0.25  # Ratings from 3.0 to 4.5
        players.append(Player(
            id=f"player_{i}",
            name=f"Player {i}",
            skill_rating=rating
        ))
    return players


def create_test_session(num_players: int = 18, num_courts: int = 4) -> Session:
    """Create a test session for competitive round robin."""
    initialize_time_manager()
    players = create_test_players(num_players)
    
    config = CompetitiveRoundRobinConfig(
        games_per_player=8,
        max_individual_opponent_repeats=2
    )
    
    session_config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        players=players,
        courts=num_courts,
        pre_seeded_ratings=True,
        competitive_round_robin_config=config
    )
    
    return create_session(session_config)


class TestRoundsBasedScheduling:
    """Test rounds-based scheduling behavior."""
    
    def test_generate_schedule_creates_rounds(self):
        """Schedule should organize matches into rounds with num_courts matches each."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        
        matches, waiters = generate_rounds_based_schedule(session, config)
        
        # Should have multiple rounds
        assert len(waiters) > 0, "Should have waiters per round"
        
        # Each round should have expected matches
        num_courts = session.config.courts
        num_rounds = len(waiters)
        
        # Group matches by round_number
        matches_by_round: dict = {}
        for m in matches:
            round_idx = m.round_number
            if round_idx not in matches_by_round:
                matches_by_round[round_idx] = []
            matches_by_round[round_idx].append(m)
        
        for round_idx in range(num_rounds):
            round_matches = matches_by_round.get(round_idx, [])
            
            # Each round should have up to num_courts matches
            assert len(round_matches) <= num_courts
            
            # Players in a round should not overlap
            players_in_round = set()
            for m in round_matches:
                match_players = set(m.team1 + m.team2)
                assert not (match_players & players_in_round), \
                    f"Round {round_idx} has overlapping players"
                players_in_round.update(match_players)
    
    def test_fair_waitlist_rotation(self):
        """Nobody should wait twice before everyone waits once."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        
        matches, waiters = generate_rounds_based_schedule(session, config)
        
        # Count how many times each player waits
        wait_counts = {}
        for player in session.config.players:
            wait_counts[player.id] = 0
        
        for round_waiters in waiters:
            for pid in round_waiters:
                wait_counts[pid] += 1
        
        # Check fair distribution
        # After everyone waits once, only then can anyone wait twice
        max_wait = max(wait_counts.values())
        min_wait = min(wait_counts.values())
        
        # The difference should be at most 1
        assert max_wait - min_wait <= 1, \
            f"Unfair wait distribution: max={max_wait}, min={min_wait}"
    
    def test_rounds_based_population_waits_for_all_courts(self):
        """Courts should not populate until ALL courts finish current round."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        
        # Generate and approve matches
        matches = generate_initial_schedule(session, config)
        for m in matches:
            m.status = 'approved'
        config.scheduled_matches = matches
        config.schedule_finalized = True
        
        # Populate first round
        populate_courts_from_schedule(session)
        
        # Should have 4 matches (one per court)
        active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        assert len(active_matches) == 4, f"Expected 4 matches, got {len(active_matches)}"
        
        # Complete only 1 match
        session.matches[0].status = 'completed'
        session.matches[0].end_time = now()
        
        # Try to populate again - should NOT add new matches
        populate_courts_from_schedule(session)
        
        active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        # Still should be 3 (one completed, three still active)
        assert len(active_matches) == 3, \
            f"New matches started before round completion: {len(active_matches)}"
        
        # Complete remaining matches
        for m in session.matches:
            if m.status in ['waiting', 'in-progress']:
                m.status = 'completed'
                m.end_time = now()
        
        # Now populate - should add next round
        populate_courts_from_schedule(session)
        
        active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        assert len(active_matches) == 4, \
            f"Next round should have 4 matches, got {len(active_matches)}"


class TestWaiterManagement:
    """Test waiter display and swapping functionality."""
    
    def test_compute_scheduled_waiters(self):
        """Should correctly compute who waits in each round."""
        session = create_test_session(num_players=18, num_courts=4)
        all_player_ids = [p.id for p in session.config.players]
        
        # Create some test matches
        matches = []
        for i in range(4):  # 4 matches = 1 round
            matches.append(ScheduledMatch(
                id=f"match_{i}",
                team1=[all_player_ids[i*4], all_player_ids[i*4 + 1]],
                team2=[all_player_ids[i*4 + 2], all_player_ids[i*4 + 3]],
                status='approved',
                match_number=i + 1,
                balance_score=100
            ))
        
        # 18 players, 16 playing = 2 waiting
        waiters = compute_scheduled_waiters(matches, all_player_ids, num_courts=4)
        
        assert len(waiters) == 1, "Should have 1 round"
        assert len(waiters[0]) == 2, f"Should have 2 waiters, got {len(waiters[0])}"
    
    def test_get_round_info(self):
        """Should return properly structured round information."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        
        matches, waiters = generate_rounds_based_schedule(session, config)
        
        round_info = get_round_info(matches, waiters, num_courts=4)
        
        assert len(round_info) == len(waiters), "Should have info for each round"
        
        for info in round_info:
            assert 'round_number' in info
            assert 'matches' in info
            assert 'waiters' in info
            assert info['round_number'] >= 1
    
    def test_swap_waiter_in_round(self):
        """Should be able to swap a waiter with a playing player."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        
        matches, waiters = generate_rounds_based_schedule(session, config)
        
        # Approve all matches
        for m in matches:
            m.status = 'approved'
        config.scheduled_matches = matches
        config.scheduled_waiters = waiters
        
        # Get a waiter and a player from round 0
        if waiters[0]:
            waiter_id = waiters[0][0]
            # Find a player in round 0 matches
            round_0_matches = matches[:4]
            player_id = round_0_matches[0].team1[0]
            
            success, error = swap_waiter_in_round(
                config, matches, 0, waiter_id, player_id, session
            )
            
            assert success, f"Swap failed: {error}"
            
            # Verify the swap
            assert player_id in config.scheduled_waiters[0], \
                "Original player should now be waiting"
            assert waiter_id not in config.scheduled_waiters[0], \
                "Original waiter should now be playing"


class TestConstraintEnforcement:
    """Test that variety constraints are enforced."""
    
    def test_no_partnership_repeats(self):
        """Same two players should never partner twice."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        
        matches, _ = generate_rounds_based_schedule(session, config)
        
        # Track all partnerships
        partnerships = {}
        for m in matches:
            # Team 1 partnership
            pair1 = tuple(sorted(m.team1))
            partnerships[pair1] = partnerships.get(pair1, 0) + 1
            
            # Team 2 partnership
            pair2 = tuple(sorted(m.team2))
            partnerships[pair2] = partnerships.get(pair2, 0) + 1
        
        # No partnership should appear more than once
        for pair, count in partnerships.items():
            assert count == 1, f"Partnership {pair} repeated {count} times"
    
    def test_opponent_limits(self):
        """Individual opponent count should not exceed limit."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        config.max_individual_opponent_repeats = 2
        
        matches, _ = generate_rounds_based_schedule(session, config)
        
        # Track opponent counts
        opponent_counts = {}
        for m in matches:
            for p1 in m.team1:
                for p2 in m.team2:
                    pair = tuple(sorted([p1, p2]))
                    opponent_counts[pair] = opponent_counts.get(pair, 0) + 1
        
        # Check limits
        for pair, count in opponent_counts.items():
            assert count <= config.max_individual_opponent_repeats, \
                f"Opponent pair {pair} faced {count} times, limit is {config.max_individual_opponent_repeats}"


class TestBackToBackPrevention:
    """Test that players don't play with/against same person in consecutive rounds (soft constraint)."""
    
    def test_back_to_back_minimized(self):
        """Back-to-back interactions should be minimized (soft constraint).
        
        This is a SOFT constraint - we prefer to avoid back-to-back games with the same
        person but don't block matches entirely. The algorithm should significantly reduce
        but not eliminate all back-to-back violations.
        """
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.competitive_round_robin_config
        
        matches, waiters = generate_rounds_based_schedule(session, config)
        
        # Group matches by round
        matches_by_round: dict = {}
        for m in matches:
            round_num = m.round_number
            if round_num not in matches_by_round:
                matches_by_round[round_num] = []
            matches_by_round[round_num].append(m)
        
        # Check consecutive rounds
        sorted_rounds = sorted(matches_by_round.keys())
        back_to_back_violations = []
        
        for i in range(len(sorted_rounds) - 1):
            round_a = sorted_rounds[i]
            round_b = sorted_rounds[i + 1]
            
            # Get players who played in round A
            round_a_players = set()
            for m in matches_by_round.get(round_a, []):
                round_a_players.update(m.get_all_players())
            
            # Get players who played in round B
            round_b_players = set()
            for m in matches_by_round.get(round_b, []):
                round_b_players.update(m.get_all_players())
            
            # Only check players who played in BOTH consecutive rounds
            both_rounds = round_a_players & round_b_players
            
            # Get all interactions in round A
            round_a_interactions: dict = {}
            for m in matches_by_round.get(round_a, []):
                for p in m.team1:
                    if p not in round_a_interactions:
                        round_a_interactions[p] = {'partners': set(), 'opponents': set()}
                    partner = m.team1[0] if m.team1[1] == p else m.team1[1]
                    round_a_interactions[p]['partners'].add(partner)
                    round_a_interactions[p]['opponents'].update(m.team2)
                
                for p in m.team2:
                    if p not in round_a_interactions:
                        round_a_interactions[p] = {'partners': set(), 'opponents': set()}
                    partner = m.team2[0] if m.team2[1] == p else m.team2[1]
                    round_a_interactions[p]['partners'].add(partner)
                    round_a_interactions[p]['opponents'].update(m.team1)
            
            # Check round B for violations (only for players who played both rounds)
            for m in matches_by_round.get(round_b, []):
                for p in m.team1:
                    # Skip if player didn't play in round A
                    if p not in both_rounds:
                        continue
                    
                    partner = m.team1[0] if m.team1[1] == p else m.team1[1]
                    
                    # Only check against players who also played both rounds
                    if partner in both_rounds and p in round_a_interactions:
                        if partner in round_a_interactions[p]['partners']:
                            back_to_back_violations.append(
                                f"Round {round_a}->{round_b}: {p} partnered with {partner} back-to-back"
                            )
                        if partner in round_a_interactions[p]['opponents']:
                            back_to_back_violations.append(
                                f"Round {round_a}->{round_b}: {p} played with {partner} after being opponents"
                            )
                    
                    # Check opponents who also played both rounds
                    for opp in m.team2:
                        if opp in both_rounds and p in round_a_interactions:
                            if opp in round_a_interactions[p]['partners']:
                                back_to_back_violations.append(
                                    f"Round {round_a}->{round_b}: {p} faces {opp} after being partners"
                                )
                            if opp in round_a_interactions[p]['opponents']:
                                back_to_back_violations.append(
                                    f"Round {round_a}->{round_b}: {p} faces {opp} back-to-back"
                                )
        
        # With a soft constraint, some violations are acceptable
        # The key is that the algorithm TRIES to minimize them
        # For 18 players, 4 courts, 8+ rounds, we allow up to 30 violations
        # (without the penalty, there would be significantly more)
        max_acceptable_violations = 30
        assert len(back_to_back_violations) <= max_acceptable_violations, \
            f"Found {len(back_to_back_violations)} back-to-back violations (max {max_acceptable_violations}):\n" + "\n".join(back_to_back_violations[:10])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
