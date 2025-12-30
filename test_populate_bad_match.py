"""
Integration test: Can populate_empty_courts_competitive_variety form the bad match?
"""
from python.session import Session
from python.pickleball_types import Player, SessionConfig, Match
from python.competitive_variety import (
    get_player_ranking,
    populate_empty_courts_competitive_variety,
)
from python.utils import create_player_stats, generate_id
from datetime import datetime


def test_populate_courts_with_amanda_carrie():
    """
    Test if populate_empty_courts_competitive_variety would create the bad match.
    """
    # Create 20 players
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
    
    players = [Player(id=f"p{i}", name=name) for i, (name, _, _, _) in enumerate(player_data)]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4
    )
    session = Session(id="test_session", config=config)
    
    # Populate player stats
    for i, (name, elo, wins, losses) in enumerate(player_data):
        session.active_players.add(f"p{i}")
        stats = create_player_stats(f"p{i}")
        stats.games_played = wins + losses
        stats.wins = wins
        stats.total_points_for = 100 + (wins * 15)
        stats.total_points_against = 100 - (wins * 10) + (losses * 10)
        session.player_stats[f"p{i}"] = stats
    
    print("Testing if populate_empty_courts would create bad match...")
    print("=" * 80)
    
    # Try to populate courts - this would create matches from the available players
    # Make all courts empty initially
    populate_empty_courts_competitive_variety(session)
    
    # Check if any match contains Amanda + Carrie
    bad_match_found = False
    for match in session.matches:
        team1_set = set(match.team1)
        team2_set = set(match.team2)
        all_players = team1_set | team2_set
        
        # Check if this is the bad match: Amanda (p0) + Carrie (p3) vs Carolyn (p17) + Dan (p16)
        if "p0" in all_players and "p3" in all_players and "p17" in all_players and "p16" in all_players:
            print(f"[FAIL] Bad match found: {match.team1} vs {match.team2}")
            bad_match_found = True
            break
        
        # Check if it's Amanda (p0) or Carrie (p3) paired with Carolyn (p17) or Dan (p16)
        if ("p0" in team1_set and ("p17" in team2_set or "p16" in team2_set)) or \
           ("p0" in team2_set and ("p17" in team1_set or "p16" in team1_set)) or \
           ("p3" in team1_set and ("p17" in team2_set or "p16" in team2_set)) or \
           ("p3" in team2_set and ("p17" in team1_set or "p16" in team1_set)):
            print(f"[FAIL] Bad match found: {match.team1} vs {match.team2}")
            bad_match_found = True
            break
    
    if bad_match_found:
        print("\nThe bug still exists!")
        return False
    else:
        print(f"No bad matches formed. Generated {len(session.matches)} matches.")
        if session.matches:
            print("\nGenerated matches:")
            for i, match in enumerate(session.matches):
                names1 = [player_data[int(p[1:])][0] for p in match.team1]
                names2 = [player_data[int(p[1:])][0] for p in match.team2]
                print(f"  Match {i+1}: {', '.join(names1)} vs {', '.join(names2)}")
        print("\n[PASS] The bug is fixed!")
        return True


if __name__ == "__main__":
    result = test_populate_courts_with_amanda_carrie()
    exit(0 if result else 1)
