#!/usr/bin/env python3

"""
Integration test to verify GUI refactoring with Session Manager Service

This test validates that the GUI properly delegates to the session manager
and that all business logic is correctly separated from the presentation layer.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from python.pickleball_types import Player, SessionConfig, KingOfCourtConfig
from python.session import create_session
from python.session_manager import create_session_manager
from python.time_manager import initialize_time_manager


class MockGUI:
    """Mock GUI class to test session manager integration"""
    
    def __init__(self, session):
        self.session = session
        self.session_manager = create_session_manager(session)
        self.events_received = []
        
        # Setup callbacks like real GUI would
        self.session_manager.add_event_listener('session_updated', self._on_session_updated)
        self.session_manager.add_event_listener('match_completed', self._on_match_completed)
        self.session_manager.add_event_listener('match_forfeited', self._on_match_forfeited)
    
    def _on_session_updated(self):
        self.events_received.append('session_updated')
    
    def _on_match_completed(self, match_id, team1_score, team2_score):
        self.events_received.append(('match_completed', match_id, team1_score, team2_score))
    
    def _on_match_forfeited(self, match_id):
        self.events_received.append(('match_forfeited', match_id))
    
    def _trigger_session_evaluation(self):
        """Method that GUI components can call (like in real refactored GUI)"""
        self.session_manager.force_session_evaluation()


def test_gui_session_manager_integration():
    """Test that GUI properly delegates to session manager"""
    initialize_time_manager()
    
    print("=== Testing GUI -> Session Manager Integration ===")
    
    # Create test session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Create mock GUI
    gui = MockGUI(session)
    gui._trigger_session_evaluation()  # Initial matches
    
    # Verify initial state
    assert len(session.matches) >= 2, "Should have initial matches"
    active_matches = [m for m in session.matches if m.status == 'waiting']
    assert len(active_matches) >= 1, "Should have active matches"
    
    # Test match completion through GUI
    first_match = active_matches[0]
    initial_events = len(gui.events_received)
    
    # GUI delegates match completion to session manager
    success, slides = gui.session_manager.handle_match_completion(first_match.id, 11, 7)
    
    assert success, "Match completion should succeed"
    assert len(gui.events_received) > initial_events, "Should receive events"
    assert 'session_updated' in gui.events_received, "Should get session update event"
    
    # Verify match was completed
    completed_match = next((m for m in session.matches if m.id == first_match.id), None)
    assert completed_match.status == 'completed', "Match should be completed"
    
    print("✓ GUI -> Session Manager delegation working")


def test_king_of_court_gui_integration():
    """Test King of Court specific GUI integration"""
    initialize_time_manager()
    
    print("\n=== Testing King of Court GUI Integration ===")
    
    # Create King of Court session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    koc_config = KingOfCourtConfig(
        seeding_option='random',
        court_ordering=[1, 2]
    )
    config = SessionConfig(
        mode='king-of-court',
        session_type='doubles',
        players=players,
        courts=2,
        king_of_court_config=koc_config
    )
    session = create_session(config)
    
    # Create mock GUI
    gui = MockGUI(session)
    
    initial_round = session.king_of_court_round_number
    active_matches = [m for m in session.matches if m.status == 'waiting']
    
    # Complete all matches to trigger round advancement
    for match in active_matches:
        success, _ = gui.session_manager.handle_match_completion(match.id, 11, 7)
        assert success, f"Should complete match {match.id}"
    
    # Should advance round
    assert session.king_of_court_round_number > initial_round, "Should advance round"
    
    # Should have new matches
    new_matches = [m for m in session.matches if m.status == 'waiting']
    assert len(new_matches) >= 2, "Should have new matches after round advancement"
    
    print("✓ King of Court GUI integration working")


def test_settings_integration():
    """Test settings changes through GUI integration"""
    initialize_time_manager()
    
    print("\n=== Testing Settings GUI Integration ===")
    
    # Create session
    players = [Player(f"player_{i}", f"Player {i}") for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    session = create_session(config)
    
    # Create mock GUI
    gui = MockGUI(session)
    
    # Test adaptive settings change (like GUI slider would do)
    initial_disabled = session.adaptive_constraints_disabled
    
    # Test enabling (setting disabled to False)
    gui.session_manager.handle_settings_change('adaptive', enabled=True)
    assert session.adaptive_constraints_disabled == False, "Should be enabled"
    
    # Test disabling (setting disabled to True) 
    gui.session_manager.handle_settings_change('adaptive', enabled=False)
    assert session.adaptive_constraints_disabled == True, "Should be disabled"
    assert 'session_updated' in gui.events_received, "Should get session update event"
    
    # Test manual override
    gui.session_manager.handle_settings_change('adaptive', weight=3.0)
    assert session.adaptive_balance_weight == 3.0, "Should set adaptive weight"
    
    print("✓ Settings integration working")


def run_integration_tests():
    """Run all integration tests"""
    print("🔧 Running GUI -> Session Manager Integration Tests")
    
    test_gui_session_manager_integration()
    test_king_of_court_gui_integration() 
    test_settings_integration()
    
    print("\n🎉 All GUI Integration tests passed!")
    print("✨ Business logic successfully separated from GUI!")
    print("🏗️  Clean architecture validated!")


if __name__ == "__main__":
    run_integration_tests()