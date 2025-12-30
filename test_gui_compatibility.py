#!/usr/bin/env python3
"""
Quick test to ensure GUI components work with adaptive constraints slider
"""

import sys
sys.path.append('.')

from python.time_manager import initialize_time_manager
from python.pickleball_types import Player, SessionConfig
from python.session import create_session

def test_gui_compatibility():
    """Test GUI compatibility with adaptive constraints slider"""
    
    print("GUI Compatibility Test")
    print("=" * 25)
    
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
    
    print(f"✓ Session created successfully")
    print(f"✓ Mode: {session.config.mode}")
    print(f"✓ Players: {len(session.config.players)}")
    print(f"✓ Courts: {session.config.courts}")
    print(f"✓ Adaptive balance weight: {session.adaptive_balance_weight}")
    
    # Test adaptive phase info
    try:
        from python.competitive_variety import get_adaptive_phase_info, apply_adaptive_constraints
        
        apply_adaptive_constraints(session)
        phase_info = get_adaptive_phase_info(session)
        
        print(f"✓ Phase info: {phase_info['phase_name']} phase")
        print(f"✓ Auto balance weight: {phase_info['auto_balance_weight']:.1f}x")
        print(f"✓ Effective balance weight: {phase_info['effective_balance_weight']:.1f}x")
        
    except Exception as e:
        print(f"❌ Error getting phase info: {e}")
        return False
    
    # Test session persistence fields
    try:
        from python.session_persistence import serialize_session, deserialize_session
        
        # Serialize and deserialize to test persistence
        data = serialize_session(session)
        print(f"✓ Session serialization successful")
        
        # Check that new field is included
        if 'adaptive_balance_weight' in data:
            print(f"✓ Adaptive balance weight field persisted: {data['adaptive_balance_weight']}")
        else:
            print(f"❌ Adaptive balance weight field missing from serialization")
            return False
            
        # Test deserialization  
        new_session = deserialize_session(data)
        print(f"✓ Session deserialization successful")
        print(f"✓ Deserialized adaptive balance weight: {new_session.adaptive_balance_weight}")
        
    except Exception as e:
        print(f"❌ Error with session persistence: {e}")
        return False
    
    print(f"\n✅ All GUI compatibility tests passed!")
    print("   • Session creation works")
    print("   • Adaptive constraints system functional")
    print("   • Session persistence includes new field")
    print("   • Ready for GUI integration")
    
    return True

if __name__ == "__main__":
    success = test_gui_compatibility()
    sys.exit(0 if success else 1)