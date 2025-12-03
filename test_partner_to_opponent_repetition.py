import unittest
from datetime import datetime
from python.types import Session, Player, Match, SessionConfig, PlayerStats
from python.competitive_variety import populate_empty_courts_competitive_variety, can_play_with_player
from python.utils import generate_id

class TestPartnerToOpponentRepetition(unittest.TestCase):
    def setUp(self):
        self.players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
        self.config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=self.players,
            courts=2
        )
        self.session = Session(
            id="test_session",
            config=self.config,
            active_players=[p.id for p in self.players]
        )
        # Initialize stats
        for p in self.players:
            self.session.player_stats[p.id] = PlayerStats(player_id=p.id)

    def test_prevent_partner_to_opponent_immediate_switch(self):
        """
        Test that players who were partners in the very last match
        cannot be opponents in the immediately following match
        (when enough players are available).
        """
        # Scenario:
        # Match 1 just finished: p0 & p1 vs p2 & p3
        # Match 2 is in progress: p4 & p5 vs p6 & p7
        # Waiters: p8, p9, p10, p11
        
        # Setup Match 1 (Completed)
        m1 = Match(
            id="m1", court_number=1,
            team1=["p0", "p1"], team2=["p2", "p3"],
            status="completed",
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(m1)
        
        # Update stats for m1
        for p in ["p0", "p1", "p2", "p3"]:
            self.session.player_stats[p].games_played = 1
        
        # p0 and p1 were partners
        self.session.player_stats["p0"].partners_played.add("p1")
        self.session.player_stats["p1"].partners_played.add("p0")
        
        # Check: Can p0 and p1 be opponents right now?
        # Role='opponent'
        can_oppose = can_play_with_player(self.session, "p0", "p1", "opponent")
        
        # Must be False because they were partners in the very last game they played.
        self.assertFalse(can_oppose, "Players should not switch from partners to opponents immediately")

if __name__ == '__main__':
    unittest.main()
