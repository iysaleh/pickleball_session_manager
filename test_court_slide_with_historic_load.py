import unittest
from python.types import SessionConfig, Player, Match
from python.session import create_session, complete_match, load_session_from_snapshot


class TestCourtSlideWithHistoricLoad(unittest.TestCase):
    """Test that court slides are undone when loading historic matches"""
    
    def test_court_slide_then_historic_load_undoes_slide(self):
        """
        Test scenario:
        1. Complete match on Court 1 (causes Court 2 to slide to Court 1)
        2. Load historic state from before the slide
        3. Verify Court 2 is back at its original position
        """
        players = [Player(id=f"p{i}", name=f"P{i}") for i in range(16)]
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=players,
            courts=4,
            court_sliding_mode='Right to Left'
        )
        session = create_session(config)
        session.matches = []
        
        # Setup initial matches on all courts
        # C1: m1, C2: m2, C3: m3, C4: m4
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p2", "p3"], status="in-progress")
        m2 = Match(id="m2", court_number=2, team1=["p4", "p5"], team2=["p6", "p7"], status="in-progress")
        m3 = Match(id="m3", court_number=3, team1=["p8", "p9"], team2=["p10", "p11"], status="in-progress")
        m4 = Match(id="m4", court_number=4, team1=["p12", "p13"], team2=["p14", "p15"], status="in-progress")
        
        session.matches = [m1, m2, m3, m4]
        
        # Record original court positions before any action
        original_positions = {m.id: m.court_number for m in session.matches}
        self.assertEqual(original_positions["m2"], 2, "m2 should start at court 2")
        
        # Complete C1 (Left). This causes C2 to slide to C1
        success, slides = complete_match(session, "m1", 11, 5)
        self.assertTrue(success)
        self.assertEqual(len(slides), 1, "Should have 1 slide")
        self.assertEqual(slides[0]['match_id'], 'm2')
        self.assertEqual(slides[0]['from'], 2)
        self.assertEqual(slides[0]['to'], 1)
        
        # Verify m2 is now at court 1
        active_m2 = next(m for m in session.matches if m.id == "m2")
        self.assertEqual(active_m2.court_number, 1, "m2 should be at court 1 after slide")
        
        # Get the snapshot that was created before completion
        self.assertGreater(len(session.match_history_snapshots), 0, "Should have snapshots")
        snapshot = session.match_history_snapshots[0]
        
        # Load the historic state (from before m1 was completed)
        success = load_session_from_snapshot(session, snapshot)
        self.assertTrue(success, "Load should succeed")
        
        # Verify m2 is back at court 2 after load
        restored_m2 = next(m for m in session.matches if m.id == "m2")
        self.assertEqual(restored_m2.court_number, 2, 
                        "m2 should be back at court 2 after loading historic state")
        
        # Verify all original positions are restored
        for match in session.matches:
            expected_court = original_positions[match.id]
            self.assertEqual(match.court_number, expected_court,
                           f"{match.id} should be back at court {expected_court} after loading historic state")
    
    def test_left_to_right_slide_then_historic_load(self):
        """Test Left to Right sliding with historic load"""
        players = [Player(id=f"p{i}", name=f"P{i}") for i in range(16)]
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=players,
            courts=4,
            court_sliding_mode='Left to Right'
        )
        session = create_session(config)
        session.matches = []
        
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p2", "p3"], status="in-progress")
        m2 = Match(id="m2", court_number=2, team1=["p4", "p5"], team2=["p6", "p7"], status="in-progress")
        session.matches = [m1, m2]
        
        original_positions = {m.id: m.court_number for m in session.matches}
        
        # Complete C2 (Right). This causes C1 to slide to C2
        success, slides = complete_match(session, "m2", 11, 5)
        self.assertTrue(success)
        self.assertEqual(len(slides), 1)
        self.assertEqual(slides[0]['match_id'], 'm1')
        self.assertEqual(slides[0]['from'], 1)
        self.assertEqual(slides[0]['to'], 2)
        
        # Verify m1 is now at court 2
        active_m1 = next(m for m in session.matches if m.id == "m1")
        self.assertEqual(active_m1.court_number, 2, "m1 should be at court 2 after slide")
        
        # Get snapshot
        snapshot = session.match_history_snapshots[0]
        
        # Load historic state
        success = load_session_from_snapshot(session, snapshot)
        self.assertTrue(success)
        
        # Verify m1 is back at court 1
        restored_m1 = next(m for m in session.matches if m.id == "m1")
        self.assertEqual(restored_m1.court_number, 1, 
                        "m1 should be back at court 1 after loading historic state")


if __name__ == '__main__':
    unittest.main()
