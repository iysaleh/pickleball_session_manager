#!/usr/bin/env python3

"""Test script to verify that player names with & characters render correctly with newlines"""

import sys
from pathlib import Path

# Add the python directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'python'))

from python.pickleball_types import Player, Session, SessionConfig, Match
from python.session import create_session
from python.gui import QApplication, CourtDisplayWidget
from PyQt6.QtWidgets import QVBoxLayout, QWidget
import uuid

def test_ampersand_names():
    """Test that player names with & characters are rendered with newlines"""
    
    # Create test players with & in their names
    players = [
        Player(id="1", name="John & Jane"),
        Player(id="2", name="Bob & Alice"), 
        Player(id="3", name="Mike & Sarah"),
        Player(id="4", name="Tom & Lisa")
    ]
    
    # Create a simple session
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        courts=1,
        players=players
    )
    
    session = create_session(config)
    
    # Create a match with these players
    match = Match(
        id=str(uuid.uuid4()),
        court_number=1,
        team1=["1", "2"],  # John & Jane, Bob & Alice
        team2=["3", "4"],  # Mike & Sarah, Tom & Lisa
        status='waiting'
    )
    
    session.matches.append(match)
    
    # Create QApplication for testing GUI components
    app = QApplication(sys.argv)
    
    # Create a court widget to test rendering
    court_widget = CourtDisplayWidget(1, session)
    court_widget.update_match(match)
    
    # Check the rendered text in the team labels
    team1_text = court_widget.team1_label.text()
    team2_text = court_widget.team2_label.text()
    
    print("Team 1 text:")
    print(repr(team1_text))
    print("Displayed as:")
    print(team1_text)
    print()
    
    print("Team 2 text:")
    print(repr(team2_text))
    print("Displayed as:")
    print(team2_text)
    print()
    
    # Verify that & characters were replaced with newlines
    assert '\n' in team1_text, "Team 1 should have newlines from & replacement"
    assert '\n' in team2_text, "Team 2 should have newlines from & replacement"
    assert '&' not in team1_text, "Team 1 should not contain & characters"
    assert '&' not in team2_text, "Team 2 should not contain & characters"
    
    # Verify specific formatting
    expected_team1 = "John \n Jane\nBob \n Alice"
    expected_team2 = "Mike \n Sarah\nTom \n Lisa"
    
    assert team1_text == expected_team1, f"Team 1 text should be '{expected_team1}' but was '{team1_text}'"
    assert team2_text == expected_team2, f"Team 2 text should be '{expected_team2}' but was '{team2_text}'"
    
    print("✅ All tests passed! Player names with & are correctly rendered with newlines.")

if __name__ == "__main__":
    test_ampersand_names()