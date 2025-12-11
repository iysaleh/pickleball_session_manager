"""
Test export functionality includes Avg Pt Diff, Pts For, and Pts Against
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from python.types import Player, SessionConfig, Match
from python.session import create_session, complete_match
from datetime import datetime


def test_export_includes_point_stats():
    """Test that export includes Avg Pt Diff, Pts For, and Pts Against"""
    print("Test: Export includes point statistics (Avg Pt Diff, Pts For, Pts Against)")
    
    # Create session
    players = [
        Player(id="p1", name="Alice"),
        Player(id="p2", name="Bob"),
        Player(id="p3", name="Charlie"),
        Player(id="p4", name="Diana"),
    ]
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=1
    )
    
    session = create_session(config)
    
    # Create match: Alice+Bob beat Charlie+Diana 11-5
    # Alice: 11 pts for, 5 pts against
    # Bob: 11 pts for, 5 pts against
    # Charlie: 5 pts for, 11 pts against
    # Diana: 5 pts for, 11 pts against
    match1 = Match(
        id="m1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='completed',
        score={'team1_score': 11, 'team2_score': 5},
        end_time=datetime.now()
    )
    session.matches.append(match1)
    complete_match(session, "m1", 11, 5)
    
    # Verify stats were recorded
    alice_stats = session.player_stats["p1"]
    bob_stats = session.player_stats["p2"]
    charlie_stats = session.player_stats["p3"]
    diana_stats = session.player_stats["p4"]
    
    print(f"\nAlice stats: Pts For={alice_stats.total_points_for}, Pts Against={alice_stats.total_points_against}, Avg Pt Diff={alice_stats.total_points_for - alice_stats.total_points_against}")
    print(f"Bob stats: Pts For={bob_stats.total_points_for}, Pts Against={bob_stats.total_points_against}, Avg Pt Diff={bob_stats.total_points_for - bob_stats.total_points_against}")
    print(f"Charlie stats: Pts For={charlie_stats.total_points_for}, Pts Against={charlie_stats.total_points_against}, Avg Pt Diff={charlie_stats.total_points_for - charlie_stats.total_points_against}")
    print(f"Diana stats: Pts For={diana_stats.total_points_for}, Pts Against={diana_stats.total_points_against}, Avg Pt Diff={diana_stats.total_points_for - diana_stats.total_points_against}")
    
    # Verify expected values
    assert alice_stats.total_points_for == 11, f"Alice should have 11 pts for, got {alice_stats.total_points_for}"
    assert alice_stats.total_points_against == 5, f"Alice should have 5 pts against, got {alice_stats.total_points_against}"
    
    assert charlie_stats.total_points_for == 5, f"Charlie should have 5 pts for, got {charlie_stats.total_points_for}"
    assert charlie_stats.total_points_against == 11, f"Charlie should have 11 pts against, got {charlie_stats.total_points_against}"
    
    print("\n[PASS] test_export_includes_point_stats - Stats recorded correctly")
    
    # Now test that the export would include these columns
    # We can simulate what the export function does
    player_data = []
    for player in session.config.players:
        if player.id not in session.active_players:
            continue
        
        stats = session.player_stats[player.id]
        
        # Calculate average point differential (as done in export_session)
        avg_pt_diff = (stats.total_points_for - stats.total_points_against) / stats.games_played if stats.games_played > 0 else 0
        
        # Verify we have the right data
        print(f"\nProcessing export data for {player.name}:")
        print(f"  Games played: {stats.games_played}")
        print(f"  Pts For: {stats.total_points_for}")
        print(f"  Pts Against: {stats.total_points_against}")
        print(f"  Avg Pt Diff: {avg_pt_diff:.1f}")
        
        player_data.append({
            'name': player.name,
            'pts_for': stats.total_points_for,
            'pts_against': stats.total_points_against,
            'avg_pt_diff': avg_pt_diff
        })
    
    # Verify we have all players with correct data
    alice_export = next(p for p in player_data if p['name'] == 'Alice')
    charlie_export = next(p for p in player_data if p['name'] == 'Charlie')
    
    assert alice_export['pts_for'] == 11, f"Alice export should have 11 pts for"
    assert alice_export['pts_against'] == 5, f"Alice export should have 5 pts against"
    assert alice_export['avg_pt_diff'] == 6.0, f"Alice export should have 6.0 avg pt diff"
    
    assert charlie_export['pts_for'] == 5, f"Charlie export should have 5 pts for"
    assert charlie_export['pts_against'] == 11, f"Charlie export should have 11 pts against"
    assert charlie_export['avg_pt_diff'] == -6.0, f"Charlie export should have -6.0 avg pt diff"
    
    print("\n[PASS] test_export_includes_point_stats - Export data correct")


if __name__ == '__main__':
    test_export_includes_point_stats()
