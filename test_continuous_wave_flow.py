"""
Tests for Continuous Wave Flow mode - dynamic matchmaking.

Key features to test:
1. Only first round is pre-scheduled
2. Dynamic match generation as courts finish
3. Priority to longest waiters
4. At least 2 players swap between matches
5. Soft variety constraints (don't block matches)
6. Warning when waitlist < 2
"""

import pytest
from typing import List
from python.pickleball_types import (
    Player, Session, SessionConfig, ContinuousWaveFlowConfig,
    ScheduledMatch, Match
)
from python.session import create_session
from python.continuous_wave_flow import (
    generate_first_round_schedule,
    generate_next_match_for_court,
    populate_courts_continuous_wave_flow,
    check_waitlist_warning,
    get_player_wait_priority
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
    """Create a test session for continuous wave flow."""
    initialize_time_manager()
    players = create_test_players(num_players)
    
    config = ContinuousWaveFlowConfig(
        games_per_player=8,
        min_waitlist_warning_threshold=2
    )
    
    session_config = SessionConfig(
        mode='continuous-wave-flow',
        session_type='doubles',
        players=players,
        courts=num_courts,
        pre_seeded_ratings=True,
        continuous_wave_flow_config=config
    )
    
    return create_session(session_config)


class TestFirstRoundScheduling:
    """Test first round scheduling behavior."""
    
    def test_generate_first_round_only(self):
        """Should only generate matches for num_courts (first round only)."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.continuous_wave_flow_config
        
        matches = generate_first_round_schedule(session, config)
        
        # Should have exactly num_courts matches (first round)
        assert len(matches) == 4, f"Expected 4 matches, got {len(matches)}"
    
    def test_first_round_balance(self):
        """First round matches should be well-balanced."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.continuous_wave_flow_config
        
        matches = generate_first_round_schedule(session, config)
        
        # All matches should have positive balance scores
        for m in matches:
            assert m.balance_score > 0, f"Match {m.id} has poor balance: {m.balance_score}"
    
    def test_first_round_no_player_overlap(self):
        """Players should not appear in multiple first round matches."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.continuous_wave_flow_config
        
        matches = generate_first_round_schedule(session, config)
        
        used_players = set()
        for m in matches:
            match_players = set(m.team1 + m.team2)
            assert not (match_players & used_players), \
                f"Player overlap in first round matches"
            used_players.update(match_players)


class TestDynamicMatchGeneration:
    """Test dynamic match generation as courts finish."""
    
    def test_prioritizes_longest_waiters(self):
        """Next match should prioritize players who waited longest."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.continuous_wave_flow_config
        
        # Generate first round
        first_round = generate_first_round_schedule(session, config)
        for m in first_round:
            m.status = 'approved'
        config.scheduled_matches = first_round
        config.schedule_finalized = True
        
        # Populate courts with first round
        populate_courts_continuous_wave_flow(session)
        
        # Track who is on courts
        players_on_courts = set()
        for m in session.matches:
            if m.status in ['waiting', 'in-progress']:
                players_on_courts.update(m.team1 + m.team2)
        
        # Mark one match as completed
        for m in session.matches:
            if m.status == 'waiting':
                m.status = 'completed'
                m.end_time = now()
                finished_players = set(m.team1 + m.team2)
                break
        
        # Generate next match
        result = generate_next_match_for_court(session, 1, finished_players)
        
        assert result is not None, "Should generate a next match"
        team1, team2 = result
        
        # The match should include at least some waiting players
        next_match_players = set(team1 + team2)
        waiting_players = set(session.active_players) - players_on_courts
        
        # At least 2 players should come from waiting list
        from_waitlist = next_match_players & waiting_players
        assert len(from_waitlist) >= 2, \
            f"Expected at least 2 from waitlist, got {len(from_waitlist)}"
    
    def test_swaps_at_least_two_players(self):
        """Each new match should swap at least 2 players from previous match."""
        session = create_test_session(num_players=18, num_courts=4)
        
        # Create a mock "just finished" set of players
        just_finished = set(['player_0', 'player_1', 'player_2', 'player_3'])
        
        # Add some waiting players with high priority
        for i in range(4, 18):
            session.player_stats[f'player_{i}'].games_waited = i - 4
        
        result = generate_next_match_for_court(session, 1, just_finished)
        
        assert result is not None, "Should generate a match"
        team1, team2 = result
        next_match_players = set(team1 + team2)
        
        # At most 2 players from the finished match should be in new match
        carried_over = next_match_players & just_finished
        assert len(carried_over) <= 2, \
            f"Too many players carried over: {len(carried_over)}"


class TestSoftVarietyConstraints:
    """Test that variety constraints are soft (don't block matches)."""
    
    def test_matches_always_generated(self):
        """Should always generate a match even with constraint violations."""
        session = create_test_session(num_players=8, num_courts=2)  # Very constrained
        
        # Play many games to create constraint conflicts
        for i in range(10):
            just_finished = set([f'player_{j}' for j in range(4)])
            result = generate_next_match_for_court(session, 1, just_finished)
            
            # Should always get a match result (soft constraints)
            assert result is not None, f"Match generation failed on iteration {i}"


class TestWaitlistWarning:
    """Test waitlist size warnings."""
    
    def test_warning_when_waitlist_small(self):
        """Should warn when waitlist has fewer than 2 players."""
        # 16 players with 4 courts = 0 waiters
        session = create_test_session(num_players=16, num_courts=4)
        
        # Create some active matches to have 0 waiters
        from python.utils import generate_id
        for i in range(4):
            match = Match(
                id=generate_id(),
                court_number=i + 1,
                team1=[f'player_{i*4}', f'player_{i*4+1}'],
                team2=[f'player_{i*4+2}', f'player_{i*4+3}'],
                status='waiting',
                start_time=now()
            )
            session.matches.append(match)
        
        warning = check_waitlist_warning(session)
        
        assert warning is not None, "Should have a warning"
        assert "Warning" in warning
    
    def test_no_warning_with_sufficient_waitlist(self):
        """Should not warn when waitlist has 2+ players."""
        session = create_test_session(num_players=18, num_courts=4)
        
        # Create matches using 16 players, leaving 2 waiting
        from python.utils import generate_id
        for i in range(4):
            match = Match(
                id=generate_id(),
                court_number=i + 1,
                team1=[f'player_{i*4}', f'player_{i*4+1}'],
                team2=[f'player_{i*4+2}', f'player_{i*4+3}'],
                status='waiting',
                start_time=now()
            )
            session.matches.append(match)
        
        warning = check_waitlist_warning(session)
        
        assert warning is None, f"Should not warn with 2 waiters: {warning}"


class TestWaitPriority:
    """Test wait priority calculations."""
    
    def test_wait_priority_increases_with_wait_time(self):
        """Players waiting longer should have higher priority."""
        session = create_test_session(num_players=18, num_courts=4)
        
        # Set different wait times
        session.player_stats['player_0'].total_wait_time = 100
        session.player_stats['player_1'].total_wait_time = 500
        
        priority_0 = get_player_wait_priority(session, 'player_0')
        priority_1 = get_player_wait_priority(session, 'player_1')
        
        assert priority_1 > priority_0, \
            f"Player 1 (wait=500) should have higher priority than Player 0 (wait=100)"
    
    def test_games_waited_affects_priority(self):
        """Legacy games_waited should also affect priority."""
        session = create_test_session(num_players=18, num_courts=4)
        
        # Same total_wait_time but different games_waited
        session.player_stats['player_0'].total_wait_time = 0
        session.player_stats['player_0'].games_waited = 0
        
        session.player_stats['player_1'].total_wait_time = 0
        session.player_stats['player_1'].games_waited = 5
        
        priority_0 = get_player_wait_priority(session, 'player_0')
        priority_1 = get_player_wait_priority(session, 'player_1')
        
        assert priority_1 > priority_0, \
            "Player with more games_waited should have higher priority"


class TestContinuousCourtPopulation:
    """Test that courts populate immediately when available."""
    
    def test_court_populates_on_finish(self):
        """When one court finishes, it should populate immediately."""
        session = create_test_session(num_players=18, num_courts=4)
        config = session.config.continuous_wave_flow_config
        
        # Generate and approve first round
        first_round = generate_first_round_schedule(session, config)
        for m in first_round:
            m.status = 'approved'
        config.scheduled_matches = first_round
        config.schedule_finalized = True
        
        # Populate first round
        populate_courts_continuous_wave_flow(session)
        
        initial_count = len(session.matches)
        assert initial_count == 4, f"Expected 4 matches, got {initial_count}"
        
        # Complete one match
        session.matches[0].status = 'completed'
        session.matches[0].end_time = now()
        
        # Clear first round scheduled matches to trigger dynamic generation
        config.scheduled_matches = []
        
        # Populate again - should add a new match
        populate_courts_continuous_wave_flow(session)
        
        # Should have 5 matches now (4 original + 1 new)
        assert len(session.matches) == 5, \
            f"Expected 5 matches after repopulation, got {len(session.matches)}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
