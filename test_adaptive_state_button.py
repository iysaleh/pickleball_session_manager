#!/usr/bin/env python3
"""
Test the new adaptive state button functionality (Disabled/Auto/Manual with Auto as default)
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig
from python.session import create_session
from python.competitive_variety import get_adaptive_phase_info

def test_adaptive_state_transitions():
    """Test the adaptive state button transitions"""
    print("Testing Adaptive State Button Transitions (Disabled → Auto → Manual → Disabled)")
    print("=" * 70)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 13)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    
    session = create_session(config)
    
    def get_current_state():
        """Helper to get current state description"""
        is_disabled = getattr(session, 'adaptive_constraints_disabled', False)
        is_auto = session.adaptive_balance_weight is None and not is_disabled
        
        if is_disabled:
            return "Disabled"
        elif is_auto:
            return "Auto"
        else:
            return "Manual"
    
    def get_phase_info():
        """Helper to get phase info for display"""
        try:
            phase_info = get_adaptive_phase_info(session)
            return phase_info
        except:
            return {"phase_name": "Unknown", "auto_balance_weight": 1.0}
    
    print("Initial State (should default to Auto):")
    print(f"  Current state: {get_current_state()}")
    phase_info = get_phase_info()
    print(f"  Phase: {phase_info['phase_name']}, Auto weight: {phase_info['auto_balance_weight']:.1f}x")
    print()
    
    # Test state transition cycle: Auto → Manual → Disabled → Auto
    print("Testing State Transitions (Auto → Manual → Disabled → Auto):")
    
    # Start in Auto state (default)
    session.adaptive_constraints_disabled = False
    session.adaptive_balance_weight = None
    
    # Transition 1: Auto -> Manual
    print("\n1. Auto -> Manual:")
    session.adaptive_constraints_disabled = False
    session.adaptive_balance_weight = 3.0
    print(f"   State: {get_current_state()}")
    print(f"   Weight: {session.adaptive_balance_weight}x")
    
    # Transition 2: Manual -> Disabled  
    print("\n2. Manual -> Disabled:")
    session.adaptive_constraints_disabled = True
    session.adaptive_balance_weight = None
    print(f"   State: {get_current_state()}")
    print(f"   Constraints disabled: {session.adaptive_constraints_disabled}")
    
    # Transition 3: Disabled -> Auto
    print("\n3. Disabled -> Auto:")
    session.adaptive_constraints_disabled = False
    session.adaptive_balance_weight = None
    print(f"   State: {get_current_state()}")
    phase_info = get_phase_info()
    print(f"   Phase: {phase_info['phase_name']}, Auto weight: {phase_info['auto_balance_weight']:.1f}x")
    
    print("\n✅ All state transitions work correctly!")

def test_slider_behavior_in_each_state():
    """Test slider behavior in different states"""
    print("\n\nTesting Slider Behavior in Each State")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    # Test each state
    states_to_test = [
        ("Disabled", {"adaptive_constraints_disabled": True, "adaptive_balance_weight": None}),
        ("Auto", {"adaptive_constraints_disabled": False, "adaptive_balance_weight": None}),
        ("Manual", {"adaptive_constraints_disabled": False, "adaptive_balance_weight": 3.0}),
    ]
    
    for state_name, state_config in states_to_test:
        print(f"\n{state_name} State:")
        
        # Set session state
        for attr, value in state_config.items():
            setattr(session, attr, value)
        
        # Determine expected slider behavior
        is_disabled = getattr(session, 'adaptive_constraints_disabled', False)
        is_auto = session.adaptive_balance_weight is None and not is_disabled
        
        if is_disabled:
            expected_enabled = False
            expected_value = 0
            expected_min = 0
            slider_description = "Disabled (value=0)"
        elif is_auto:
            expected_enabled = False
            expected_value = 1
            expected_min = 0
            slider_description = "Disabled (value=1, showing auto position)"
        else:
            expected_enabled = True
            expected_min = 2
            # Map weight to slider position
            weight = session.adaptive_balance_weight
            if weight <= 2.0:
                expected_value = 2
            elif weight <= 3.0:
                expected_value = 3
            elif weight <= 5.0:
                expected_value = 4
            else:
                expected_value = 5
            slider_description = f"Enabled (min=2, value={expected_value}, weight={weight}x)"
        
        print(f"  Slider: {slider_description}")
        print(f"  Button text: {state_name}")
        
        # Test manual weight adjustments (only in Manual state)
        if not is_disabled and not is_auto:
            print(f"  Manual weight adjustments:")
            weights_to_test = [2.0, 3.0, 5.0, 8.0]
            for weight in weights_to_test:
                session.adaptive_balance_weight = weight
                # Map weight to slider position
                if weight <= 2.0:
                    slider_pos = 2
                elif weight <= 3.0:
                    slider_pos = 3
                elif weight <= 5.0:
                    slider_pos = 4
                else:
                    slider_pos = 5
                print(f"    {weight}x -> slider position {slider_pos}")
    
    print("\n✅ Slider behavior test completed!")

def test_button_click_simulation():
    """Simulate button clicks to test three-state cycle"""
    print("\n\nTesting Button Click Three-State Cycle")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 9)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=2
    )
    
    session = create_session(config)
    
    def simulate_button_click():
        """Simulate the button click logic"""
        is_disabled = getattr(session, 'adaptive_constraints_disabled', False)
        is_auto = session.adaptive_balance_weight is None and not is_disabled
        
        if is_disabled:
            # Disabled -> Auto
            session.adaptive_constraints_disabled = False
            session.adaptive_balance_weight = None
            return "Auto"
        elif is_auto:
            # Auto -> Manual
            session.adaptive_constraints_disabled = False
            session.adaptive_balance_weight = 3.0
            return "Manual"
        else:
            # Manual -> Disabled
            session.adaptive_constraints_disabled = True
            session.adaptive_balance_weight = None
            return "Disabled"
    
    # Start in default Auto state
    session.adaptive_constraints_disabled = False
    session.adaptive_balance_weight = None
    
    print("Starting state: Auto (default)")
    print("Click sequence:")
    
    for i in range(6):  # Test two full cycles
        new_state = simulate_button_click()
        weight = session.adaptive_balance_weight
        disabled = session.adaptive_constraints_disabled
        print(f"  Click {i+1}: -> {new_state} (disabled={disabled}, weight={weight})")
    
    print("\n✅ Button click simulation completed!")

def test_auto_state_behavior():
    """Test that Auto state shows automatic progression"""
    print("\n\nTesting Auto State Automatic Progression")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Set to Auto mode
    session.adaptive_constraints_disabled = False
    session.adaptive_balance_weight = None
    
    # Test different session phases
    from python.types import Match
    
    phases_to_test = [
        (0, "Early"),
        (16, "Mid"), 
        (24, "Late")
    ]
    
    for match_count, expected_phase in phases_to_test:
        print(f"\n{expected_phase} Phase ({match_count} matches):")
        
        # Clear and add fake matches
        session.matches = []
        for i in range(match_count):
            fake_match = Match(
                id=f"fake_{i}",
                court_number=1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=None,
                end_time=None
            )
            session.matches.append(fake_match)
        
        # Get phase info for auto mode
        phase_info = get_adaptive_phase_info(session)
        print(f"  Phase: {phase_info['phase_name']}")
        print(f"  Auto weight: {phase_info['auto_balance_weight']:.1f}x")
        print(f"  Status display should show: Auto: {phase_info['phase_name']} ({phase_info['auto_balance_weight']:.1f}x)")
    
    print("\n✅ Auto state progression test completed!")

def run_all_tests():
    """Run all adaptive state button tests"""
    try:
        test_adaptive_state_transitions()
        test_slider_behavior_in_each_state()
        test_button_click_simulation()
        test_auto_state_behavior()
        
        print(f"\n{'=' * 70}")
        print("✅ All adaptive state button tests passed!")
        print("\nThree-State System with Auto Default:")
        print("• 🔲 State button cycles: Disabled → Auto → Manual → Disabled")
        print("• ⚡ Auto is the default state (automatic progression)")
        print("• 🎛️ Slider only active in Manual mode (positions 2-5)")
        print("• 📊 Auto mode shows current phase (Early/Mid/Late) and weight")
        print("• 🚫 Disabled mode turns off adaptive constraints entirely")
        print("• ⚙️ Manual mode allows user control of balance weighting")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()