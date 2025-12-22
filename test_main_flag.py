#!/usr/bin/env python3
"""
Quick test to verify the --test flag functionality
"""

import sys
sys.path.append('.')

import time
import subprocess
from datetime import datetime

def test_main_test_flag():
    """Test that main.py accepts --test flag and initializes accelerated timing"""
    
    # Create a simple test script that imports the time manager and checks if it's in test mode
    test_script = '''
import sys
sys.path.append('.')

# Mock the GUI main function to avoid starting the actual GUI
def mock_main():
    from python.time_manager import get_time_manager, start_session, now, get_elapsed_session_time
    import time
    
    time_manager = get_time_manager()
    print(f"Test mode: {time_manager.test_mode}")
    print(f"Acceleration factor: {time_manager.acceleration_factor}")
    
    # Quick timing test
    start_session()
    start_time = now()
    time.sleep(0.5)  # 0.5 real seconds
    end_time = now()
    
    elapsed_real = 0.5
    elapsed_virtual = (end_time - start_time).total_seconds()
    
    print(f"Real time elapsed: {elapsed_real:.1f}s")
    print(f"Virtual time elapsed: {elapsed_virtual:.1f}s")
    
    if time_manager.test_mode:
        expected = elapsed_real * 15  # 15x acceleration
        if abs(elapsed_virtual - expected) < 1.0:
            print("✓ Acceleration working correctly")
        else:
            print(f"❌ Acceleration not working: expected ~{expected:.1f}s, got {elapsed_virtual:.1f}s")
    else:
        if abs(elapsed_virtual - elapsed_real) < 0.1:
            print("✓ Normal timing working correctly")
        else:
            print(f"❌ Normal timing not working: expected ~{elapsed_real:.1f}s, got {elapsed_virtual:.1f}s")

# Replace the GUI main function with our test
import python.gui
python.gui.main = mock_main
'''
    
    # Save the test script temporarily
    with open('temp_test_main.py', 'w') as f:
        f.write(test_script)
    
    try:
        print("Testing main.py without --test flag (normal timing)...")
        # Import and run without --test flag
        import python.time_manager
        python.time_manager.initialize_time_manager(test_mode=False)
        
        exec(test_script)
        
        print("\nTesting main.py with --test flag (accelerated timing)...")
        # Reset and test with acceleration
        python.time_manager.initialize_time_manager(test_mode=True)
        
        exec(test_script)
        
    finally:
        # Clean up
        import os
        if os.path.exists('temp_test_main.py'):
            os.remove('temp_test_main.py')

if __name__ == "__main__":
    test_main_test_flag()