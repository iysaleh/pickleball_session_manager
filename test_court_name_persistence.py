#!/usr/bin/env python3
"""
Test court name persistence functionality
"""

import sys
sys.path.append('.')

import os
import tempfile
from pathlib import Path
from python.time_manager import initialize_time_manager
from python.gui import CourtDisplayWidget
from python.pickleball_types import Player, SessionConfig
from python.session import create_session
from python.session_persistence import (
    save_court_names, load_court_names, get_saved_court_name, 
    save_single_court_name, COURT_NAMES_FILE
)
from PyQt6.QtWidgets import QApplication

def test_court_name_persistence():
    """Test court name persistence functionality"""
    print("Testing Court Name Persistence")
    print("=" * 35)
    
    # Initialize
    initialize_time_manager(test_mode=False)
    app = QApplication(sys.argv)
    
    # Clean up any existing court names file for testing
    if COURT_NAMES_FILE.exists():
        backup_path = str(COURT_NAMES_FILE) + ".backup"
        COURT_NAMES_FILE.rename(backup_path)
        print(f"Backed up existing court names to {backup_path}")
    
    try:
        # Test 1: Save and load court names
        print("\n1. Testing basic save/load functionality")
        court_names = {1: "Main Court", 2: "Practice Court", 3: "Tournament Court"}
        
        result = save_court_names(court_names, 3)
        print(f"   Save result: {result}")
        
        loaded_names = load_court_names(3)
        print(f"   Loaded names: {loaded_names}")
        
        # Convert keys to int for comparison (JSON stores as strings)
        loaded_names_int = {int(k): v for k, v in loaded_names.items()}
        assert loaded_names_int == court_names, f"Expected {court_names}, got {loaded_names_int}"
        print("   ✓ Basic save/load works correctly")
        
        # Test 2: Court count mismatch
        print("\n2. Testing court count mismatch")
        loaded_different_count = load_court_names(5)  # Different number of courts
        print(f"   Loaded with different court count: {loaded_different_count}")
        assert loaded_different_count == {}, "Should return empty dict for different court count"
        print("   ✓ Court count mismatch handled correctly")
        
        # Test 3: Single court name save
        print("\n3. Testing single court name save/load")
        
        # Update one court name
        result = save_single_court_name(2, "Updated Practice Court", 3)
        print(f"   Single save result: {result}")
        
        loaded_name = get_saved_court_name(2, 3)
        print(f"   Loaded single court name: {loaded_name}")
        assert loaded_name == "Updated Practice Court", f"Expected 'Updated Practice Court', got {loaded_name}"
        
        # Verify other courts unchanged
        loaded_name_1 = get_saved_court_name(1, 3)
        loaded_name_3 = get_saved_court_name(3, 3)
        assert loaded_name_1 == "Main Court", f"Court 1 should still be 'Main Court', got {loaded_name_1}"
        assert loaded_name_3 == "Tournament Court", f"Court 3 should still be 'Tournament Court', got {loaded_name_3}"
        print("   ✓ Single court save/load works correctly")
        
        # Test 4: Remove custom name (set to None)
        print("\n4. Testing custom name removal")
        result = save_single_court_name(2, None, 3)  # Remove custom name for court 2
        print(f"   Remove custom name result: {result}")
        
        loaded_name = get_saved_court_name(2, 3)
        print(f"   Loaded name after removal: {loaded_name}")
        assert loaded_name is None, f"Expected None, got {loaded_name}"
        print("   ✓ Custom name removal works correctly")
        
        # Test 5: GUI Integration
        print("\n5. Testing GUI integration")
        
        # Save some court names for a 2-court setup
        test_names = {1: "Alpha Court", 2: "Beta Court"}
        save_court_names(test_names, 2)
        
        # Create session with 2 courts
        players = [Player(id=f'p{i}', name=f'Player {i}') for i in range(1, 5)]
        config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2)
        session = create_session(config)
        
        # Create court widgets - they should load the saved names
        court1 = CourtDisplayWidget(1, session)
        court2 = CourtDisplayWidget(2, session)
        
        print(f"   Court 1 custom title: {court1.custom_title}")
        print(f"   Court 2 custom title: {court2.custom_title}")
        print(f"   Court 1 display title: {court1.title.text()}")
        print(f"   Court 2 display title: {court2.title.text()}")
        
        assert court1.custom_title == "Alpha Court", f"Court 1 should have 'Alpha Court', got {court1.custom_title}"
        assert court2.custom_title == "Beta Court", f"Court 2 should have 'Beta Court', got {court2.custom_title}"
        assert court1.title.text() == "Alpha Court", f"Court 1 display should show 'Alpha Court', got {court1.title.text()}"
        assert court2.title.text() == "Beta Court", f"Court 2 display should show 'Beta Court', got {court2.title.text()}"
        print("   ✓ GUI integration works correctly")
        
        # Test 6: Different court count in GUI (should use defaults)
        print("\n6. Testing GUI with different court count")
        
        # Create session with 3 courts (different from saved 2-court names)
        config_3_courts = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=3)
        session_3_courts = create_session(config_3_courts)
        
        court1_new = CourtDisplayWidget(1, session_3_courts)
        court2_new = CourtDisplayWidget(2, session_3_courts) 
        court3_new = CourtDisplayWidget(3, session_3_courts)
        
        print(f"   Court 1 (3-court session) custom title: {court1_new.custom_title}")
        print(f"   Court 2 (3-court session) custom title: {court2_new.custom_title}")
        print(f"   Court 3 (3-court session) custom title: {court3_new.custom_title}")
        
        # Should all be None (using defaults) because court count doesn't match
        assert court1_new.custom_title is None, f"Should be None, got {court1_new.custom_title}"
        assert court2_new.custom_title is None, f"Should be None, got {court2_new.custom_title}"
        assert court3_new.custom_title is None, f"Should be None, got {court3_new.custom_title}"
        print("   ✓ Different court count correctly uses defaults")
        
        print(f"\n{'=' * 35}")
        print("✅ All court name persistence tests passed!")
        
    finally:
        # Clean up test file
        if COURT_NAMES_FILE.exists():
            COURT_NAMES_FILE.unlink()
            print(f"\nCleaned up test court names file")
        
        # Restore backup if it exists
        backup_path = Path(str(COURT_NAMES_FILE) + ".backup")
        if backup_path.exists():
            backup_path.rename(COURT_NAMES_FILE)
            print(f"Restored original court names from backup")

if __name__ == "__main__":
    test_court_name_persistence()