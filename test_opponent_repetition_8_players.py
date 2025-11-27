
import unittest
from datetime import datetime
from python.session import Session, SessionConfig
from python.types import Match, Player, PlayerStats
from python.competitive_variety import can_play_with_player, update_variety_tracking_after_match

class TestOpponentRepetition8Players(unittest.TestCase):
    def setUp(self):
        # Create a session with 8 players
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(8)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=2
        )
        self.session = Session(id="test_session", config=config)
        self.session.active_players = {p.id for p in players}
        for p in players:
            self.session.player_stats[p.id] = PlayerStats(player_id=p.id)

    def test_opponent_repetition_limit_8_players(self):
        # Game 1: P0/P1 vs P2/P3
        # P0's opponents are P2 and P3
        team1 = ["p0", "p1"]
        team2 = ["p2", "p3"]
        match1 = Match(id="m1", court_number=1, team1=team1, team2=team2, status="completed")
        self.session.matches.append(match1)
        update_variety_tracking_after_match(self.session, 1, team1, team2)
        
        # Game 2: P0/P4 vs P5/P6 (P0 plays different opponents)
        team3 = ["p0", "p4"]
        team4 = ["p5", "p6"]
        match2 = Match(id="m2", court_number=2, team1=team3, team2=team4, status="completed")
        self.session.matches.append(match2)
        update_variety_tracking_after_match(self.session, 2, team3, team4)
        
        # Current Global Games: 2.
        # P0 last played against P2 in Game 1.
        # Elapsed = 2 - 1 = 1.
        
        # Case 1: Gap = 1. Expected FAIL (Constraint 3)
        self.assertFalse(can_play_with_player(self.session, "p0", "p2", "opponent"),
                         "Should not allow opponent with gap 1")

        # Game 3: Random others
        match3 = Match(id="m3", court_number=1, team1=["p1","p3"], team2=["p5","p7"], status="completed")
        self.session.matches.append(match3)
        # Global Games: 3. Elapsed = 3 - 1 = 2.
        
        # Case 2: Gap = 2. Expected FAIL (Constraint 3)
        self.assertFalse(can_play_with_player(self.session, "p0", "p2", "opponent"),
                         "Should not allow opponent with gap 2")

        # Game 4: Random others
        match4 = Match(id="m4", court_number=2, team1=["p1","p4"], team2=["p3","p7"], status="completed")
        self.session.matches.append(match4)
        # Global Games: 4. Elapsed = 4 - 1 = 3.
        
        # Case 3: Gap = 3. Expected PASS (Constraint 3)
        self.assertTrue(can_play_with_player(self.session, "p0", "p2", "opponent"),
                        "Should allow opponent with gap 3")

if __name__ == '__main__':
    unittest.main()
