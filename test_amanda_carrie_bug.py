"""
Test to reproduce and fix the Amanda + Carrie vs Carolyn + Dan bug

This test mimics the exact session state that allowed:
Amanda (rank #1, ELO 1894) + Carrie D (rank #4, ELO 1824) 
vs 
Carolyn (rank #19, ELO 1470) + Dan (rank #18, ELO 1477)

This is a terrible match - top 2 vs bottom 2 players!
With 20 players and 50% roaming range, Amanda can only play with ranks 1-10,
so Carolyn (rank 19) and Dan (rank 18) should NEVER be allowed in a match with Amanda.
"""
from python.session import Session
from python.pickleball_types import Player, SessionConfig, Match
from python.competitive_variety import (
    get_player_ranking,
    get_roaming_rank_range,
    can_all_players_play_together,
    populate_empty_courts_competitive_variety,
)
from python.utils import create_player_stats


def test_amanda_carrie_vs_carolyn_dan_bug():
    """
    Reproduce the exact bug where Amanda+Carrie played against Carolyn+Dan.
    This violates the 50% roaming range rule completely.
    """
    # Create 20 players with the exact ELO ratings from the problematic session
    player_data = [
        ("Amanda", 1894, 4, 0),
        ("Lisa K", 1885, 2, 0),
        ("Lee", 1867, 2, 0),
        ("Carrie D", 1824, 4, 1),
        ("Ibraheem", 1792, 3, 1),
        ("Jim K", 1777, 2, 1),
        ("Joshua", 1748, 2, 1),
        ("Andrew", 1748, 2, 1),
        ("Brandon", 1687, 1, 1),
        ("Patrick", 1683, 3, 3),
        ("Jeremy", 1575, 2, 2),
        ("Johnny", 1543, 1, 2),
        ("Julie", 1535, 1, 2),
        ("Tony", 1522, 1, 2),
        ("Ellie", 1508, 1, 3),
        ("Payton", 1501, 1, 3),
        ("Dan", 1477, 1, 3),
        ("Carolyn", 1470, 1, 3),
        ("Ralph", 1458, 1, 3),
        ("Lia", 1439, 1, 4),
    ]
    
    players = []
    for i, (name, elo, wins, losses) in enumerate(player_data):
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
    
    # Populate player stats to match the session
    for i, (name, elo, wins, losses) in enumerate(player_data):
        session.active_players.add(f"p{i}")
        stats = create_player_stats(f"p{i}")
        stats.games_played = wins + losses
        stats.wins = wins
        
        # Set point differentials to create the right ELO
        stats.total_points_for = 100 + (wins * 15)
        stats.total_points_against = 100 - (wins * 10) + (losses * 10)
        
        session.player_stats[f"p{i}"] = stats
    
    # Verify rankings
    print("Player Rankings and Roaming Ranges:")
    print("=" * 80)
    rankings = {}
    for i in range(20):
        rank, rating = get_player_ranking(session, f"p{i}")
        name = player_data[i][0]
        min_range, max_range = get_roaming_rank_range(session, f"p{i}")
        rankings[f"p{i}"] = rank
        print(f"Rank #{rank:2d}: {name:12s} (ELO {rating:7.1f}) -> Range {min_range:2d}-{max_range:2d}")
    
    # Verify Amanda and Carrie's rankings
    amanda_rank = rankings["p0"]
    carrie_rank = rankings["p3"]
    carolyn_rank = rankings["p17"]
    dan_rank = rankings["p16"]
    
    print("\n" + "=" * 80)
    print(f"PROBLEMATIC MATCH: Amanda (rank #{amanda_rank}) + Carrie (rank #{carrie_rank})")
    print(f"                  vs Carolyn (rank #{carolyn_rank}) + Dan (rank #{dan_rank})")
    print("=" * 80)
    
    # Check roaming ranges
    amanda_min, amanda_max = get_roaming_rank_range(session, "p0")
    print(f"\nAmanda's roaming range: #{amanda_min}-{amanda_max}")
    print(f"Carolyn is rank #{carolyn_rank} - OUTSIDE range? {carolyn_rank > amanda_max or carolyn_rank < amanda_min}")
    print(f"Dan is rank #{dan_rank} - OUTSIDE range? {dan_rank > amanda_max or dan_rank < amanda_min}")
    
    # Try to form the problematic match
    print(f"\nAttempting to form match: Amanda, Carrie vs Carolyn, Dan")
    match_players = ["p0", "p3", "p17", "p16"]  # Amanda, Carrie, Carolyn, Dan
    can_form = can_all_players_play_together(session, match_players)
    
    print(f"Can form match? {can_form}")
    print(f"Expected: False (should be rejected by roaming range)")
    
    if can_form:
        print("\n[FAIL] - The bug still exists! This match should NOT be allowed!")
        print("Roaming range enforcement is not working correctly.")
        return False
    else:
        print("\n[PASS] - The bug is fixed! This match is correctly rejected.")
        return True


if __name__ == "__main__":
    result = test_amanda_carrie_vs_carolyn_dan_bug()
    exit(0 if result else 1)
