
import unittest
from python.roundrobin import generate_round_robin_queue
from python.pickleball_types import Player, PlayerStats, QueuedMatch
from python.utils import create_player_stats

class TestRoundRobinStrictness(unittest.TestCase):
    def test_strict_partnership_avoidance(self):
        """
        Test that the generator strictly avoids repeated partnerships
        when unique partnerships are available.
        """
        # Create 12 players (66 unique pairs)
        players = [Player(id=str(i), name=f"P{i}") for i in range(12)]
        
        # Initialize stats
        stats = {p.id: create_player_stats(p.id) for p in players}
        
        # Simulate that Player 0 and Player 1 have ALREADY played together
        stats['0'].partners_played['1'] = 1
        stats['1'].partners_played['0'] = 1
        stats['0'].games_played = 1
        stats['1'].games_played = 1
        
        # Generate queue
        # We expect matches. None of them should have (0, 1) as a pair.
        matches = generate_round_robin_queue(
            players=players,
            session_type='doubles',
            banned_pairs=[],
            max_matches=20,
            player_stats=stats
        )
        
        for m in matches:
            t1 = sorted(m.team1)
            t2 = sorted(m.team2)
            
            self.assertNotEqual(t1, ['0', '1'], "Player 0 and 1 should not be paired again")
            self.assertNotEqual(t2, ['0', '1'], "Player 0 and 1 should not be paired again")

    def test_strict_opponent_avoidance(self):
        """
        Test that the generator strictly avoids repeated opponents
        when unique matchups are available.
        """
        players = [Player(id=str(i), name=f"P{i}") for i in range(8)]
        stats = {p.id: create_player_stats(p.id) for p in players}
        
        # Simulate that Player 0 played against Player 2
        stats['0'].opponents_played['2'] = 1
        stats['0'].opponents_played['3'] = 1
        stats['1'].opponents_played['2'] = 1
        stats['1'].opponents_played['3'] = 1
        stats['2'].opponents_played['0'] = 1
        stats['2'].opponents_played['1'] = 1
        stats['3'].opponents_played['0'] = 1
        stats['3'].opponents_played['1'] = 1
        
        # We want to see if we can avoid repeating 0 vs 2
        matches = generate_round_robin_queue(
            players=players,
            session_type='doubles',
            banned_pairs=[],
            max_matches=10,
            player_stats=stats
        )
        
        for m in matches:
            # Check if 0 and 2 are on opposite teams
            team1 = m.team1
            team2 = m.team2
            
            if '0' in team1 and '2' in team2:
                 self.fail("Player 0 and 2 played against each other again")
            if '0' in team2 and '2' in team1:
                 self.fail("Player 0 and 2 played against each other again") 

if __name__ == "__main__":
    unittest.main()
