#!/usr/bin/env python3

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.session import create_session
from python.types import Player, SessionConfig
from python.competitive_variety import get_adaptive_constraints, get_adaptive_phase_info
from python.time_manager import initialize_time_manager

def test_disabled_state():
    """Test the disabled state of adaptive constraints"""
    print("Testing adaptive constraints disabled state...")
    
    # Initialize time manager first
    initialize_time_manager(test_mode=False)
    
    # Create session with competitive variety mode
    players = [Player(id=f"player{i+1}", name=f"Player {i+1}") for i in range(8)]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=2)
    session = create_session(config)
    
    print("\n1. Normal operation (auto mode):")
    session.adaptive_balance_weight = None
    session.adaptive_constraints_disabled = False
    
    constraints = get_adaptive_constraints(session)
    phase_info = get_adaptive_phase_info(session)
    
    print(f"   Phase: {phase_info['phase_name']}")
    print(f"   Balance weight: {constraints['balance_weight']}")
    print(f"   Partner repetition: {constraints['partner_repetition']}")
    print(f"   Opponent repetition: {constraints['opponent_repetition']}")
    
    print("\n2. Adaptive constraints disabled:")
    session.adaptive_constraints_disabled = True
    
    constraints = get_adaptive_constraints(session)
    phase_info = get_adaptive_phase_info(session)
    
    print(f"   Phase: {phase_info['phase_name']}")
    print(f"   Balance weight: {constraints['balance_weight']}")
    print(f"   Partner repetition: {constraints['partner_repetition']}")
    print(f"   Opponent repetition: {constraints['opponent_repetition']}")
    
    # Verify disabled state maintains standard constraints
    assert phase_info['phase_name'] == "Disabled"
    assert constraints['balance_weight'] == 1.0
    assert constraints['partner_repetition'] == 3
    assert constraints['opponent_repetition'] == 2
    
    print("\n✅ Disabled state test passed!")

if __name__ == "__main__":
    test_disabled_state()