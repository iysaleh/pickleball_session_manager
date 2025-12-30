"""
Full session simulation test: Amanda + Carrie vs Carolyn + Dan bug

This test replays the EXACT match history from pickleball_session_20251203_214055.txt
and then checks if the bad match (currently on Court 2) would be formed by the algorithm.

The session file shows:
- 18 completed matches in MATCH HISTORY
- Currently on courts: Amanda+Carrie vs Carolyn+Dan (the bad match!)

This test verifies:
1. Replay the 18 completed matches faithfully
2. Reach the exact game state where the bad match should be formed
3. Check if the algorithm would create this illegal match
4. Verify the fix prevents it
"""
from python.session import Session
from python.pickleball_types import Player, SessionConfig, Match
from python.competitive_variety import (
    get_player_ranking,
    get_roaming_rank_range,
    can_all_players_play_together,
    calculate_elo_rating,
)
from python.utils import create_player_stats, generate_id
from datetime import datetime, timedelta


def replay_session_until_bad_match():
    """
    Replay the exact match history up to the point where the bad match should form
    """
    # Exact match history from the session file (18 completed matches)
    match_history = [
        (["Ellie", "Patrick"], ["Dan", "Ralph"]),
        (["Ralph", "Patrick"], ["Carolyn", "Lia"]),
        (["Jim K", "Andrew"], ["Patrick", "Lia"]),
        (["Dan", "Carrie D"], ["Johnny", "Jeremy"]),
        (["Carolyn", "Amanda"], ["Ellie", "Ibraheem"]),
        (["Jeremy", "Carrie D"], ["Lia", "Payton"]),
        (["Andrew", "Patrick"], ["Ralph", "Tony"]),
        (["Lee", "Joshua"], ["Brandon", "Julie"]),
        (["Ibraheem", "Amanda"], ["Carrie D", "Payton"]),
        (["Lisa K", "Jim K"], ["Johnny", "Dan"]),
        (["Jeremy", "Lia"], ["Carolyn", "Ellie"]),
        (["Payton", "Amanda"], ["Patrick", "Tony"]),
        (["Carrie D", "Ibraheem"], ["Joshua", "Julie"]),
        (["Lee", "Brandon"], ["Andrew", "Ralph"]),
        (["Ibraheem", "Julie"], ["Dan", "Jim K"]),
        (["Amanda", "Tony"], ["Lia", "Ellie"]),
        (["Carrie D", "Joshua"], ["Payton", "Patrick"]),
        (["Johnny", "Lisa K"], ["Jeremy", "Carolyn"]),
    ]
    
    # The bad match that should NOT be formed (but is currently on Court 2)
    bad_match_team1 = {"Amanda", "Carrie D"}
    bad_match_team2 = {"Carolyn", "Dan"}
    
    # Current matches on courts (from the session file snapshot)
    current_court_matches = [
        (["Brandon", "Joshua"], ["Tony", "Payton"]),      # Court 1
        (["Amanda", "Carrie D"], ["Carolyn", "Dan"]),     # Court 2 - THE BAD MATCH
        (["Lisa K", "Andrew"], ["Lee", "Julie"]),         # Court 3
        (["Ibraheem", "Jeremy"], ["Johnny", "Jim K"]),    # Court 4
    ]
    
    # Current waitlist
    waitlist = ["Patrick", "Lia", "Ellie", "Ralph"]
    
    # Expected final stats (from the session file)
    expected_final_stats = {
        "Amanda": {"games": 4, "wins": 4},
        "Lisa K": {"games": 2, "wins": 2},
        "Lee": {"games": 2, "wins": 2},
        "Carrie D": {"games": 5, "wins": 4},
        "Ibraheem": {"games": 4, "wins": 3},
        "Jim K": {"games": 3, "wins": 2},
        "Joshua": {"games": 3, "wins": 2},
        "Andrew": {"games": 3, "wins": 2},
        "Brandon": {"games": 2, "wins": 1},
        "Patrick": {"games": 6, "wins": 3},
        "Jeremy": {"games": 4, "wins": 2},
        "Johnny": {"games": 3, "wins": 1},
        "Julie": {"games": 3, "wins": 1},
        "Tony": {"games": 3, "wins": 1},
        "Ellie": {"games": 4, "wins": 1},
        "Payton": {"games": 4, "wins": 1},
        "Dan": {"games": 4, "wins": 1},
        "Carolyn": {"games": 4, "wins": 1},
        "Ralph": {"games": 4, "wins": 1},
        "Lia": {"games": 5, "wins": 1},
    }
    
    # Create session
    all_players = sorted(expected_final_stats.keys())
    players = [Player(id=f"p{i}", name=name) for i, name in enumerate(all_players)]
    player_id_map = {p.name: p.id for p in players}
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = Session(id="replay_session", config=config)
    
    # Initialize player stats
    for player in players:
        session.active_players.add(player.id)
        stats = create_player_stats(player.id)
        session.player_stats[player.id] = stats
    
    print("REPLAYING SESSION TO BAD MATCH POINT")
    print("=" * 80)
    print(f"Total completed matches to replay: {len(match_history)}\n")
    
    # Replay each completed match
    for match_num, (team1_names, team2_names) in enumerate(match_history, 1):
        team1_ids = [player_id_map[name] for name in team1_names]
        team2_ids = [player_id_map[name] for name in team2_names]
        
        # Assume team1 always wins (based on match history format)
        for pid in team1_ids:
            session.player_stats[pid].wins += 1
            session.player_stats[pid].games_played += 1
        for pid in team2_ids:
            session.player_stats[pid].losses += 1
            session.player_stats[pid].games_played += 1
        
        print(f"Match {match_num:2d}: {', '.join(team1_names):20s} vs {', '.join(team2_names):20s}")
    
    # Verify the stats match expected
    print("\n" + "=" * 80)
    print("VERIFYING GAME STATE...")
    print("-" * 80)
    
    stats_match = True
    for player_name in all_players:
        player_id = player_id_map[player_name]
        expected = expected_final_stats[player_name]
        actual_games = session.player_stats[player_id].games_played
        actual_wins = session.player_stats[player_id].wins
        
        if actual_games != expected["games"] or actual_wins != expected["wins"]:
            print(f"[MISMATCH] {player_name}: expected {expected['wins']}-{expected['games']-expected['wins']}, " +
                  f"got {actual_wins}-{actual_games-actual_wins}")
            stats_match = False
    
    if stats_match:
        print("[OK] All game stats match expected values!")
    else:
        print("[ERROR] Game stats don't match!")
    
    # Now check the problematic match
    print("\n" + "=" * 80)
    print("CHECKING THE BAD MATCH (Amanda+Carrie vs Carolyn+Dan)...")
    print("=" * 80 + "\n")
    
    # Get player IDs for the bad match
    bad_match_ids = [player_id_map[name] for name in (bad_match_team1 | bad_match_team2)]
    
    # Get rankings at this game state
    print("Roaming Ranges at this game state (20 players, 50% window = 10):\n")
    amanda_id = player_id_map["Amanda"]
    carrie_id = player_id_map["Carrie D"]
    carolyn_id = player_id_map["Carolyn"]
    dan_id = player_id_map["Dan"]
    
    for name, pid in [("Amanda", amanda_id), ("Carrie D", carrie_id), ("Carolyn", carolyn_id), ("Dan", dan_id)]:
        rank, elo = get_player_ranking(session, pid)
        min_r, max_r = get_roaming_rank_range(session, pid)
        print(f"  {name:12s}: rank #{rank:2d} (ELO {elo:7.1f}), range #{min_r:2d}-{max_r:2d}")
    
    print(f"\nTeam 1 (Amanda+Carrie) ranges:")
    amanda_rank, _ = get_player_ranking(session, amanda_id)
    amanda_min, amanda_max = get_roaming_rank_range(session, amanda_id)
    print(f"  Amanda range:    #{amanda_min}-{amanda_max}")
    carrie_rank, _ = get_player_ranking(session, carrie_id)
    carrie_min, carrie_max = get_roaming_rank_range(session, carrie_id)
    print(f"  Carrie range:    #{carrie_min}-{carrie_max}")
    print(f"  Overlap:         #{max(amanda_min, carrie_min)}-{min(amanda_max, carrie_max)}")
    
    print(f"\nTeam 2 (Carolyn+Dan) ranks:")
    carolyn_rank, _ = get_player_ranking(session, carolyn_id)
    carolyn_min, carolyn_max = get_roaming_rank_range(session, carolyn_id)
    print(f"  Carolyn rank:    #{carolyn_rank}, range #{carolyn_min}-{carolyn_max}")
    dan_rank, _ = get_player_ranking(session, dan_id)
    dan_min, dan_max = get_roaming_rank_range(session, dan_id)
    print(f"  Dan rank:        #{dan_rank}, range #{dan_min}-{dan_max}")
    
    print(f"\nCrossover check:")
    print(f"  Carolyn (rank {carolyn_rank}) in Amanda range {amanda_min}-{amanda_max}? {amanda_min <= carolyn_rank <= amanda_max}")
    print(f"  Carolyn (rank {carolyn_rank}) in Carrie range {carrie_min}-{carrie_max}? {carrie_min <= carolyn_rank <= carrie_max}")
    print(f"  Dan (rank {dan_rank}) in Amanda range {amanda_min}-{amanda_max}? {amanda_min <= dan_rank <= amanda_max}")
    print(f"  Dan (rank {dan_rank}) in Carrie range {carrie_min}-{carrie_max}? {carrie_min <= dan_rank <= carrie_max}")
    
    # Check if the match would be allowed
    print(f"\n" + "=" * 80)
    can_form = can_all_players_play_together(session, bad_match_ids)
    print(f"Can form match (Amanda+Carrie vs Carolyn+Dan)? {can_form}")
    print(f"Expected: False (should be REJECTED)\n")
    
    if can_form:
        print("[FAIL] The bad match is ALLOWED - bug not fixed!")
        return False
    else:
        print("[PASS] The bad match is correctly REJECTED by roaming range!")
        print("\nThe fix successfully prevents the illegal match from being formed!")
        return True


if __name__ == "__main__":
    result = replay_session_until_bad_match()
    exit(0 if result else 1)

