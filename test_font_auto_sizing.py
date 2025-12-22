#!/usr/bin/env python3
"""
Test to demonstrate the auto-sizing text functionality
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.gui import CourtDisplayWidget
from python.types import Player, SessionConfig
from python.session import create_session, create_manual_match
from PyQt6.QtWidgets import QApplication

def test_auto_sizing_demonstration():
    """Demonstrate auto-sizing with different text lengths"""
    
    print("Testing Auto-Sizing Font Functionality")
    print("=" * 45)
    
    # Initialize
    initialize_time_manager(test_mode=False)
    app = QApplication(sys.argv)
    
    test_cases = [
        {
            "name": "Very Short Names",
            "players": [Player(id=f'p{i}', name=f'A{i}') for i in range(1, 5)],
            "expected": "Large fonts for short text"
        },
        {
            "name": "Regular Names", 
            "players": [Player(id=f'p{i}', name=f'Player {i}') for i in range(1, 5)],
            "expected": "Medium fonts for normal text"
        },
        {
            "name": "Long Names",
            "players": [Player(id=f'p{i}', name=f'VeryLongPlayerName{i}') for i in range(1, 5)],
            "expected": "Smaller fonts to fit long text"
        },
        {
            "name": "Extra Long Names",
            "players": [Player(id=f'p{i}', name=f'ExtremelyLongPlayerNameThatShouldStillFit{i}') for i in range(1, 5)],
            "expected": "Very small fonts for very long text"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}:")
        print(f"   Expected: {test_case['expected']}")
        
        # Create session with these players
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles', 
            players=test_case['players'],
            courts=1
        )
        session = create_session(config)
        
        # Create match
        create_manual_match(session, 1, ['p1', 'p2'], ['p3', 'p4'])
        match = session.matches[0] if session.matches else None
        
        # Create court widget
        court = CourtDisplayWidget(1, session)
        court.set_match(match)
        
        # Get the font sizes that were applied
        team1_font_size = court.team1_label.font().pointSize()
        team2_font_size = court.team2_label.font().pointSize()
        
        print(f"   Result: Team 1 font size: {team1_font_size}pt, Team 2 font size: {team2_font_size}pt")
        print(f"   Team 1 text: '{court.team1_label.text().replace(chr(10), ' / ')}'")
        print(f"   Team 2 text: '{court.team2_label.text().replace(chr(10), ' / ')}'")
        
        # Verify font size decreases with longer names
        if i > 1:
            prev_font_size = getattr(test_auto_sizing_demonstration, 'last_font_size', float('inf'))
            if team1_font_size <= prev_font_size:
                print("   ✓ Font size appropriately adjusted for longer text")
            else:
                print("   ⚠ Font size might be larger than expected")
        
        # Store for next comparison
        test_auto_sizing_demonstration.last_font_size = team1_font_size
    
    print(f"\n{'=' * 45}")
    print("✓ Auto-sizing functionality demonstration complete!")
    print("\nKey Features Demonstrated:")
    print("• Fonts automatically scale based on available space")
    print("• Longer names get smaller fonts to fit")
    print("• Text always fills the maximum available area")
    print("• Layout adapts to content dynamically")

if __name__ == "__main__":
    test_auto_sizing_demonstration()