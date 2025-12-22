#!/usr/bin/env python3
"""
Final validation test for complete auto-sizing system including horizontal scrollbar fix
"""

import os

def test_complete_auto_sizing_system():
    """Test the complete auto-sizing system including all recent fixes"""
    
    print("🔍 Final Complete Auto-Sizing System Test")
    print("=" * 60)
    
    # Test all components
    tests = [
        ("test_waitlist_auto_sizing_validation.py", "Waitlist Auto-Sizing"),
        ("test_comprehensive_auto_sizing.py", "Comprehensive Auto-Sizing"),
        ("test_horizontal_scrollbar_fix.py", "Horizontal Scrollbar Fix"),
    ]
    
    all_passed = True
    
    for test_file, test_name in tests:
        print(f"\n📋 Running {test_name}...")
        
        if not os.path.exists(test_file):
            print(f"   ❌ Test file {test_file} not found")
            all_passed = False
            continue
            
        # Import and run the test
        try:
            if test_file == "test_waitlist_auto_sizing_validation.py":
                from test_waitlist_auto_sizing_validation import test_waitlist_auto_sizing_implementation, test_font_sizing_logic
                test_waitlist_auto_sizing_implementation()
                test_font_sizing_logic()
            elif test_file == "test_comprehensive_auto_sizing.py":
                from test_comprehensive_auto_sizing import test_comprehensive_auto_sizing
                test_comprehensive_auto_sizing()
            elif test_file == "test_horizontal_scrollbar_fix.py":
                from test_horizontal_scrollbar_fix import test_horizontal_scrollbar_fix, test_algorithm_logic
                test_horizontal_scrollbar_fix()
                test_algorithm_logic()
                
            print(f"   ✅ {test_name} passed")
            
        except Exception as e:
            print(f"   ❌ {test_name} failed: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL AUTO-SIZING TESTS PASSED!")
        print("\n📋 Complete System Summary:")
        print("   ✅ Active Courts Auto-Sizing: Working")
        print("   ✅ Waitlist Auto-Sizing: Working")
        print("   ✅ Horizontal Scrollbar Prevention: Working")
        print("   ✅ Dynamic Width/Height Adjustment: Working")
        print("   ✅ Font Size Optimization: Working")
        print("   ✅ Error Handling & Edge Cases: Working")
        print("\n🚀 Complete auto-sizing system is fully functional!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = test_complete_auto_sizing_system()
    exit(0 if success else 1)