#!/usr/bin/env python3
"""
Demonstration of the Complete Adaptive Constraints Slider System

This script shows the final implementation of the adaptive constraints slider
that provides both automatic progression and manual control for balance weighting.
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import (
    get_adaptive_phase_info, calculate_session_thresholds, apply_adaptive_constraints
)

def demonstrate_adaptive_slider_system():
    """Demonstrate the complete adaptive constraints slider system"""
    
    print("COMPLETE ADAPTIVE CONSTRAINTS SLIDER SYSTEM")
    print("=" * 50)
    print()
    
    print("FEATURES:")
    print("• 🎛️ GUI slider with 5 positions (Auto, Low, Medium, High, Max)")
    print("• 🔄 Automatic progression based on games per player")
    print("• 🎯 Manual override for advanced users")
    print("• 📊 Real-time phase indicator and status display")
    print("• 💾 Persistent settings across session save/load")
    print()
    
    initialize_time_manager(test_mode=False)
    
    # Create 16-player session for demonstration
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    thresholds = calculate_session_thresholds(session)
    
    print("SLIDER POSITIONS AND MAPPING:")
    print("-" * 35)
    
    slider_positions = [
        (0, None, "Auto", "Automatically adjusts based on session progression"),
        (1, 2.0, "Low", "Slight emphasis on balance over variety"),
        (2, 3.0, "Medium", "Moderate emphasis on balance"),
        (3, 5.0, "High", "Strong emphasis on balance"),
        (4, 8.0, "Max", "Maximum balance prioritization")
    ]
    
    for position, weight, name, description in slider_positions:
        print(f"Position {position}: {name:6s} ({weight if weight else 'Auto':>4}) - {description}")
    
    print()
    print("AUTOMATIC PROGRESSION SIMULATION (16 Players):")
    print("-" * 45)
    
    # Simulate realistic session progression
    progression_timeline = [
        (0, "Session Start"),
        (4, "Round 1 Complete (1.0 games/player)"),
        (8, "Round 2 Complete (2.0 games/player)"),
        (12, "Round 3 Complete (3.0 games/player)"),
        (16, "Round 4 Complete (4.0 games/player) ← MID PHASE"),
        (20, "Round 5 Complete (5.0 games/player)"),
        (24, "Round 6 Complete (6.0 games/player) ← LATE PHASE"),
        (28, "Round 7 Complete (7.0 games/player)"),
        (32, "Round 8 Complete (8.0 games/player)")
    ]
    
    for match_count, description in progression_timeline:
        # Simulate session state
        session.matches = []
        session.adaptive_balance_weight = None  # Auto mode
        
        for i in range(match_count):
            fake_match = Match(
                id=f"sim_{i}",
                court_number=(i % 4) + 1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=None,
                end_time=None
            )
            session.matches.append(fake_match)
        
        apply_adaptive_constraints(session)
        phase_info = get_adaptive_phase_info(session)
        
        phase_name = phase_info['phase_name']
        auto_weight = phase_info['auto_balance_weight']
        partner_rep = session.competitive_variety_partner_repetition_limit
        opponent_rep = session.competitive_variety_opponent_repetition_limit
        
        status_text = f"Auto: {phase_name} ({auto_weight:.1f}x) | P:{partner_rep} O:{opponent_rep}"
        
        print(f"{description:45s}: {status_text}")
    
    print()
    print("GUI SLIDER BEHAVIOR:")
    print("-" * 25)
    
    # Reset to early session for GUI demonstration
    session.matches = []
    for i in range(5):  # Early session
        fake_match = Match(
            id=f"gui_{i}",
            court_number=1,
            team1=['p1', 'p2'],
            team2=['p3', 'p4'],
            status='completed',
            start_time=None,
            end_time=None
        )
        session.matches.append(fake_match)
    
    print("When user moves slider:")
    
    for position, weight, name, _ in slider_positions:
        session.adaptive_balance_weight = weight
        apply_adaptive_constraints(session)
        phase_info = get_adaptive_phase_info(session)
        
        if weight is None:
            auto_weight = phase_info['auto_balance_weight']
            status_display = f"Auto: Early ({auto_weight:.1f}x)"
        else:
            status_display = f"Manual: {weight:.1f}x"
        
        print(f"  Slider position {position} ({name:6s}): GUI shows '{status_display}'")
    
    print()
    print("TECHNICAL INTEGRATION:")
    print("-" * 25)
    print("📱 GUI Components:")
    print("   • QSlider with 5 positions (0-4)")
    print("   • Real-time status label showing current phase/weight")
    print("   • Auto-updates as matches complete")
    print("   • Manual override persists until reset to Auto")
    print()
    print("🔧 Backend Integration:")
    print("   • session.adaptive_balance_weight: Optional[float]")
    print("   • None = automatic mode, float = manual override")
    print("   • get_adaptive_phase_info() provides all GUI display data")
    print("   • apply_adaptive_constraints() respects manual override")
    print()
    print("💾 Persistence:")
    print("   • Manual override saved/loaded with session")
    print("   • Auto mode preserves across session resume")
    print("   • Backwards compatible with existing sessions")
    print()
    
    print("COMPETITIVE VARIETY CONSTRAINT PROGRESSION:")
    print("-" * 45)
    
    constraints_examples = [
        ("Early (0-3 games/player)", {"partner": 3, "opponent": 2, "auto_weight": 1.0}),
        ("Mid (4-5 games/player)", {"partner": 2, "opponent": 1, "auto_weight": 3.0}),
        ("Late (6+ games/player)", {"partner": 1, "opponent": 1, "auto_weight": 5.0})
    ]
    
    for phase_name, constraints in constraints_examples:
        p = constraints["partner"]
        o = constraints["opponent"] 
        w = constraints["auto_weight"]
        print(f"{phase_name:25s}: Partner={p}, Opponent={o}, Auto Weight={w:.1f}x")
    
    print()
    print("✅ COMPLETE ADAPTIVE CONSTRAINTS SLIDER SYSTEM READY!")
    print()
    print("🎯 USER BENEFITS:")
    print("   • Automatic optimization for most users")
    print("   • Expert control for advanced users")
    print("   • Visual feedback on current state")
    print("   • Smooth progression without jarring changes")
    print("   • Maintains all existing variety and quality constraints")

if __name__ == "__main__":
    demonstrate_adaptive_slider_system()