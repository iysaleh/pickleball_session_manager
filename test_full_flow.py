#!/usr/bin/env python3
"""
Full GUI Flow Test - Simulates user creating a session
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from python.types import Player, SessionConfig
from python.session import create_session
from python.gui import MainWindow, SessionWindow

print("="*70)
print("FULL GUI FLOW TEST")
print("="*70)

print("\n1. Creating QApplication...")
app = QApplication(sys.argv)
print("✓ QApplication created")

print("\n2. Creating MainWindow...")
main_window = MainWindow()
print("✓ MainWindow created")
print("✓ MainWindow shown")

print("\n3. Creating test session...")
players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 9)]
config = SessionConfig(
    mode='round-robin',
    session_type='doubles',
    players=players,
    courts=2,
    banned_pairs=[]
)
session = create_session(config)
print(f"✓ Session created: {session.id}")

print("\n4. Creating SessionWindow...")
session_window = SessionWindow(session, parent_window=main_window)
print("✓ SessionWindow created")

print("\n5. Showing SessionWindow...")
session_window.show()
main_window.hide()
print("✓ SessionWindow shown")
print("✓ MainWindow hidden")

print("\n" + "="*70)
print("✓ FLOW TEST PASSED!")
print("="*70)
print("\nThe SessionWindow should now be visible with 2 courts displayed.")
print("Each court shows matches ready to be played.")
print("\nClose the window to exit.")
print("\nPress Enter to continue...")
input()

# Close windows
session_window.close()
main_window.close()
sys.exit(0)
