#!/usr/bin/env python3
"""
Integration test for complete court name persistence workflow
"""

import sys
sys.path.append('.')

from pathlib import Path
from python.time_manager import initialize_time_manager
from python.gui import CourtDisplayWidget
from python.pickleball_types import Player, SessionConfig
from python.session import create_session
from python.session_persistence import COURT_NAMES_FILE
from PyQt6.QtWidgets import QApplication

def test_court_name_integration_workflow():
    """Test the complete workflow of court name persistence"""
    print("Integration Test: Court Name Persistence Workflow")
    print("=" * 50)
    
    # Clean up for fresh test
    if COURT_NAMES_FILE.exists():
        COURT_NAMES_FILE.unlink()
    
    # Initialize
    initialize_time_manager(test_mode=False)
    app = QApplication(sys.argv)
    
    try:
        # Phase 1: Create first session and set court names
        print("\nPhase 1: First session with custom court names")
        players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(1, 9)]
        config1 = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=3)
        session1 = create_session(config1)
        
        # Create court widgets
        courts1 = [CourtDisplayWidget(i, session1) for i in range(1, 4)]
        
        print(f"Initial court titles: {[court.title.text() for court in courts1]}")
        assert all(court.custom_title is None for court in courts1), "Should start with no custom titles"
        
        # Manually set custom titles (simulating user edits)
        courts1[0].custom_title = "Championship Court"
        courts1[0].title.setText(courts1[0].custom_title)
        courts1[0]._save_court_name()
        
        courts1[1].custom_title = "Practice Arena"  
        courts1[1].title.setText(courts1[1].custom_title)
        courts1[1]._save_court_name()
        
        # Leave court 3 with default name (custom_title = None)
        courts1[2]._save_court_name()
        
        print(f"After setting custom names: {[court.title.text() for court in courts1]}")
        print(f"Custom titles: {[court.custom_title for court in courts1]}")
        
        # Phase 2: "End session" and start new one with same court count
        print(f"\nPhase 2: New session with same court count (3)")
        config2 = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=3)
        session2 = create_session(config2)
        
        # Create new court widgets - should load saved names
        courts2 = [CourtDisplayWidget(i, session2) for i in range(1, 4)]
        
        print(f"New session court titles: {[court.title.text() for court in courts2]}")
        print(f"New session custom titles: {[court.custom_title for court in courts2]}")
        
        # Verify persistence
        assert courts2[0].custom_title == "Championship Court", f"Court 1 should be 'Championship Court', got {courts2[0].custom_title}"
        assert courts2[1].custom_title == "Practice Arena", f"Court 2 should be 'Practice Arena', got {courts2[1].custom_title}"  
        assert courts2[2].custom_title is None, f"Court 3 should be None (default), got {courts2[2].custom_title}"
        
        assert courts2[0].title.text() == "Championship Court"
        assert courts2[1].title.text() == "Practice Arena"
        assert courts2[2].title.text() == "Court 3"  # Default
        
        print("✓ Court names correctly persisted across sessions")
        
        # Phase 3: Different court count should not load saved names
        print(f"\nPhase 3: New session with different court count (2)")
        config3 = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2)
        session3 = create_session(config3)
        
        courts3 = [CourtDisplayWidget(i, session3) for i in range(1, 3)]
        
        print(f"Different court count titles: {[court.title.text() for court in courts3]}")
        print(f"Different court count custom titles: {[court.custom_title for court in courts3]}")
        
        # Should use defaults because court count doesn't match
        assert all(court.custom_title is None for court in courts3), "Should all be None for different court count"
        assert courts3[0].title.text() == "Court 1"
        assert courts3[1].title.text() == "Court 2"
        
        print("✓ Different court count correctly ignores saved names")
        
        # Phase 4: Back to original court count should restore names
        print(f"\nPhase 4: Back to original court count (3)")
        config4 = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=3)
        session4 = create_session(config4)
        
        courts4 = [CourtDisplayWidget(i, session4) for i in range(1, 4)]
        
        print(f"Restored session court titles: {[court.title.text() for court in courts4]}")
        
        # Should load the original saved names again
        assert courts4[0].custom_title == "Championship Court"
        assert courts4[1].custom_title == "Practice Arena"
        assert courts4[2].custom_title is None
        
        print("✓ Court names restored when returning to matching court count")
        
        # Phase 5: Test updating an existing name
        print(f"\nPhase 5: Update existing court name")
        
        courts4[1].custom_title = "Training Facility"
        courts4[1].title.setText(courts4[1].custom_title)
        courts4[1]._save_court_name()
        
        print(f"Updated court 2 name to: {courts4[1].title.text()}")
        
        # Verify update persisted
        config5 = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=3)
        session5 = create_session(config5)
        courts5 = [CourtDisplayWidget(i, session5) for i in range(1, 4)]
        
        assert courts5[1].custom_title == "Training Facility", f"Updated name should persist"
        print("✓ Court name updates persist correctly")
        
        print(f"\n{'=' * 50}")
        print("✅ Complete integration workflow test passed!")
        
        print(f"\nWorkflow Summary:")
        print(f"• Custom court names persist across sessions")
        print(f"• Names only load when court count matches")  
        print(f"• Different court counts use default names")
        print(f"• Updates to existing names are saved")
        print(f"• Default names (None) are handled correctly")
        
    finally:
        # Clean up
        if COURT_NAMES_FILE.exists():
            COURT_NAMES_FILE.unlink()
            print(f"\nCleaned up test files")

if __name__ == "__main__":
    test_court_name_integration_workflow()