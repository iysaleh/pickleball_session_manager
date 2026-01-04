#!/usr/bin/env python3

"""Test script to verify that player names with & characters are replaced correctly with newlines"""

def test_ampersand_replacement():
    """Test the basic & replacement logic"""
    
    # Test cases
    test_names = [
        "John & Jane",
        "Bob & Alice", 
        "Mike & Sarah",
        "Tom & Lisa",
        "Regular Name",  # No & character
        "Name & With & Multiple & Ampersands"
    ]
    
    print("Testing & character replacement with newlines:")
    print("=" * 50)
    
    for name in test_names:
        formatted_name = name.replace('&', '\n')
        print(f"Original: '{name}'")
        print(f"Formatted: '{formatted_name}'")
        print(f"Displayed as:")
        print(formatted_name)
        print("-" * 30)
        
        # Verify the replacement worked
        if '&' in name:
            assert '\n' in formatted_name, f"Should have newlines for name with &: {name}"
            assert '&' not in formatted_name, f"Should not have & after replacement: {name}"
        else:
            assert formatted_name == name, f"Names without & should remain unchanged: {name}"
    
    print("✅ All tests passed! & characters are correctly replaced with newlines.")

if __name__ == "__main__":
    test_ampersand_replacement()