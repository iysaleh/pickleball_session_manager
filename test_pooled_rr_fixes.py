"""
Test suite for Pooled Continuous RR fixes:
1. Head-to-head tiebreaker ranking
2. First bye court mixing bug fix
3. Pool persistence
4. Export format (Rank column, Pool Stats columns, "defeated" wording)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
import json
import tempfile
from unittest.mock import patch
from typing import List, Dict

from python.pickleball_types import (
    Session, Player, SessionConfig, PooledContinuousRRConfig, PooledMatch, Match
)
from python.session import create_session
from python.time_manager import initialize_time_manager


class TestHeadToHeadTiebreaker(unittest.TestCase):
    """Test head-to-head tiebreaker for pool standings"""
    
    @classmethod
    def setUpClass(cls):
        initialize_time_manager()
    
    def _create_session_with_pool(self, player_ids: List[str]) -> tuple:
        """Helper to create a session with a single pool"""
        players = [Player(id=pid, name=pid.replace('_', ' ').title()) for pid in player_ids]
        config = PooledContinuousRRConfig()
        config.pools = {"Pool 1": player_ids}
        config.scheduled_pool_matches = []
        
        session_config = SessionConfig(
            mode='pooled-continuous-rr',
            session_type='singles',
            players=players,
            courts=2,
            pooled_continuous_rr_config=config
        )
        session = create_session(session_config)
        return session, config
    
    def _add_completed_match(self, session, config, pool_id, p1, p2, p1_score, p2_score, match_id=None):
        """Helper to add a completed match to session and config"""
        if match_id is None:
            match_id = f"test_{p1}_{p2}"
        
        pool_match = PooledMatch(
            id=match_id,
            team1=[p1],
            team2=[p2],
            status='approved',
            match_number=len(config.scheduled_pool_matches) + 1,
            pool_id=pool_id
        )
        config.scheduled_pool_matches.append(pool_match)
        
        match = Match(
            id=match_id,
            team1=[p1],
            team2=[p2],
            status='completed',
            court_number=1,
            score={'team1_score': p1_score, 'team2_score': p2_score}
        )
        session.matches.append(match)
    
    def test_two_way_tie_head_to_head_winner_ranks_higher(self):
        """When 2 players are tied on wins, head-to-head winner should rank higher"""
        from python.pooled_continuous_rr import calculate_pool_standings
        
        # 3 players: A beats B, B beats C, C beats A
        # A: 1-1, B: 1-1, but we focus on the A vs B tie
        # Actually, let's make a cleaner scenario:
        # 4 players where A and B both have 2 wins, but B beat A head-to-head
        player_ids = ['alice', 'bob', 'charlie', 'dave']
        session, config = self._create_session_with_pool(player_ids)
        
        # alice beats charlie and dave (2 wins)
        self._add_completed_match(session, config, 'Pool 1', 'alice', 'charlie', 11, 5)
        self._add_completed_match(session, config, 'Pool 1', 'alice', 'dave', 11, 3)
        
        # bob beats alice and charlie (2 wins) 
        self._add_completed_match(session, config, 'Pool 1', 'bob', 'alice', 11, 9)
        self._add_completed_match(session, config, 'Pool 1', 'bob', 'charlie', 11, 7)
        
        # alice loses to bob (already added above)
        # bob loses to dave
        self._add_completed_match(session, config, 'Pool 1', 'dave', 'bob', 11, 8)
        
        # charlie beats dave
        self._add_completed_match(session, config, 'Pool 1', 'charlie', 'dave', 11, 6)
        
        standings = calculate_pool_standings(session, 'Pool 1', config)
        
        # alice: 2 wins (beat charlie, dave), 1 loss (to bob)
        # bob: 2 wins (beat alice, charlie), 1 loss (to dave)  
        # Both have 2 wins - tie should be broken by head-to-head
        # bob beat alice, so bob should rank higher
        
        alice_standing = next(s for s in standings if s['player_id'] == 'alice')
        bob_standing = next(s for s in standings if s['player_id'] == 'bob')
        
        self.assertEqual(alice_standing['wins'], 2)
        self.assertEqual(bob_standing['wins'], 2)
        self.assertLess(bob_standing['rank'], alice_standing['rank'], 
                       "Bob should rank higher than Alice since Bob beat Alice head-to-head")
    
    def test_two_way_tie_point_diff_fallback(self):
        """When 2 players tied on wins haven't played each other, fall back to pt diff"""
        from python.pooled_continuous_rr import calculate_pool_standings
        
        player_ids = ['alice', 'bob', 'charlie', 'dave']
        session, config = self._create_session_with_pool(player_ids)
        
        # alice beats charlie with big margin (1 win, pt_diff: +8)
        self._add_completed_match(session, config, 'Pool 1', 'alice', 'charlie', 11, 3)
        
        # bob beats dave with small margin (1 win, pt_diff: +1) 
        self._add_completed_match(session, config, 'Pool 1', 'bob', 'dave', 11, 10)
        
        standings = calculate_pool_standings(session, 'Pool 1', config)
        
        # Both have 1 win, no head-to-head, so pt_diff should break the tie
        alice_standing = next(s for s in standings if s['player_id'] == 'alice')
        bob_standing = next(s for s in standings if s['player_id'] == 'bob')
        
        self.assertEqual(alice_standing['wins'], 1)
        self.assertEqual(bob_standing['wins'], 1)
        # alice has higher pt_diff (+8 vs +1), should rank higher
        self.assertLess(alice_standing['rank'], bob_standing['rank'],
                       "Alice should rank higher with better pt_diff when no head-to-head")
    
    def test_three_way_tie_uses_point_differential(self):
        """For 3+ way ties, point differential should be used (not head-to-head)"""
        from python.pooled_continuous_rr import calculate_pool_standings
        
        player_ids = ['alice', 'bob', 'charlie', 'dave']
        session, config = self._create_session_with_pool(player_ids)
        
        # All three have 1 win each (circular):
        # alice beats bob by 1
        self._add_completed_match(session, config, 'Pool 1', 'alice', 'bob', 11, 10)
        # bob beats charlie by 5
        self._add_completed_match(session, config, 'Pool 1', 'bob', 'charlie', 11, 6)
        # charlie beats alice by 3
        self._add_completed_match(session, config, 'Pool 1', 'charlie', 'alice', 11, 8)
        
        # dave has 0 wins (loses to everyone, just 1 match here)
        self._add_completed_match(session, config, 'Pool 1', 'dave', 'alice', 3, 11, 'extra1')
        self._add_completed_match(session, config, 'Pool 1', 'dave', 'bob', 3, 11, 'extra2')
        self._add_completed_match(session, config, 'Pool 1', 'dave', 'charlie', 3, 11, 'extra3')
        
        standings = calculate_pool_standings(session, 'Pool 1', config)
        
        # alice: 2W-1L (beat bob, beat dave, lost to charlie)
        # bob: 2W-1L (beat charlie, beat dave, lost to alice)
        # charlie: 2W-1L (beat alice, beat dave, lost to bob)
        # dave: 0W-3L
        
        # 3-way tie with alice, bob, charlie all having 2 wins
        # Should use point differential, NOT head-to-head
        alice_s = next(s for s in standings if s['player_id'] == 'alice')
        bob_s = next(s for s in standings if s['player_id'] == 'bob')
        charlie_s = next(s for s in standings if s['player_id'] == 'charlie')
        dave_s = next(s for s in standings if s['player_id'] == 'dave')
        
        # All three should have 2 wins
        self.assertEqual(alice_s['wins'], 2)
        self.assertEqual(bob_s['wins'], 2)
        self.assertEqual(charlie_s['wins'], 2)
        self.assertEqual(dave_s['wins'], 0)
        
        # dave should be last
        self.assertEqual(dave_s['rank'], 4)
        
        # The top 3 should be sorted by pt_diff (descending)
        top3 = sorted([alice_s, bob_s, charlie_s], key=lambda x: x['rank'])
        # Verify pt_diff ordering
        for i in range(len(top3) - 1):
            self.assertGreaterEqual(top3[i]['pt_diff'], top3[i+1]['pt_diff'],
                                   "3-way tie should be broken by point differential")
    
    def test_no_tie(self):
        """When there's no tie, rankings should be by wins only"""
        from python.pooled_continuous_rr import calculate_pool_standings
        
        player_ids = ['alice', 'bob', 'charlie']
        session, config = self._create_session_with_pool(player_ids)
        
        # alice beats everyone (2-0)
        self._add_completed_match(session, config, 'Pool 1', 'alice', 'bob', 11, 5)
        self._add_completed_match(session, config, 'Pool 1', 'alice', 'charlie', 11, 3)
        # bob beats charlie (1-1)
        self._add_completed_match(session, config, 'Pool 1', 'bob', 'charlie', 11, 7)
        
        standings = calculate_pool_standings(session, 'Pool 1', config)
        
        alice_s = next(s for s in standings if s['player_id'] == 'alice')
        bob_s = next(s for s in standings if s['player_id'] == 'bob')
        charlie_s = next(s for s in standings if s['player_id'] == 'charlie')
        
        self.assertEqual(alice_s['rank'], 1)
        self.assertEqual(bob_s['rank'], 2)
        self.assertEqual(charlie_s['rank'], 3)


class TestFirstByeCourtAssignment(unittest.TestCase):
    """Test that first bye players don't cause pool-court mixing"""
    
    @classmethod
    def setUpClass(cls):
        initialize_time_manager()
    
    def test_first_bye_respects_court_assignments(self):
        """First bye players should NOT cause matches from wrong pool on restricted courts"""
        from python.pooled_continuous_rr import (
            initialize_pools, generate_all_pool_schedules, get_next_match_for_court
        )
        
        # Create 8 players, 2 pools, 2 courts
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(8)]
        config = PooledContinuousRRConfig()
        
        session_config = SessionConfig(
            mode='pooled-continuous-rr',
            session_type='singles',
            players=players,
            courts=2,
            first_bye_players=['p0', 'p1'],  # First bye in pool 1
            pooled_continuous_rr_config=config
        )
        session = create_session(session_config)
        
        # Manually assign pools
        config.pools = {
            'Pool 1': ['p0', 'p1', 'p2', 'p3'],
            'Pool 2': ['p4', 'p5', 'p6', 'p7']
        }
        
        # Restrict courts: Pool 1 on Court 1, Pool 2 on Court 2
        config.pool_court_assignments = {
            'Pool 1': [1],
            'Pool 2': [2]
        }
        
        config.scheduled_pool_matches = generate_all_pool_schedules(session, config)
        config.pool_completed = {'Pool 1': False, 'Pool 2': False}
        config.pools_finalized = True
        
        # Get match for Court 1 - should ONLY be Pool 1 match
        match = get_next_match_for_court(session, 1, config)
        if match:
            # Verify the match is from Pool 1, not Pool 2
            pool1_players = set(config.pools['Pool 1'])
            match_players = set(match.get_all_players())
            self.assertTrue(match_players.issubset(pool1_players),
                           f"Court 1 got match with players {match_players} but should only have Pool 1 players {pool1_players}")
        
        # Get match for Court 2 - should ONLY be Pool 2 match
        match2 = get_next_match_for_court(session, 2, config)
        if match2:
            pool2_players = set(config.pools['Pool 2'])
            match2_players = set(match2.get_all_players())
            self.assertTrue(match2_players.issubset(pool2_players),
                           f"Court 2 got match with players {match2_players} but should only have Pool 2 players {pool2_players}")
    
    def test_first_bye_no_court_restrictions_can_cross(self):
        """Without court restrictions, first bye override can still work"""
        from python.pooled_continuous_rr import (
            initialize_pools, generate_all_pool_schedules, get_next_match_for_court
        )
        
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(8)]
        config = PooledContinuousRRConfig()
        
        session_config = SessionConfig(
            mode='pooled-continuous-rr',
            session_type='singles',
            players=players,
            courts=2,
            first_bye_players=['p0', 'p1', 'p2', 'p3'],  # ALL Pool 1 players are first bye
            pooled_continuous_rr_config=config
        )
        session = create_session(session_config)
        
        config.pools = {
            'Pool 1': ['p0', 'p1', 'p2', 'p3'],
            'Pool 2': ['p4', 'p5', 'p6', 'p7']
        }
        # NO court restrictions
        config.pool_court_assignments = {}
        config.scheduled_pool_matches = generate_all_pool_schedules(session, config)
        config.pool_completed = {'Pool 1': False, 'Pool 2': False}
        config.pools_finalized = True
        
        # Without restrictions, Court 1 should be able to get any pool's match
        match = get_next_match_for_court(session, 1, config)
        self.assertIsNotNone(match, "Should find a match even with first bye players")


class TestPoolPersistence(unittest.TestCase):
    """Test that pool assignments persist between dialog opens and sessions"""
    
    @classmethod
    def setUpClass(cls):
        initialize_time_manager()
    
    def test_save_and_load_pool_assignments(self):
        """Pool assignments should be saved and loaded from player history"""
        from python.session_persistence import save_player_history, load_player_history_with_ratings
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            import python.session_persistence as sp
            original_file = sp.PLAYER_HISTORY_FILE
            from pathlib import Path
            sp.PLAYER_HISTORY_FILE = Path(temp_path)
            
            # Save with pool assignments
            pool_assignments = {
                'Pool 1': ['Alice', 'Bob', 'Charlie'],
                'Pool 2': ['Dave', 'Eve', 'Frank']
            }
            pool_court_assignments = {
                'Pool 1': [1, 2],
                'Pool 2': [3, 4]
            }
            
            save_player_history(
                ['Alice', 'Bob', 'Charlie', 'Dave', 'Eve', 'Frank'],
                game_mode='pooled-continuous-rr',
                session_type='singles',
                pool_assignments=pool_assignments,
                pool_court_assignments=pool_court_assignments
            )
            
            # Load and verify
            data = load_player_history_with_ratings()
            
            self.assertEqual(data['pool_assignments'], pool_assignments)
            self.assertEqual(data['pool_court_assignments'], pool_court_assignments)
            self.assertEqual(data['game_mode'], 'pooled-continuous-rr')
        finally:
            sp.PLAYER_HISTORY_FILE = original_file
            os.unlink(temp_path)
    
    def test_load_without_pool_assignments(self):
        """Loading history without pool assignments should return None"""
        from python.session_persistence import save_player_history, load_player_history_with_ratings
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            import python.session_persistence as sp
            original_file = sp.PLAYER_HISTORY_FILE
            from pathlib import Path
            sp.PLAYER_HISTORY_FILE = Path(temp_path)
            
            save_player_history(['Alice', 'Bob'], game_mode='competitive-variety')
            
            data = load_player_history_with_ratings()
            self.assertIsNone(data['pool_assignments'])
            self.assertIsNone(data['pool_court_assignments'])
        finally:
            sp.PLAYER_HISTORY_FILE = original_file
            os.unlink(temp_path)


class TestExportFormat(unittest.TestCase):
    """Test export format changes"""
    
    @classmethod
    def setUpClass(cls):
        initialize_time_manager()
    
    def test_head_to_head_data_tracked(self):
        """Verify head_to_head dict is populated correctly in standings"""
        from python.pooled_continuous_rr import calculate_pool_standings
        
        player_ids = ['alice', 'bob']
        players = [Player(id=pid, name=pid.title()) for pid in player_ids]
        config = PooledContinuousRRConfig()
        config.pools = {"Pool 1": player_ids}
        config.scheduled_pool_matches = []
        
        session_config = SessionConfig(
            mode='pooled-continuous-rr',
            session_type='singles',
            players=players,
            courts=1,
            pooled_continuous_rr_config=config
        )
        session = create_session(session_config)
        
        # alice beats bob
        pm = PooledMatch(id='m1', team1=['alice'], team2=['bob'], status='approved', 
                        match_number=1, pool_id='Pool 1')
        config.scheduled_pool_matches.append(pm)
        
        m = Match(id='m1', team1=['alice'], team2=['bob'], status='completed',
                 court_number=1, score={'team1_score': 11, 'team2_score': 5})
        session.matches.append(m)
        
        standings = calculate_pool_standings(session, 'Pool 1', config)
        
        alice_s = next(s for s in standings if s['player_id'] == 'alice')
        bob_s = next(s for s in standings if s['player_id'] == 'bob')
        
        self.assertEqual(alice_s['head_to_head']['bob'], 'W')
        self.assertEqual(bob_s['head_to_head']['alice'], 'L')
        self.assertEqual(alice_s['pts_for'], 11)
        self.assertEqual(alice_s['pts_against'], 5)
        self.assertEqual(bob_s['pts_for'], 5)
        self.assertEqual(bob_s['pts_against'], 11)


if __name__ == '__main__':
    unittest.main()
