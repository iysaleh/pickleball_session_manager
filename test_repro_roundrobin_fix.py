
import unittest
from python.pickleball_types import Player, SessionType, PlayerStats
from python.roundrobin import generate_round_robin_queue

class TestRoundRobinFix(unittest.TestCase):
    def test_six_player_doubles_generation(self):
        """
        Verify that round robin generation works for 6 players in doubles.
        Previously it stopped at 3 matches due to strict uniqueness constraints.
        """
        players = [Player(id=str(i), name=f"P{i}") for i in range(1, 7)]
        session_type = 'doubles'
        banned_pairs = []
        max_matches = 20
        
        matches = generate_round_robin_queue(
            players=players,
            session_type=session_type,
            banned_pairs=banned_pairs,
            max_matches=max_matches
        )
        
        print(f"Generated {len(matches)} matches for 6 players.")
        for i, m in enumerate(matches):
            print(f"Match {i+1}: {m.team1} vs {m.team2}")
            
        # It should generate exactly max_matches if constraints are relaxable
        self.assertEqual(len(matches), max_matches)
        
        # Verify diversity
        # Everyone should play roughly equal games
        games_played = {p.id: 0 for p in players}
        for m in matches:
            for pid in m.team1 + m.team2:
                games_played[pid] += 1
                
        print("Games played:", games_played)
        min_games = min(games_played.values())
        max_games = max(games_played.values())
        
        # Fair distribution check
        self.assertLessEqual(max_games - min_games, 2)

if __name__ == '__main__':
    unittest.main()
