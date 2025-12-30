#!/usr/bin/env python3
"""
GUI Debug Test - Tests session window creation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("="*70)
    print("GUI DEBUG TEST")
    print("="*70)
    
    print("\n1. Testing session creation...")
    from python.pickleball_types import Player, SessionConfig
    from python.session import create_session
    
    players = [
        Player(id=f"p{i}", name=f"Player {i}")
        for i in range(1, 9)
    ]
    
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=2,
        banned_pairs=[]
    )
    
    session = create_session(config)
    print(f"✓ Session created: {session.id}")
    print(f"  - Courts: {session.config.courts}")
    print(f"  - Queue size: {len(session.match_queue)}")
    
    print("\n2. Testing PyQt6 imports...")
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
    from PyQt6.QtCore import Qt
    print("✓ PyQt6 imports OK")
    
    print("\n3. Testing CourtDisplayWidget...")
    from python.gui import CourtDisplayWidget
    app = QApplication(sys.argv)
    widget = CourtDisplayWidget(1, session)
    print("✓ CourtDisplayWidget created")
    
    print("\n4. Testing SessionWindow initialization...")
    from python.gui import SessionWindow
    session_window = SessionWindow(session)
    print("✓ SessionWindow created")
    print(f"  - Court widgets: {len(session_window.court_widgets)}")
    print(f"  - Title: {session_window.title.text()}")
    
    print("\n5. Testing refresh_display...")
    session_window.refresh_display()
    print("✓ refresh_display() succeeded")
    
    print("\n" + "="*70)
    print("✓ ALL DEBUG TESTS PASSED!")
    print("="*70)
    print("\nThe GUI should work. Try running: python main.py")
    
except Exception as e:
    print(f"\n{'='*70}")
    print(f"✗ ERROR: {str(e)}")
    print(f"{'='*70}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
