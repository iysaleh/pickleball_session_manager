
import unittest
from python.session import Session, SessionConfig
from python.types import Match, Player, PlayerStats
from python.competitive_variety import can_play_with_player, ROAMING_RANK_PERCENTAGE, get_player_ranking

class TestRoamingRange(unittest.TestCase):
    def setUp(self):
        # 18 Players
        # limit = 18 * 0.5 = 9
        self.players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(18)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=self.players,
            courts=4
        )
        self.session = Session(id="test_session", config=config)
        self.session.active_players = {p.id for p in self.players}
        
        # Setup Ranks explicitly by manipulating ELO
        # p0 -> #1 (Highest ELO) ... p17 -> #18 (Lowest ELO)
        base_elo = 2000
        for i, p in enumerate(self.players):
            stats = PlayerStats(player_id=p.id)
            # p0 gets 2000, p1 1990, ...
            # calculate_elo_rating depends on games/wins.
            # Let's hack it: We will mock get_player_ranking or carefully set stats?
            # Setting wins/games allows some control.
            # Or I can just rely on the fact that I added them in order?
            # No, get_player_ranking sorts by rating.
            # Default rating is 1500.
            # I need to give them distinct ratings.
            # p0: 100 wins / 100 games.
            # p1: 99 wins / 100 games...
            stats.games_played = 100
            stats.wins = 100 - i # 100 down to 83
            self.session.player_stats[p.id] = stats

    def test_roaming_range_logic(self):
        # Verify Ranks
        r1, _ = get_player_ranking(self.session, "p0")
        self.assertEqual(r1, 1)
        r18, _ = get_player_ranking(self.session, "p17")
        self.assertEqual(r18, 18)
        
        # Limit = 9
        # #1 (p0) should play with up to #10 (p9). 
        # Diff 9. |1 - 10| = 9 <= 9. OK.
        
        # Check #1 vs #10
        self.assertTrue(can_play_with_player(self.session, "p0", "p9", "partner"), 
                        "Rank 1 should play with Rank 10 (Diff 9)")
        
        # Check #1 vs #11 (p10) -> Diff 10. Fail.
        self.assertFalse(can_play_with_player(self.session, "p0", "p10", "partner"),
                         "Rank 1 should NOT play with Rank 11 (Diff 10)")
                         
        # Check #9 (p8) vs #18 (p17)
        # Diff |9 - 18| = 9. OK.
        self.assertTrue(can_play_with_player(self.session, "p8", "p17", "partner"),
                        "Rank 9 should play with Rank 18 (Diff 9)")
        
        # Check #9 vs #1
        self.assertTrue(can_play_with_player(self.session, "p8", "p0", "partner"),
                        "Rank 9 should play with Rank 1")

        # Check #2 vs #11 (Diff 9) -> OK
        self.assertTrue(can_play_with_player(self.session, "p1", "p10", "partner"),
                        "Rank 2 should play with Rank 11")
                        
        # Check #2 vs #12 (Diff 10) -> Fail
        self.assertFalse(can_play_with_player(self.session, "p1", "p11", "partner"),
                         "Rank 2 should NOT play with Rank 12")

if __name__ == '__main__':
    unittest.main()
