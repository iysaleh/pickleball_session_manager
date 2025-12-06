
import unittest
from python.types import SessionConfig, Player, Session, Match
from python.session import create_session, complete_match
from python.team_competitive_variety import populate_empty_courts_team_competitive_variety
from python.utils import create_player_stats

class TestTeamCompetitiveVariety(unittest.TestCase):
    
    def setUp(self):
        # Create players
        self.players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 17)] # 16 players
        
        # Create 8 locked teams (Pairs)
        # Team 1: p1, p2
        # ...
        # Team 8: p15, p16
        self.locked_teams = []
        for i in range(0, 16, 2):
            self.locked_teams.append([self.players[i].id, self.players[i+1].id])
            
        self.config = SessionConfig(
            mode='team-competitive-variety',
            session_type='doubles',
            players=self.players,
            courts=4,
            locked_teams=self.locked_teams
        )
        
        self.session = create_session(self.config)
        
        # Manually set some stats to simulate ELO differences
        # Team 1 (p1, p2): High ELO (wins=10, games=10)
        self.session.player_stats['p1'].games_played = 10
        self.session.player_stats['p1'].wins = 10
        self.session.player_stats['p2'].games_played = 10
        self.session.player_stats['p2'].wins = 10
        
        # Team 2 (p3, p4): High ELO (wins=10, games=10)
        self.session.player_stats['p3'].games_played = 10
        self.session.player_stats['p3'].wins = 10
        self.session.player_stats['p4'].games_played = 10
        self.session.player_stats['p4'].wins = 10
        
        # Team 3 (p5, p6): Low ELO (wins=0, games=10)
        self.session.player_stats['p5'].games_played = 10
        self.session.player_stats['p5'].wins = 0
        self.session.player_stats['p6'].games_played = 10
        self.session.player_stats['p6'].wins = 0
        
        # Team 4 (p7, p8): Low ELO (wins=0, games=10)
        self.session.player_stats['p7'].games_played = 10
        self.session.player_stats['p7'].wins = 0
        self.session.player_stats['p8'].games_played = 10
        self.session.player_stats['p8'].wins = 0

    def test_validation_missing_team(self):
        """Test that session creation fails if a player is not on a team"""
        players = [Player(id="p1", name="P1"), Player(id="p2", name="P2"), Player(id="p3", name="P3")]
        # Only p1, p2 on team
        locked_teams = [["p1", "p2"]]
        
        config = SessionConfig(
            mode='team-competitive-variety',
            session_type='doubles',
            players=players,
            courts=1,
            locked_teams=locked_teams
        )
        
        with self.assertRaises(ValueError):
            create_session(config)

    def test_initial_population_elo_matching(self):
        """Test that initial population respects ELO matching"""
        # We expect Team 1 to match with Team 2 (High vs High)
        # And Team 3 to match with Team 4 (Low vs Low)
        
        populate_empty_courts_team_competitive_variety(self.session)
        
        self.assertEqual(len(self.session.matches), 4) # Should fill all 4 courts (8 teams)
        
        matches = self.session.matches
        
        # Check matchups
        # Helper to identifying teams
        def get_team_index(team_ids):
            for i, team in enumerate(self.locked_teams):
                if set(team) == set(team_ids):
                    return i
            return -1
            
        found_high_match = False
        found_low_match = False
        
        for m in matches:
            idx1 = get_team_index(m.team1)
            idx2 = get_team_index(m.team2)
            
            # Team 0 and Team 1 are High ELO (indices 0 and 1)
            # Team 2 and Team 3 are Low ELO (indices 2 and 3)
            
            if (idx1 == 0 and idx2 == 1) or (idx1 == 1 and idx2 == 0):
                found_high_match = True
            
            if (idx1 == 2 and idx2 == 3) or (idx1 == 3 and idx2 == 2):
                found_low_match = True
                
        self.assertTrue(found_high_match, "High ELO teams should play each other")
        self.assertTrue(found_low_match, "Low ELO teams should play each other")

    def test_opponent_repetition(self):
        """Test opponent repetition constraints"""
        # Create a smaller session for easier tracking
        # 5 teams (10 players), 1 court
        players = [Player(id=f"p{i}", name=f"P{i}") for i in range(10)]
        locked_teams = [[players[i].id, players[i+1].id] for i in range(0, 10, 2)]
        # Teams: T0, T1, T2, T3, T4
        
        config = SessionConfig(
            mode='team-competitive-variety',
            session_type='doubles',
            players=players,
            courts=1,
            locked_teams=locked_teams
        )
        session = create_session(config)
        
        # T0 vs T1
        m1 = Match(id="m1", court_number=1, team1=locked_teams[0], team2=locked_teams[1], status='waiting')
        session.matches.append(m1)
        
        # Complete m1
        complete_match(session, "m1", 11, 9)
        
        # Now T0 and T1 are free. T0 should NOT play T1 again immediately.
        # Buffer size for 5 teams = 5 * 0.6 = 3.
        # T0's last opponent is T1.
        
        # Clear matches list (it has completed match)
        # populate_empty_courts checks available players.
        
        # Force T0 to have high priority (wait time)
        session.player_stats[locked_teams[0][0]].games_waited = 100
        
        populate_empty_courts_team_competitive_variety(session)
        
        # Should create a match
        self.assertEqual(len([m for m in session.matches if m.status == 'waiting']), 1)
        new_match = [m for m in session.matches if m.status == 'waiting'][0]
        
        # T0 should be in it (high priority)
        self.assertTrue(locked_teams[0] == new_match.team1 or locked_teams[0] == new_match.team2)
        
        # Opponent should NOT be T1
        opponent = new_match.team2 if new_match.team1 == locked_teams[0] else new_match.team1
        self.assertNotEqual(sorted(opponent), sorted(locked_teams[1]), "Should not repeat recent opponent T1")
        
        # Let's say it played T2. Complete it.
        complete_match(session, new_match.id, 11, 9)
        
        # Now history: T1, T2.
        # Buffer size 3.
        # Next match should not be T1 or T2.
        
        session.player_stats[locked_teams[0][0]].games_waited = 200 # Ensure T0 picked
        populate_empty_courts_team_competitive_variety(session)
        
        new_match_2 = [m for m in session.matches if m.status == 'waiting' and m.id != new_match.id][0] # Find the newest one
        opponent_2 = new_match_2.team2 if new_match_2.team1 == locked_teams[0] else new_match_2.team1
        
        self.assertNotEqual(sorted(opponent_2), sorted(locked_teams[1]), "Should not repeat T1")
        self.assertNotEqual(sorted(opponent_2), sorted(locked_teams[2]), "Should not repeat T2")

if __name__ == '__main__':
    unittest.main()
