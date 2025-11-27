
import unittest
from datetime import datetime
from python.session import Session, SessionConfig
from python.types import Match, Player, PlayerStats
from python.competitive_variety import populate_empty_courts_competitive_variety, can_play_with_player

class TestDenseConstraints(unittest.TestCase):
    def setUp(self):
        # 12 Players
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=4
        )
        self.session = Session(id="test_session", config=config)
        self.session.active_players = {p.id for p in players}
        for p in players:
            self.session.player_stats[p.id] = PlayerStats(player_id=p.id)

    def test_dense_history_resolution(self):
        # Create a history where almost everyone played recently, creating many constraints.
        # Goal: Ensure populate_empty_courts can still find the few valid combinations.
        
        # Matches creating constraints (Global games 1, 2, 3)
        # Players p0-p11
        
        # Game 1: p0,p1 vs p2,p3
        self.session.matches.append(Match(id="m1", court_number=1, team1=["p0","p1"], team2=["p2","p3"], status="completed"))
        # Game 2: p4,p5 vs p6,p7
        self.session.matches.append(Match(id="m2", court_number=2, team1=["p4","p5"], team2=["p6","p7"], status="completed"))
        # Game 3: p8,p9 vs p0,p4 (Mixing it up)
        self.session.matches.append(Match(id="m3", court_number=3, team1=["p8","p9"], team2=["p0","p4"], status="completed"))
        
        # Now we have 11 waiters (everyone except maybe p10,p11 who haven't played? No, p10,p11 haven't played).
        # Actually p0 and p4 played twice.
        
        # Current Global Game Count = 3.
        # Next Game = 4.
        # Constraint = 3-game gap.
        
        # Valid players must not have played in G1, G2, G3?
        # No, gap is INTERVENING games.
        # If I played G1. Current is G4. Intervening G2, G3 (2 games).
        # 2 < 3 -> False.
        # So anyone who played in G1, G2, G3 is potentially locked if they try to repeat.
        
        # p10, p11 have never played. They are free.
        # p0 played G1, G3.
        # p1, p2, p3 played G1.
        # p4 played G2, G3.
        # p5, p6, p7 played G2.
        # p8, p9 played G3.
        
        # Everyone except p10, p11 has constraints.
        
        # populate should be able to find a match using p10, p11 and two others who don't conflict.
        # e.g. p10, p11 + p2, p5 (p2 played G1, p5 played G2. They haven't played each other).
        
        populate_empty_courts_competitive_variety(self.session)
        
        # Check if a match was created
        new_matches = [m for m in self.session.matches if m.status == 'waiting']
        self.assertTrue(len(new_matches) > 0, "Should be able to create a match despite dense constraints")

if __name__ == '__main__':
    unittest.main()
