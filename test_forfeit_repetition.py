
import unittest
from python.session import create_session, forfeit_match
from python.types import SessionConfig, Player, SessionType, GameMode
from python.competitive_variety import populate_empty_courts_competitive_variety, update_variety_tracking_after_match
from datetime import datetime

class TestForfeitRepetition(unittest.TestCase):
    def test_forfeit_repetition(self):
        # Setup session with enough players to form matches
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(8)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=1,
            banned_pairs=[],
            locked_teams=[],
            court_sliding_mode='None',
            randomize_player_order=False
        )
        session = create_session(config)
        
        # Populate first match
        populate_empty_courts_competitive_variety(session)
        
        self.assertEqual(len(session.matches), 1)
        match1 = session.matches[0]
        team1 = match1.team1
        team2 = match1.team2
        
        print(f"Match 1: {team1} vs {team2}")
        
        # Forfeit the match
        forfeit_match(session, match1.id)
        
        # Verify status
        self.assertEqual(match1.status, 'forfeited')
        
        # Now try to populate again
        # The same players are now available. 
        # If forfeit logic works correctly, it should treat this as a "played" game 
        # or otherwise penalize the repetition so they don't play immediately again.
        
        populate_empty_courts_competitive_variety(session)
        
        # There should be a new match
        # We need to find the new match (the forfeited one is still in the list but status is forfeited)
        active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
        self.assertEqual(len(active_matches), 1)
        
        match2 = active_matches[0]
        print(f"Match 2: {match2.team1} vs {match2.team2}")
        
        # Check if it's the exact same matchup
        same_team1 = set(match2.team1) == set(team1)
        same_team2 = set(match2.team2) == set(team2)
        
        # It shouldn't be the exact same matchup (both teams same)
        # Even stronger: The partners shouldn't be the same if we have variety rules.
        # With 8 players and 1 court, we have 4 players sitting out. 
        # The system SHOULD pick the waiting players, not the ones who just forfeited.
        
        # If the forfeited players are picked again immediately, that's bad.
        players_in_match2 = set(match2.team1 + match2.team2)
        players_in_match1 = set(team1 + team2)
        
        # If the queue was working, the waiting players should have been picked.
        # But let's check if the specific issue "same exact players... same configuration" happens.
        
        if players_in_match2 == players_in_match1:
             print("FAILURE: Same players selected immediately after forfeit")
             
             # Check teams
             if same_team1 and same_team2:
                 print("FAILURE: Exact same teams selected")
                 self.fail("Exact same match scheduled immediately after forfeit")
        else:
            print("Success: Different players selected.")

if __name__ == '__main__':
    unittest.main()
