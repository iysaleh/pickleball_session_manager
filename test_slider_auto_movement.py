#!/usr/bin/env python3
"""
Test slider movement during auto progression simulation
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import get_adaptive_phase_info, apply_adaptive_constraints

def test_slider_auto_progression():
    """Test that slider moves automatically during session progression"""
    print("Testing Slider Movement in Auto Mode")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create session
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Start in Auto mode (default)
    session.adaptive_constraints_disabled = False
    session.adaptive_balance_weight = None
    
    def simulate_slider_update():
        """Simulate what the GUI update_adaptive_constraints_slider does"""
        try:
            phase_info = get_adaptive_phase_info(session)
            
            # Check current state
            is_disabled = session.adaptive_constraints_disabled
            is_auto = session.adaptive_balance_weight is None and not is_disabled
            
            if is_auto:
                # Auto mode - set slider to reflect current phase
                phase_name = phase_info['phase_name']
                auto_weight = phase_info['auto_balance_weight']
                
                # Map auto weight to visual slider position
                if auto_weight <= 1.0:
                    slider_value = 1  # Early phase
                elif auto_weight <= 3.0:
                    slider_value = 3  # Mid phase  
                else:
                    slider_value = 4  # Late phase (5.0x)
                
                status_text = f"Auto: {phase_name} ({auto_weight:.1f}x)"
                return slider_value, status_text, True
            
            return 0, "Not Auto", False
            
        except Exception as e:
            return -1, f"Error: {e}", False
    
    # Test progression through phases
    progression_timeline = [
        (0, "Session Start"),
        (4, "Round 1 Complete"), 
        (8, "Round 2 Complete"),
        (16, "Round 4 Complete → MID PHASE"),
        (20, "Round 5 Complete"),
        (24, "Round 6 Complete → LATE PHASE"),
        (32, "Round 8 Complete")
    ]
    
    print("Session progression and slider movement:")
    print()
    
    for match_count, description in progression_timeline:
        # Set up session state
        session.matches = []
        for i in range(match_count):
            fake_match = Match(
                id=f"match_{i}",
                court_number=(i % 4) + 1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=None,
                end_time=None
            )
            session.matches.append(fake_match)
        
        # Apply adaptive constraints (updates effective weight)
        apply_adaptive_constraints(session)
        
        # Simulate GUI slider update
        slider_pos, status, is_auto = simulate_slider_update()
        
        avg_games_per_player = (match_count * 4) / 16
        
        print(f"{description:35s}: {avg_games_per_player:.1f} games/player")
        print(f"  {'Slider position:':20s} {slider_pos}")
        print(f"  {'Status:':20s} {status}")
        print(f"  {'Auto mode:':20s} {is_auto}")
        print()
    
    print("Expected slider movement:")
    print("  Early phase (0-15 matches): Slider at position 1")
    print("  Mid phase (16-23 matches):  Slider at position 3") 
    print("  Late phase (24+ matches):   Slider at position 4")
    print()
    print("✅ Slider should move automatically as session progresses in Auto mode!")

if __name__ == "__main__":
    test_slider_auto_progression()