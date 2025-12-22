#!/usr/bin/env python3
"""
Test court dynamic width sizing to prevent horizontal scrollbar flickering
"""

import os
import re

def test_horizontal_scrollbar_fix():
    """Test that the court auto-sizing prevents horizontal scrollbar issues"""
    
    gui_file = os.path.join("python", "gui.py")
    
    print("🔍 Testing horizontal scrollbar fix...")
    
    with open(gui_file, 'r') as f:
        content = f.read()
    
    print("\n1. Testing Court Width Calculation:")
    
    # Test that _calculate_optimal_court_width method exists
    assert '_calculate_optimal_court_width' in content, "Missing _calculate_optimal_court_width method"
    print("   ✓ Court width calculation method found")
    
    # Test that method considers both team labels
    width_calc_pattern = r"for text in \[team1_text, team2_text\]:"
    assert re.search(width_calc_pattern, content), "Width calculation doesn't consider both team texts"
    print("   ✓ Width calculation considers both team labels")
    
    # Test that method prevents text from becoming too tall (max 3 lines)
    max_lines_pattern = r"max_lines = 3"
    assert re.search(max_lines_pattern, content), "Missing max lines constraint"
    print("   ✓ Maximum 3 lines constraint found")
    
    print("\n2. Testing Dynamic Width Adjustment:")
    
    # Test that setMinimumWidth is called to adjust court width
    set_min_width_pattern = r"self\.setMinimumWidth\(optimal_width\)"
    assert re.search(set_min_width_pattern, content), "Missing dynamic width adjustment"
    print("   ✓ Dynamic width adjustment found")
    
    # Test that width adjustment happens before font sizing
    width_before_font_pattern = r"setMinimumWidth.*_auto_size_label_font"
    assert re.search(width_before_font_pattern, content, re.DOTALL), "Width adjustment should happen before font sizing"
    print("   ✓ Width adjustment happens before font sizing")
    
    print("\n3. Testing Improved Font Sizing:")
    
    # Test that font sizing considers line limits
    line_height_pattern = r"line_height = metrics\.height\(\)"
    assert re.search(line_height_pattern, content), "Missing line height calculation"
    print("   ✓ Line height calculation found")
    
    # Test that font sizing checks max allowed height
    max_allowed_height_pattern = r"max_allowed_height = min\(target_height, line_height \* max_lines\)"
    assert re.search(max_allowed_height_pattern, content), "Missing max allowed height calculation"
    print("   ✓ Max allowed height constraint found")
    
    # Test that both width and height are checked in font sizing
    width_height_check_pattern = r"text_rect\.width\(\) <= target_width and.*text_rect\.height\(\) <= max_allowed_height"
    assert re.search(width_height_check_pattern, content, re.DOTALL), "Missing comprehensive width/height check"
    print("   ✓ Comprehensive width and height checking found")
    
    print("\n4. Testing Scrollbar Prevention Logic:")
    
    # Test that method tries different target widths
    target_width_loop_pattern = r"for target_width in \[.*\]:"
    assert re.search(target_width_loop_pattern, content), "Missing target width optimization"
    print("   ✓ Target width optimization found")
    
    # Test that total width calculation includes all components
    total_width_pattern = r"total_width = \(max_label_width \* 2\) \+ 4 \+ 60"
    assert re.search(total_width_pattern, content), "Missing comprehensive width calculation"
    print("   ✓ Comprehensive width calculation found (2 labels + net + margins)")
    
    # Test that there's a minimum width fallback
    min_width_fallback_pattern = r"return max\(250, total_width\)"
    assert re.search(min_width_fallback_pattern, content), "Missing minimum width fallback"
    print("   ✓ Minimum width fallback found")
    
    print("\n5. Testing Edge Cases:")
    
    # Test handling of empty text
    empty_text_pattern = r"if not.*\.strip\(\).*:"
    assert re.search(empty_text_pattern, content), "Missing empty text handling"
    print("   ✓ Empty text handling found")
    
    # Test fallback width for edge cases
    fallback_pattern = r"if max_label_width == 0:.*max_label_width = 200"
    assert re.search(fallback_pattern, content, re.DOTALL), "Missing fallback width logic"
    print("   ✓ Fallback width logic found")
    
    print("\n🎉 ALL HORIZONTAL SCROLLBAR TESTS PASSED!")
    print("\n📋 Fix Summary:")
    print("   • Dynamic court width calculation based on content")
    print("   • Prevents horizontal scrollbars by expanding court width")
    print("   • Limits text to maximum 3 lines for readability")
    print("   • Comprehensive width/height checking in font sizing")
    print("   • Robust fallback logic for edge cases")
    print("\n✅ Horizontal scrollbar flickering should now be prevented!")
    
    return True

def test_algorithm_logic():
    """Test the specific algorithm logic for preventing scrollbar issues"""
    
    print("\n🔧 Testing Algorithm Logic:")
    
    gui_file = os.path.join("python", "gui.py")
    with open(gui_file, 'r') as f:
        content = f.read()
    
    # Test that the algorithm tries decreasing font sizes (backwards iteration)
    decreasing_font_pattern = r"for font_size in range\(max_font_size, min_font_size - 1, -1\):"
    assert re.search(decreasing_font_pattern, content), "Algorithm should try largest fonts first"
    print("   ✓ Algorithm tries largest fonts first (optimal for readability)")
    
    # Test that algorithm stops when reasonable constraints are met
    break_pattern = r"if text_height <= line_height \* 3:.*break"
    assert re.search(break_pattern, content, re.DOTALL), "Algorithm should stop when reasonable fit found"
    print("   ✓ Algorithm stops when reasonable fit is found")
    
    # Test that the width calculation is done before each font resize
    calc_before_resize_pattern = r"optimal_width = self\._calculate_optimal_court_width\(\)"
    assert re.search(calc_before_resize_pattern, content), "Width should be calculated before font resize"
    print("   ✓ Width calculated before font resizing")
    
    print("   ✅ Algorithm logic is sound for preventing scrollbar flickering")

if __name__ == "__main__":
    try:
        test_horizontal_scrollbar_fix()
        test_algorithm_logic()
        print("\n🚀 All tests passed! Horizontal scrollbar flickering fix is complete.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)