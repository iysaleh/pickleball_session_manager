#!/usr/bin/env python3
"""
Final comprehensive validation test for auto-sizing functionality
"""

import os
import re

def test_comprehensive_auto_sizing():
    """Test that both court and waitlist auto-sizing are properly implemented"""
    
    gui_file = os.path.join("python", "gui.py")
    
    print("🔍 Testing comprehensive auto-sizing functionality...")
    
    with open(gui_file, 'r') as f:
        content = f.read()
    
    print("\n1. Testing Court Auto-Sizing (Existing):")
    
    # Test court auto-sizing methods exist in CourtWidget
    assert '_auto_size_team_fonts' in content, "Missing _auto_size_team_fonts method for courts"
    print("   ✓ Court team font auto-sizing method found")
    
    assert '_auto_size_label_font' in content, "Missing _auto_size_label_font method for courts"
    print("   ✓ Court label font auto-sizing method found")
    
    # Test court auto-sizing font range (8-72 for courts)
    court_font_range = r"min_font_size = 8\s+max_font_size = 72"
    assert re.search(court_font_range, content), "Court font range not found"
    print("   ✓ Court font range (8-72) properly configured")
    
    # Test court font weight is Bold
    court_font_weight = r"QFont\(\"Arial\", font_size, QFont\.Weight\.Bold\)"
    assert re.search(court_font_weight, content), "Court font weight not Bold"
    print("   ✓ Court font weight set to Bold")
    
    print("\n2. Testing Waitlist Auto-Sizing (New):")
    
    # Test waitlist auto-sizing methods exist in SessionWindow
    assert '_auto_size_waitlist_fonts' in content, "Missing _auto_size_waitlist_fonts method"
    print("   ✓ Waitlist auto-sizing method found")
    
    assert '_auto_size_list_widget_fonts' in content, "Missing _auto_size_list_widget_fonts method"
    print("   ✓ List widget auto-sizing method found")
    
    # Test waitlist auto-sizing font range (8-24 for lists)
    list_font_range = r"min_font_size = 8\s+max_font_size = 24.*# Smaller max for list items"
    assert re.search(list_font_range, content), "List font range not found"
    print("   ✓ List font range (8-24) properly configured")
    
    # Test waitlist font weight is Normal
    list_font_weight = r"QFont\(\"Arial\", font_size, QFont\.Weight\.Normal\)"
    assert re.search(list_font_weight, content), "List font weight not Normal"
    print("   ✓ List font weight set to Normal")
    
    print("\n3. Testing Integration:")
    
    # Test waitlist auto-sizing is called after updates
    auto_size_call = r"QTimer\.singleShot\(50, self\._auto_size_waitlist_fonts\)"
    assert re.search(auto_size_call, content), "Auto-sizing call not found after waitlist update"
    print("   ✓ Auto-sizing triggered after waitlist updates")
    
    # Test resize event handling
    resize_event = r"def resizeEvent.*_auto_size_waitlist_fonts"
    assert re.search(resize_event, content, re.DOTALL), "Resize event handling not found"
    print("   ✓ Resize event handling for waitlist found")
    
    print("\n4. Testing Method Placement:")
    
    # Verify methods are in correct classes
    # Find SessionWindow class boundaries
    session_window_start = content.find("class SessionWindow(QMainWindow):")
    next_class_start = content.find("\nclass ", session_window_start + 1)
    if next_class_start == -1:
        session_window_content = content[session_window_start:]
    else:
        session_window_content = content[session_window_start:next_class_start]
    
    assert '_auto_size_waitlist_fonts' in session_window_content, "Waitlist auto-sizing not in SessionWindow class"
    print("   ✓ Waitlist auto-sizing methods in SessionWindow class")
    
    # Find CourtDisplayWidget class boundaries  
    court_widget_start = content.find("class CourtDisplayWidget(QWidget):")
    next_class_after_court = content.find("\nclass ", court_widget_start + 1)
    if next_class_after_court == -1:
        court_widget_content = content[court_widget_start:]
    else:
        court_widget_content = content[court_widget_start:next_class_after_court]
    
    assert '_auto_size_team_fonts' in court_widget_content, "Court auto-sizing not in CourtDisplayWidget class"
    print("   ✓ Court auto-sizing methods in CourtDisplayWidget class")
    
    print("\n5. Testing Error Handling:")
    
    # Check for proper error handling
    error_patterns = [
        r"if.*width\(\) <= 0 or.*height\(\) <= 0:",  # Size validation
        r"if not.*\.strip\(\):",  # Text validation  
        r"QTimer\.singleShot\(.*lambda:",  # Retry mechanism
    ]
    
    for pattern in error_patterns:
        assert re.search(pattern, content), f"Error handling pattern not found: {pattern}"
    print("   ✓ Error handling patterns found")
    
    print("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
    print("\n📋 Summary:")
    print("   • Court auto-sizing: Bold fonts, 8-72pt range, for team labels")
    print("   • Waitlist auto-sizing: Normal fonts, 8-24pt range, for list items")
    print("   • Automatic triggers: Resize events and content updates")
    print("   • Proper class placement: SessionWindow vs CourtDisplayWidget")
    print("   • Robust error handling: Size validation and retry logic")
    print("\n✅ Both Active Courts and Waitlist now have auto-sizing fonts!")
    
    return True

if __name__ == "__main__":
    try:
        test_comprehensive_auto_sizing()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)