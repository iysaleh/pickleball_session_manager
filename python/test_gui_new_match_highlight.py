import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# This is needed to import modules from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication, QFrame
from python.types import Player, Session, SessionConfig, GameMode, SessionType, Match, MatchStatus
from python.gui import CourtDisplayWidget

# Initialize QApplication only once
app = None
if QApplication.instance():
    app = QApplication.instance()
else:
    app = QApplication(sys.argv)


def test_new_match_highlight():
    """Test that newly started matches (<= 30 seconds) have a green highlight."""
    print("\nRunning test_new_match_highlight...")

    # Setup dummy session and players
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana"),
    ]
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=1,
        banned_pairs=[],
        court_sliding_mode="None",
        randomize_player_order=False
    )
    session = Session(id="test_session", config=config, matches=[], player_stats={}, waiting_players=[], active_players=set([p.id for p in players]), match_queue=[])

    # Create CourtDisplayWidget
    court_widget = CourtDisplayWidget(court_number=1, session=session)

    # --- Test Case 1: Match just started (within 30 seconds) ---
    start_time_recent = datetime.now() - timedelta(seconds=15) # 15 seconds ago
    new_match = Match(
        id="match_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        start_time=start_time_recent,
        end_time=None,
        status='in-progress'
    )
    court_widget.set_match(new_match)
    
    # Check for green highlight in the stylesheet
    assert "border: 3px solid #4CAF50;" in court_widget.court_area.styleSheet(), \
        f"Expected green highlight for new match. Actual: {court_widget.court_area.styleSheet()}"

    # --- Test Case 2: Match started over 30 seconds ago ---
    start_time_old = datetime.now() - timedelta(seconds=31) # 31 seconds ago
    old_match = Match(
        id="match_2",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        start_time=start_time_old,
        end_time=None,
        status='in-progress'
    )
    court_widget.set_match(old_match)

    # Check for default border (no green highlight)
    assert "border: 2px solid #333;" in court_widget.court_area.styleSheet() and \
           "border: 3px solid #4CAF50;" not in court_widget.court_area.styleSheet(), \
        f"Expected default border for old match. Actual: {court_widget.court_area.styleSheet()}"

    # --- Test Case 3: No match on court ---
    court_widget.set_match(None)
    assert "border: 2px dashed #999;" in court_widget.court_area.styleSheet(), \
        f"Expected dashed border for empty court. Actual: {court_widget.court_area.styleSheet()}"

    print("[PASS] test_new_match_highlight")


if __name__ == '__main__':
    test_new_match_highlight()
    print("\n[ALL PASS] All GUI tests passed!")
