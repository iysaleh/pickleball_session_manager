#!/usr/bin/env python3
"""
Test enhanced ELO ranking to verify Bill & Bob ranks higher than Ibraheem & Tony
"""

from python.kingofcourt import calculate_player_rating
from python.pickleball_types import PlayerStats

def test_enhanced_elo_ranking():
    """Test that enhanced ELO ranking properly considers point differential"""
    
    # Bill & Bob: 4-1 record, 53-21 points (+32 differential, +6.4 avg)
    bill_bob_stats = PlayerStats(
        player_id="bill_bob",
        games_played=5,
        wins=4,
        total_points_for=53,
        total_points_against=21
    )
    
    # Ibraheem & Tony: 4-1 record, 54-35 points (+19 differential, +3.8 avg)  
    ibraheem_tony_stats = PlayerStats(
        player_id="ibraheem_tony",
        games_played=5,
        wins=4,
        total_points_for=54,
        total_points_against=35
    )
    
    # Calculate ELO ratings
    bill_bob_elo = calculate_player_rating(bill_bob_stats)
    ibraheem_tony_elo = calculate_player_rating(ibraheem_tony_stats)
    
    print(f"Bill & Bob ELO: {bill_bob_elo:.2f}")
    print(f"Ibraheem & Tony ELO: {ibraheem_tony_elo:.2f}")
    print(f"Difference: {bill_bob_elo - ibraheem_tony_elo:.2f} points")
    
    # Verify Bill & Bob ranks higher due to better point differential
    assert bill_bob_elo > ibraheem_tony_elo, f"Bill & Bob ({bill_bob_elo:.2f}) should rank higher than Ibraheem & Tony ({ibraheem_tony_elo:.2f})"
    
    # Verify the difference is significant (more than 20 points)
    difference = bill_bob_elo - ibraheem_tony_elo
    assert difference > 20, f"Difference should be significant (>20 points), got {difference:.2f}"
    
    print("✅ Enhanced ELO ranking test PASSED!")
    print(f"✅ Bill & Bob correctly ranks higher by {difference:.1f} ELO points")
    print("✅ Point differential is now properly considered in Round-Robin mode")

if __name__ == "__main__":
    test_enhanced_elo_ranking()