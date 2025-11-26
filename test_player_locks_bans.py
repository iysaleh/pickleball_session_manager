import unittest
from python.types import Player, Session, SessionConfig, PlayerStats
from python.roundrobin import generate_round_robin_queue
from python.competitive_variety import can_play_with_player, populate_empty_courts_competitive_variety
from python.session import create_session

class TestPlayerLocksBans(unittest.TestCase):
    def setUp(self):
        self.players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(8)]
        self.player_stats = {p.id: PlayerStats(player_id=p.id) for p in self.players}

    def test_round_robin_locks(self):
        # Lock p0 and p1
        locked_teams = [['p0', 'p1']]
        banned_pairs = []
        
        matches = generate_round_robin_queue(
            self.players, 
            'doubles', 
            banned_pairs, 
            locked_teams=locked_teams,
            player_stats=self.player_stats
        )
        
        for match in matches:
            if 'p0' in match.team1:
                self.assertIn('p1', match.team1)
            if 'p1' in match.team1:
                self.assertIn('p0', match.team1)
            if 'p0' in match.team2:
                self.assertIn('p1', match.team2)
            if 'p1' in match.team2:
                self.assertIn('p0', match.team2)

    def test_round_robin_bans(self):
        # Ban p0 and p1
        banned_pairs = [('p0', 'p1')]
        
        matches = generate_round_robin_queue(
            self.players, 
            'doubles', 
            banned_pairs, 
            player_stats=self.player_stats
        )
        
        for match in matches:
            # Check team 1
            if 'p0' in match.team1:
                self.assertNotIn('p1', match.team1)
            # Check team 2
            if 'p0' in match.team2:
                self.assertNotIn('p1', match.team2)

    def test_competitive_variety_locks_logic(self):
        # Test can_play_with_player logic
        session = create_session(SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=self.players,
            courts=2,
            locked_teams=[['p0', 'p1']]
        ))
        
        # p0 and p1 MUST be partners
        self.assertTrue(can_play_with_player(session, 'p0', 'p1', 'partner'))
        # p0 and p1 CANNOT be opponents
        self.assertFalse(can_play_with_player(session, 'p0', 'p1', 'opponent'))
        
        # p0 CANNOT partner with p2
        self.assertFalse(can_play_with_player(session, 'p0', 'p2', 'partner'))
        
        # p2 can partner with p3
        self.assertTrue(can_play_with_player(session, 'p2', 'p3', 'partner'))

    def test_competitive_variety_bans_logic(self):
        session = create_session(SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=self.players,
            courts=2,
            banned_pairs=[('p0', 'p1')]
        ))
        
        # p0 and p1 CANNOT be partners
        self.assertFalse(can_play_with_player(session, 'p0', 'p1', 'partner'))
        
        # p0 and p1 can be opponents
        self.assertTrue(can_play_with_player(session, 'p0', 'p1', 'opponent'))

    def test_competitive_variety_match_generation(self):
        # p0 and p1 locked
        session = create_session(SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=self.players,
            courts=1,
            locked_teams=[['p0', 'p1']]
        ))
        
        # Initialize stats for everyone so they are active
        for p in self.players:
            session.active_players.add(p.id)
            session.player_stats[p.id] = PlayerStats(player_id=p.id)

        # Generate match
        populate_empty_courts_competitive_variety(session)
        
        self.assertTrue(len(session.matches) > 0)
        match = session.matches[0]
        
        # Verify lock respected if they played
        players_in_match = match.team1 + match.team2
        if 'p0' in players_in_match:
            self.assertIn('p1', players_in_match)
            # Must be on same team
            if 'p0' in match.team1:
                self.assertIn('p1', match.team1)
            else:
                self.assertIn('p1', match.team2)

if __name__ == '__main__':
    unittest.main()
