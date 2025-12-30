#!/usr/bin/env python3
"""
Test court ordering persistence for King of Court mode
"""

import os
import json
from pathlib import Path
from python.kingofcourt import get_court_ordering, set_court_ordering
from python.pickleball_types import Session, SessionConfig, Player, KingOfCourtConfig
from python.session_persistence import save_court_ordering, load_court_ordering, COURT_ORDERING_FILE


def test_court_ordering_persistence():
    """Test that court ordering persists between sessions"""
    print("🏓 Testing Court Ordering Persistence")
    
    # Clean up any existing court ordering file
    if COURT_ORDERING_FILE.exists():
        COURT_ORDERING_FILE.unlink()
    
    # Create test session 1
    players = [Player(id=str(i), name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=4
    )
    session1 = Session(id='test1', config=config)
    
    # Test 1: Initial state should use default ordering
    print("\n📋 Test 1: Default ordering when no saved data")
    ordering1 = get_court_ordering(session1)
    expected_default = [1, 2, 3, 4]
    assert ordering1 == expected_default, f"Expected {expected_default}, got {ordering1}"
    print(f"✅ Default ordering: {ordering1}")
    
    # Test 2: Set a custom ordering and verify it's saved
    print("\n📋 Test 2: Setting custom ordering")
    custom_ordering = [3, 1, 4, 2]  # Court 3 = Kings, Court 1 = mid-high, Court 4 = mid-low, Court 2 = Bottom
    session1 = set_court_ordering(session1, custom_ordering)
    
    # Verify it was applied to the session
    current_ordering = get_court_ordering(session1)
    assert current_ordering == custom_ordering, f"Expected {custom_ordering}, got {current_ordering}"
    print(f"✅ Custom ordering applied: {current_ordering}")
    
    # Verify it was saved to file
    assert COURT_ORDERING_FILE.exists(), "Court ordering file should exist after setting"
    with open(COURT_ORDERING_FILE, 'r') as f:
        file_data = json.load(f)
    assert file_data['court_ordering'] == custom_ordering, "File should contain the custom ordering"
    assert file_data['num_courts'] == 4, "File should contain correct court count"
    print(f"✅ Ordering saved to file: {file_data['court_ordering']}")
    
    # Test 3: Create new session and verify it loads the saved ordering
    print("\n📋 Test 3: Loading ordering in new session")
    session2 = Session(id='test2', config=config)
    
    # Initially, the session shouldn't have king_of_court_config
    assert session2.config.king_of_court_config is None, "New session shouldn't have KOC config initially"
    
    # But get_court_ordering should load from persistence and update the session
    loaded_ordering = get_court_ordering(session2)
    assert loaded_ordering == custom_ordering, f"Expected {custom_ordering}, got {loaded_ordering}"
    print(f"✅ Ordering loaded from persistence: {loaded_ordering}")
    
    # Verify the session was updated with the loaded config
    assert session2.config.king_of_court_config is not None, "Session should have KOC config after loading"
    assert session2.config.king_of_court_config.court_ordering == custom_ordering, "Session config should match loaded ordering"
    print("✅ Session config properly updated with loaded ordering")
    
    # Test 4: Different court count should not load saved ordering
    print("\n📋 Test 4: Different court count should ignore saved data")
    config_3_courts = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players[:6],  # Fewer players for fewer courts
        courts=3
    )
    session3 = Session(id='test3', config=config_3_courts)
    
    ordering_3_courts = get_court_ordering(session3)
    expected_3_courts = [1, 2, 3]
    assert ordering_3_courts == expected_3_courts, f"Expected {expected_3_courts}, got {ordering_3_courts}"
    print(f"✅ Different court count uses default: {ordering_3_courts}")
    
    # Test 5: Update ordering again and verify persistence
    print("\n📋 Test 5: Updating ordering again")
    new_custom = [2, 4, 1, 3]
    session1 = set_court_ordering(session1, new_custom)
    
    # Create another new session and verify it gets the latest ordering
    session4 = Session(id='test4', config=config)
    final_ordering = get_court_ordering(session4)
    assert final_ordering == new_custom, f"Expected {new_custom}, got {final_ordering}"
    print(f"✅ Latest ordering loaded: {final_ordering}")
    
    # Test 6: Direct persistence functions
    print("\n📋 Test 6: Direct persistence functions")
    test_ordering = [4, 3, 2, 1]
    save_success = save_court_ordering(test_ordering, 4)
    assert save_success, "save_court_ordering should return True on success"
    
    loaded_direct = load_court_ordering(4)
    assert loaded_direct == test_ordering, f"Expected {test_ordering}, got {loaded_direct}"
    print(f"✅ Direct save/load works: {loaded_direct}")
    
    # Test with wrong court count
    loaded_wrong = load_court_ordering(5)
    assert loaded_wrong is None, "load_court_ordering should return None for wrong court count"
    print("✅ Wrong court count returns None")
    
    print("\n🎉 All court ordering persistence tests passed!")


if __name__ == "__main__":
    test_court_ordering_persistence()