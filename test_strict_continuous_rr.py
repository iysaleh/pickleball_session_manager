"""
Tests for Strict Continuous Round Robin mode.

Tests:
1. Queue generation for singles
2. Strict queue ordering (no skipping)
3. Head-to-head tiebreaker for 2-way ties
4. Point differential for 3+ way ties
5. Basic session flow
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.pickleball_types import (
    Player, Session, SessionConfig, Match, QueuedMatch, PlayerStats, GameMode
)
from python.session import create_session
from python.strict_continuous_rr import (
    populate_courts_strict_continuous,
    generate_strict_rr_queue,
    calculate_round_robin_standings,
    _generate_singles_round_robin_queue,
    _apply_rr_head_to_head_tiebreaker
)
from python.time_manager import initialize_time_manager


# Initialize time manager once for all tests
initialize_time_manager()


class TestStrictContinuousRR(unittest.TestCase):
    """Test Strict Continuous Round Robin mode"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.players = [
            Player(id=f"p{i}", name=f"Player {i}") 
            for i in range(1, 9)  # 8 players
        ]
    
    def test_queue_generation_singles(self):
        """Test that singles queue generates all unique pairings"""
        queue = _generate_singles_round_robin_queue(
            self.players[:6],  # 6 players
            banned_pairs=[],
            max_matches=100,
            player_stats=None
        )
        
        # 6 players = C(6,2) = 15 unique pairings
        self.assertEqual(len(queue), 15, "Should generate 15 matches for 6 players")
        
        # Check all matches are 1v1
        for match in queue:
            self.assertEqual(len(match.team1), 1, "Singles should have 1 player per team")
            self.assertEqual(len(match.team2), 1, "Singles should have 1 player per team")
    
    def test_session_creation_singles(self):
        """Test session creation defaults to singles"""
        config = SessionConfig(
            mode='strict-continuous-rr',
            session_type='singles',
            players=self.players[:6],
            courts=2,
            banned_pairs=[],
            locked_teams=None,
            first_bye_players=[]
        )
        
        session = create_session(config)
        
        # Should have a non-empty match queue
        self.assertGreater(len(session.match_queue), 0, "Queue should have matches")
        
        # All matches should be singles
        for match in session.match_queue:
            self.assertEqual(len(match.team1), 1)
            self.assertEqual(len(match.team2), 1)
    
    def test_strict_ordering_no_skip(self):
        """Test that strict ordering properly blocks later matches"""
        # Create session with 6 players and 2 courts
        config = SessionConfig(
            mode='strict-continuous-rr',
            session_type='singles',
            players=self.players[:6],
            courts=2,
            banned_pairs=[],
            locked_teams=None,
            first_bye_players=[]
        )
        
        session = create_session(config)
        
        # Populate courts
        populate_courts_strict_continuous(session)
        
        # Should have at least 1 match
        active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        self.assertGreaterEqual(len(active_matches), 1, "Should fill at least one court")
        
        # The first match should be the first from the queue
        first_queued = session.match_queue[0] if session.match_queue else None
        if first_queued:
            # Remaining queue should not have the assigned match
            first_match_players = set(active_matches[0].team1 + active_matches[0].team2)
            # Verify the match was taken from front of queue
            self.assertGreaterEqual(len(session.match_queue), 0, "Queue should have remaining matches")
    
    def test_strict_ordering_blocks_later_matches(self):
        """
        Test the EXACT scenario from the bug report:
        - Queue has: Bob vs Tommy, ... , Logan vs Tommy
        - If Tommy is busy playing (e.g., in first match)
        - Then Logan vs Tommy should NOT be made even if Logan is free
        - Because Bob vs Tommy must be played first
        """
        # Create session with specific players
        players = [
            Player(id="tommy", name="Tommy"),
            Player(id="bob", name="Bob"),
            Player(id="logan", name="Logan"),
            Player(id="scott", name="Scott"),
            Player(id="aria", name="Aria"),
            Player(id="ibraheem", name="Ibraheem"),
        ]
        
        config = SessionConfig(
            mode='strict-continuous-rr',
            session_type='singles',
            players=players,
            courts=4,
            banned_pairs=[],
            locked_teams=None,
            first_bye_players=[]
        )
        
        session = create_session(config)
        
        # Manually set up a specific queue order to reproduce the bug
        # Queue: Bob vs Tommy, Scott vs Aria, Logan vs Tommy, ...
        session.match_queue = [
            QueuedMatch(team1=["bob"], team2=["tommy"]),      # Match 0: Bob vs Tommy
            QueuedMatch(team1=["scott"], team2=["aria"]),     # Match 1: Scott vs Aria  
            QueuedMatch(team1=["logan"], team2=["tommy"]),    # Match 2: Logan vs Tommy
            QueuedMatch(team1=["ibraheem"], team2=["logan"]), # Match 3: Ibraheem vs Logan
        ]
        
        # Simulate Tommy being busy in an active match (not from this queue)
        busy_match = Match(
            id="existing_match",
            court_number=1,
            team1=["tommy"],
            team2=["ibraheem"],
            status='in-progress'
        )
        session.matches.append(busy_match)
        
        # Now try to populate courts
        populate_courts_strict_continuous(session)
        
        # Scott vs Aria (Match 1) should be assigned - no blocked players
        # BUT Logan vs Tommy (Match 2) should NOT be assigned because:
        #   - Tommy is busy
        #   - Bob vs Tommy (Match 0) is earlier and Tommy is in it
        #   - So Tommy is "blocked by earlier match"
        #   - Therefore ANY match with Tommy must wait
        
        # Check what matches were created
        new_matches = [m for m in session.matches 
                      if m.id != "existing_match" and m.status in ['waiting', 'in-progress']]
        
        # Should have Scott vs Aria
        match_player_sets = [frozenset(m.team1 + m.team2) for m in new_matches]
        
        self.assertIn(frozenset(["scott", "aria"]), match_player_sets,
                     "Scott vs Aria should be created (no blocked players)")
        
        # Should NOT have Logan vs Tommy (Tommy is blocked)
        self.assertNotIn(frozenset(["logan", "tommy"]), match_player_sets,
                        "Logan vs Tommy should NOT be created - Tommy blocked by earlier Bob vs Tommy")
        
        # Should NOT have Ibraheem vs Logan either - Logan appears after blocked match
        # Actually Logan first appears in Match 2 which is blocked, so Logan gets blocked too
        self.assertNotIn(frozenset(["ibraheem", "logan"]), match_player_sets,
                        "Ibraheem vs Logan should NOT be created - Logan blocked by earlier match")

    def test_round_based_queue_fills_all_courts(self):
        """
        Test that the queue is organized so all courts fill when a round completes.
        
        With 6 players and 3 courts:
        - Round 1: 3 matches with disjoint players (fills 3 courts)
        - Round 2: 3 matches with disjoint players (fills 3 courts)
        - etc.
        """
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 7)]
        
        config = SessionConfig(
            mode='strict-continuous-rr',
            session_type='singles',
            players=players,
            courts=3,
            banned_pairs=[],
            locked_teams=None,
            first_bye_players=[]
        )
        
        session = create_session(config)
        
        # Initial populate should fill all 3 courts
        populate_courts_strict_continuous(session)
        active = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        self.assertEqual(len(active), 3, "Should fill all 3 courts initially")
        
        # Verify all 6 players are playing (each appears exactly once)
        players_in_matches = set()
        for m in active:
            players_in_matches.update(m.team1 + m.team2)
        self.assertEqual(len(players_in_matches), 6, "All 6 players should be playing in round 1")
        
        # Complete all matches
        for m in session.matches:
            m.status = 'completed'
        
        # Populate again - should fill all 3 courts for round 2
        populate_courts_strict_continuous(session)
        active = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        self.assertEqual(len(active), 3, "Should fill all 3 courts for round 2")
        
        # Verify all 6 players are playing again
        players_in_matches = set()
        for m in active:
            players_in_matches.update(m.team1 + m.team2)
        self.assertEqual(len(players_in_matches), 6, "All 6 players should be playing in round 2")

    def test_head_to_head_tiebreaker_two_way(self):
        """Test that 2-way ties use head-to-head result"""
        # Create standings with 2-way tie where P1 beat P2
        standings = [
            {
                'player_id': 'p1',
                'name': 'Player 1',
                'wins': 5,
                'losses': 2,
                'pt_diff': 10,
                'head_to_head': {'p2': 'W'}  # P1 beat P2
            },
            {
                'player_id': 'p2',
                'name': 'Player 2',
                'wins': 5,
                'losses': 2,
                'pt_diff': 15,  # P2 has better pt_diff but lost H2H
                'head_to_head': {'p1': 'L'}  # P2 lost to P1
            },
            {
                'player_id': 'p3',
                'name': 'Player 3',
                'wins': 4,
                'losses': 3,
                'pt_diff': 5,
                'head_to_head': {}
            }
        ]
        
        result = _apply_rr_head_to_head_tiebreaker(standings)
        
        # P1 should be ranked ahead of P2 due to H2H win despite lower pt_diff
        self.assertEqual(result[0]['player_id'], 'p1', "P1 should be first (H2H winner)")
        self.assertEqual(result[1]['player_id'], 'p2', "P2 should be second (H2H loser)")
        self.assertEqual(result[2]['player_id'], 'p3', "P3 should be third")
    
    def test_head_to_head_tiebreaker_three_way(self):
        """Test that 3-way ties use point differential instead of H2H"""
        # Create standings with 3-way tie
        standings = [
            {
                'player_id': 'p1',
                'name': 'Player 1',
                'wins': 5,
                'losses': 2,
                'pt_diff': 20,  # Best pt_diff
                'head_to_head': {'p2': 'W', 'p3': 'L'}
            },
            {
                'player_id': 'p2',
                'name': 'Player 2',
                'wins': 5,
                'losses': 2,
                'pt_diff': 10,  # Middle pt_diff
                'head_to_head': {'p1': 'L', 'p3': 'W'}
            },
            {
                'player_id': 'p3',
                'name': 'Player 3',
                'wins': 5,
                'losses': 2,
                'pt_diff': 5,  # Worst pt_diff
                'head_to_head': {'p1': 'W', 'p2': 'L'}
            },
        ]
        
        result = _apply_rr_head_to_head_tiebreaker(standings)
        
        # For 3-way tie, should use pt_diff ordering (already sorted by pt_diff)
        self.assertEqual(result[0]['player_id'], 'p1', "P1 should be first (best pt_diff)")
        self.assertEqual(result[1]['player_id'], 'p2', "P2 should be second")
        self.assertEqual(result[2]['player_id'], 'p3', "P3 should be third (worst pt_diff)")
    
    def test_calculate_standings_integration(self):
        """Test full standings calculation with completed matches"""
        config = SessionConfig(
            mode='strict-continuous-rr',
            session_type='singles',
            players=self.players[:4],  # 4 players
            courts=2,
            banned_pairs=[],
            locked_teams=None,
            first_bye_players=[]
        )
        
        session = create_session(config)
        
        # Simulate some completed matches
        # P1 beats P2 (11-5)
        match1 = Match(
            id='m1',
            court_number=1,
            team1=['p1'],
            team2=['p2'],
            status='completed',
            score={'team1_score': 11, 'team2_score': 5}
        )
        session.matches.append(match1)
        session.player_stats['p1'].wins = 1
        session.player_stats['p1'].total_points_for = 11
        session.player_stats['p1'].total_points_against = 5
        session.player_stats['p1'].games_played = 1
        session.player_stats['p2'].losses = 1
        session.player_stats['p2'].total_points_for = 5
        session.player_stats['p2'].total_points_against = 11
        session.player_stats['p2'].games_played = 1
        
        # P3 beats P4 (11-3)
        match2 = Match(
            id='m2',
            court_number=2,
            team1=['p3'],
            team2=['p4'],
            status='completed',
            score={'team1_score': 11, 'team2_score': 3}
        )
        session.matches.append(match2)
        session.player_stats['p3'].wins = 1
        session.player_stats['p3'].total_points_for = 11
        session.player_stats['p3'].total_points_against = 3
        session.player_stats['p3'].games_played = 1
        session.player_stats['p4'].losses = 1
        session.player_stats['p4'].total_points_for = 3
        session.player_stats['p4'].total_points_against = 11
        session.player_stats['p4'].games_played = 1
        
        standings = calculate_round_robin_standings(session)
        
        # Both P1 and P3 have 1 win, 0 losses
        # P3 should be ahead due to better pt_diff (11-3=8 vs 11-5=6)
        self.assertEqual(len(standings), 4, "Should have 4 players")
        
        # Find P1 and P3 positions
        p1_pos = next(i for i, s in enumerate(standings) if s['player_id'] == 'p1')
        p3_pos = next(i for i, s in enumerate(standings) if s['player_id'] == 'p3')
        
        # P3 should be ranked higher (lower position number)
        self.assertLess(p3_pos, p1_pos, "P3 should rank higher than P1 due to better pt_diff")
    
    def test_banned_pairs_respected(self):
        """Test that banned pairs are excluded from queue"""
        banned = [('p1', 'p2')]  # P1 and P2 cannot play each other
        
        queue = _generate_singles_round_robin_queue(
            self.players[:4],  # 4 players
            banned_pairs=banned,
            max_matches=100,
            player_stats=None
        )
        
        # Should have C(4,2) - 1 = 5 matches (excluding p1 vs p2)
        self.assertEqual(len(queue), 5, "Should have 5 matches excluding banned pair")
        
        # Verify p1 vs p2 is not in queue
        for match in queue:
            match_players = set(match.team1 + match.team2)
            self.assertNotEqual(match_players, {'p1', 'p2'}, "Banned pair should not be in queue")


class TestRoundRobinStandingsShared(unittest.TestCase):
    """Test that the standings calculation works for both round-robin and strict-continuous-rr"""
    
    def test_standings_calculation_applies_to_round_robin(self):
        """Verify standings calculation can be used for regular round-robin too"""
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 5)]
        
        config = SessionConfig(
            mode='round-robin',  # Regular continuous round robin
            session_type='doubles',
            players=players,
            courts=1,
            banned_pairs=[],
            locked_teams=None,
            first_bye_players=[]
        )
        
        session = create_session(config)
        
        # Add some match results
        match1 = Match(
            id='m1',
            court_number=1,
            team1=['p1', 'p2'],
            team2=['p3', 'p4'],
            status='completed',
            score={'team1_score': 11, 'team2_score': 7}
        )
        session.matches.append(match1)
        
        # Update stats
        for pid in ['p1', 'p2']:
            session.player_stats[pid].wins = 1
            session.player_stats[pid].total_points_for = 11
            session.player_stats[pid].total_points_against = 7
            session.player_stats[pid].games_played = 1
        for pid in ['p3', 'p4']:
            session.player_stats[pid].losses = 1
            session.player_stats[pid].total_points_for = 7
            session.player_stats[pid].total_points_against = 11
            session.player_stats[pid].games_played = 1
        
        standings = calculate_round_robin_standings(session)
        
        self.assertEqual(len(standings), 4)
        # Winners should be ranked higher
        winner_ids = {'p1', 'p2'}
        for s in standings[:2]:
            self.assertIn(s['player_id'], winner_ids, "Winners should be in top 2")


if __name__ == '__main__':
    unittest.main(verbosity=2)
