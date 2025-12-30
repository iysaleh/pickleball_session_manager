import unittest
from python.pickleball_types import SessionConfig, Player, Match
from python.session import create_session, complete_match, load_session_from_snapshot


class TestVarietyParametersReset(unittest.TestCase):
    """Test that competitive variety parameters are preserved when loading historic matches"""
    
    def test_variety_parameters_reset_on_historic_load(self):
        """
        Test that variety parameters are restored when loading a historic match
        """
        players = [Player(id=f"p{i}", name=f"P{i}") for i in range(16)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=4,
            competitive_variety_roaming_range_percent=0.6,
            competitive_variety_partner_repetition_limit=4,
            competitive_variety_opponent_repetition_limit=3
        )
        session = create_session(config)
        
        # Record original variety parameters
        original_roaming = 0.6
        original_partner_limit = 4
        original_opponent_limit = 3
        
        self.assertEqual(session.competitive_variety_roaming_range_percent, original_roaming)
        self.assertEqual(session.competitive_variety_partner_repetition_limit, original_partner_limit)
        self.assertEqual(session.competitive_variety_opponent_repetition_limit, original_opponent_limit)
        
        # Setup some matches
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p2", "p3"], status="in-progress")
        m2 = Match(id="m2", court_number=2, team1=["p4", "p5"], team2=["p6", "p7"], status="in-progress")
        m3 = Match(id="m3", court_number=3, team1=["p8", "p9"], team2=["p10", "p11"], status="in-progress")
        m4 = Match(id="m4", court_number=4, team1=["p12", "p13"], team2=["p14", "p15"], status="in-progress")
        
        session.matches = [m1, m2, m3, m4]
        
        # Complete a match to create a snapshot
        success, slides = complete_match(session, "m1", 11, 5)
        self.assertTrue(success)
        
        # Get the snapshot
        self.assertGreater(len(session.match_history_snapshots), 0)
        snapshot = session.match_history_snapshots[0]
        
        # Simulate changing the variety parameters (like a user might do)
        session.competitive_variety_roaming_range_percent = 0.35
        session.competitive_variety_partner_repetition_limit = 2
        session.competitive_variety_opponent_repetition_limit = 1
        
        # Verify they changed
        self.assertEqual(session.competitive_variety_roaming_range_percent, 0.35)
        self.assertEqual(session.competitive_variety_partner_repetition_limit, 2)
        self.assertEqual(session.competitive_variety_opponent_repetition_limit, 1)
        
        # Load the historic state
        success = load_session_from_snapshot(session, snapshot)
        self.assertTrue(success)
        
        # Check if variety parameters are restored
        # This is the bug - they should be restored but currently they're not
        self.assertEqual(session.competitive_variety_roaming_range_percent, original_roaming,
                        "Roaming range should be restored to original value")
        self.assertEqual(session.competitive_variety_partner_repetition_limit, original_partner_limit,
                        "Partner limit should be restored to original value")
        self.assertEqual(session.competitive_variety_opponent_repetition_limit, original_opponent_limit,
                        "Opponent limit should be restored to original value")


if __name__ == '__main__':
    unittest.main()
