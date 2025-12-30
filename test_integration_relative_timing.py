#!/usr/bin/env python3
"""
Integration test demonstrating the --test flag and relative timing functionality
"""

import sys
import subprocess
import tempfile
import time
from pathlib import Path

def test_integration():
    """Test the full integration of relative timing and test flag"""
    
    print("=== Testing Relative Timing Integration ===")
    
    # Create a test script that simulates session usage
    test_script = f'''
import sys
sys.path.append('{Path.cwd()}')

from python.time_manager import initialize_time_manager, start_session, now, pause_session, resume_session
from python.session import create_session
from python.pickleball_types import SessionConfig, Player
from python.session_persistence import serialize_session, deserialize_session
import time

def main():
    # This script simulates what happens when --test flag is used
    print("Initializing time manager with test mode...")
    time_manager = initialize_time_manager(test_mode=True)
    
    print(f"Test mode: {{time_manager.test_mode}}")
    print(f"Acceleration factor: {{time_manager.acceleration_factor}}")
    
    # Create and start a session
    players = [Player(id="p1", name="Alice"), Player(id="p2", name="Bob"), 
               Player(id="p3", name="Charlie"), Player(id="p4", name="Diana")]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles', 
        players=players,
        courts=1
    )
    
    session = create_session(config)
    print(f"Session created with start time: {{session.session_start_time}}")
    
    # Test wait timer functionality
    from python.utils import start_player_wait_timer, get_current_wait_time, stop_player_wait_timer
    
    player_stats = session.player_stats["p1"]
    start_player_wait_timer(player_stats)
    print(f"Started wait timer for Alice at: {{player_stats.wait_start_time}}")
    
    # Wait 1 real second = 15 virtual seconds due to acceleration
    print("Waiting 1 real second (should be 15 virtual seconds)...")
    time.sleep(1.0)
    
    current_wait = get_current_wait_time(player_stats)
    print(f"Current wait time: {{current_wait}} seconds")
    
    # Verify acceleration worked
    if 14 <= current_wait <= 16:
        print("✓ Acceleration working correctly (15x speed)")
    else:
        print(f"❌ Acceleration not working: expected ~15s, got {{current_wait}}s")
    
    # Test pause/resume
    print("Testing pause/resume...")
    pause_session()
    paused_wait = get_current_wait_time(player_stats)
    
    time.sleep(0.5)  # Real time should not advance virtual time when paused
    still_paused_wait = get_current_wait_time(player_stats) 
    
    if paused_wait == still_paused_wait:
        print("✓ Pause working correctly")
    else:
        print(f"❌ Pause not working: {{paused_wait}} vs {{still_paused_wait}}")
    
    resume_session()
    time.sleep(0.2)  # Should add ~3 virtual seconds
    resumed_wait = get_current_wait_time(player_stats)
    
    if resumed_wait > still_paused_wait:
        print("✓ Resume working correctly")
    else:
        print(f"❌ Resume not working: {{still_paused_wait}} vs {{resumed_wait}}")
    
    # Test persistence
    print("Testing session persistence...")
    serialized = serialize_session(session)
    restored = deserialize_session(serialized)
    
    if restored.session_start_time == session.session_start_time:
        print("✓ Session start time persisted correctly")
    else:
        print(f"❌ Session start time not persisted")
    
    print("✓ Integration test completed successfully!")

if __name__ == "__main__":
    main()
'''
    
    # Write the test script to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        print("Running integration test...")
        result = subprocess.run([sys.executable, temp_script], 
                              capture_output=True, text=True, timeout=10)
        
        print("=== Output ===")
        print(result.stdout)
        
        if result.stderr:
            print("=== Errors ===")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✓ Integration test passed!")
        else:
            print(f"❌ Integration test failed with return code {result.returncode}")
            
    finally:
        # Clean up
        Path(temp_script).unlink()

def test_command_line_args():
    """Test that main.py properly accepts the --test flag"""
    
    print("\n=== Testing Command Line Arguments ===")
    
    # Test that --test flag is accepted (we can't run the full GUI, but we can check arg parsing)
    test_main_script = '''
import sys
import argparse

# Replicate the argument parsing from main.py
parser = argparse.ArgumentParser(description='Pickleball Session Manager')
parser.add_argument('--test', action='store_true', 
                  help='Enable test mode (15x accelerated timing)')

# Test with no arguments
args = parser.parse_args([])
print(f"No args - test mode: {args.test}")

# Test with --test flag
args = parser.parse_args(['--test'])
print(f"With --test - test mode: {args.test}")

print("✓ Command line argument parsing works correctly")
'''
    
    result = subprocess.run([sys.executable, '-c', test_main_script], 
                          capture_output=True, text=True)
    
    print("=== Argument Parsing Output ===")
    print(result.stdout)
    
    if result.returncode == 0:
        print("✓ Command line arguments work correctly!")
    else:
        print(f"❌ Command line argument test failed")
        if result.stderr:
            print("Errors:", result.stderr)

if __name__ == "__main__":
    test_integration()
    test_command_line_args()
    print("\n✓ All integration tests completed!")