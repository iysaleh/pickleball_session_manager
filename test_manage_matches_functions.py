"""
Comprehensive tests for Manage Scheduled Matches functions.

Tests the core functions used by ManageMatchesDialog:
- regenerate_round_with_type: Regenerate a single round with a specific type
- regenerate_subsequent_rounds: Regenerate all rounds after a modified round
- swap_player_between_matches_or_waitlist: Swap players within a round
- get_round_info: Get round information for display

Key requirements tested:
1. All courts must be filled when regenerating rounds (no missing matches)
2. VARIETY rounds must introduce randomization (different results on repeated calls)
3. COMPETITIVE and ULTRA-COMPETITIVE rounds must also have some randomization
4. Subsequent round regeneration must not break earlier rounds
5. All players must be accounted for (no player loss or duplication)
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.pickleball_types import Session, SessionConfig, Player, CompetitiveRoundRobinConfig
from python.session import create_session
from python.time_manager import initialize_time_manager
from python.competitive_round_robin import (
    generate_rounds_based_schedule,
    regenerate_round_with_type,
    regenerate_subsequent_rounds,
    swap_player_between_matches_or_waitlist,
    get_round_info,
    ROUND_TYPE_COMPETITIVE,
    ROUND_TYPE_VARIETY,
    ROUND_TYPE_ULTRA_COMPETITIVE
)


def create_test_session(num_players: int = 19, num_courts: int = 4) -> Session:
    """Create a test session with specified number of players and courts."""
    initialize_time_manager()
    
    players = []
    for i in range(num_players):
        rating = 4.5 - (i * 0.1)  # Ratings from 4.5 down
        if rating < 2.5:
            rating = 2.5
        players.append(Player(
            id=f"player_{i}",
            name=f"Player {i}",
            skill_rating=rating
        ))
    
    config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        players=players,
        courts=num_courts
    )
    
    session = create_session(config)
    session.config.competitive_round_robin_config = CompetitiveRoundRobinConfig(
        games_per_player=8
    )
    
    return session


class TestRegenerateSubsequentRoundsFillsCourts(unittest.TestCase):
    """Test that regenerate_subsequent_rounds fills all courts properly."""
    
    def test_all_courts_filled_after_regeneration(self):
        """After regenerating subsequent rounds, all courts should have matches."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        # Generate initial schedule
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        # Count matches per round before
        num_courts = session.config.courts
        num_rounds = len(scheduled_waiters)
        
        # Regenerate from round 0 (should regenerate rounds 1 onward)
        new_matches, new_waiters = regenerate_subsequent_rounds(
            session, scheduled_matches, scheduled_waiters, 0, config
        )
        
        # Check each round has correct number of matches
        for round_idx in range(num_rounds):
            start_idx = round_idx * num_courts
            end_idx = start_idx + num_courts
            round_matches = new_matches[start_idx:end_idx]
            
            self.assertEqual(
                len(round_matches), num_courts,
                f"Round {round_idx + 1} should have {num_courts} matches, got {len(round_matches)}"
            )
    
    def test_no_missing_courts_after_multiple_regenerations(self):
        """Multiple regenerations should not cause court loss."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        num_courts = session.config.courts
        
        # Regenerate 5 times from different starting points
        for start_round in range(min(3, len(scheduled_waiters) - 1)):
            scheduled_matches, scheduled_waiters = regenerate_subsequent_rounds(
                session, scheduled_matches, scheduled_waiters, start_round, config
            )
            
            # Verify all rounds still have correct court count
            for round_idx in range(len(scheduled_waiters)):
                start_idx = round_idx * num_courts
                end_idx = start_idx + num_courts
                round_matches = scheduled_matches[start_idx:end_idx]
                
                self.assertEqual(
                    len(round_matches), num_courts,
                    f"After regenerating from round {start_round}, round {round_idx + 1} has {len(round_matches)} matches, expected {num_courts}"
                )


class TestVarietyRoundRandomization(unittest.TestCase):
    """Test that VARIETY rounds produce different results on repeated calls."""
    
    def test_variety_produces_different_results(self):
        """Calling regenerate_round_with_type(VARIETY) multiple times should produce different results."""
        session = create_test_session(16, 4)  # No waiters to simplify
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        num_courts = session.config.courts
        
        # Generate VARIETY round 10 times and collect unique configurations
        unique_configs = set()
        
        for _ in range(10):
            new_matches, error = regenerate_round_with_type(
                session, scheduled_matches, scheduled_waiters, 0, ROUND_TYPE_VARIETY, config
            )
            
            self.assertEqual(error, "", f"Error regenerating VARIETY round: {error}")
            self.assertEqual(len(new_matches), num_courts, "Should generate matches for all courts")
            
            # Create a hashable configuration signature
            config_sig = tuple(sorted([
                tuple(sorted(m.team1 + m.team2)) for m in new_matches
            ]))
            unique_configs.add(config_sig)
        
        # Should have at least 2 different configurations (high probability with randomization)
        self.assertGreater(
            len(unique_configs), 1,
            "VARIETY round should produce different configurations on repeated calls"
        )
    
    def test_competitive_produces_different_team_pairings(self):
        """COMPETITIVE rounds should produce different team pairings."""
        session = create_test_session(16, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        # Generate COMPETITIVE round multiple times
        unique_team_configs = set()
        
        for _ in range(10):
            new_matches, error = regenerate_round_with_type(
                session, scheduled_matches, scheduled_waiters, 0, ROUND_TYPE_COMPETITIVE, config
            )
            
            self.assertEqual(error, "")
            
            # Capture team pairings (who is partnered with whom)
            teams_sig = tuple(sorted([
                (tuple(sorted(m.team1)), tuple(sorted(m.team2))) for m in new_matches
            ]))
            unique_team_configs.add(teams_sig)
        
        # Should see some variation in team pairings
        self.assertGreater(
            len(unique_team_configs), 1,
            "COMPETITIVE round should produce different team pairings on repeated calls"
        )
    
    def test_ultra_competitive_produces_different_pairings(self):
        """ULTRA-COMPETITIVE rounds should produce different pairings within skill groups."""
        session = create_test_session(16, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        unique_pairings = set()
        
        for _ in range(10):
            new_matches, error = regenerate_round_with_type(
                session, scheduled_matches, scheduled_waiters, 0, ROUND_TYPE_ULTRA_COMPETITIVE, config
            )
            
            self.assertEqual(error, "")
            
            # Capture pairings
            pairings_sig = tuple(sorted([
                (tuple(sorted(m.team1)), tuple(sorted(m.team2))) for m in new_matches
            ]))
            unique_pairings.add(pairings_sig)
        
        # Should see some variation
        self.assertGreater(
            len(unique_pairings), 1,
            "ULTRA-COMPETITIVE round should produce different pairings on repeated calls"
        )


class TestAllPlayersAccountedFor(unittest.TestCase):
    """Test that all players are accounted for after regeneration."""
    
    def test_no_player_loss_after_regeneration(self):
        """All players should be either playing or waiting after regeneration."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        all_player_ids = {p.id for p in session.config.players}
        
        # Regenerate from round 1
        new_matches, new_waiters = regenerate_subsequent_rounds(
            session, scheduled_matches, scheduled_waiters, 1, config
        )
        
        # Check each round
        for round_idx, waiters in enumerate(new_waiters):
            num_courts = session.config.courts
            start_idx = round_idx * num_courts
            end_idx = start_idx + num_courts
            round_matches = new_matches[start_idx:end_idx]
            
            # Get all players in this round
            players_in_round = set()
            for match in round_matches:
                players_in_round.update(match.team1 + match.team2)
            players_in_round.update(waiters)
            
            self.assertEqual(
                players_in_round, all_player_ids,
                f"Round {round_idx + 1}: All players should be either playing or waiting"
            )
    
    def test_no_player_duplication_after_regeneration(self):
        """No player should appear twice in the same round."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        new_matches, new_waiters = regenerate_subsequent_rounds(
            session, scheduled_matches, scheduled_waiters, 0, config
        )
        
        for round_idx, waiters in enumerate(new_waiters):
            num_courts = session.config.courts
            start_idx = round_idx * num_courts
            end_idx = start_idx + num_courts
            round_matches = new_matches[start_idx:end_idx]
            
            # Collect all player appearances
            players_seen = []
            for match in round_matches:
                players_seen.extend(match.team1 + match.team2)
            players_seen.extend(waiters)
            
            # Check for duplicates
            self.assertEqual(
                len(players_seen), len(set(players_seen)),
                f"Round {round_idx + 1}: No player should appear twice"
            )


class TestRoundTypePreservation(unittest.TestCase):
    """Test that round types are properly set and preserved."""
    
    def test_regenerate_sets_round_type(self):
        """Regenerated rounds should have correct round_type attribute."""
        session = create_test_session(16, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        for round_type in [ROUND_TYPE_VARIETY, ROUND_TYPE_COMPETITIVE, ROUND_TYPE_ULTRA_COMPETITIVE]:
            new_matches, error = regenerate_round_with_type(
                session, scheduled_matches, scheduled_waiters, 0, round_type, config
            )
            
            self.assertEqual(error, "")
            
            for match in new_matches:
                self.assertEqual(
                    match.round_type, round_type,
                    f"Match should have round_type={round_type}"
                )
    
    def test_subsequent_rounds_follow_pattern(self):
        """Subsequent rounds should follow the expected pattern."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        new_matches, new_waiters = regenerate_subsequent_rounds(
            session, scheduled_matches, scheduled_waiters, 0, config
        )
        
        num_courts = session.config.courts
        
        # Check pattern: Round 0 = ultra-competitive, then 1,3,5 = competitive, 2,4,6 = variety
        for round_idx in range(1, len(new_waiters)):  # Start from round 1 (regenerated)
            start_idx = round_idx * num_courts
            if start_idx >= len(new_matches):
                break
            
            match = new_matches[start_idx]
            
            if round_idx == 0:
                expected = ROUND_TYPE_ULTRA_COMPETITIVE
            elif (round_idx - 1) % 2 == 0:  # rounds 1, 3, 5, ...
                expected = ROUND_TYPE_COMPETITIVE
            else:  # rounds 2, 4, 6, ...
                expected = ROUND_TYPE_VARIETY
            
            self.assertEqual(
                match.round_type, expected,
                f"Round {round_idx + 1} should be {expected}, got {match.round_type}"
            )


class TestSwapPlayerFunctionality(unittest.TestCase):
    """Test swap_player_between_matches_or_waitlist edge cases."""
    
    def test_swap_preserves_all_players(self):
        """Swapping players should not lose any players."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        all_player_ids = {p.id for p in session.config.players}
        
        # Get two players from round 0 - one playing, one waiting
        player1 = scheduled_matches[0].team1[0]  # Playing
        player2 = scheduled_waiters[0][0] if scheduled_waiters[0] else None  # Waiting
        
        if player2:
            success, error = swap_player_between_matches_or_waitlist(
                session, scheduled_matches, scheduled_waiters, 0, player1, player2, config
            )
            
            self.assertTrue(success, f"Swap should succeed: {error}")
            
            # Verify all players still present
            players_in_round = set()
            num_courts = session.config.courts
            for match in scheduled_matches[:num_courts]:
                players_in_round.update(match.team1 + match.team2)
            players_in_round.update(scheduled_waiters[0])
            
            self.assertEqual(
                players_in_round, all_player_ids,
                "All players should still be present after swap"
            )
    
    def test_swap_between_different_matches(self):
        """Swapping players between different matches should work."""
        session = create_test_session(16, 4)  # No waiters
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        # Get players from match 0 and match 1
        player1 = scheduled_matches[0].team1[0]
        player2 = scheduled_matches[1].team1[0]
        
        success, error = swap_player_between_matches_or_waitlist(
            session, scheduled_matches, scheduled_waiters, 0, player1, player2, config
        )
        
        self.assertTrue(success, f"Swap between matches should succeed: {error}")
        
        # Verify players swapped positions
        self.assertIn(player2, scheduled_matches[0].team1 + scheduled_matches[0].team2)
        self.assertIn(player1, scheduled_matches[1].team1 + scheduled_matches[1].team2)


class TestGetRoundInfo(unittest.TestCase):
    """Test get_round_info function."""
    
    def test_round_info_structure(self):
        """get_round_info should return proper structure."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        rounds_info = get_round_info(scheduled_matches, scheduled_waiters, session.config.courts)
        
        self.assertEqual(len(rounds_info), len(scheduled_waiters))
        
        for round_info in rounds_info:
            self.assertIn('round_number', round_info)
            self.assertIn('matches', round_info)
            self.assertIn('waiters', round_info)
            self.assertIsInstance(round_info['matches'], list)
            self.assertIsInstance(round_info['waiters'], list)
    
    def test_round_info_match_counts(self):
        """Each round should have correct number of matches (except possibly the last)."""
        session = create_test_session(19, 4)
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        num_courts = session.config.courts
        
        rounds_info = get_round_info(scheduled_matches, scheduled_waiters, num_courts)
        
        # Check all rounds except the last one (which might be partial)
        for round_info in rounds_info[:-1]:
            if len(round_info['matches']) > 0:  # Skip truly empty rounds
                self.assertEqual(
                    len(round_info['matches']), num_courts,
                    f"Round {round_info['round_number']} should have {num_courts} matches"
                )


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_exact_court_capacity(self):
        """Test with exactly 4 players per court (no waiters)."""
        session = create_test_session(16, 4)  # 16 players, 4 courts = 0 waiters
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        # All rounds should have 0 waiters
        for waiters in scheduled_waiters:
            self.assertEqual(len(waiters), 0, "Should have no waiters with exact capacity")
        
        # Regeneration should still work
        new_matches, new_waiters = regenerate_subsequent_rounds(
            session, scheduled_matches, scheduled_waiters, 0, config
        )
        
        for round_idx, waiters in enumerate(new_waiters):
            self.assertEqual(len(waiters), 0, f"Round {round_idx + 1} should still have no waiters")
    
    def test_many_waiters(self):
        """Test with many players waiting each round."""
        session = create_test_session(23, 4)  # 23 players, 4 courts = 7 waiters
        config = session.config.competitive_round_robin_config
        
        scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
        
        # Each round should have 7 waiters
        for waiters in scheduled_waiters:
            self.assertEqual(len(waiters), 7, "Should have 7 waiters each round")
        
        # Regeneration should maintain waiter count
        new_matches, new_waiters = regenerate_subsequent_rounds(
            session, scheduled_matches, scheduled_waiters, 0, config
        )
        
        for round_idx, waiters in enumerate(new_waiters):
            self.assertEqual(
                len(waiters), 7,
                f"Round {round_idx + 1} should have 7 waiters after regeneration"
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
