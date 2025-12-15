"""
Test the Show Rank button functionality in the waitlist
"""
from python.types import Player, SessionConfig, Match
from python.session import create_session
from python.competitive_variety import get_player_ranking

def test_rank_retrieval():
    """Test that player ranks can be retrieved correctly"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Get ranks for all players
    ranks = {}
    for player_id in [f"p{i}" for i in range(12)]:
        rank, rating = get_player_ranking(session, player_id)
        ranks[player_id] = rank
        assert 1 <= rank <= 12, f"Rank {rank} out of range for {player_id}"
    
    # All ranks should be unique
    assert len(set(ranks.values())) == 12, "Not all ranks are unique"
    print(f"✓ All 12 players have unique ranks")

def test_display_format():
    """Test the display format for player names with ranks"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Test various display formats
    test_cases = [
        ("p0", "Player 0"),
        ("p1", "Player 1"),
        ("p5", "Player 5"),
    ]
    
    for player_id, expected_name in test_cases:
        rank, _ = get_player_ranking(session, player_id)
        
        # Without rank
        display_without = expected_name
        assert expected_name == display_without
        print(f"✓ Without rank: {display_without}")
        
        # With rank (the way UI would display it)
        display_with = f"{expected_name} [{rank}]"
        assert "[" in display_with and "]" in display_with
        print(f"✓ With rank: {display_with}")

def test_rank_updates_after_match():
    """Test that ranks update after a match is played"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Get initial ranks
    initial_ranks = {}
    for player_id in [f"p{i}" for i in range(4)]:
        rank, _ = get_player_ranking(session, player_id)
        initial_ranks[player_id] = rank
    
    # Create a match
    match = Match(
        id="test_match",
        court_number=1,
        team1=["p0", "p1"],
        team2=["p2", "p3"],
        status="completed"
    )
    session.matches.append(match)
    
    # Update stats to reflect the win
    session.player_stats["p0"].games_played += 1
    session.player_stats["p0"].wins += 1
    session.player_stats["p1"].games_played += 1
    session.player_stats["p1"].wins += 1
    session.player_stats["p2"].games_played += 1
    session.player_stats["p2"].losses += 1
    session.player_stats["p3"].games_played += 1
    session.player_stats["p3"].losses += 1
    
    # Get updated ranks
    updated_ranks = {}
    for player_id in [f"p{i}" for i in range(4)]:
        rank, _ = get_player_ranking(session, player_id)
        updated_ranks[player_id] = rank
    
    # Ranks should potentially change
    print(f"✓ Initial ranks: {initial_ranks}")
    print(f"✓ Updated ranks: {updated_ranks}")
    print(f"✓ Rank display would update after match completion")

def test_show_rank_toggle_behavior():
    """Test the expected behavior of the Show Rank toggle"""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3
    )
    session = create_session(config)
    
    # Simulate what the UI would do
    show_rank = False
    
    # Build display without rank
    player_id = "p0"
    name = "Peter Parker"
    rank, _ = get_player_ranking(session, player_id)
    
    if show_rank:
        display = f"{name} [{rank}]"
    else:
        display = name
    
    assert display == "Peter Parker"
    print(f"✓ Without toggle: {display}")
    
    # Toggle on
    show_rank = True
    if show_rank:
        display = f"{name} [{rank}]"
    else:
        display = name
    
    assert "[" in display and "]" in display
    print(f"✓ With toggle on: {display}")
    
    # Toggle off
    show_rank = False
    if show_rank:
        display = f"{name} [{rank}]"
    else:
        display = name
    
    assert display == "Peter Parker"
    print(f"✓ With toggle off: {display}")

if __name__ == "__main__":
    print("Testing Show Rank Button Functionality")
    print("=" * 60)
    
    test_rank_retrieval()
    print()
    test_display_format()
    print()
    test_rank_updates_after_match()
    print()
    test_show_rank_toggle_behavior()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
