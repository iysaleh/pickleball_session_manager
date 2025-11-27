
import unittest
from datetime import datetime, timedelta
from python.session import Session, SessionConfig
from python.types import Match, Player, PlayerStats
from python.competitive_variety import populate_empty_courts_competitive_variety, _get_last_played_info

class TestPriorityQueueing(unittest.TestCase):
    def setUp(self):
        # Create 12 players
        self.players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=self.players,
            courts=2  # 2 courts = 8 playing, 4 waiting
        )
        self.session = Session(id="test_session", config=config)
        self.session.active_players = {p.id for p in self.players}
        for p in self.players:
            self.session.player_stats[p.id] = PlayerStats(player_id=p.id)

    def test_wait_time_priority(self):
        # Setup: 
        # Players p0-p7 are just finishing a game (wait time ~0).
        # Players p8-p11 have been waiting (wait time >> 0).
        # p0-p7 have HIGH ELO (force them to be picked if ELO sorting is used).
        # p8-p11 have LOW ELO.
        
        # Set stats/ELO
        for i in range(8):
            # High win rate -> High ELO
            self.session.player_stats[f"p{i}"].games_played = 10
            self.session.player_stats[f"p{i}"].wins = 10
            # Last played in game #1 (just now)
            # We simulate this by adding a completed match
        
        for i in range(8, 12):
            # Low win rate -> Low ELO
            self.session.player_stats[f"p{i}"].games_played = 0
            # Never played
        
        # Add a completed match for p0-p3 and p4-p7
        # Game 1
        m1 = Match(id="m1", court_number=1, team1=["p0","p1"], team2=["p2","p3"], status="completed")
        self.session.matches.append(m1)
        # Game 2
        m2 = Match(id="m2", court_number=2, team1=["p4","p5"], team2=["p6","p7"], status="completed")
        self.session.matches.append(m2)
        
        # Now courts are empty.
        # populate should pick p8-p11 because they haven't played.
        # But if it sorts by ELO, it might pick p0-p7 again.
        
        populate_empty_courts_competitive_variety(self.session)
        
        # Check who is in the new matches
        new_matches = [m for m in self.session.matches if m.status == 'waiting']
        self.assertTrue(len(new_matches) > 0, "Should create new matches")
        
        players_in_new = []
        for m in new_matches:
            players_in_new.extend(m.team1)
            players_in_new.extend(m.team2)
            
        # We expect p8, p9, p10, p11 to be in the matches
        expected_waiters = {"p8", "p9", "p10", "p11"}
        present_waiters = set(players_in_new).intersection(expected_waiters)
        
        self.assertEqual(len(present_waiters), 4, 
                         f"All waiters should be picked. Found: {present_waiters}. New players: {players_in_new}")

if __name__ == '__main__':
    unittest.main()
