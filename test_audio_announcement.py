
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Mock PyQt6 before importing gui
# It's hard to mock the whole library if it's imported at top level.
# We'll rely on it being installed.
from PyQt6.QtWidgets import QApplication

from python.types import Session, SessionConfig, Player, Match
from python.gui import SessionWindow
from python.session import create_session

class TestAudioAnnouncement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        # Create a dummy session
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(4)]
        config = SessionConfig(
            mode='round-robin',
            session_type='doubles',
            players=players,
            courts=1
        )
        self.session = create_session(config)
        self.window = SessionWindow(self.session)
        
        # Stop the timer so it doesn't auto-refresh during test
        self.window.update_timer.stop()

    def tearDown(self):
        self.window.close()

    @patch('python.gui.subprocess.Popen')
    def test_toggle_sound(self, mock_popen):
        # Initial state: sound disabled
        self.assertFalse(self.window.sound_enabled)
        self.assertFalse(self.window.sound_toggle_btn.isChecked())
        
        # Click the button (simulate)
        self.window.sound_toggle_btn.setChecked(True)
        
        # Mock platform.system to return "Darwin" (macOS) for consistency with previous tests
        with patch('platform.system', return_value="Darwin"):
            self.window.toggle_sound()
        
        # Check state
        self.assertTrue(self.window.sound_enabled)
        self.assertEqual(self.window.sound_toggle_btn.text(), "🔊")
        
        # Check that the beep sound was played using afplay
        # We expect it to try to play the generated beep file
        # The exact path might differ, but it should contain "announcement_beep.wav"
        # and be passed to afplay
        if mock_popen.called:
             args, _ = mock_popen.call_args
             cmd = args[0]
             self.assertIn("afplay", cmd)
             self.assertIn("AnnouncementNotification.mp3", cmd)

    @patch('python.gui.QTimer.singleShot')
    @patch('python.gui.subprocess.Popen')
    def test_announce_match(self, mock_popen, mock_single_shot):
        # Enable sound
        self.window.sound_enabled = True
        
        # Create a match
        match = Match(
            id="m1",
            court_number=1,
            team1=["p0", "p1"],
            team2=["p2", "p3"],
            status="waiting",
            start_time=datetime.now()
        )
        
        # Manually trigger announcement without custom court name
        self.window.announce_match(1, match)
        
        # This now just queues the announcement
        self.assertEqual(len(self.window.announcement_queue), 1)
        expected_text_default = "New Match Ready on Court 1, Team Player 0 And Player 1 versus Player 2 And Player 3."
        self.assertEqual(self.window.announcement_queue[0], expected_text_default)
        
        # Process queue, mocking platform to be macOS
        with patch('platform.system', return_value="Darwin"):
            self.window.process_announcement_queue()
        
        # Should have popped from queue
        self.assertEqual(len(self.window.announcement_queue), 0)
        self.assertTrue(self.window.is_announcing)
        
        # Verify Popen called with afplay and say
        args, _ = mock_popen.call_args
        cmd = args[0]
        self.assertIn("afplay", cmd)
        self.assertIn("say", cmd)
        self.assertIn(expected_text_default, cmd)
        
        mock_popen.reset_mock()
        
        # Reset announcing flag
        self.window._reset_announcing_flag()
        self.assertFalse(self.window.is_announcing)
        
        # Now, set a custom court name
        custom_court_name = "Center Court Fun"
        # Access the CourtDisplayWidget and set its custom_title
        court_widget = self.window.court_widgets.get(1)
        self.assertIsNotNone(court_widget, "CourtDisplayWidget for court 1 should exist")
        court_widget.custom_title = custom_court_name
        
        # Manually trigger announcement with custom court name
        self.window.announce_match(1, match)
        
        # Check queue
        self.assertEqual(len(self.window.announcement_queue), 1)
        expected_text_custom = f"New Match Ready on {custom_court_name}, Team Player 0 And Player 1 versus Player 2 And Player 3."
        self.assertEqual(self.window.announcement_queue[0], expected_text_custom)
        
        # Process queue
        with patch('platform.system', return_value="Darwin"):
            self.window.process_announcement_queue()
        
        # Verify Popen called
        args, _ = mock_popen.call_args
        cmd = args[0]
        self.assertIn(expected_text_custom, cmd)

    @patch('python.gui.subprocess.Popen')
    def test_refresh_display_triggers_announcement(self, mock_popen):
        # Enable sound
        self.window.sound_enabled = True
        
        # Initial state: refresh_display() was called in __init__
        # So court 1 likely has a match (since we have 4 players and 1 court)
        # And last_known_matches should have it.
        
        # Let's verify we have a match
        from python.queue_manager import get_match_for_court
        match = get_match_for_court(self.session, 1)
        self.assertIsNotNone(match, "Expected a match to be auto-populated on court 1")
        
        # Verify it is in last_known_matches
        self.assertEqual(self.window.last_known_matches.get(1), match.id)
        
        # Now, to test the TRIGGER, we simulate a "new" match.
        # We can simply clear last_known_matches. This simulates that the match just appeared
        self.window.last_known_matches = {}
        
        # Call refresh_display
        self.window.refresh_display()
        
        # Verify announcement queued (not called directly anymore)
        self.assertEqual(len(self.window.announcement_queue), 1)
        self.assertIn("New Match Ready", self.window.announcement_queue[0])
        
        # Reset mock/queue
        mock_popen.reset_mock()
        self.window.announcement_queue = []
        
        # Call refresh_display again
        self.window.refresh_display()
        
        # Should NOT announce again
        self.assertEqual(len(self.window.announcement_queue), 0)
        
        # Now simulate a match change
        # Forfeit the current match
        from python.session import forfeit_match
        forfeit_match(self.session, match.id)
        
        # To be safe, let's manually put a NEW match on court 1
        new_match = Match(
             id="m_new",
             court_number=1,
             team1=["p0", "p2"],
             team2=["p1", "p3"],
             status="waiting",
             start_time=datetime.now()
        )
        self.session.matches.append(new_match)
        
        # refresh_display
        try:
             self.window.refresh_display()
        except Exception as e:
             pass

        # Should announce because ID changed (from match.id to m_new)
        self.assertEqual(len(self.window.announcement_queue), 1)
        self.assertIn("New Match Ready", self.window.announcement_queue[0])

if __name__ == '__main__':
    unittest.main()
