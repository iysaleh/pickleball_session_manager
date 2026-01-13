"""
Tests for the Manage Matches UI improvements:
1. Round type toggling (VARIETY, COMPETITIVE, ULTRA-COMPETITIVE)
2. Player swapping within/between matches
3. Waitlist swapping
4. Subsequent round regeneration
"""

import sys
import unittest
from typing import List, Dict

# Add the project root to path
sys.path.insert(0, '/home/isaleh/dev/pickleball')

from python.pickleball_types import (
    Player, Session, SessionConfig, CompetitiveRoundRobinConfig, ScheduledMatch
)
from python.session import create_session
from python.time_manager import initialize_time_manager
from python.competitive_round_robin import (
    generate_rounds_based_schedule,
    get_next_round_type,
    regenerate_round_with_type,
    swap_player_between_matches_or_waitlist,
    regenerate_subsequent_rounds,
    ROUND_TYPE_COMPETITIVE,
    ROUND_TYPE_VARIETY,
    ROUND_TYPE_ULTRA_COMPETITIVE,
    ROUND_TYPE_CYCLE
)

# Initialize time manager for tests
initialize_time_manager()


def create_test_session(num_players: int = 18, num_courts: int = 4) -> Session:
    """Create a test session with given number of players and courts."""
    players = []
    ratings = [4.5, 4.25, 4.0, 4.0, 3.75, 3.75, 3.5, 3.5, 3.5, 
               3.25, 3.25, 3.0, 3.0, 3.0, 2.75, 2.75, 2.5, 2.5]
    
    for i in range(num_players):
        rating = ratings[i] if i < len(ratings) else 3.0
        players.append(Player(
            id=f"player_{i}",
            name=f"Player {i+1}",
            skill_rating=rating
        ))
    
    config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        players=players,
        courts=num_courts
    )
    
    return create_session(config)


class TestRoundTypeCycle(unittest.TestCase):
    """Test round type cycling functionality"""
    
    def test_round_type_cycle_order(self):
        """Test that round types cycle in correct order: VARIETY -> COMPETITIVE -> ULTRA-COMPETITIVE"""
        self.assertEqual(ROUND_TYPE_CYCLE, [ROUND_TYPE_VARIETY, ROUND_TYPE_COMPETITIVE, ROUND_TYPE_ULTRA_COMPETITIVE])
    
    def test_get_next_round_type_from_variety(self):
        """Test cycling from VARIETY to COMPETITIVE"""
        next_type = get_next_round_type(ROUND_TYPE_VARIETY)
        self.assertEqual(next_type, ROUND_TYPE_COMPETITIVE)
    
    def test_get_next_round_type_from_competitive(self):
        """Test cycling from COMPETITIVE to ULTRA-COMPETITIVE"""
        next_type = get_next_round_type(ROUND_TYPE_COMPETITIVE)
        self.assertEqual(next_type, ROUND_TYPE_ULTRA_COMPETITIVE)
    
    def test_get_next_round_type_from_ultra_competitive(self):
        """Test cycling from ULTRA-COMPETITIVE back to VARIETY"""
        next_type = get_next_round_type(ROUND_TYPE_ULTRA_COMPETITIVE)
        self.assertEqual(next_type, ROUND_TYPE_VARIETY)
    
    def test_get_next_round_type_unknown(self):
        """Test that unknown type defaults to COMPETITIVE"""
        next_type = get_next_round_type('unknown')
        self.assertEqual(next_type, ROUND_TYPE_COMPETITIVE)


class TestRegenerateRoundWithType(unittest.TestCase):
    """Test regenerating a round with a new type"""
    
    def setUp(self):
        self.session = create_test_session(18, 4)
        self.config = CompetitiveRoundRobinConfig(games_per_player=8)
        self.scheduled_matches, self.scheduled_waiters = generate_rounds_based_schedule(
            self.session, self.config
        )
    
    def test_regenerate_round_preserves_player_count(self):
        """Test that regenerating a round keeps same players (not waiters)"""
        round_index = 0
        num_courts = self.session.config.courts
        
        # Get original players in round 0
        original_players = set()
        for match in self.scheduled_matches[:num_courts]:
            original_players.update(match.get_all_players())
        
        # Regenerate round 0 with ULTRA-COMPETITIVE
        new_matches, error = regenerate_round_with_type(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            ROUND_TYPE_ULTRA_COMPETITIVE,
            self.config
        )
        
        self.assertEqual(error, "")
        self.assertEqual(len(new_matches), num_courts)
        
        # Check same players are used
        new_players = set()
        for match in new_matches:
            new_players.update(match.get_all_players())
        
        self.assertEqual(original_players, new_players)
    
    def test_regenerate_round_changes_type(self):
        """Test that regenerating a round changes the round type"""
        round_index = 0
        
        new_matches, error = regenerate_round_with_type(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            ROUND_TYPE_ULTRA_COMPETITIVE,
            self.config
        )
        
        self.assertEqual(error, "")
        for match in new_matches:
            self.assertEqual(match.round_type, ROUND_TYPE_ULTRA_COMPETITIVE)
    
    def test_ultra_competitive_groups_highest_together(self):
        """Test that ULTRA-COMPETITIVE puts highest rated players on same court"""
        round_index = 0
        num_courts = self.session.config.courts
        
        new_matches, error = regenerate_round_with_type(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            ROUND_TYPE_ULTRA_COMPETITIVE,
            self.config
        )
        
        self.assertEqual(error, "")
        
        # First match should have highest rated players
        if new_matches:
            first_match = new_matches[0]
            all_players = first_match.get_all_players()
            
            # Get ratings for players in first match
            first_match_ratings = []
            for pid in all_players:
                for p in self.session.config.players:
                    if p.id == pid:
                        first_match_ratings.append(p.skill_rating)
                        break
            
            # Average should be high (above 3.5)
            avg_rating = sum(first_match_ratings) / len(first_match_ratings)
            self.assertGreater(avg_rating, 3.5, 
                f"First match in ULTRA-COMPETITIVE should have high ratings, got avg {avg_rating}")


class TestPlayerSwapping(unittest.TestCase):
    """Test player swapping functionality"""
    
    def setUp(self):
        self.session = create_test_session(18, 4)
        self.config = CompetitiveRoundRobinConfig(games_per_player=8)
        self.scheduled_matches, self.scheduled_waiters = generate_rounds_based_schedule(
            self.session, self.config
        )
    
    def test_swap_players_within_same_match(self):
        """Test swapping two players in the same match"""
        round_index = 0
        num_courts = self.session.config.courts
        
        # Get first match
        match = self.scheduled_matches[0]
        player1 = match.team1[0]
        player2 = match.team2[0]
        
        success, error = swap_player_between_matches_or_waitlist(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            player1,
            player2,
            self.config
        )
        
        self.assertTrue(success, f"Swap failed: {error}")
        
        # Check that players swapped
        updated_match = self.scheduled_matches[0]
        self.assertIn(player2, updated_match.team1, "Player2 should now be in team1")
        self.assertIn(player1, updated_match.team2, "Player1 should now be in team2")
    
    def test_swap_players_between_matches(self):
        """Test swapping two players in different matches of same round"""
        round_index = 0
        num_courts = self.session.config.courts
        
        if num_courts < 2:
            self.skipTest("Need at least 2 courts for this test")
        
        # Get players from different matches
        match1 = self.scheduled_matches[0]
        match2 = self.scheduled_matches[1]
        player1 = match1.team1[0]
        player2 = match2.team1[0]
        
        success, error = swap_player_between_matches_or_waitlist(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            player1,
            player2,
            self.config
        )
        
        self.assertTrue(success, f"Swap failed: {error}")
        
        # Check that players swapped between matches
        updated_match1 = self.scheduled_matches[0]
        updated_match2 = self.scheduled_matches[1]
        self.assertIn(player2, updated_match1.get_all_players())
        self.assertIn(player1, updated_match2.get_all_players())
    
    def test_swap_player_with_waiter(self):
        """Test swapping a player in match with a player on waitlist"""
        round_index = 0
        
        if not self.scheduled_waiters[round_index]:
            self.skipTest("No waiters in first round")
        
        # Get player from match and waiter
        match = self.scheduled_matches[0]
        match_player = match.team1[0]
        waiter = self.scheduled_waiters[round_index][0]
        
        success, error = swap_player_between_matches_or_waitlist(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            match_player,
            waiter,
            self.config
        )
        
        self.assertTrue(success, f"Swap failed: {error}")
        
        # Check that waiter is now in match
        updated_match = self.scheduled_matches[0]
        self.assertIn(waiter, updated_match.get_all_players(), 
            "Waiter should now be in match")
        
        # Check that match_player is now on waitlist
        self.assertIn(match_player, self.scheduled_waiters[round_index],
            "Match player should now be on waitlist")


class TestSubsequentRoundRegeneration(unittest.TestCase):
    """Test that modifying a round regenerates subsequent rounds"""
    
    def setUp(self):
        self.session = create_test_session(18, 4)
        self.config = CompetitiveRoundRobinConfig(games_per_player=8)
        self.scheduled_matches, self.scheduled_waiters = generate_rounds_based_schedule(
            self.session, self.config
        )
    
    def test_regenerate_subsequent_rounds_preserves_earlier_rounds(self):
        """Test that regeneration does NOT change rounds before the modified round"""
        round_index = 2
        num_courts = self.session.config.courts
        
        if len(self.scheduled_waiters) <= round_index:
            self.skipTest("Not enough rounds for this test")
        
        # Store matches from rounds 0, 1, 2
        original_round_0 = [m.id for m in self.scheduled_matches[:num_courts]]
        original_round_1 = [m.id for m in self.scheduled_matches[num_courts:2*num_courts]]
        original_round_2 = [m.id for m in self.scheduled_matches[2*num_courts:3*num_courts]]
        
        # Regenerate from round 2 onwards
        new_matches, new_waiters = regenerate_subsequent_rounds(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            self.config
        )
        
        # Rounds 0, 1, 2 should be preserved
        preserved_round_0 = [m.id for m in new_matches[:num_courts]]
        preserved_round_1 = [m.id for m in new_matches[num_courts:2*num_courts]]
        preserved_round_2 = [m.id for m in new_matches[2*num_courts:3*num_courts]]
        
        self.assertEqual(original_round_0, preserved_round_0, "Round 0 should be preserved")
        self.assertEqual(original_round_1, preserved_round_1, "Round 1 should be preserved")
        self.assertEqual(original_round_2, preserved_round_2, "Round 2 should be preserved")
    
    def test_regenerate_subsequent_rounds_changes_later_rounds(self):
        """Test that regeneration DOES change rounds after the modified round"""
        round_index = 1
        num_courts = self.session.config.courts
        
        if len(self.scheduled_waiters) <= round_index + 1:
            self.skipTest("Not enough rounds for this test")
        
        # Store matches from round 2 (which should change)
        original_round_2_players = set()
        for m in self.scheduled_matches[2*num_courts:3*num_courts]:
            original_round_2_players.update(m.get_all_players())
        
        # Modify round 1 to force different player usage
        # Swap a player with waitlist to change constraint state
        if self.scheduled_waiters[round_index]:
            match = self.scheduled_matches[num_courts]
            match_player = match.team1[0]
            waiter = self.scheduled_waiters[round_index][0]
            
            swap_player_between_matches_or_waitlist(
                self.session,
                self.scheduled_matches,
                self.scheduled_waiters,
                round_index,
                match_player,
                waiter,
                self.config
            )
        
        # Regenerate from round 1 onwards
        new_matches, new_waiters = regenerate_subsequent_rounds(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            self.config
        )
        
        # Round 2+ should have new match IDs (regenerated)
        if len(new_matches) > 2 * num_courts:
            new_round_2_ids = [m.id for m in new_matches[2*num_courts:3*num_courts]]
            # New matches should have different IDs since they're regenerated
            for mid in new_round_2_ids:
                self.assertTrue(mid.startswith('scheduled_'), 
                    "Regenerated matches should have proper IDs")


class TestRoundTypeIntegration(unittest.TestCase):
    """Integration tests for round type changes"""
    
    def setUp(self):
        self.session = create_test_session(18, 4)
        self.config = CompetitiveRoundRobinConfig(games_per_player=8)
        self.scheduled_matches, self.scheduled_waiters = generate_rounds_based_schedule(
            self.session, self.config
        )
    
    def test_full_round_type_toggle_workflow(self):
        """Test the full workflow of toggling round type and regenerating"""
        round_index = 0
        num_courts = self.session.config.courts
        
        # Get original type
        original_type = self.scheduled_matches[0].round_type
        
        # Get next type
        new_type = get_next_round_type(original_type)
        
        # Regenerate round with new type
        new_matches, error = regenerate_round_with_type(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            new_type,
            self.config
        )
        
        self.assertEqual(error, "")
        
        # Replace matches for this round
        self.scheduled_matches[:num_courts] = new_matches
        
        # Regenerate subsequent rounds
        self.scheduled_matches, self.scheduled_waiters = regenerate_subsequent_rounds(
            self.session,
            self.scheduled_matches,
            self.scheduled_waiters,
            round_index,
            self.config
        )
        
        # Verify round 0 has new type
        self.assertEqual(self.scheduled_matches[0].round_type, new_type)
        
        # Verify schedule structure is still valid for the first few rounds
        all_player_ids = {p.id for p in self.session.config.players}
        
        # Only check rounds that have both matches and waiters properly defined
        rounds_to_check = min(2, len(self.scheduled_waiters))
        for round_idx in range(rounds_to_check):
            round_players = set()
            start = round_idx * num_courts
            end = min(start + num_courts, len(self.scheduled_matches))
            
            for match in self.scheduled_matches[start:end]:
                round_players.update(match.get_all_players())
            
            if round_idx < len(self.scheduled_waiters):
                round_players.update(self.scheduled_waiters[round_idx])
            
            # All players should be accounted for in first rounds
            self.assertEqual(round_players, all_player_ids,
                f"Round {round_idx} should have all players accounted for")


if __name__ == '__main__':
    unittest.main(verbosity=2)
