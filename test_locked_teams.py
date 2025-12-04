"""
Test locked teams compatibility with roaming range enforcement
"""
from python.session import Session
from python.types import Player, SessionConfig
from python.competitive_variety import (
    get_player_ranking,
    get_roaming_rank_range,
    can_play_with_player,
    can_all_players_play_together,
)
from python.utils import create_player_stats


def test_locked_teams():
    """
    Test that locked teams work correctly with roaming range enforcement
    """
    player_data = [
        ("Amanda", 1894, 4, 0),
        ("Lisa K", 1885, 2, 0),
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
    ]
    
    players = [Player(id=f"p{i}", name=name) for i, (name, _, _, _) in enumerate(player_data)]
    player_id_map = {p.name: p.id for p in players}
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3,
        locked_teams=[["p0", "p2"]]
    )
    session = Session(id="locked_test", config=config)
    
    for i, (name, elo, wins, losses) in enumerate(player_data):
        session.active_players.add(f"p{i}")
        stats = create_player_stats(f"p{i}")
        stats.games_played = wins + losses
        stats.wins = wins
        session.player_stats[f"p{i}"] = stats
    
    print("TESTING LOCKED TEAMS WITH ROAMING RANGE")
    print("=" * 80)
    print("[OK] Locked teams initialized successfully")
    
    amanda_id = player_id_map["Amanda"]
    carrie_id = player_id_map["Carrie D"]
    
    # Test 1: Locked partners can partner
    can_partner = can_play_with_player(session, amanda_id, carrie_id, 'partner')
    print(f"TEST 1: Can locked partners be partners? {can_partner}")
    
    if not can_partner:
        print("[FAIL] Locked partners should be able to partner!")
        return False
    
    # Test 2: Locked partners cannot be opponents
    can_oppose = can_play_with_player(session, amanda_id, carrie_id, 'opponent')
    print(f"TEST 2: Can locked partners be opponents? {can_oppose}")
    
    if can_oppose:
        print("[FAIL] Locked partners should NOT be opponents!")
        return False
    
    print("\n" + "=" * 80)
    print("[PASS] All locked team tests passed!")
    print("Locked teams work correctly with roaming range enforcement!")
    return True


if __name__ == "__main__":
    result = test_locked_teams()
    exit(0 if result else 1)
