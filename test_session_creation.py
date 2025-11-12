#!/usr/bin/env python3
"""
Debug script to test session creation without GUI
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from python.types import Player, SessionConfig
from python.session import create_session

try:
    print("Creating test players...")
    players = [
        Player(id=f"p{i}", name=f"Player {i}")
        for i in range(1, 9)
    ]
    print(f"✓ Created {len(players)} players")
    
    print("\nCreating session config...")
    config = SessionConfig(
        mode='round-robin',
        session_type='doubles',
        players=players,
        courts=2,
        banned_pairs=[]
    )
    print("✓ Config created")
    
    print("\nCreating session...")
    session = create_session(config)
    print(f"✓ Session created: {session.id}")
    
    print("\nSession details:")
    print(f"  - Mode: {session.config.mode}")
    print(f"  - Type: {session.config.session_type}")
    print(f"  - Players: {len(session.config.players)}")
    print(f"  - Courts: {session.config.courts}")
    print(f"  - Matches: {len(session.matches)}")
    print(f"  - Queue size: {len(session.match_queue)}")
    
    print("\n✓ ALL TESTS PASSED - Session creation works!")
    
except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
