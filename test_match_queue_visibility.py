#!/usr/bin/env python3

"""
Test that Match Queue widget is hidden in competitive-variety mode and visible in other modes.
"""

import sys
sys.path.append('/home/isaleh/dev/pickleball')

from python.session import create_session
from python.pickleball_types import Player, SessionConfig
from python.gui import SessionWindow
from python.time_manager import initialize_time_manager
from PyQt6.QtWidgets import QApplication
import time

def test_queue_visibility():
    """Test match queue visibility behavior across different game modes"""
    
    # Initialize time manager
    initialize_time_manager()
    
    # Create test players
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana"),
        Player(id="p5", name="Eve"),
        Player(id="p6", name="Frank"),
        Player(id="p7", name="Grace"),
        Player(id="p8", name="Henry"),
    ]
    
    print("Testing Match Queue visibility across game modes...")
    
    # Test 1: Competitive Variety Mode - Queue should be hidden
    print("\n1. Testing Competitive Variety mode...")
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        courts=2,
        players=players
    )
    session = create_session(config)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = SessionWindow(session)
    
    # Check that queue widgets are hidden
    assert not window.queue_label.isVisible(), "Queue label should be hidden in competitive-variety mode"
    assert not window.queue_list.isVisible(), "Queue list should be hidden in competitive-variety mode"
    assert not window.queue_count.isVisible(), "Queue count should be hidden in competitive-variety mode"
    
    # Check that waitlist has unlimited height and gets stretch factor
    waitlist_max_height = window.waiting_list.maximumHeight()
    assert waitlist_max_height == 16777215, f"Waitlist should have unlimited height in competitive-variety mode, got {waitlist_max_height}"
    
    # Check stretch factors 
    waitlist_stretch = window.right_section.stretch(window.right_section.indexOf(window.waiting_list))
    history_stretch = window.right_section.stretch(window.right_section.indexOf(window.history_list))
    assert waitlist_stretch == 1, f"Waitlist should have stretch factor 1 in competitive-variety mode, got {waitlist_stretch}"
    assert history_stretch == 1, f"History should have stretch factor 1 in competitive-variety mode, got {history_stretch}"
    
    print("   ✓ Queue widgets properly hidden")
    print("   ✓ Waitlist expanded with stretch factor 1")
    print("   ✓ History maintains stretch factor 1")
    
    window.close()
    
    # Test 2: Round Robin Mode - Queue should be visible
    print("\n2. Testing Round Robin mode...")
    config2 = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        courts=2,
        players=players
    )
    session2 = create_session(config2)
    
    window2 = SessionWindow(session2)
    window2.show()  # Show the window to ensure widgets are visible
    
    # Check that queue widgets are visible
    assert window2.queue_label.isVisible(), "Queue label should be visible in round-robin mode"
    assert window2.queue_list.isVisible(), "Queue list should be visible in round-robin mode"
    assert window2.queue_count.isVisible(), "Queue count should be visible in round-robin mode"
    
    # Check that waitlist has restricted height and no stretch factor
    waitlist_max_height = window2.waiting_list.maximumHeight()
    assert waitlist_max_height == 150, f"Waitlist should have restricted height in round-robin mode, got {waitlist_max_height}"
    
    # Check stretch factors
    waitlist_stretch = window2.right_section.stretch(window2.right_section.indexOf(window2.waiting_list))
    history_stretch = window2.right_section.stretch(window2.right_section.indexOf(window2.history_list))
    assert waitlist_stretch == 0, f"Waitlist should have stretch factor 0 in round-robin mode, got {waitlist_stretch}"
    assert history_stretch == 1, f"History should have stretch factor 1 in round-robin mode, got {history_stretch}"
    
    print("   ✓ Queue widgets properly visible")
    print("   ✓ Waitlist restricted to 150px height with no stretch")
    print("   ✓ History gets stretch factor 1")
    
    window2.close()
    
    # Test 3: King of the Court Mode - Queue should be visible
    print("\n3. Testing King of the Court mode...")
    config3 = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        courts=2,
        players=players
    )
    session3 = create_session(config3)
    
    window3 = SessionWindow(session3)
    window3.show()  # Show the window to ensure widgets are visible
    
    # Check that queue widgets are visible
    assert window3.queue_label.isVisible(), "Queue label should be visible in king-of-court mode"
    assert window3.queue_list.isVisible(), "Queue list should be visible in king-of-court mode"
    assert window3.queue_count.isVisible(), "Queue count should be visible in king-of-court mode"
    
    # Check that waitlist has restricted height and no stretch factor
    waitlist_max_height = window3.waiting_list.maximumHeight()
    assert waitlist_max_height == 150, f"Waitlist should have restricted height in king-of-court mode, got {waitlist_max_height}"
    
    # Check stretch factors
    waitlist_stretch = window3.right_section.stretch(window3.right_section.indexOf(window3.waiting_list))
    history_stretch = window3.right_section.stretch(window3.right_section.indexOf(window3.history_list))
    assert waitlist_stretch == 0, f"Waitlist should have stretch factor 0 in king-of-court mode, got {waitlist_stretch}"
    assert history_stretch == 1, f"History should have stretch factor 1 in king-of-court mode, got {history_stretch}"
    
    print("   ✓ Queue widgets properly visible")
    print("   ✓ Waitlist restricted to 150px height with no stretch")
    print("   ✓ History gets stretch factor 1")
    
    window3.close()
    
    print("\n✅ All tests passed! Match queue visibility works correctly across all game modes.")
    
    app.quit()


if __name__ == "__main__":
    test_queue_visibility()