
import unittest
from python.session import create_session, complete_match
from python.pickleball_types import SessionConfig, Player
from python.competitive_variety import populate_empty_courts_competitive_variety
from python.roundrobin import generate_round_robin_queue
import datetime

class TestAddPlayerRepetition(unittest.TestCase):
    def test_add_player_repetition(self):
        # 12 players to trigger hard caps
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(12)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=2,
            banned_pairs=[],
            locked_teams=[],
            court_sliding_mode='None',
            randomize_player_order=False
        )
        session = create_session(config)
        
        # Fill courts
        populate_empty_courts_competitive_variety(session)
        
        # Complete match on Court 1
        match1 = session.matches[0]
        p1, p2 = match1.team1 # Partners
        
        print(f"Match 1: {p1}, {p2} (Partners) vs ...")
        
        complete_match(session, match1.id, 11, 5)
        
        # Simulate "Adding a Player" via the GUI logic which might regenerate queue
        # This mirrors the `save_changes` logic in `SessionWindow.manage_players`
        
        # 1. Add new player to config
        new_player = Player(id="p_new", name="New Player")
        session.config.players.append(new_player)
        session.active_players.add(new_player.id)
        
        # Initialize stats for new player
        from python.pickleball_types import PlayerStats
        session.player_stats[new_player.id] = PlayerStats(player_id=new_player.id)
        
        # 2. THE BAD LOGIC: Blindly regenerate round robin queue
        # This is what we suspect causes the issue in `competitive-variety` mode
        # because the GUI does this:
        session.match_queue = generate_round_robin_queue(
            [p for p in session.config.players if p.id in session.active_players],
            session.config.session_type,
            session.config.banned_pairs,
            player_stats=session.player_stats,
            active_matches=session.matches
        )
        
        # 3. Populate courts again
        populate_empty_courts_competitive_variety(session)
        
        # Check new matches
        # We want to verify that p1 and p2 are NOT partners again
        
        active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        
        found_repeat_partnership = False
        for m in active_matches:
            # Check team 1
            if p1 in m.team1 and p2 in m.team1:
                found_repeat_partnership = True
                print(f"FAIL: Found repeat partnership {p1}+{p2} in Match {m.id}")
            # Check team 2
            if p1 in m.team2 and p2 in m.team2:
                found_repeat_partnership = True
                print(f"FAIL: Found repeat partnership {p1}+{p2} in Match {m.id}")
                
        self.assertFalse(found_repeat_partnership, "Partnership repeated immediately after adding player and regenerating queue")

if __name__ == '__main__':
    unittest.main()
