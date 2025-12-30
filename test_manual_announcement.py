
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QPushButton

from python.pickleball_types import Session, SessionConfig, Player, Match
from python.gui import SessionWindow
from python.session import create_session

class TestManualAnnouncement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(4)]
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=players,
            courts=2
        )
        self.session = create_session(config)
        self.window = SessionWindow(self.session)
        self.window.update_timer.stop()
        self.window.announcement_timer.stop() # stop background timer
        self.window.announcement_queue = [] # clear any init stuff

    def tearDown(self):
        self.window.close()

    def test_toggle_sound_silent(self):
        """Test that toggling sound does NOT announce 'enabled'"""
        self.assertFalse(self.window.sound_enabled)
        self.window.sound_toggle_btn.setChecked(True)
        self.window.toggle_sound()
        
        self.assertTrue(self.window.sound_enabled)
        # Check queue is EMPTY
        self.assertEqual(len(self.window.announcement_queue), 0, "Queue should be empty after toggling sound")

    def test_announce_all_courts(self):
        """Test manual announcement of all courts"""
        # Setup: Court 1 has a match
        # Since we have 4 players and 2 courts, only Court 1 will be filled (4 players needed for 1 match)
        # Wait, create_session might fill courts.
        # With 4 players, 1 match is possible.
        
        # Verify court 1 has match
        widget1 = self.window.court_widgets[1]
        self.assertIsNotNone(widget1.current_match)
        
        # Court 2 should be empty
        widget2 = self.window.court_widgets[2]
        self.assertIsNone(widget2.current_match)
        
        # Call the method
        self.window.announce_all_courts()
        
        # Expectation: 
        # 1. "Announcing current matches."
        # 2. "On Court 1, Player 0 And Player 1 versus Player 2 And Player 3." (or similar team composition)
        
        self.assertEqual(len(self.window.announcement_queue), 2)
        self.assertEqual(self.window.announcement_queue[0], "Announcing current matches.")
        self.assertIn("On Court 1", self.window.announcement_queue[1])
        self.assertIn("versus", self.window.announcement_queue[1])

    def test_announce_button_exists(self):
        """Test that the button was added to the UI"""
        # Search for button with text "📢 Announce Courts"
        found = False
        for child in self.window.findChildren(QPushButton):
            if child.text() == "📢 Announce Courts":
                found = True
                # verify connection
                # difficult to verify connection without emitting click, so let's emit click
                child.click()
                break
        
        self.assertTrue(found, "Announce Courts button not found in UI")
        
        # Since we clicked it, queue should have items
        self.assertGreater(len(self.window.announcement_queue), 0)

if __name__ == '__main__':
    unittest.main()
