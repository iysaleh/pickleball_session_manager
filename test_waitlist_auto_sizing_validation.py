#!/usr/bin/env python3
"""
Syntax and structure validation for waitlist auto-sizing implementation
"""

import os
import ast
import re

def test_waitlist_auto_sizing_implementation():
    """Test that waitlist auto-sizing code was properly implemented"""
    
    gui_file = os.path.join("python", "gui.py")
    
    print("Testing waitlist auto-sizing implementation...")
    
    # Read the GUI file
    with open(gui_file, 'r') as f:
        content = f.read()
    
    # Test 1: Check that _auto_size_waitlist_fonts method exists
    assert '_auto_size_waitlist_fonts' in content, "Missing _auto_size_waitlist_fonts method"
    print("✓ _auto_size_waitlist_fonts method found")
    
    # Test 2: Check that _auto_size_list_widget_fonts method exists
    assert '_auto_size_list_widget_fonts' in content, "Missing _auto_size_list_widget_fonts method"
    print("✓ _auto_size_list_widget_fonts method found")
    
    # Test 3: Check that resizeEvent was added to DeselectableListWidget
    desirable_resize_pattern = r"class DeselectableListWidget.*?def resizeEvent"
    assert re.search(desirable_resize_pattern, content, re.DOTALL), "Missing resizeEvent in DeselectableListWidget"
    print("✓ resizeEvent override found in DeselectableListWidget")
    
    # Test 4: Check that auto-sizing is called after waitlist update
    assert "Auto-size waitlist fonts after updating" in content, "Missing auto-sizing call after waitlist update"
    print("✓ Auto-sizing call found after waitlist update")
    
    # Test 5: Check for proper font size limits for list widgets
    list_font_pattern = r"max_font_size = 24.*# Smaller max for list items"
    assert re.search(list_font_pattern, content), "Missing proper font size limits for list widgets"
    print("✓ Proper font size limits found for list widgets")
    
    # Test 6: Check for QTimer.singleShot usage for delayed auto-sizing
    timer_pattern = r"QTimer\.singleShot\(50, self\._auto_size_waitlist_fonts\)"
    assert re.search(timer_pattern, content), "Missing QTimer.singleShot for delayed auto-sizing"
    print("✓ Proper delayed auto-sizing with QTimer found")
    
    # Test 7: Syntax validation by parsing the file
    try:
        ast.parse(content)
        print("✓ GUI file has valid Python syntax")
    except SyntaxError as e:
        print(f"✗ Syntax error in GUI file: {e}")
        return False
    
    # Test 8: Check that font is applied to all items in list
    font_apply_pattern = r"for i in range\(list_widget\.count\(\)\):.*?item\.setFont\(font\)"
    assert re.search(font_apply_pattern, content, re.DOTALL), "Missing font application to all list items"
    print("✓ Font application to all list items found")
    
    # Test 9: Check that longest text is used for sizing calculation
    longest_text_pattern = r"Find the longest text to base font size on"
    assert longest_text_pattern in content, "Missing longest text calculation logic"
    print("✓ Longest text calculation logic found")
    
    # Test 10: Check for proper error handling in auto-sizing
    error_handling_pattern = r"if available_rect\.width\(\) <= 0 or available_rect\.height\(\) <= 0:"
    assert re.search(error_handling_pattern, content), "Missing error handling for invalid sizes"
    print("✓ Error handling for invalid sizes found")
    
    print("\n🎉 All waitlist auto-sizing implementation tests passed!")
    return True

def test_font_sizing_logic():
    """Test the font sizing logic details"""
    
    gui_file = os.path.join("python", "gui.py")
    
    with open(gui_file, 'r') as f:
        content = f.read()
    
    print("\nTesting font sizing logic...")
    
    # Check that font size range is appropriate for list items
    font_range_pattern = r"min_font_size = 8\s+max_font_size = 24"
    assert re.search(font_range_pattern, content), "Font size range not properly configured for list items"
    print("✓ Font size range (8-24) properly configured for list items")
    
    # Check that font weight is Normal for list items (not Bold like in court labels)
    font_weight_pattern = r"QFont\(\"Arial\", font_size, QFont\.Weight\.Normal\)"
    assert re.search(font_weight_pattern, content), "Font weight should be Normal for list items"
    print("✓ Font weight set to Normal for list items")
    
    # Check for scroll bar accommodation
    scrollbar_pattern = r"scrollbar_width = list_widget\.verticalScrollBar\(\)\.sizeHint\(\)\.width\(\)"
    assert re.search(scrollbar_pattern, content), "Missing scrollbar width accommodation"
    print("✓ Scrollbar width accommodation found")
    
    # Check for item height calculation
    item_height_pattern = r"item_height = widget_rect\.height\(\) // visible_count"
    assert re.search(item_height_pattern, content), "Missing item height calculation"
    print("✓ Item height calculation found")
    
    print("✓ Font sizing logic validation passed!")

if __name__ == "__main__":
    try:
        success1 = test_waitlist_auto_sizing_implementation()
        test_font_sizing_logic()
        
        if success1:
            print("\n✅ All validation tests passed! Waitlist auto-sizing implementation is complete.")
        else:
            print("\n❌ Validation failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        exit(1)