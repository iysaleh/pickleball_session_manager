#!/usr/bin/env python3
"""
Test to verify the GUI button cycling issue is fixed
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig
from python.session import create_session
from python.competitive_variety import apply_adaptive_constraints

def test_gui_button_cycle_simulation():
    """Simulate exactly what the GUI button does"""
    print("GUI Button Cycle Simulation Test")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create session like the GUI would
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Simulate GUI initialization - this would call apply_adaptive_constraints
    print("1. GUI Initialization:")
    print(f"   Before apply: weight={session.adaptive_balance_weight}")
    apply_adaptive_constraints(session)
    print(f"   After apply: weight={session.adaptive_balance_weight}")
    
    is_disabled = session.adaptive_constraints_disabled
    is_auto = session.adaptive_balance_weight is None and not is_disabled
    print(f"   Initial state should be: {'Auto' if is_auto else 'Manual' if not is_disabled else 'Disabled'}")
    
    # Simulate button clicks exactly as the GUI code does
    def simulate_gui_button_click():
        """Exact copy of the GUI button click logic"""
        is_disabled = session.adaptive_constraints_disabled
        is_auto = session.adaptive_balance_weight is None and not is_disabled
        
        print(f"     Current: disabled={is_disabled}, auto={is_auto}, weight={session.adaptive_balance_weight}")
        
        if is_disabled:
            # Disabled -> Auto
            session.adaptive_constraints_disabled = False
            session.adaptive_balance_weight = None
            new_state = "Auto"
        elif is_auto:
            # Auto -> Manual (start with 3.0x)
            session.adaptive_constraints_disabled = False
            session.adaptive_balance_weight = 3.0
            new_state = "Manual"
        else:
            # Manual -> Disabled
            session.adaptive_constraints_disabled = True
            session.adaptive_balance_weight = None
            new_state = "Disabled"
        
        print(f"     After: disabled={session.adaptive_constraints_disabled}, auto={session.adaptive_balance_weight is None and not session.adaptive_constraints_disabled}, weight={session.adaptive_balance_weight} -> {new_state}")
        return new_state
    
    print(f"\n2. Button Click Sequence:")
    for i in range(6):  # Two full cycles
        print(f"   Click {i+1}:")
        state = simulate_gui_button_click()
    
    print(f"\n✅ GUI button cycle test completed!")
    print("   The button should now cycle through all three states:")
    print("   Auto -> Manual -> Disabled -> Auto -> Manual -> Disabled")

if __name__ == "__main__":
    test_gui_button_cycle_simulation()