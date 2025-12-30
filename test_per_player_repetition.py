
import unittest
from datetime import datetime
from python.session import Session, SessionConfig
from python.pickleball_types import Match, Player, PlayerStats
from python.competitive_variety import can_play_with_player

class TestPerPlayerRepetition(unittest.TestCase):
    def setUp(self):
        # 12 Players
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
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

    def test_per_player_gap_constraint(self):
        # Scenario: Brock (p0) plays with Cachi (p1).
        # Then Brock plays with Mic (p2).
        # Then Brock tries to play with Cachi (p1) again.
        # This is GAP 1 for Brock (only 1 game in between).
        # Constraint is 3. So this should fail.
        
        # Match 1: p0 & p1
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p3", "p4"], status="completed")
        self.session.matches.append(m1)
        
        # Match 2: p0 & p2 (Brock plays with someone else)
        m2 = Match(id="m2", court_number=2, team1=["p0", "p2"], team2=["p5", "p6"], status="completed")
        self.session.matches.append(m2)
        
        # Now check if p0 can play with p1 again.
        # History for p0: Match 1 (with p1), Match 2 (with p2).
        # Last time with p1 was Match 1.
        # Current is upcoming Match 3.
        # Gap = Match 3 - Match 1 = 2 games ??? No.
        
        # Let's count "Intervening Games".
        # Games p0 played since Match 1: Match 2.
        # So 1 intervening game.
        # Requirement: 3 games gap.
        
        can_play = can_play_with_player(self.session, "p0", "p1", "partner")
        self.assertFalse(can_play, "Should not allow p0 and p1 to partner. Gap is only 1 game for p0.")

        # Match 3: p0 & p7 (Brock plays with someone else again)
        m3 = Match(id="m3", court_number=1, team1=["p0", "p7"], team2=["p8", "p9"], status="completed")
        self.session.matches.append(m3)
        
        # History for p0: M1(p1), M2(p2), M3(p7).
        # Intervening: M2, M3. (2 games).
        # Requirement: 3.
        # Should still fail? Or pass if req is 2?
        # User said "until 2 games have elapsed" in prompt, but code has PARTNER_REPETITION_GAMES_REQUIRED = 3.
        # Wait, previous turn user said "strict constraint... 3 games".
        # So it should be 3.
        
        can_play_2 = can_play_with_player(self.session, "p0", "p1", "partner")
        self.assertFalse(can_play_2, "Should not allow p0 and p1. Gap is 2 games for p0. Req is 3.")

        # Match 4: p0 & p8
        m4 = Match(id="m4", court_number=2, team1=["p0", "p8"], team2=["p9", "p10"], status="completed")
        self.session.matches.append(m4)
        
        # Gap is now 3. Should pass.
        can_play_3 = can_play_with_player(self.session, "p0", "p1", "partner")
        self.assertTrue(can_play_3, "Should allow. Gap is 3.")

if __name__ == '__main__':
    unittest.main()
