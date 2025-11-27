
import unittest
from datetime import datetime
from python.session import Session, SessionConfig
from python.types import Match, Player, PlayerStats
from python.competitive_variety import can_play_with_player, update_variety_tracking_after_match

class TestBackToBackPartnerBug(unittest.TestCase):
    def setUp(self):
        # Create a session with 16 players to trigger the "12+ players" logic if needed,
        # but the bug is about back-to-back regardless of player count usually.
        # Although the code says "ALWAYS enforce at least 1 game gap".
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(16)]
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

    def test_back_to_back_partner_constraint(self):
        # Simulate P1 and P2 playing together in Game 1
        team1 = ["p1", "p2"]
        team2 = ["p3", "p4"]
        
        # Create a completed match 1
        match1 = Match(
            id="m1", court_number=1, 
            team1=team1, team2=team2, 
            status="completed", 
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(match1)
        
        # Update stats
        update_variety_tracking_after_match(self.session, 1, team1, team2)
        
        # Check: P1 should NOT be able to play with P2 immediately
        # Current global game count = 1.
        # last_game for P1 with P2 = 1.
        # games_elapsed = 1 - 1 = 0.
        # 0 < 1 => False. Correctly prevented if it's truly immediate globally.
        self.assertFalse(can_play_with_player(self.session, "p1", "p2", "partner"),
                         "Should not allow back-to-back partner immediately")

        # Now, simulate OTHER games happening on other courts.
        # This increments the global game counter.
        # Suppose 3 other games finish.
        for i in range(2, 5):
            m = Match(
                id=f"m{i}", court_number=2, 
                team1=["p5", "p6"], team2=["p7", "p8"], 
                status="completed",
                start_time=datetime.now(), end_time=datetime.now()
            )
            self.session.matches.append(m)
            # We don't need to update stats for these dummy players for P1/P2's sake,
            # but we do need the global game count to increase.
            # update_variety_tracking_after_match uses len(completed_matches).
        
        # Now global game count is 4.
        # P1's last game with P2 was Game 1.
        # games_elapsed = 4 - 1 = 3.
        # Constraint: if players >= 12, wait 2 games. 3 >= 2.
        # So currently, this returns TRUE.
        # BUT P1 has NOT played since Game 1. So this is P1's NEXT game.
        # It should be FALSE because it's back-to-back for P1.
        
        can_play = can_play_with_player(self.session, "p1", "p2", "partner")
        self.assertFalse(can_play, 
                         f"Should not allow back-to-back partner even if global games passed. "
                         f"Global games: 4, Last played: 1. Gap: 3. But P1 played 0 games in between.")

if __name__ == '__main__':
    unittest.main()
