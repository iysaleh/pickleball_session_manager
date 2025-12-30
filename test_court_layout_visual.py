#!/usr/bin/env python3
"""
Visual test for court display layout changes with auto-sizing fonts.
This creates court widgets to visually verify the layout improvements and font auto-sizing.
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.gui import CourtDisplayWidget
from python.pickleball_types import Player, SessionConfig
from python.session import create_session, create_manual_match
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt

def create_visual_test():
    """Create a simple window showing the court layout with auto-sizing"""
    
    # Initialize time manager
    initialize_time_manager(test_mode=False)
    
    app = QApplication(sys.argv)
    
    # Create test sessions with different name lengths
    
    # Session 1: Short names
    players_short = [Player(id=f'p{i}', name=f'P{i}') for i in range(1, 5)]
    config_short = SessionConfig(mode='competitive-variety', session_type='doubles', players=players_short, courts=1)
    session_short = create_session(config_short)
    create_manual_match(session_short, 1, ['p1', 'p2'], ['p3', 'p4'])
    
    # Session 2: Medium names  
    players_medium = [Player(id=f'p{i}', name=f'Player {i}') for i in range(1, 5)]
    config_medium = SessionConfig(mode='competitive-variety', session_type='doubles', players=players_medium, courts=1)
    session_medium = create_session(config_medium)
    create_manual_match(session_medium, 1, ['p1', 'p2'], ['p3', 'p4'])
    
    # Session 3: Long names
    players_long = [Player(id=f'p{i}', name=f'VeryLongPlayerName{i}') for i in range(1, 5)]
    config_long = SessionConfig(mode='competitive-variety', session_type='doubles', players=players_long, courts=1)
    session_long = create_session(config_long)
    create_manual_match(session_long, 1, ['p1', 'p2'], ['p3', 'p4'])
    
    # Create main window
    main_widget = QWidget()
    main_widget.setWindowTitle("Court Auto-Sizing Font Test")
    main_widget.setGeometry(100, 100, 1000, 700)
    
    layout = QVBoxLayout()
    
    # Add description
    description = QLabel("Auto-Sizing Font Demonstration:\n• Fonts automatically scale to fill available space\n• Different name lengths get appropriate font sizes\n• Text uses maximum available area")
    description.setStyleSheet("QLabel { font-size: 14px; font-weight: bold; margin: 10px; }")
    layout.addWidget(description)
    
    # Row 1: Short names (should have large fonts)
    row1_layout = QHBoxLayout()
    row1_label = QLabel("Short Names:")
    row1_label.setStyleSheet("QLabel { font-weight: bold; }")
    row1_layout.addWidget(row1_label)
    
    court1 = CourtDisplayWidget(1, session_short)
    match1 = session_short.matches[0] if session_short.matches else None
    court1.set_match(match1)
    row1_layout.addWidget(court1)
    
    layout.addLayout(row1_layout)
    
    # Row 2: Medium names (should have medium fonts)
    row2_layout = QHBoxLayout()
    row2_label = QLabel("Medium Names:")
    row2_label.setStyleSheet("QLabel { font-weight: bold; }")
    row2_layout.addWidget(row2_label)
    
    court2 = CourtDisplayWidget(1, session_medium)
    match2 = session_medium.matches[0] if session_medium.matches else None
    court2.set_match(match2)
    row2_layout.addWidget(court2)
    
    layout.addLayout(row2_layout)
    
    # Row 3: Long names (should have smaller fonts to fit)
    row3_layout = QHBoxLayout()
    row3_label = QLabel("Long Names:")
    row3_label.setStyleSheet("QLabel { font-weight: bold; }")
    row3_layout.addWidget(row3_label)
    
    court3 = CourtDisplayWidget(1, session_long)
    match3 = session_long.matches[0] if session_long.matches else None
    court3.set_match(match3)
    row3_layout.addWidget(court3)
    
    layout.addLayout(row3_layout)
    
    main_widget.setLayout(layout)
    main_widget.show()
    
    print("Auto-sizing font test window opened. You can see:")
    print("  • Row 1: Short names (P1, P2, etc.) with large fonts")
    print("  • Row 2: Medium names (Player 1, Player 2, etc.) with medium fonts")  
    print("  • Row 3: Long names (VeryLongPlayerName1, etc.) with smaller fonts")
    print("  • All fonts automatically sized to maximize space usage")
    print("  • Try resizing the window to see fonts adjust!")
    print("Press Ctrl+C to close the test window.")
    
    try:
        app.exec()
    except KeyboardInterrupt:
        print("\nTest window closed.")

if __name__ == "__main__":
    create_visual_test()