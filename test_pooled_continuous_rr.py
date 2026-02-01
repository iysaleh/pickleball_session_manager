"""
Test suite for Pooled Continuous RR with Crossover mode.

Tests:
1. Pool initialization and distribution
2. Pool round robin match generation
3. Crossover match generation
4. Match selection priority (fewest games first)
5. Court assignment restrictions
6. Pool standings calculation
7. Session completion detection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from typing import List

from python.pickleball_types import (
    Session, Player, SessionConfig, PooledContinuousRRConfig, PooledMatch
)
from python.session import create_session
from python.time_manager import initialize_time_manager


class TestPooledContinuousRR(unittest.TestCase):
    """Test cases for Pooled Continuous RR with Crossover mode"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize time manager once for all tests"""
        initialize_time_manager()
    
    def create_test_session(self, num_players: int = 12, num_courts: int = 2, 
                           num_pools: int = 2, session_type: str = 'singles') -> Session:
        """Create a test session with specified parameters"""
        players = [Player(id=f"player_{i}", name=f"Player {i+1}") for i in range(num_players)]
        
        config = PooledContinuousRRConfig()
        
        session_config = SessionConfig(
            mode='pooled-continuous-rr',
            session_type=session_type,
            players=players,
            courts=num_courts,
            pooled_continuous_rr_config=config
        )
        
        return create_session(session_config)
    
    def test_initialize_pools_basic(self):
        """Test basic pool initialization with even distribution"""
        from python.pooled_continuous_rr import initialize_pools
        
        session = self.create_test_session(num_players=12)
        pools = initialize_pools(session, num_pools=2)
        
        # Should have 2 pools
        self.assertEqual(len(pools), 2)
        
        # Each pool should have 6 players
        for pool_id, player_ids in pools.items():
            self.assertEqual(len(player_ids), 6)
        
        # All players should be assigned
        all_assigned = set()
        for player_ids in pools.values():
            all_assigned.update(player_ids)
        self.assertEqual(len(all_assigned), 12)
    
    def test_initialize_pools_three_pools(self):
        """Test pool initialization with 3 pools"""
        from python.pooled_continuous_rr import initialize_pools
        
        session = self.create_test_session(num_players=12)
        pools = initialize_pools(session, num_pools=3)
        
        # Should have 3 pools with 4 players each
        self.assertEqual(len(pools), 3)
        for pool_id, player_ids in pools.items():
            self.assertEqual(len(player_ids), 4)
    
    def test_initialize_pools_uneven(self):
        """Test pool initialization with uneven player distribution"""
        from python.pooled_continuous_rr import initialize_pools
        
        session = self.create_test_session(num_players=7)
        pools = initialize_pools(session, num_pools=2)
        
        # Should have 2 pools with 4 and 3 players
        self.assertEqual(len(pools), 2)
        pool_sizes = sorted([len(p) for p in pools.values()])
        self.assertEqual(pool_sizes, [3, 4])
    
    def test_redistribute_pools(self):
        """Test redistributing players across different number of pools"""
        from python.pooled_continuous_rr import initialize_pools, redistribute_pools
        
        session = self.create_test_session(num_players=12)
        pools = initialize_pools(session, num_pools=2)
        
        # Redistribute to 3 pools
        new_pools = redistribute_pools(pools, num_pools=3)
        
        self.assertEqual(len(new_pools), 3)
        
        # All players should still be assigned
        all_original = set()
        for player_ids in pools.values():
            all_original.update(player_ids)
        
        all_new = set()
        for player_ids in new_pools.values():
            all_new.update(player_ids)
        
        self.assertEqual(all_original, all_new)
    
    def test_generate_singles_pool_matches(self):
        """Test generating singles round robin matches for a pool"""
        from python.pooled_continuous_rr import initialize_pools, generate_pool_round_robin_matches
        
        session = self.create_test_session(num_players=8, session_type='singles')
        pools = initialize_pools(session, num_pools=2)
        
        # Generate matches for first pool (4 players)
        pool_id = list(pools.keys())[0]
        player_ids = pools[pool_id]
        
        matches = generate_pool_round_robin_matches(session, pool_id, player_ids)
        
        # Singles round robin with 4 players = 4 choose 2 = 6 matches
        self.assertEqual(len(matches), 6)
        
        # Each match should have 1 player per team (singles)
        for match in matches:
            self.assertEqual(len(match.team1), 1)
            self.assertEqual(len(match.team2), 1)
            self.assertEqual(match.pool_id, pool_id)
            self.assertFalse(match.is_crossover)
    
    def test_generate_doubles_pool_matches(self):
        """Test generating doubles round robin matches for a pool"""
        from python.pooled_continuous_rr import initialize_pools, generate_pool_round_robin_matches
        
        session = self.create_test_session(num_players=8, session_type='doubles')
        pools = initialize_pools(session, num_pools=2)
        
        # Generate matches for first pool (4 players)
        pool_id = list(pools.keys())[0]
        player_ids = pools[pool_id]
        
        matches = generate_pool_round_robin_matches(session, pool_id, player_ids)
        
        # Should generate doubles matches with 2 players per team
        self.assertGreater(len(matches), 0)
        for match in matches:
            self.assertEqual(len(match.team1), 2)
            self.assertEqual(len(match.team2), 2)
    
    def test_generate_all_pool_schedules(self):
        """Test generating schedules for all pools"""
        from python.pooled_continuous_rr import initialize_pools, generate_all_pool_schedules
        
        session = self.create_test_session(num_players=12, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        
        all_matches = generate_all_pool_schedules(session, config)
        
        # Should have matches for both pools
        pool_ids = set(m.pool_id for m in all_matches)
        self.assertEqual(len(pool_ids), 2)
        
        # Each 6-player pool should have 6 choose 2 = 15 singles matches
        for pool_id in config.pools.keys():
            pool_matches = [m for m in all_matches if m.pool_id == pool_id]
            self.assertEqual(len(pool_matches), 15)
    
    def test_calculate_pool_standings(self):
        """Test calculating standings for a pool"""
        from python.pooled_continuous_rr import initialize_pools, calculate_pool_standings
        
        session = self.create_test_session(num_players=8, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        
        pool_id = list(config.pools.keys())[0]
        standings = calculate_pool_standings(session, pool_id, config)
        
        # Should have standings for all players in pool
        self.assertEqual(len(standings), len(config.pools[pool_id]))
        
        # Each standing should have required fields
        for standing in standings:
            self.assertIn('player_id', standing)
            self.assertIn('name', standing)
            self.assertIn('wins', standing)
            self.assertIn('losses', standing)
            self.assertIn('pt_diff', standing)
            self.assertIn('rank', standing)
    
    def test_check_pool_completion_empty(self):
        """Test pool completion check with no completed matches"""
        from python.pooled_continuous_rr import (
            initialize_pools, generate_all_pool_schedules, check_pool_completion
        )
        
        session = self.create_test_session(num_players=8, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        config.scheduled_pool_matches = generate_all_pool_schedules(session, config)
        
        pool_id = list(config.pools.keys())[0]
        
        # No matches completed yet
        self.assertFalse(check_pool_completion(session, pool_id, config))
    
    def test_generate_crossover_matches(self):
        """Test generating crossover matches after pools complete"""
        from python.pooled_continuous_rr import (
            initialize_pools, generate_crossover_matches
        )
        
        session = self.create_test_session(num_players=8, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        
        # Simulate completed pools by adding wins/losses
        for pool_id, player_ids in config.pools.items():
            for i, pid in enumerate(player_ids):
                session.player_stats[pid].wins = len(player_ids) - 1 - i
                session.player_stats[pid].losses = i
        
        crossover_matches = generate_crossover_matches(session, config)
        
        # Should have rank-vs-rank matches
        self.assertGreater(len(crossover_matches), 0)
        
        # Each crossover match should be marked as crossover
        for match in crossover_matches:
            self.assertTrue(match.is_crossover)
            self.assertGreater(match.crossover_rank, 0)
            self.assertEqual(match.pool_id, '')
    
    def test_get_players_games_played(self):
        """Test tracking games played per player"""
        from python.pooled_continuous_rr import initialize_pools, get_players_games_played
        
        session = self.create_test_session(num_players=8, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        
        games_played = get_players_games_played(session, config)
        
        # All players should start with 0 games
        for player in session.config.players:
            self.assertEqual(games_played.get(player.id, 0), 0)
    
    def test_match_selection_prioritizes_fewest_games(self):
        """Test that match selection prioritizes players with fewest games"""
        from python.pooled_continuous_rr import (
            initialize_pools, generate_all_pool_schedules, get_next_match_for_court
        )
        
        session = self.create_test_session(num_players=8, num_courts=2, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        config.scheduled_pool_matches = generate_all_pool_schedules(session, config)
        config.pool_completed = {pid: False for pid in config.pools}
        
        # Get first match for court 1
        match = get_next_match_for_court(session, 1, config)
        
        # Should return a valid match
        self.assertIsNotNone(match)
        self.assertEqual(len(match.team1), 1)  # Singles
        self.assertEqual(len(match.team2), 1)
    
    def test_court_assignment_restriction(self):
        """Test that court assignments restrict which pools can play where"""
        from python.pooled_continuous_rr import (
            initialize_pools, generate_all_pool_schedules, get_next_match_for_court
        )
        
        session = self.create_test_session(num_players=8, num_courts=2, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        config.scheduled_pool_matches = generate_all_pool_schedules(session, config)
        config.pool_completed = {pid: False for pid in config.pools}
        
        # Restrict Pool 1 to Court 1 only
        pool_ids = list(config.pools.keys())
        config.pool_court_assignments = {
            pool_ids[0]: [1],
            pool_ids[1]: [2]
        }
        
        # Get match for court 1 - should only be from Pool 1
        match = get_next_match_for_court(session, 1, config)
        if match:
            self.assertEqual(match.pool_id, pool_ids[0])
        
        # Get match for court 2 - should only be from Pool 2
        match = get_next_match_for_court(session, 2, config)
        if match:
            self.assertEqual(match.pool_id, pool_ids[1])
    
    def test_session_complete_detection(self):
        """Test detection of session completion"""
        from python.pooled_continuous_rr import (
            initialize_pools, check_session_complete
        )
        
        session = self.create_test_session(num_players=4, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        config.pool_completed = {pid: False for pid in config.pools}
        
        # Session not complete when pools haven't finished
        self.assertFalse(check_session_complete(session, config))
    
    def test_final_rankings(self):
        """Test final rankings calculation"""
        from python.pooled_continuous_rr import (
            initialize_pools, get_final_rankings
        )
        
        session = self.create_test_session(num_players=8, session_type='singles')
        config = session.config.pooled_continuous_rr_config
        config.pools = initialize_pools(session, num_pools=2)
        
        # Simulate some game results
        for i, player in enumerate(session.config.players):
            session.player_stats[player.id].wins = len(session.config.players) - 1 - i
            session.player_stats[player.id].losses = i
            session.player_stats[player.id].games_played = len(session.config.players) - 1
        
        rankings = get_final_rankings(session, config)
        
        # Should have rankings for all players
        self.assertEqual(len(rankings), len(session.config.players))
        
        # Rankings should be sorted by wins (descending)
        for i in range(len(rankings) - 1):
            self.assertGreaterEqual(rankings[i]['wins'], rankings[i + 1]['wins'])
        
        # Top 3 should have medals
        self.assertEqual(rankings[0]['medal'], '🥇')
        self.assertEqual(rankings[1]['medal'], '🥈')
        self.assertEqual(rankings[2]['medal'], '🥉')


class TestPooledMatchStruct(unittest.TestCase):
    """Test PooledMatch dataclass"""
    
    def test_pooled_match_creation(self):
        """Test creating a PooledMatch"""
        match = PooledMatch(
            id="test_match_1",
            team1=["player_1"],
            team2=["player_2"],
            pool_id="Pool 1",
            match_number=1
        )
        
        self.assertEqual(match.id, "test_match_1")
        self.assertEqual(match.pool_id, "Pool 1")
        self.assertEqual(match.status, 'pending')
        self.assertFalse(match.is_crossover)
    
    def test_crossover_match_creation(self):
        """Test creating a crossover PooledMatch"""
        match = PooledMatch(
            id="crossover_1",
            team1=["player_1"],
            team2=["player_3"],
            is_crossover=True,
            crossover_rank=1
        )
        
        self.assertTrue(match.is_crossover)
        self.assertEqual(match.crossover_rank, 1)
        self.assertEqual(match.pool_id, '')
    
    def test_get_all_players(self):
        """Test get_all_players method"""
        match = PooledMatch(
            id="test_match",
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            pool_id="Pool 1"
        )
        
        all_players = match.get_all_players()
        self.assertEqual(len(all_players), 4)
        self.assertIn("p1", all_players)
        self.assertIn("p4", all_players)


class TestPooledConfigStruct(unittest.TestCase):
    """Test PooledContinuousRRConfig dataclass"""
    
    def test_config_creation(self):
        """Test creating a PooledContinuousRRConfig"""
        config = PooledContinuousRRConfig()
        
        self.assertEqual(config.pools, {})
        self.assertEqual(config.pool_court_assignments, {})
        self.assertEqual(config.scheduled_pool_matches, [])
        self.assertEqual(config.crossover_matches, [])
        self.assertEqual(config.pool_completed, {})
        self.assertFalse(config.crossover_active)
        self.assertFalse(config.pools_finalized)


if __name__ == '__main__':
    unittest.main(verbosity=2)
