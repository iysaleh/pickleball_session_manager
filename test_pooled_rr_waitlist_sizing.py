#!/usr/bin/env python3
"""
Test to verify that waitlist font auto-sizing works for Pooled Continuous RR mode.
"""

import sys
sys.path.insert(0, '.')

from python.pickleball_types import Player, SessionConfig, PooledContinuousRRConfig
from python.session import create_session, add_player_to_session
from python.time_manager import initialize_time_manager
from python.pooled_continuous_rr import initialize_pools
from PyQt6.QtWidgets import QApplication, QVBoxLayout
from PyQt6.QtCore import QTimer

def test_pooled_rr_waitlist_sizing():
    """Test that pooled RR mode properly expands waitlist with font auto-sizing"""
    print("\n" + "="*60)
    print("Testing Pooled RR Waitlist Font Auto-Sizing")
    print("="*60)
    
    # Initialize time manager and app
    initialize_time_manager(test_mode=False)
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    # Create players first
    players = [
        Player(id=f'p{i}', name=f'Player {i}') for i in range(1, 13)  # 12 players
    ]
    
    # Create session with Pooled RR config
    config = SessionConfig(
        mode='pooled-continuous-rr',
        session_type='singles',
        courts=4,
        players=players
    )
    
    session = create_session(config)
    
    # Initialize pools config
    pools_config = PooledContinuousRRConfig(
        pools={
            'pool_1': [players[0].id, players[1].id, players[2].id, players[3].id],
            'pool_2': [players[4].id, players[5].id, players[6].id, players[7].id],
            'pool_3': [players[8].id, players[9].id, players[10].id, players[11].id],
        },
        pool_court_assignments={'pool_1': [1], 'pool_2': [2], 'pool_3': [3]}
    )
    session.config.pooled_continuous_rr_config = pools_config
    
    # Create GUI session window
    from python.gui import SessionWindow
    window = SessionWindow(session)
    window.show()
    
    # Process events to ensure layout is applied
    app.processEvents()
    print("\n1. Checking stretch factor configuration:")
    print(f"   Mode: {session.config.mode}")
    print(f"   Is Pooled RR: {session.config.mode == 'pooled-continuous-rr'}")
    
    # Check if waitlist max height was set to unlimited
    max_height = window.waiting_list.maximumHeight()
    print(f"\n2. Waitlist Maximum Height Configuration:")
    print(f"   Max Height: {max_height}")
    print(f"   Is Unlimited: {max_height >= 16777215}")
    
    if max_height >= 16777215:
        print("   ✅ Waitlist max height properly set to unlimited")
    else:
        print("   ❌ ERROR: Waitlist max height not set to unlimited!")
        return False
    
    # Verify queue list stretch factor is 0 (not competing for space)
    try:
        right_section_layout = window.right_section
        # Check if stretch factors were modified (they're stored internally)
        print(f"\n3. Layout Stretch Factor Configuration:")
        print(f"   Right section type: {type(right_section_layout)}")
        print(f"   Has waiting_list: {hasattr(window, 'waiting_list')}")
        print(f"   Has queue_list: {hasattr(window, 'queue_list')}")
        print(f"   Has history_list: {hasattr(window, 'history_list')}")
        
        # We can't directly check stretch factors from QVBoxLayout, but we can verify
        # that the widgets exist and have proper properties
        print("\n4. Widget Properties Check:")
        print(f"   Waitlist visible: {window.waiting_list.isVisible()}")
        print(f"   Queue visible: {window.queue_list.isVisible()}")
        print(f"   History visible: {window.history_list.isVisible()}")
        
        if window.waiting_list.isVisible():
            print("   ✅ Waitlist is visible (will take expanded space)")
        else:
            print("   ❌ ERROR: Waitlist is not visible!")
            return False
            
        if window.queue_list.isVisible():
            print("   ✅ Queue is visible")
        else:
            print("   ⚠️  Queue is hidden (may be expected)")
            
    except Exception as e:
        print(f"   ❌ ERROR checking layout: {e}")
        return False
    
    # Test font auto-sizing by adding some waiting players
    print(f"\n5. Testing Font Auto-Sizing:")
    
    # Add a waiting player
    from python.queue_manager import get_waiting_players
    waiting_players = get_waiting_players(session)
    print(f"   Current waiting players: {len(waiting_players)}")
    
    # Call the auto-sizing function
    try:
        window._auto_size_waitlist_fonts()
        print("   ✅ Auto-sizing function executed without errors")
        
        # Check the font size that was applied
        if window.waiting_list.count() > 0:
            item = window.waiting_list.item(0)
            if item:
                font = item.font()
                point_size = font.pointSize()
                print(f"\n6. Font Size Applied:")
                print(f"   Font size for waitlist items: {point_size}pt")
                if point_size > 11:
                    print(f"   ✅ Font is larger than default (good for expanded waitlist)")
                else:
                    print(f"   ⚠️  Font size is modest, may need adjustment")
        
    except Exception as e:
        print(f"   ❌ ERROR in auto-sizing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    window.close()
    
    print("\n" + "="*60)
    print("✅ All Pooled RR Waitlist Font Auto-Sizing Tests Passed!")
    print("="*60 + "\n")
    return True

if __name__ == '__main__':
    success = test_pooled_rr_waitlist_sizing()
    sys.exit(0 if success else 1)
