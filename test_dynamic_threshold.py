"""
Test to verify that dynamic threshold prevents queueing lockup
"""
from python.roundrobin import generate_round_robin_queue
from python.types import Player, PlayerStats
from python.utils import create_player_stats

def test_dynamic_threshold_prevents_lockup():
    """
    Simulate a session where:
    - 6 players (smaller pool for easier saturation)
    - Many games have been played (~20 games per player)
    - With strict uniqueness constraints, very few new matchups are possible
    - Dynamic threshold should allow some repetition to prevent stalling
    
    With 6 players in doubles (2v2), there are only 15 unique pairs possible.
    After ~20 games per player, we've exhausted most unique pairs.
    Without dynamic threshold, it blocks. With it, it allows controlled repetition.
    """
    # Create 6 players
    players = [Player(id=str(i), name=f"Player{i}") for i in range(6)]
    
    # Create stats where players have played many games
    stats = {}
    for p in players:
        stats[p.id] = create_player_stats(p.id)
        stats[p.id].games_played = 20  # Many games played
    
    # Simulate most pairs have been tried (with some repetition)
    # In 20 games with 6 players: 20 * 2 = 40 player-game slots
    # Each player appears ~13 times. A pair appears together ~6-7 times.
    for pid in stats:
        for other_pid in stats:
            if pid != other_pid:
                # Most players have played together 2-3 times as partners
                stats[pid].partners_played[other_pid] = 2
                # Most players have faced each other 3-4 times as opponents
                stats[pid].opponents_played[other_pid] = 3
    
    # Generate queue - with strict uniqueness, this might fail
    # With dynamic threshold, it should generate matches even though there's repetition
    matches = generate_round_robin_queue(
        players=players,
        session_type='doubles',
        banned_pairs=[],
        max_matches=5,
        player_stats=stats
    )
    
    # We should get at least some matches, not zero
    if len(matches) == 0:
        print("FAIL: No matches generated - threshold is too strict!")
        return False
    
    print(f"SUCCESS: Generated {len(matches)} matches with dynamic threshold")
    print(f"With {len(players)} players and {stats[players[0].id].games_played} games played per player")
    return True


def test_threshold_allows_repetition_when_necessary():
    """
    Test that after enough games, players CAN play together again
    even if they have history.
    
    With 6 players and 50 games, dynamic threshold should be ~2 repetitions
    """
    players = [Player(id=str(i), name=f"Player{i}") for i in range(6)]
    
    stats = {}
    for p in players:
        stats[p.id] = create_player_stats(p.id)
        stats[p.id].games_played = 40  # Many games
    
    # Everyone has played together multiple times
    for pid in stats:
        for other_pid in stats:
            if pid != other_pid:
                stats[pid].partners_played[other_pid] = 2
                stats[pid].opponents_played[other_pid] = 3
    
    matches = generate_round_robin_queue(
        players=players,
        session_type='doubles',
        banned_pairs=[],
        max_matches=5,
        player_stats=stats
    )
    
    # With 6 players, after many games, some repetition is expected and OK
    if len(matches) == 0:
        print("FAIL: With 6 players and 40 games each, still no matches!")
        return False
    
    print(f"SUCCESS: With 6 players and many games, generated {len(matches)} matches")
    return True


if __name__ == "__main__":
    result1 = test_dynamic_threshold_prevents_lockup()
    result2 = test_threshold_allows_repetition_when_necessary()
    
    if result1 and result2:
        print("\nAll dynamic threshold tests passed!")
    else:
        print("\nSome tests failed - dynamic threshold not working correctly")
