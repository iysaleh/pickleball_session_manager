#!/usr/bin/env python3
"""
Unit tests for Pickleball Session Manager - Round Robin Mode
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from datetime import datetime
from python.types import (
    Player, Session, SessionConfig, GameMode, SessionType,
    Match, MatchStatus, PlayerStats, QueuedMatch
)
from python.session import (
    create_session, add_player_to_session, remove_player_from_session,
    complete_match, forfeit_match, get_player_name, get_active_matches,
    get_completed_matches
)
from python.roundrobin import generate_round_robin_queue


class TestRoundRobinBasics(unittest.TestCase):
    """Test basic Round Robin functionality"""
    
    def setUp(self):
        """Create test players"""
        self.players = [
            Player(id="p1", name="Alice"),
            Player(id="p2", name="Bob"),
            Player(id="p3", name="Charlie"),
            Player(id="p4", name="Diana"),
        ]
    
    def test_round_robin_queue_generation_doubles(self):
        """Test generating round-robin queue for doubles"""
        queue = generate_round_robin_queue(
            self.players,
            session_type='doubles',
            banned_pairs=[],
            max_matches=10
        )
        
        self.assertGreater(len(queue), 0)
        
        # Check that each match has 2v2
        for match in queue:
            self.assertEqual(len(match.team1), 2)
            self.assertEqual(len(match.team2), 2)
    
    def test_round_robin_queue_generation_singles(self):
        """Test generating round-robin queue for singles"""
        queue = generate_round_robin_queue(
            self.players,
            session_type='singles',
            banned_pairs=[],
            max_matches=10
        )
        
        self.assertGreater(len(queue), 0)
        
        # Check that each match has 1v1
        for match in queue:
            self.assertEqual(len(match.team1), 1)
            self.assertEqual(len(match.team2), 1)
    
    def test_banned_pairs(self):
        """Test that banned pairs are not created"""
        banned = [("p1", "p2")]  # Alice and Bob can't play together
        
        queue = generate_round_robin_queue(
            self.players,
            session_type='doubles',
            banned_pairs=banned,
            max_matches=50
        )
        
        # Check no matches have banned pair together
        for match in queue:
            # Check team1 doesn't have the banned pair
            if "p1" in match.team1 and "p2" in match.team1:
                self.fail("Banned pair found in team1")
            if "p1" in match.team2 and "p2" in match.team2:
                self.fail("Banned pair found in team2")


class TestSessionManagement(unittest.TestCase):
    """Test session creation and management"""
    
    def setUp(self):
        """Create test data"""
        self.players = [
            Player(id=f"p{i}", name=f"Player{i}")
            for i in range(1, 9)
        ]
    
    def test_create_session(self):
        """Test creating a session"""
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=self.players,
            courts=2,
            banned_pairs=[]
        )
        
        session = create_session(config)
        
        self.assertIsNotNone(session.id)
        self.assertEqual(len(session.config.players), 8)
        self.assertEqual(session.config.courts, 2)
        self.assertGreater(len(session.match_queue), 0)
    
    def test_add_player_to_session(self):
        """Test adding a player to active session"""
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=self.players[:4],
            courts=1,
            banned_pairs=[]
        )
        
        session = create_session(config)
        initial_player_count = len(session.config.players)
        
        new_player = Player(id="pnew", name="NewPlayer")
        session = add_player_to_session(session, new_player)
        
        self.assertEqual(len(session.config.players), initial_player_count + 1)
        self.assertIn("pnew", session.active_players)
    
    def test_complete_match(self):
        """Test completing a match with scores"""
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=self.players[:4],
            courts=1,
            banned_pairs=[]
        )
        
        session = create_session(config)
        
        # Create a test match
        match = Match(
            id="test_match",
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status='in-progress'
        )
        session.matches.append(match)
        
        # Complete the match
        result = complete_match(session, "test_match", 21, 15)
        
        self.assertTrue(result)
        self.assertEqual(match.status, 'completed')
        self.assertEqual(match.score['team1_score'], 21)
        self.assertEqual(match.score['team2_score'], 15)
        
        # Check stats updated
        team1_player_stats = session.player_stats.get("p1")
        self.assertIsNotNone(team1_player_stats)
        self.assertEqual(team1_player_stats.wins, 1)
        self.assertEqual(team1_player_stats.games_played, 1)
    
    def test_forfeit_match(self):
        """Test forfeiting a match"""
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=self.players[:4],
            courts=1,
            banned_pairs=[]
        )
        
        session = create_session(config)
        
        # Create a test match
        match = Match(
            id="test_match",
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status='in-progress'
        )
        session.matches.append(match)
        
        # Forfeit the match
        result = forfeit_match(session, "test_match")
        
        self.assertTrue(result)
        self.assertEqual(match.status, 'forfeited')
        
        # Check stats: partners and opponents recorded but no win/loss
        team1_stats = session.player_stats.get("p1")
        self.assertIn("p2", team1_stats.partners_played)
        self.assertIn("p3", team1_stats.opponents_played)
        self.assertEqual(team1_stats.wins, 0)
        self.assertEqual(team1_stats.losses, 0)


class TestPlayerStats(unittest.TestCase):
    """Test player statistics tracking"""
    
    def test_stats_tracking_through_wins(self):
        """Test that stats are correctly tracked through wins"""
        players = [
            Player(id="p1", name="Alice"),
            Player(id="p2", name="Bob"),
            Player(id="p3", name="Charlie"),
            Player(id="p4", name="Diana"),
        ]
        
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=players,
            courts=1,
            banned_pairs=[]
        )
        
        session = create_session(config)
        
        # Play multiple matches
        match1 = Match(
            id="m1",
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status='in-progress'
        )
        session.matches.append(match1)
        complete_match(session, "m1", 21, 19)
        
        match2 = Match(
            id="m2",
            court_number=1,
            team1=["p1", "p3"],
            team2=["p2", "p4"],
            status='in-progress'
        )
        session.matches.append(match2)
        complete_match(session, "m2", 20, 21)
        
        # Check stats
        p1_stats = session.player_stats["p1"]
        self.assertEqual(p1_stats.games_played, 2)
        self.assertEqual(p1_stats.wins, 1)
        self.assertEqual(p1_stats.losses, 1)
        self.assertEqual(p1_stats.total_points_for, 41)
        self.assertEqual(p1_stats.total_points_against, 40)
        
        # Check partnerships
        self.assertIn("p2", p1_stats.partners_played)
        self.assertIn("p3", p1_stats.partners_played)
        
        # Check opponents
        self.assertIn("p3", p1_stats.opponents_played)
        self.assertIn("p4", p1_stats.opponents_played)


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
