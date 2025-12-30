import unittest
from python.session import create_session, complete_match, load_session_from_snapshot
from python.pickleball_types import SessionConfig, Player, Match
from python.session_persistence import serialize_session, deserialize_session
from python.utils import generate_id
from datetime import datetime


class TestMatchHistorySnapshots(unittest.TestCase):
    
    def test_snapshot_created_on_match_complete(self):
        """Test that snapshots are created when matches complete"""
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
            courts=2
        )
        
        session = create_session(config)
        
        match_id = generate_id()
        match = Match(
            id=match_id,
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status="in-progress",
            start_time=datetime.now()
        )
        session.matches.append(match)
        
        # Verify no snapshots yet
        self.assertEqual(len(session.match_history_snapshots), 0)
        
        # Complete the match
        success, slides = complete_match(session, match_id, 11, 9)
        
        # Verify the match was completed
        self.assertTrue(success)
        self.assertEqual(match.status, 'completed')
        self.assertEqual(match.score, {'team1_score': 11, 'team2_score': 9})
        
        # Verify a snapshot was created
        self.assertEqual(len(session.match_history_snapshots), 1)
        
        snapshot = session.match_history_snapshots[0]
        self.assertEqual(snapshot.match_id, match_id)
        self.assertEqual(len(snapshot.matches), 1)
        self.assertEqual(snapshot.matches[0]['status'], 'in-progress')
        self.assertIsNone(snapshot.matches[0]['score'])
    
    
    def test_load_from_snapshot_reverts_state(self):
        """Test that loading from snapshot reverts session state"""
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
            courts=2
        )
        
        session = create_session(config)
        
        match1_id = generate_id()
        match1 = Match(
            id=match1_id,
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status="in-progress",
            start_time=datetime.now()
        )
        session.matches.append(match1)
        
        # Set some initial stats
        session.player_stats["p1"].games_waited = 2
        session.player_stats["p2"].games_waited = 1
        
        # Complete first match
        complete_match(session, match1_id, 11, 9)
        
        # Verify state after match
        self.assertEqual(match1.status, 'completed')
        self.assertEqual(session.player_stats["p1"].wins, 1)
        self.assertEqual(len(session.match_history_snapshots), 1)
        
        snapshot_before_reload = session.match_history_snapshots[0]
        initial_p1_games_waited = snapshot_before_reload.player_stats["p1"]["games_waited"]
        
        # Load from snapshot
        success = load_session_from_snapshot(session, snapshot_before_reload)
        
        self.assertTrue(success)
        
        # Verify we're back to the pre-match state
        match1_after_load = None
        for m in session.matches:
            if m.id == match1_id:
                match1_after_load = m
                break
        
        self.assertIsNotNone(match1_after_load)
        self.assertEqual(match1_after_load.status, 'in-progress')
        self.assertIsNone(match1_after_load.score)
        
        # Stats should be reverted
        self.assertEqual(session.player_stats["p1"].wins, 0)
        self.assertEqual(session.player_stats["p1"].games_waited, initial_p1_games_waited)
        
        # Snapshots should be cleared after loading
        self.assertEqual(len(session.match_history_snapshots), 0)
    
    
    def test_snapshot_persistence_serialization(self):
        """Test that snapshots are properly serialized and deserialized"""
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
            courts=2
        )
        
        session = create_session(config)
        
        match_id = generate_id()
        match = Match(
            id=match_id,
            court_number=1,
            team1=["p1", "p2"],
            team2=["p3", "p4"],
            status="in-progress",
            start_time=datetime.now()
        )
        session.matches.append(match)
        
        # Complete the match
        complete_match(session, match_id, 11, 9)
        
        # Serialize the session
        serialized = serialize_session(session)
        
        # Verify snapshots are in serialized data
        self.assertIn("match_history_snapshots", serialized)
        self.assertEqual(len(serialized["match_history_snapshots"]), 1)
        
        # Deserialize the session
        session2 = deserialize_session(serialized)
        
        # Verify snapshots are restored
        self.assertEqual(len(session2.match_history_snapshots), 1)
        self.assertEqual(session2.match_history_snapshots[0].match_id, match_id)


if __name__ == '__main__':
    unittest.main()
