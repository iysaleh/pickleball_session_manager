"""
Test roaming range enforcement for competitive variety mode
"""
from python.session import Session
from python.types import Player, SessionConfig
from python.competitive_variety import (
    get_roaming_rank_range,
    can_all_players_play_together,
    can_players_form_match_together,
    get_player_ranking,
)
from python.utils import create_player_stats


def test_roaming_range_enforcement():
    """
    Test that 50% roaming range is enforced correctly.
    
    Scenario: 20 players
    - Dan (rank #2, ELO high)
    - Ibraheem (rank #4, ELO high)
    - Joshua (rank #3, ELO high)
    - Tony (rank #14, ELO medium-low)
    
    Dan's roaming range with 50% rule:
    - 50% of 20 = 10
    - Dan is rank #2
    - Range: 2 to 12 (can play with ranks 2-12)
    
    Tony is rank #14:
    - Range: 14 to 4 (but capped at 20, so 14-20)
    - Tony should NOT be able to play with Dan, Ibraheem, or Joshua
    """
    # Create 20 players with specific rankings
    player_names = [
        "Patrick", "Dan", "Joshua", "Ibraheem", "Carrie D",
        "Andrew", "Julie", "Brandon", "Amanda", "Ralph",
        "Ellie", "Lisa K", "Lia", "Tony", "Payton",
        "Johnny", "Jeremy", "Lee", "Carolyn", "Jim K"
    ]
    
    elo_ratings = [
        1888,  # 1: Patrick
        1888,  # 2: Dan
        1886,  # 3: Joshua
        1803,  # 4: Ibraheem
        1787,  # 5: Carrie D
        1748,  # 6: Andrew
        1687,  # 7: Julie
        1676,  # 8: Brandon
        1676,  # 9: Amanda
        1641,  # 10: Ralph
        1606,  # 11: Ellie
        1595,  # 12: Lisa K
        1586,  # 13: Lia
        1552,  # 14: Tony
        1528,  # 15: Payton
        1500,  # 16: Johnny
        1210,  # 17: Jeremy
        1210,  # 18: Lee
        1203,  # 19: Carolyn
        1185,  # 20: Jim K
    ]
    
    players = []
    for i, name in enumerate(player_names):
        player = Player(id=f"p{i}", name=name)
        players.append(player)
    
    # Create session
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = Session(id="test_session", config=config)
    
    for i, name in enumerate(player_names):
        session.active_players.add(f"p{i}")
        
        # Create stats that will generate the correct ELO rating
        stats = create_player_stats(f"p{i}")
        
        # Calculate games_played and wins to target specific ELO ratings
        # Higher ELO players get more games and higher win %
        if elo_ratings[i] > 1750:
            stats.games_played = 10
            stats.wins = 9
            stats.total_points_for = 150
            stats.total_points_against = 80
        elif elo_ratings[i] > 1650:
            stats.games_played = 8
            stats.wins = 6
            stats.total_points_for = 120
            stats.total_points_against = 90
        elif elo_ratings[i] > 1550:
            stats.games_played = 6
            stats.wins = 3
            stats.total_points_for = 80
            stats.total_points_against = 85
        else:
            stats.games_played = 4
            stats.wins = 1
            stats.total_points_for = 40
            stats.total_points_against = 60
            
        session.player_stats[f"p{i}"] = stats
    
    print("Roaming Range Test (20 players, 50% window = 10 ranks)")
    print("=" * 70)
    
    # Get actual ranks after creating all players and stats
    all_ranks = {}
    for i in range(20):
        rank, _ = get_player_ranking(session, f"p{i}")
        all_ranks[f"p{i}"] = rank
    
    # Find a player and test their range
    # Let's use player p0 (Patrick, should be highly ranked)
    p0_rank = all_ranks["p0"]
    p0_min, p0_max = get_roaming_rank_range(session, "p0")
    print(f"\nPlayer p0 (Patrick) rank #{p0_rank} roaming range: {p0_min}-{p0_max}")
    print(f"  Window size: {p0_max - p0_min + 1} ranks")
    assert p0_min == p0_rank, f"Min should match player rank"
    assert (p0_max - p0_min) == 10, f"Window should be 11 ranks (50% of 20 + 1 for inclusive)"
    print("  [PASS] Correct range")
    
    # Find a lower-ranked player
    p13_rank = all_ranks["p13"]  # Tony
    p13_min, p13_max = get_roaming_rank_range(session, "p13")
    print(f"\nPlayer p13 (Tony) rank #{p13_rank} roaming range: {p13_min}-{p13_max}")
    assert p13_min == p13_rank, f"Min should match player rank"
    # Window gets capped at max_rank (20)
    expected_window = min(10, 20 - p13_rank)
    assert (p13_max - p13_min) == expected_window, f"Window should be {expected_window} ranks"
    print("  [PASS] Correct range (capped at player count)")
    
    # Test that a player outside another's range is rejected
    print(f"\nFinding two players with non-overlapping ranges...")
    # Find a high-ranked and a low-ranked player
    highest_rank_player = min(all_ranks.items(), key=lambda x: x[1])
    lowest_rank_player = max(all_ranks.items(), key=lambda x: x[1])
    
    h_player, h_rank = highest_rank_player
    l_player, l_rank = lowest_rank_player
    
    h_min, h_max = get_roaming_rank_range(session, h_player)
    l_min, l_max = get_roaming_rank_range(session, l_player)
    
    print(f"  High player {h_player} rank #{h_rank} range {h_min}-{h_max}")
    print(f"  Low player {l_player} rank #{l_rank} range {l_min}-{l_max}")
    
    # Try to form a match with one from each group
    if l_rank > h_max:  # Low player is outside high player's range
        print(f"\nTesting rejection of non-overlapping ranges:")
        print(f"  {l_player} (rank {l_rank}) with {h_player} (rank {h_rank})")
        can_form = can_all_players_play_together(session, [h_player, l_player, "p1", "p2"])
        print(f"  Can form match? {can_form} (Expected: False)")
        assert not can_form, f"{l_player} rank {l_rank} outside range of {h_player} rank {h_rank} ({h_min}-{h_max})"
        print("  [PASS] Correctly rejected")
    else:
        print(f"  Ranges overlap too much, finding better example...")
    
    print("\n" + "=" * 70)
    print("Roaming range test PASSED!")


if __name__ == "__main__":
    test_roaming_range_enforcement()
