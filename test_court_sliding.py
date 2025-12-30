import unittest
from python.pickleball_types import SessionConfig, Player, Match
from python.session import create_session, complete_match

class TestCourtSlidingRowBased(unittest.TestCase):
    def test_right_to_left_row_sliding(self):
        """
        Test Right to Left sliding logic (Row Based).
        Odd courts (1, 3) are Left. Even courts (2, 4) are Right.
        If C1 finishes, C2 slides to C1.
        If C3 finishes, C4 slides to C3.
        If C2 finishes, nothing slides (C2 is rightmost in row).
        If C4 finishes, nothing slides.
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
        
        # Setup active matches on all courts
        # C1: m1, C2: m2, C3: m3, C4: m4
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p2", "p3"], status="in-progress")
        m2 = Match(id="m2", court_number=2, team1=["p4", "p5"], team2=["p6", "p7"], status="in-progress")
        m3 = Match(id="m3", court_number=3, team1=["p8", "p9"], team2=["p10", "p11"], status="in-progress")
        m4 = Match(id="m4", court_number=4, team1=["p12", "p13"], team2=["p14", "p15"], status="in-progress")
        
        session.matches = [m1, m2, m3, m4]
        
        # 1. Complete C1 (Left). C2 should slide to C1. C3/C4 unchanged.
        success, slides = complete_match(session, "m1", 11, 5)
        self.assertTrue(success)
        self.assertEqual(len(slides), 1)
        
        slide = slides[0]
        self.assertEqual(slide['match_id'], 'm2')
        self.assertEqual(slide['from'], 2)
        self.assertEqual(slide['to'], 1)
        
        # Verify positions
        active_m2 = next(m for m in session.matches if m.id == "m2")
        self.assertEqual(active_m2.court_number, 1)
        
        active_m3 = next(m for m in session.matches if m.id == "m3")
        self.assertEqual(active_m3.court_number, 3) # Unchanged
        
        active_m4 = next(m for m in session.matches if m.id == "m4")
        self.assertEqual(active_m4.court_number, 4) # Unchanged

        # Reset positions for next sub-test
        session.matches = []
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p2", "p3"], status="in-progress")
        m2 = Match(id="m2", court_number=2, team1=["p4", "p5"], team2=["p6", "p7"], status="in-progress")
        m3 = Match(id="m3", court_number=3, team1=["p8", "p9"], team2=["p10", "p11"], status="in-progress")
        m4 = Match(id="m4", court_number=4, team1=["p12", "p13"], team2=["p14", "p15"], status="in-progress")
        session.matches = [m1, m2, m3, m4]

        # 2. Complete C3 (Left). C4 should slide to C3. C1/C2 unchanged.
        success, slides = complete_match(session, "m3", 11, 5)
        self.assertTrue(success)
        self.assertEqual(len(slides), 1)
        self.assertEqual(slides[0]['match_id'], 'm4')
        self.assertEqual(slides[0]['from'], 4)
        self.assertEqual(slides[0]['to'], 3)
        
        active_m4 = next(m for m in session.matches if m.id == "m4")
        self.assertEqual(active_m4.court_number, 3)

        # Reset
        session.matches = []
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p2", "p3"], status="in-progress")
        m2 = Match(id="m2", court_number=2, team1=["p4", "p5"], team2=["p6", "p7"], status="in-progress")
        session.matches = [m1, m2]

        # 3. Complete C2 (Right). No slide.
        success, slides = complete_match(session, "m2", 11, 5)
        self.assertTrue(success)
        self.assertEqual(len(slides), 0)
        
        active_m1 = next(m for m in session.matches if m.id == "m1")
        self.assertEqual(active_m1.court_number, 1)

    def test_left_to_right_row_sliding(self):
        """
        Test Left to Right sliding logic.
        Odd (Left), Even (Right).
        If C2 finishes, C1 slides to C2.
        If C1 finishes, no slide.
        """
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
        m3 = Match(id="m3", court_number=3, team1=["p8", "p9"], team2=["p10", "p11"], status="in-progress")
        m4 = Match(id="m4", court_number=4, team1=["p12", "p13"], team2=["p14", "p15"], status="in-progress")
        session.matches = [m1, m2, m3, m4]
        
        # 1. Complete C2 (Right). C1 slides to C2.
        success, slides = complete_match(session, "m2", 11, 5)
        self.assertTrue(success)
        self.assertEqual(len(slides), 1)
        self.assertEqual(slides[0]['match_id'], 'm1')
        self.assertEqual(slides[0]['from'], 1)
        self.assertEqual(slides[0]['to'], 2)
        
        active_m1 = next(m for m in session.matches if m.id == "m1")
        self.assertEqual(active_m1.court_number, 2)
        
        active_m3 = next(m for m in session.matches if m.id == "m3")
        self.assertEqual(active_m3.court_number, 3) # Unchanged
        
        # Reset
        session.matches = []
        m1 = Match(id="m1", court_number=1, team1=["p0", "p1"], team2=["p2", "p3"], status="in-progress")
        m2 = Match(id="m2", court_number=2, team1=["p4", "p5"], team2=["p6", "p7"], status="in-progress")
        session.matches = [m1, m2]

        # 2. Complete C1 (Left). No slide.
        success, slides = complete_match(session, "m1", 11, 5)
        self.assertTrue(success)
        self.assertEqual(len(slides), 0)
        
        active_m2 = next(m for m in session.matches if m.id == "m2")
        self.assertEqual(active_m2.court_number, 2)

if __name__ == '__main__':
    unittest.main()