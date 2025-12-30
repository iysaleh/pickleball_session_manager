
import unittest
from datetime import datetime
from python.session import create_session, add_player_to_session, remove_player_from_session, get_player_name, complete_match
from python.pickleball_types import SessionConfig, Player, Match

class TestGuiCrash(unittest.TestCase):
    def test_remove_player_breaks_history(self):
        """Test that removing a player from config.players breaks history resolution"""
        p1 = Player(id="p1", name="Alice")
        p2 = Player(id="p2", name="Bob")
        p3 = Player(id="p3", name="Charlie")
        p4 = Player(id="p4", name="Dave")
        
        config = SessionConfig(
            mode="round-robin",
            session_type="doubles",
            players=[p1, p2, p3, p4],
            courts=1,
            banned_pairs=[],
            locked_teams=[]
        )
        
        session = create_session(config)
        
        # Setup a match
        match = Match(
            id="m1",
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status="completed",
            start_time=datetime.now(),
            end_time=datetime.now(),
            score={"team1_score": 11, "team2_score": 9}
        )
        session.matches.append(match)
        
        # Simulate GUI removal (BUGGY BEHAVIOR)
        # The GUI removes from both active_players and config.players
        session.active_players.discard("p1")
        session.config.players = [p for p in session.config.players if p.id != "p1"]
        
        # Verify get_player_name returns None for p1
        self.assertIsNone(get_player_name(session, "p1"))
        
        # Verify this causes the TypeError seen in the traceback
        # Traceback: team1_str = ", ".join(team1_names) -> TypeError: sequence item 0: expected str instance, NoneType found
        team1_names = [get_player_name(session, pid) for pid in match.team1]
        
        # team1 has "p1" and "p2". "p1" returns None. "p2" returns "Bob".
        # team1_names = [None, "Bob"]
        
        with self.assertRaises(TypeError):
            ", ".join(team1_names)
            
    def test_correct_removal_preserves_history(self):
        """Test that correct removal preserves history"""
        p1 = Player(id="p1", name="Alice")
        p2 = Player(id="p2", name="Bob")
        p3 = Player(id="p3", name="Charlie")
        p4 = Player(id="p4", name="Dave")
        
        config = SessionConfig(
            mode="round-robin",
            session_type="doubles",
            players=[p1, p2, p3, p4],
            courts=1,
            banned_pairs=[],
            locked_teams=[]
        )
        
        session = create_session(config)
        
        # Setup a match
        match = Match(
            id="m1",
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status="completed",
            start_time=datetime.now(),
            end_time=datetime.now(),
            score={"team1_score": 11, "team2_score": 9}
        )
        session.matches.append(match)
        
        # Correct removal (using session.py logic, or what GUI SHOULD do)
        # Only remove from active_players
        session = remove_player_from_session(session, "p1")
        
        # Verify p1 is still in config.players
        self.assertTrue(any(p.id == "p1" for p in session.config.players))
        
        # Verify p1 is NOT in active_players
        self.assertNotIn("p1", session.active_players)
        
        # Verify get_player_name works
        self.assertEqual(get_player_name(session, "p1"), "Alice")
        
        # Verify no crash
        team1_names = [get_player_name(session, pid) for pid in match.team1]
        team1_str = ", ".join(team1_names)
        self.assertEqual(team1_str, "Alice, Bob")

    def test_add_player_reactivation(self):
        """Test that add_player_to_session reactivates an inactive player"""
        p1 = Player(id="p1", name="Alice")
        p2 = Player(id="p2", name="Bob")
        
        config = SessionConfig(
            mode="round-robin",
            session_type="doubles",
            players=[p1, p2],
            courts=1,
            banned_pairs=[],
            locked_teams=[]
        )
        
        session = create_session(config)
        
        # Remove p1 correctly
        session = remove_player_from_session(session, "p1")
        self.assertNotIn("p1", session.active_players)
        
        # Try to add p1 back
        session = add_player_to_session(session, p1)
        
        # Verify p1 is active again
        # CURRENTLY FAILS because add_player_to_session doesn't reactivate
        self.assertIn("p1", session.active_players)

if __name__ == '__main__':
    unittest.main()
