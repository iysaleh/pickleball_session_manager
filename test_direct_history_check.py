import unittest
from datetime import datetime
from python.session import Session, SessionConfig
from python.types import Match, Player, PlayerStats
from python.competitive_variety import can_play_with_player, update_variety_tracking_after_match

class TestDirectHistoryCheck(unittest.TestCase):
    def setUp(self):
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

    def test_direct_history_check(self):
        # Game 1: P1 & P2 play together.
        team1 = ["p1", "p2"]
        team2 = ["p3", "p4"]
        match1 = Match(
            id="m1", court_number=1, 
            team1=team1, team2=team2, 
            status="completed", 
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(match1)
        
        # Even if we DO NOT update stats (simulating a bug in stats update),
        # the can_play_with_player should now catch this by looking at matches.
        
        # Verify NEW behavior (blocks match even if stats not updated)
        self.assertFalse(can_play_with_player(self.session, "p1", "p2", "partner"),
                        "Should block play using match history, even without stats update.")
        
        # Now we update stats (standard flow) and ensure it still blocks
        update_variety_tracking_after_match(self.session, 1, team1, team2)
        self.assertFalse(can_play_with_player(self.session, "p1", "p2", "partner"),
                         "With stats update, it should also block.")

    def test_robustness_against_stale_stats(self):
        # This test ensures we check match history directly.
        
        team1 = ["p5", "p6"]
        team2 = ["p7", "p8"]
        match = Match(
            id="m2", court_number=1, 
            team1=team1, team2=team2, 
            status="completed",
            start_time=datetime.now(), end_time=datetime.now()
        )
        self.session.matches.append(match)
        
        # DO NOT update stats.
        # can_play_with_player should return False because it sees the match in history.
        self.assertFalse(can_play_with_player(self.session, "p5", "p6", "partner"),
                         "Should block partner repetition from history")
        
        # Check opponent repetition too
        self.assertFalse(can_play_with_player(self.session, "p5", "p7", "opponent"),
                         "Should block opponent repetition from history")

if __name__ == '__main__':
    unittest.main()