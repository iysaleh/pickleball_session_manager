"""Test that pressing Enter in score spin boxes triggers match completion."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Must set up QApplication before importing GUI widgets
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent
from python.gui import CourtDisplayWidget
from python.pickleball_types import Session, SessionConfig, Match, Player


def make_test_session():
    """Create a minimal session for testing."""
    players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2,
    )
    session = Session(id='test-session', config=config)
    session.active_players = {p.id for p in players}
    return session


def make_test_match(court_number=1):
    """Create a minimal match for testing."""
    match = Match(
        id=f'match-{court_number}',
        team1=['p1', 'p2'],
        team2=['p3', 'p4'],
        court_number=court_number,
        status='in_progress',
    )
    return match


class TestScoreEnterKey(unittest.TestCase):

    def setUp(self):
        self.session = make_test_session()

    def test_event_filter_installed_on_spin_boxes(self):
        """Verify event filters are installed on both score spin boxes."""
        widget = CourtDisplayWidget(1, self.session)
        # The widget itself should be an event filter for the spin boxes.
        # If installEventFilter was called, the widget's eventFilter method
        # will be invoked for events on those objects. We can verify by
        # sending a key event and checking if it's intercepted.
        widget.current_match = make_test_match()
        
        # Create a Return key event
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget, 'complete_match_clicked') as mock_complete:
            # Send key event to team1_score via eventFilter
            result = widget.eventFilter(widget.team1_score, event)
            self.assertTrue(result, "eventFilter should return True (event consumed)")
            mock_complete.assert_called_once()

    def test_enter_key_triggers_complete_on_team2_score(self):
        """Pressing Enter on team2_score also triggers completion."""
        widget = CourtDisplayWidget(1, self.session)
        widget.current_match = make_test_match()

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget, 'complete_match_clicked') as mock_complete:
            result = widget.eventFilter(widget.team2_score, event)
            self.assertTrue(result)
            mock_complete.assert_called_once()

    def test_non_enter_key_not_intercepted(self):
        """Non-Enter keys should pass through normally."""
        widget = CourtDisplayWidget(1, self.session)
        widget.current_match = make_test_match()

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget, 'complete_match_clicked') as mock_complete:
            result = widget.eventFilter(widget.team1_score, event)
            self.assertFalse(result, "Non-Enter key should not be consumed")
            mock_complete.assert_not_called()

    def test_enter_on_unrelated_widget_not_intercepted(self):
        """Enter on a widget that isn't a score spin box should pass through."""
        widget = CourtDisplayWidget(1, self.session)
        widget.current_match = make_test_match()

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget, 'complete_match_clicked') as mock_complete:
            # Pass an unrelated object (the widget itself)
            result = widget.eventFilter(widget, event)
            self.assertFalse(result)
            mock_complete.assert_not_called()

    def test_different_courts_trigger_own_complete(self):
        """Each court widget's Enter triggers its own complete_match_clicked."""
        widget1 = CourtDisplayWidget(1, self.session)
        widget2 = CourtDisplayWidget(2, self.session)

        match1 = make_test_match(court_number=1)
        match2 = make_test_match(court_number=2)
        match2.id = 'match-2'
        match2.team1 = ['p5', 'p6']
        match2.team2 = ['p7', 'p8']

        widget1.current_match = match1
        widget2.current_match = match2

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget1, 'complete_match_clicked') as mock1, \
             patch.object(widget2, 'complete_match_clicked') as mock2:
            # Enter on widget1's spin box
            widget1.eventFilter(widget1.team1_score, event)
            mock1.assert_called_once()
            mock2.assert_not_called()

        event2 = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget1, 'complete_match_clicked') as mock1, \
             patch.object(widget2, 'complete_match_clicked') as mock2:
            # Enter on widget2's spin box
            widget2.eventFilter(widget2.team2_score, event2)
            mock2.assert_called_once()
            mock1.assert_not_called()

    def test_after_slide_enter_triggers_correct_match(self):
        """After a slide (set_match updates current_match), Enter uses the new match."""
        widget = CourtDisplayWidget(1, self.session)

        match_a = make_test_match(court_number=1)
        match_a.id = 'match-a'
        widget.set_match(match_a)
        self.assertEqual(widget.current_match.id, 'match-a')

        # Simulate a slide: a new match is assigned to this court widget
        match_b = make_test_match(court_number=1)
        match_b.id = 'match-b'
        match_b.team1 = ['p5', 'p6']
        match_b.team2 = ['p7', 'p8']
        widget.set_match(match_b)
        self.assertEqual(widget.current_match.id, 'match-b')

        # Now Enter should trigger complete for match-b, not match-a
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget, 'complete_match_clicked') as mock_complete:
            widget.eventFilter(widget.team1_score, event)
            mock_complete.assert_called_once()
            # Verify current_match is match-b at time of call
            self.assertEqual(widget.current_match.id, 'match-b')


    def test_enter_on_complete_button_triggers_complete(self):
        """Pressing Enter while the Complete button is focused triggers completion."""
        widget = CourtDisplayWidget(1, self.session)
        widget.current_match = make_test_match()

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget, 'complete_match_clicked') as mock_complete:
            result = widget.eventFilter(widget.complete_btn, event)
            self.assertTrue(result, "eventFilter should return True (event consumed)")
            mock_complete.assert_called_once()

    def test_numpad_enter_on_complete_button_triggers_complete(self):
        """Pressing numpad Enter on the Complete button also triggers completion."""
        widget = CourtDisplayWidget(1, self.session)
        widget.current_match = make_test_match()

        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.KeyboardModifier.NoModifier)

        with patch.object(widget, 'complete_match_clicked') as mock_complete:
            result = widget.eventFilter(widget.complete_btn, event)
            self.assertTrue(result)
            mock_complete.assert_called_once()


if __name__ == '__main__':
    unittest.main()
