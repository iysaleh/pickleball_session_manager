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

    def test_prevent_opponent_to_partner_immediate_switch(self):
        """
        Test that players who were opponents in the very last match
        cannot be partners in the immediately following match.
        """
        # Setup Match 1 (Completed) - p0 vs p1
        m1 = Match(
            id="m1", court_number=1,
            team1=["p0", "p2"], team2=["p1", "p3"],
            status="completed",
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(m1)
        
        # Update stats
        for p in ["p0", "p1", "p2", "p3"]:
            self.session.player_stats[p].games_played = 1
            
        # p0 and p1 were opponents
        self.session.player_stats["p0"].opponents_played.add("p1")
        self.session.player_stats["p1"].opponents_played.add("p0")
        
        # Check: Can p0 and p1 be partners right now?
        can_partner = can_play_with_player(self.session, "p0", "p1", "partner")
        
        # Must be False
        self.assertFalse(can_partner, "Players should not switch from opponents to partners immediately")

    def test_asymmetric_history_check(self):
        """
        Test that repetition rules are checked for BOTH players.
        Scenario:
        - P0 and P1 play together (Match 1).
        - P0 plays several more games (Match 2, 3, 4).
        - P1 waits and plays no more games.
        - Can P0 and P1 play as opponents now?
        
        P0 has 'cleared' the variety buffer. P1 has NOT (their last game was with P0).
        Should return False.
        """
        # Match 1: P0 & P1 together (Completed)
        m1 = Match(
            id="m1", court_number=1,
            team1=["p0", "p1"], team2=["p2", "p3"],
            status="completed",
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(m1)
        
        # Match 2: P0 plays with someone else (Completed)
        m2 = Match(
            id="m2", court_number=1,
            team1=["p0", "p4"], team2=["p5", "p6"],
            status="completed",
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(m2)
        
        # Match 3: P0 plays again (Completed)
        m3 = Match(
            id="m3", court_number=1,
            team1=["p0", "p7"], team2=["p8", "p9"],
            status="completed",
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(m3)
        
        # Check from P0's perspective (P0 has played 3 games)
        # We call can_play_with_player(p0, p1)
        # If it only checks p0's history, it might pass.
        # But p1's LAST game was with p0, so p1 should reject this.
        
        can_oppose = can_play_with_player(self.session, "p0", "p1", "opponent")
        self.assertFalse(can_oppose, "Should fail because P1 just played with P0 in P1's last game")

if __name__ == '__main__':
    unittest.main()
