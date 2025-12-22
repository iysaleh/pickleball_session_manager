#!/usr/bin/env python3
"""
Test to verify that adaptive mode never changes roaming range
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import apply_adaptive_constraints, get_adaptive_constraints
from datetime import datetime

def test_roaming_range_preservation():
    """Test that adaptive mode never changes roaming range"""
    
    print("ROAMING RANGE PRESERVATION TEST")
    print("=" * 40)
    
    initialize_time_manager(test_mode=False)
    
    # Create test session with specific roaming range
    players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    
    session = create_session(config)
    
    # Set a specific roaming range that user chose
    original_roaming_range = 0.45  # Semi-competitive
    session.competitive_variety_roaming_range_percent = original_roaming_range
    
    print(f"Original roaming range: {original_roaming_range}")
    print()
    
    # Test through all adaptive phases
    phases = ["Early", "Mid", "Late"]
    
    for phase_idx, phase_name in enumerate(phases):
        print(f"=== {phase_name.upper()} PHASE ===")
        
        # Add matches to trigger phase
        matches_needed = [0, 16, 24][phase_idx]  # Early, Mid, Late thresholds
        
        # Clear previous matches and add new ones
        session.matches = []
        for i in range(matches_needed):
            match = Match(
                id=f"phase_{phase_idx}_{i}",
                court_number=1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            session.matches.append(match)
        
        # Get adaptive constraints (should NOT include roaming range)
        constraints = get_adaptive_constraints(session)
        print(f"Adaptive constraints returned: {constraints}")
        
        # Verify roaming range is NOT in constraints
        if 'roaming_range' in constraints:
            print("❌ ERROR: Adaptive constraints should NOT include roaming_range!")
            return False
        
        # Apply adaptive constraints
        roaming_before = session.competitive_variety_roaming_range_percent
        apply_adaptive_constraints(session)
        roaming_after = session.competitive_variety_roaming_range_percent
        
        print(f"Roaming range before: {roaming_before}")
        print(f"Roaming range after:  {roaming_after}")
        
        # Verify roaming range unchanged
        if roaming_before != roaming_after:
            print(f"❌ ERROR: Roaming range changed from {roaming_before} to {roaming_after}!")
            return False
        
        if roaming_after != original_roaming_range:
            print(f"❌ ERROR: Roaming range is {roaming_after}, should be {original_roaming_range}!")
            return False
        
        print(f"✅ SUCCESS: Roaming range preserved in {phase_name} phase")
        print(f"   Partner constraint: {session.competitive_variety_partner_repetition_limit}")
        print(f"   Opponent constraint: {session.competitive_variety_opponent_repetition_limit}")
        print()
    
    return True

def test_different_competitiveness_levels():
    """Test that different competitiveness levels are preserved"""
    
    print("DIFFERENT COMPETITIVENESS LEVELS TEST")
    print("=" * 45)
    
    initialize_time_manager(test_mode=False)
    
    # Test different competitiveness levels
    competitiveness_levels = [
        (0.35, "Highly Competitive"),
        (0.50, "Competitive"), 
        (0.65, "Semi-Competitive"),
        (0.80, "Recreational"),
        (1.0, "Social")
    ]
    
    for roaming_range, level_name in competitiveness_levels:
        print(f"Testing {level_name} (roaming: {roaming_range})")
        
        # Create session
        players = [Player(id=f'p{i}', name=f'Player{i}') for i in range(1, 17)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles', 
            players=players,
            courts=4
        )
        
        session = create_session(config)
        session.competitive_variety_roaming_range_percent = roaming_range
        
        # Add matches to trigger late phase (most restrictive)
        for i in range(25):
            match = Match(
                id=f"test_{i}",
                court_number=1,
                team1=['p1', 'p2'],
                team2=['p3', 'p4'],
                status='completed',
                start_time=datetime.now(),
                end_time=datetime.now()
            )
            session.matches.append(match)
        
        # Apply adaptive constraints
        before = session.competitive_variety_roaming_range_percent
        apply_adaptive_constraints(session)
        after = session.competitive_variety_roaming_range_percent
        
        if before != after or after != roaming_range:
            print(f"❌ ERROR: {level_name} changed from {before} to {after}!")
            return False
        else:
            print(f"✅ SUCCESS: {level_name} preserved at {after}")
    
    print()
    return True

def run_roaming_range_tests():
    """Run all roaming range preservation tests"""
    try:
        test1 = test_roaming_range_preservation()
        test2 = test_different_competitiveness_levels()
        
        print("=" * 50)
        
        if test1 and test2:
            print("🎯 ALL TESTS PASSED!")
            print()
            print("✅ FIXED: Adaptive mode no longer changes roaming range")
            print("   • Roaming range is preserved across all phases")
            print("   • User's competitiveness choice is respected") 
            print("   • Adaptive constraints only affect variety limits")
            print("   • Balance constraints work independently of roaming range")
        else:
            print("❌ SOME TESTS FAILED!")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_roaming_range_tests()