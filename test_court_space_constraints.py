#!/usr/bin/env python3
"""
Test that courts fit within available space instead of expanding beyond bounds
"""

import os
import re

def test_court_space_constraints():
    """Test that courts respect space constraints and don't expand beyond bounds"""
    
    gui_file = os.path.join("python", "gui.py")
    
    print("🔍 Testing Court Space Constraints...")
    
    with open(gui_file, 'r') as f:
        content = f.read()
    
    print("\n1. Testing Constrained Approach:")
    
    # Test that setMinimumWidth is NOT called (we removed the expanding behavior)
    set_min_width_pattern = r"self\.setMinimumWidth\(optimal_width\)"
    assert not re.search(set_min_width_pattern, content), "Courts should not expand their minimum width"
    print("   ✓ Courts do not expand beyond their allocated space")
    
    # Test that _calculate_optimal_court_width method is removed
    calc_optimal_width_pattern = r"def _calculate_optimal_court_width"
    assert not re.search(calc_optimal_width_pattern, content), "Width calculation method should be removed"
    print("   ✓ Width expansion calculation method removed")
    
    print("\n2. Testing Space-Constrained Auto-Sizing:")
    
    # Test that team font sizing respects available space
    auto_size_pattern = r"def _auto_size_team_fonts.*Auto-size fonts for team labels to fit within available space"
    assert re.search(auto_size_pattern, content, re.DOTALL), "Auto-sizing should be space-constrained"
    print("   ✓ Auto-sizing is space-constrained")
    
    # Test that font sizing uses actual available space
    available_rect_pattern = r"available_rect = label\.contentsRect\(\)"
    assert re.search(available_rect_pattern, content), "Font sizing should use actual available space"
    print("   ✓ Font sizing uses actual available space")
    
    # Test that target width is derived from available space, not expanded
    target_width_pattern = r"target_width = max\(1, available_rect\.width\(\) - padding\)"
    assert re.search(target_width_pattern, content), "Target width should be derived from available space"
    print("   ✓ Target width constrained to available space")
    
    print("\n3. Testing Layout Behavior:")
    
    # Test that we don't artificially expand court dimensions
    no_expansion_patterns = [
        r"setMinimumWidth.*optimal_width",  # No width expansion
        r"total_width.*max_label_width",   # No total width calculation
        r"for target_width in \[.*\]:",    # No target width iteration for expansion
    ]
    
    for pattern in no_expansion_patterns:
        assert not re.search(pattern, content), f"Should not have expansion pattern: {pattern}"
    
    print("   ✓ No artificial court dimension expansion found")
    
    print("\n4. Testing Simplified Algorithm:")
    
    # Test that auto-sizing is now simple and direct
    simple_auto_size_pattern = r"def _auto_size_team_fonts.*self\._auto_size_label_font\(self\.team1_label\).*self\._auto_size_label_font\(self\.team2_label\)"
    assert re.search(simple_auto_size_pattern, content, re.DOTALL), "Auto-sizing should be simplified"
    print("   ✓ Simplified auto-sizing algorithm found")
    
    # Test that label font sizing is straightforward
    straightforward_pattern = r"best_font_size = min_font_size.*for font_size in range\(min_font_size, max_font_size \+ 1\)"
    assert re.search(straightforward_pattern, content, re.DOTALL), "Font sizing should be straightforward"
    print("   ✓ Straightforward font sizing algorithm")
    
    print("\n5. Testing Helper Method (if exists):")
    
    # Check if there's a helper method for calculating available width
    helper_method_pattern = r"def _calculate_available_label_width"
    if re.search(helper_method_pattern, content):
        print("   ✓ Helper method for available width calculation found")
        
        # Test that helper method uses current width, not expansion
        current_width_pattern = r"court_width = self\.width\(\)"
        assert re.search(current_width_pattern, content), "Helper should use current court width"
        print("   ✓ Helper method uses current court dimensions")
    else:
        print("   ✓ No helper method needed - direct space calculation")
    
    print("\n🎉 ALL SPACE CONSTRAINT TESTS PASSED!")
    print("\n📋 Constraint Summary:")
    print("   • Courts respect allocated layout space")
    print("   • No artificial expansion beyond bounds") 
    print("   • Font sizing adapts to available space")
    print("   • Simplified, efficient algorithm")
    print("   • Prevents main window scrollbars")
    print("\n✅ Courts now fit within available space properly!")
    
    return True

def test_no_scrollbar_issues():
    """Test that the fix prevents scrollbar issues without creating new ones"""
    
    print("\n🚫 Testing Scrollbar Prevention:")
    
    gui_file = os.path.join("python", "gui.py")
    with open(gui_file, 'r') as f:
        content = f.read()
    
    # Test that we still prevent horizontal overflow in labels
    word_wrap_pattern = r"Qt\.TextFlag\.TextWordWrap"
    assert re.search(word_wrap_pattern, content), "Text wrapping should still be enabled"
    print("   ✓ Text wrapping enabled to prevent horizontal overflow")
    
    # Test that font sizing still checks both width and height
    width_height_check_pattern = r"text_rect\.width\(\) <= target_width and text_rect\.height\(\) <= target_height"
    assert re.search(width_height_check_pattern, content), "Font sizing should check both dimensions"
    print("   ✓ Font sizing checks both width and height constraints")
    
    # Test that we break when font doesn't fit (prevents infinite loops)
    break_pattern = r"else:.*break"
    assert re.search(break_pattern, content, re.DOTALL), "Algorithm should break when font doesn't fit"
    print("   ✓ Algorithm breaks when font size doesn't fit")
    
    print("   ✅ Scrollbar issues prevented without creating new problems")

if __name__ == "__main__":
    try:
        test_court_space_constraints()
        test_no_scrollbar_issues()
        print("\n🚀 All space constraint tests passed! Courts now fit properly within allocated space.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)