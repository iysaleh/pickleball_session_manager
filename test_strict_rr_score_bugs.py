"""
Test Strict Continuous Round Robin Score Correlation and Edit History Bugs

Bug 1: Scores can be attributed to wrong players in match history/statistics
Bug 2: Editing match scores doesn't recalculate statistics  
Bug 3: Missing games in match export for Strict Continuous RR
"""

import sys
import os
import unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.pickleball_types import (
    Session, SessionConfig, Player, PlayerStats, Match, QueuedMatch
)
from python.strict_continuous_rr import (
    _generate_singles_round_robin_queue,
    populate_courts_strict_continuous,
    calculate_round_robin_standings
)
from python.session import complete_match, get_player_name, create_session
from python.time_manager import now, initialize_time_manager
import random

initialize_time_manager()


def create_test_session(num_players=6, num_courts=3):
    """Create a test session for Strict Continuous RR"""
    players = [Player(id=f"p{i+1}", name=f"Player-{i+1}") for i in range(num_players)]
    
    config = SessionConfig(
        players=players,
        courts=num_courts,
        mode='strict-continuous-rr',
        session_type='singles',
        court_sliding_mode='None',
        banned_pairs=[],
        locked_teams=[],
        first_bye_players=[]
    )
    
    session = create_session(config)
    return session


class TestScorePlayerCorrelation(unittest.TestCase):
    """Test Bug 1: Score/player correlation in Strict Continuous RR"""

    def test_scores_match_team_assignment(self):
        """Verify scores are correctly attributed regardless of side randomization."""
        random.seed(42)
        session = create_test_session()
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        populate_courts_strict_continuous(session)
        active = [m for m in session.matches if m.status == 'waiting']
        self.assertTrue(len(active) > 0)
        
        for match in active:
            success, _ = complete_match(session, match.id, 11, 4)
            self.assertTrue(success)
            
            # team1 player should have the win (they scored 11)
            t1_stats = session.player_stats[match.team1[0]]
            t2_stats = session.player_stats[match.team2[0]]
            
            self.assertGreaterEqual(t1_stats.wins, 1,
                f"{get_player_name(session, match.team1[0])} (team1, scored 11) should have won")
            self.assertGreaterEqual(t2_stats.losses, 1,
                f"{get_player_name(session, match.team2[0])} (team2, scored 4) should have lost")
            self.assertGreaterEqual(t1_stats.total_points_for, 11)
            self.assertGreaterEqual(t2_stats.total_points_for, 4)

    def test_h2h_correct_after_completion(self):
        """Verify head-to-head records are correct in standings."""
        random.seed(42)
        session = create_test_session()
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        populate_courts_strict_continuous(session)
        for match in [m for m in session.matches if m.status == 'waiting']:
            complete_match(session, match.id, 11, 4)
        
        standings = calculate_round_robin_standings(session)
        
        for s in standings:
            for opp_id, result in s['head_to_head'].items():
                # Find the match between these two
                for m in session.matches:
                    if m.status != 'completed' or not m.score:
                        continue
                    if s['player_id'] in set(m.team1 + m.team2) and opp_id in set(m.team1 + m.team2):
                        if s['player_id'] in m.team1:
                            expected = 'W' if m.score['team1_score'] > m.score['team2_score'] else 'L'
                        else:
                            expected = 'W' if m.score['team2_score'] > m.score['team1_score'] else 'L'
                        self.assertEqual(result, expected,
                            f"H2H for {s['name']} vs {get_player_name(session, opp_id)}: got {result}, expected {expected}")

    def test_match_history_display_consistent(self):
        """Simulate match history display and verify consistency."""
        random.seed(123)
        session = create_test_session()
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        populate_courts_strict_continuous(session)
        for match in [m for m in session.matches if m.status == 'waiting']:
            complete_match(session, match.id, 11, 7)
        
        completed = [m for m in session.matches if m.status == 'completed']
        for match in completed:
            t1_score = match.score['team1_score']
            t2_score = match.score['team2_score']
            
            # Simulate export format
            if t1_score >= t2_score:
                winner_names = [get_player_name(session, pid) for pid in match.team1]
                loser_names = [get_player_name(session, pid) for pid in match.team2]
            else:
                winner_names = [get_player_name(session, pid) for pid in match.team2]
                loser_names = [get_player_name(session, pid) for pid in match.team1]
            
            # Verify winner's stats include a win for this match
            winner_ids = match.team1 if t1_score > t2_score else match.team2
            for pid in winner_ids:
                self.assertGreaterEqual(session.player_stats[pid].wins, 1,
                    f"Winner {get_player_name(session, pid)} should have at least 1 win")


class TestEditMatchRecalculatesStats(unittest.TestCase):
    """Test Bug 2: Editing match scores recalculates statistics"""

    def test_basic_score_edit(self):
        """Edit a single match and verify stats are recalculated."""
        random.seed(42)
        session = create_test_session(num_players=4, num_courts=2)
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        populate_courts_strict_continuous(session)
        active = [m for m in session.matches if m.status == 'waiting']
        self.assertTrue(len(active) >= 1)
        
        match = active[0]
        success, _ = complete_match(session, match.id, 11, 4)
        self.assertTrue(success)
        
        t1_id = match.team1[0]
        t2_id = match.team2[0]
        
        # Verify initial stats
        self.assertEqual(session.player_stats[t1_id].wins, 1)
        self.assertEqual(session.player_stats[t1_id].losses, 0)
        self.assertEqual(session.player_stats[t2_id].wins, 0)
        self.assertEqual(session.player_stats[t2_id].losses, 1)
        
        # Edit: reverse the score
        from python.session import recalculate_stats_after_edit
        
        old_score = match.score.copy()
        new_score = {'team1_score': 4, 'team2_score': 11}
        recalculate_stats_after_edit(session, match, old_score, new_score)
        match.score = new_score
        
        # After edit: team1 lost, team2 won
        self.assertEqual(session.player_stats[t1_id].wins, 0)
        self.assertEqual(session.player_stats[t1_id].losses, 1)
        self.assertEqual(session.player_stats[t1_id].total_points_for, 4)
        self.assertEqual(session.player_stats[t1_id].total_points_against, 11)
        
        self.assertEqual(session.player_stats[t2_id].wins, 1)
        self.assertEqual(session.player_stats[t2_id].losses, 0)
        self.assertEqual(session.player_stats[t2_id].total_points_for, 11)
        self.assertEqual(session.player_stats[t2_id].total_points_against, 4)
        
        # Games played unchanged
        self.assertEqual(session.player_stats[t1_id].games_played, 1)
        self.assertEqual(session.player_stats[t2_id].games_played, 1)

    def test_edit_doesnt_affect_other_players(self):
        """Editing one match shouldn't affect uninvolved players' stats."""
        random.seed(42)
        session = create_test_session(num_players=6, num_courts=3)
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        # Complete 2 rounds
        for _ in range(2):
            populate_courts_strict_continuous(session)
            for m in [m for m in session.matches if m.status == 'waiting']:
                complete_match(session, m.id, 11, 7)
        
        completed = [m for m in session.matches if m.status == 'completed']
        match_to_edit = completed[0]
        involved = set(match_to_edit.team1 + match_to_edit.team2)
        
        # Record uninvolved players' stats
        uninvolved_stats = {}
        for p in session.config.players:
            if p.id not in involved:
                s = session.player_stats[p.id]
                uninvolved_stats[p.id] = (s.wins, s.losses, s.total_points_for, s.total_points_against)
        
        # Edit the match
        from python.session import recalculate_stats_after_edit
        old_score = match_to_edit.score.copy()
        new_score = {'team1_score': 7, 'team2_score': 11}
        recalculate_stats_after_edit(session, match_to_edit, old_score, new_score)
        match_to_edit.score = new_score
        
        # Verify uninvolved players unchanged
        for pid, (w, l, pf, pa) in uninvolved_stats.items():
            s = session.player_stats[pid]
            self.assertEqual(s.wins, w, f"Player {pid} wins changed")
            self.assertEqual(s.losses, l, f"Player {pid} losses changed")
            self.assertEqual(s.total_points_for, pf, f"Player {pid} pts_for changed")
            self.assertEqual(s.total_points_against, pa, f"Player {pid} pts_against changed")

    def test_standings_correct_after_edit(self):
        """Round robin standings should be correct after editing a match."""
        random.seed(42)
        session = create_test_session(num_players=4, num_courts=2)
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        populate_courts_strict_continuous(session)
        for m in [m for m in session.matches if m.status == 'waiting']:
            complete_match(session, m.id, 11, 5)
        
        # Edit first match: reverse score
        completed = [m for m in session.matches if m.status == 'completed']
        match_to_edit = completed[0]
        
        from python.session import recalculate_stats_after_edit
        old_score = match_to_edit.score.copy()
        new_score = {'team1_score': 5, 'team2_score': 11}
        recalculate_stats_after_edit(session, match_to_edit, old_score, new_score)
        match_to_edit.score = new_score
        
        # Verify standings match actual match results
        standings = calculate_round_robin_standings(session)
        for s in standings:
            pid = s['player_id']
            actual_wins = 0
            actual_losses = 0
            actual_pf = 0
            actual_pa = 0
            
            for m in session.matches:
                if m.status != 'completed' or not m.score:
                    continue
                if pid in m.team1:
                    actual_pf += m.score['team1_score']
                    actual_pa += m.score['team2_score']
                    if m.score['team1_score'] > m.score['team2_score']:
                        actual_wins += 1
                    else:
                        actual_losses += 1
                elif pid in m.team2:
                    actual_pf += m.score['team2_score']
                    actual_pa += m.score['team1_score']
                    if m.score['team2_score'] > m.score['team1_score']:
                        actual_wins += 1
                    else:
                        actual_losses += 1
            
            self.assertEqual(s['wins'], actual_wins, f"{s['name']} standings wins mismatch")
            self.assertEqual(s['losses'], actual_losses, f"{s['name']} standings losses mismatch")
            self.assertEqual(s['pts_for'], actual_pf, f"{s['name']} standings pts_for mismatch")
            self.assertEqual(s['pts_against'], actual_pa, f"{s['name']} standings pts_against mismatch")


class TestExportIncludesAllMatches(unittest.TestCase):
    """Test Bug 3: All completed matches appear in export data"""

    def test_all_matches_in_session(self):
        """Verify all completed matches are tracked in session.matches."""
        random.seed(42)
        session = create_test_session(num_players=6, num_courts=3)
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        total_completed = 0
        for _ in range(3):
            populate_courts_strict_continuous(session)
            active = [m for m in session.matches if m.status == 'waiting']
            for match in active:
                complete_match(session, match.id, 11, 7)
                total_completed += 1
        
        completed_in_session = [m for m in session.matches if m.status == 'completed']
        self.assertEqual(len(completed_in_session), total_completed,
            f"Expected {total_completed} completed matches, found {len(completed_in_session)}")

    def test_stats_add_up(self):
        """Total wins/losses should equal number of completed matches."""
        random.seed(42)
        session = create_test_session(num_players=6, num_courts=3)
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        total_completed = 0
        for _ in range(3):
            populate_courts_strict_continuous(session)
            for m in [m for m in session.matches if m.status == 'waiting']:
                complete_match(session, m.id, 11, 7)
                total_completed += 1
        
        total_wins = sum(session.player_stats[p.id].wins for p in session.config.players)
        total_losses = sum(session.player_stats[p.id].losses for p in session.config.players)
        
        # Singles: each match = 1 win + 1 loss
        self.assertEqual(total_wins, total_completed)
        self.assertEqual(total_losses, total_completed)

    def test_export_match_history_complete(self):
        """Simulate export and verify all matches are represented."""
        random.seed(42)
        session = create_test_session(num_players=6, num_courts=3)
        
        session.match_queue = _generate_singles_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.banned_pairs, 100, session.player_stats
        )
        
        total_completed = 0
        for _ in range(3):
            populate_courts_strict_continuous(session)
            for m in [m for m in session.matches if m.status == 'waiting']:
                complete_match(session, m.id, 11, 7)
                total_completed += 1
        
        # Simulate export: build match history lines
        completed = [m for m in session.matches if m.status == 'completed']
        export_lines = []
        for match in reversed(completed):
            t1_names = [get_player_name(session, pid) for pid in match.team1]
            t2_names = [get_player_name(session, pid) for pid in match.team2]
            if match.score:
                t1 = match.score['team1_score']
                t2 = match.score['team2_score']
                if t1 >= t2:
                    export_lines.append(f"{', '.join(t1_names)}: {t1} defeated {', '.join(t2_names)}: {t2}")
                else:
                    export_lines.append(f"{', '.join(t2_names)}: {t2} defeated {', '.join(t1_names)}: {t1}")
        
        self.assertEqual(len(export_lines), total_completed,
            f"Export has {len(export_lines)} lines but {total_completed} matches were completed")


if __name__ == '__main__':
    unittest.main(verbosity=2)
