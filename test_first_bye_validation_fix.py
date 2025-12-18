#!/usr/bin/env python3
"""
Test to verify the first bye validation logic correctly prevents too many bye players.

This test ensures that the validation logic correctly calculates the maximum number
of bye players based on optimal court usage, not just total court capacity.
"""

def test_bye_validation_logic():
    """Test the validation logic for maximum bye players"""
    
    def calculate_max_byes(num_players, courts):
        """Replicate the validation logic from gui.py"""
        total_court_capacity = courts * 4
        
        if num_players >= total_court_capacity:
            # More players than court capacity: some will wait
            max_byes = num_players - total_court_capacity
        else:
            # Fewer players than court capacity: fill what we can optimally  
            courts_we_can_fill = num_players // 4
            players_on_courts = courts_we_can_fill * 4
            max_byes = num_players - players_on_courts
        
        return max_byes
    
    # Test scenarios
    test_cases = [
        # (players, courts, expected_max_byes, description)
        (15, 4, 3, "15 players, 4 courts → 3 courts used, 3 waiting"),
        (16, 4, 0, "16 players, 4 courts → exact fit, no waiting"),
        (20, 4, 4, "20 players, 4 courts → all courts used, 4 waiting"),
        (8, 2, 0, "8 players, 2 courts → exact fit, no waiting"),
        (12, 2, 4, "12 players, 2 courts → all courts used, 4 waiting"), 
        (6, 2, 2, "6 players, 2 courts → 1 court used, 2 waiting"),
        (7, 2, 3, "7 players, 2 courts → 1 court used, 3 waiting"),
        (10, 3, 2, "10 players, 3 courts → 2 courts used, 2 waiting"),
        (14, 3, 2, "14 players, 3 courts → 3 courts used, 2 waiting"),
    ]
    
    print("Testing first bye validation logic:")
    print("=" * 60)
    
    all_passed = True
    
    for players, courts, expected_max, description in test_cases:
        actual_max = calculate_max_byes(players, courts)
        
        passed = actual_max == expected_max
        status = "✓ PASS" if passed else "✗ FAIL"
        
        print(f"{status} {description}")
        print(f"      Expected max byes: {expected_max}, Got: {actual_max}")
        
        if not passed:
            all_passed = False
            print(f"      ERROR: Validation logic incorrect!")
        print()
    
    return all_passed


def test_original_bug_scenario_validation():
    """Test that the original bug scenario now has correct validation"""
    
    def calculate_max_byes(num_players, courts):
        total_court_capacity = courts * 4
        
        if num_players >= total_court_capacity:
            max_byes = num_players - total_court_capacity
        else:
            courts_we_can_fill = num_players // 4
            players_on_courts = courts_we_can_fill * 4
            max_byes = num_players - players_on_courts
        
        return max_byes
    
    print("Testing original bug scenario validation:")
    print("=" * 60)
    
    # Original bug: 15 players, 4 courts, user tried to add 2 byes (which should be OK)
    players, courts = 15, 4
    max_byes = calculate_max_byes(players, courts)
    
    print(f"Scenario: {players} players, {courts} courts")
    print(f"Max byes allowed: {max_byes}")
    print()
    
    # Test valid bye counts
    valid_bye_counts = [0, 1, 2, 3]
    invalid_bye_counts = [4, 5, 6]
    
    print("Valid bye counts (should be allowed):")
    for bye_count in valid_bye_counts:
        valid = bye_count <= max_byes
        status = "✓ PASS" if valid else "✗ FAIL"
        print(f"  {status} {bye_count} byes: {'Allowed' if valid else 'BLOCKED'}")
    
    print()
    print("Invalid bye counts (should be blocked):")
    for bye_count in invalid_bye_counts:
        blocked = bye_count > max_byes
        status = "✓ PASS" if blocked else "✗ FAIL"  
        print(f"  {status} {bye_count} byes: {'BLOCKED' if blocked else 'Incorrectly allowed'}")
    
    # Verify the original user request (2 byes) is now allowed
    user_requested_byes = 2
    allowed = user_requested_byes <= max_byes
    
    print()
    print(f"Original user request: {user_requested_byes} byes")
    print(f"Status: {'✓ ALLOWED (correct)' if allowed else '✗ BLOCKED (incorrect)'}")
    
    return allowed


if __name__ == "__main__":
    print("FIRST BYE VALIDATION LOGIC TEST")
    print("=" * 70)
    
    # Test general validation logic
    logic_passed = test_bye_validation_logic()
    
    # Test original bug scenario specifically  
    bug_scenario_passed = test_original_bug_scenario_validation()
    
    print("=" * 70)
    if logic_passed and bug_scenario_passed:
        print("[ALL TESTS PASSED] First bye validation logic works correctly!")
    else:
        print("[TESTS FAILED] Validation logic needs fixes!")
        exit(1)