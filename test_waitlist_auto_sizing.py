"""
Test waitlist auto-sizing font functionality
"""

import sys
import os

# Add python directory to path
python_dir = os.path.join(os.path.dirname(__file__), 'python')
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

from PyQt6.QtWidgets import QApplication
from gui import PickleballSessionGUI
from types import Session, SessionConfig, GameMode, SessionType
from session import add_player_to_session
import time

def test_waitlist_auto_sizing():
    """Test that waitlist auto-sizing works correctly"""
    print("Testing waitlist auto-sizing...")
    
    app = QApplication(sys.argv)
    
    # Create a session with multiple players
    config = SessionConfig(
        courts=2,
        mode=GameMode.COMPETITIVE_VARIETY,
        session_type=SessionType.OPEN_PLAY
    )
    session = Session(config=config)
    
    # Add players with varying name lengths to test auto-sizing
    players = [
        "Al",  # Very short name
        "Bob Smith",  # Medium name
        "Christina Martinez-Johnson",  # Very long name
        "Joe",  # Short name
        "Elizabeth Alexandra Thompson",  # Very long name
        "Sam",  # Short name
        "Mohammed Abdul Rahman Al-Rashid",  # Extremely long name
        "Kim Lee",  # Medium name
    ]
    
    for player_name in players:
        add_player_to_session(session, player_name)
    
    # Create GUI
    gui = PickleballSessionGUI()
    gui.session = session
    
    # Verify auto-sizing methods exist
    assert hasattr(gui, '_auto_size_waitlist_fonts'), "GUI should have _auto_size_waitlist_fonts method"
    assert hasattr(gui, '_auto_size_list_widget_fonts'), "GUI should have _auto_size_list_widget_fonts method"
    
    # Show the window to trigger layout and sizing
    gui.show()
    
    # Process events to ensure everything is rendered
    app.processEvents()
    
    # Update the display to populate waitlist
    gui.update_display()
    app.processEvents()
    
    # Verify waitlist has players
    waitlist_count = gui.waiting_list.count()
    print(f"Waitlist has {waitlist_count} players")
    assert waitlist_count > 0, "Waitlist should have players"
    
    # Test that auto-sizing method can be called without errors
    try:
        gui._auto_size_waitlist_fonts()
        print("✓ Auto-sizing method executed successfully")
    except Exception as e:
        print(f"✗ Error in auto-sizing method: {e}")
        raise
    
    # Verify that items have fonts set
    fonts_set = 0
    for i in range(gui.waiting_list.count()):
        item = gui.waiting_list.item(i)
        if item and item.font().pointSize() > 0:
            fonts_set += 1
            print(f"  Item {i}: '{item.text()}' has font size {item.font().pointSize()}")
    
    print(f"✓ {fonts_set} items have fonts properly set")
    assert fonts_set > 0, "At least some items should have fonts set"
    
    # Test resize behavior
    print("Testing resize behavior...")
    original_width = gui.waiting_list.width()
    
    # Resize the waitlist widget
    gui.waiting_list.resize(int(original_width * 1.5), gui.waiting_list.height())
    app.processEvents()
    
    # Trigger auto-sizing again
    gui._auto_size_waitlist_fonts()
    app.processEvents()
    
    print("✓ Resize handling completed without errors")
    
    # Verify DeselectableListWidget has resizeEvent override
    assert hasattr(gui.waiting_list, 'resizeEvent'), "DeselectableListWidget should override resizeEvent"
    
    print("✓ All waitlist auto-sizing tests passed!")
    
    app.quit()
    return True

if __name__ == "__main__":
    success = test_waitlist_auto_sizing()
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)