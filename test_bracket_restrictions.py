
import unittest
from python.session import Session, SessionConfig
from python.types import Match, Player, PlayerStats
from python.competitive_variety import populate_empty_courts_competitive_variety, get_player_ranking, calculate_elo_rating

class TestBracketRestrictions(unittest.TestCase):
    def setUp(self):
        # 15 Players (triggering 12+ bracket rule)
        # 4 Courts
        players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(15)]
        config = SessionConfig(
            mode='competitive-variety',
            session_type='doubles',
            players=players,
            courts=4
        )
        self.session = Session(id="test_session", config=config)
        self.session.active_players = {p.id for p in players}
        
        # Setup ELOs to create distinct Top/Bottom brackets
        # Top 8 (0-7): High ELO
        # Bottom 7 (8-14): Low ELO
        for i in range(15):
            self.session.player_stats[f"p{i}"] = PlayerStats(player_id=f"p{i}")
            if i < 8:
                self.session.player_stats[f"p{i}"].games_played = 20
                self.session.player_stats[f"p{i}"].wins = 20 # High rating
            else:
                self.session.player_stats[f"p{i}"].games_played = 20
                self.session.player_stats[f"p{i}"].wins = 0 # Low rating

    def test_cross_bracket_fallback(self):
        # Scenario:
        # 8 Players are playing (filling 2 courts, say).
        # But let's say specifically WHO is playing.
        # Playing: p0, p1, p2, p3 (Top) AND p8, p9, p10, p11 (Bottom).
        # Waiting: p4, p5, p6, p7 (Top - 4 players) AND p12, p13, p14 (Bottom - 3 players).
        # Wait... if 4 Top are waiting, they should match with each other!
        
        # We need a split where NEITHER side has 4.
        # Total 15.
        # Playing: p0-p3 (4 Top).
        # Playing: p8-p11 (4 Bottom).
        # Waiting: p4, p5 (2 Top).
        # Waiting: p12, p13, p14 (3 Bottom).
        # Total waiting: 5.
        # Courts empty: 2.
        
        # Strict rule: Top can only play Top. Bottom can only play Bottom.
        # Top has 2 available. Need 4. -> Fail.
        # Bottom has 3 available. Need 4. -> Fail.
        # Result: 5 people waiting, courts empty.
        
        # Setup "Matches" to occupy the others
        # M1: Top players
        self.session.matches.append(Match(id="m1", court_number=1, team1=["p0","p1"], team2=["p2","p3"], status="in-progress"))
        # M2: Bottom players
        self.session.matches.append(Match(id="m2", court_number=2, team1=["p8","p9"], team2=["p10","p11"], status="in-progress"))
        
        # Remaining available: p4, p5, p6, p7 are NOT in matches... wait.
        # I want p4, p5 to be available. p6, p7 should be "unavailable" (say, just finished match? No, let's just put them in M1 for simplicity logic, or just have them be busy).
        # I need 4 Top players busy. p0, p1, p2, p3.
        # I need 2 Top players waiting. p4, p5.
        # What about p6, p7? I need them BUSY too.
        # So M3: p6, p7 vs ... someone?
        # Ah, I only have 8 Top players.
        # p0, p1, p2, p3 are BUSY.
        # p6, p7 are BUSY.
        # p4, p5 are WAITING.
        
        # M3: p6, p7 vs p14 (Bottom? No cross bracket allowed?)
        # If matches are already formed, valid or not, they take players out of availability.
        # So I can just put p6, p7 in a dummy match with anyone.
        # self.session.matches.append(Match(id="m3", court_number=3, team1=["p6","p7"], team2=["p14","p12"], status="in-progress"))
        # Note: M3 is technically invalid cross-bracket but existing matches are ignored by matchmaking logic, they just consume players.
        
        # Now Available:
        # Top: p4, p5. (2 players)
        # Bottom: p13. (1 player? I used p12, p14 in M3).
        # That's only 3 players total. Cannot form match.
        
        # Let's adjust.
        # Top (8): p0-p7.
        # Bottom (7): p8-p14.
        
        # Busy:
        # p0-p3 (Top) -> M1
        # p8-p11 (Bottom) -> M2
        
        # Available:
        # p4-p7 (Top) -> 4 players! They should match!
        # Wait, user said "all 3 courts are rarely used".
        # Maybe the split is different?
        # If available is 3 Top and 3 Bottom. Total 6.
        # Busy: p0-p4 (5 Top). p8-p11 (4 Bottom).
        # M1: p0, p1, p2, p3.
        # M2: p8, p9, p10, p11.
        # p4 is "Busy" (maybe in a singles match? or just manually set to active in another way? Or put in M3 with a placeholder).
        self.session.matches.append(Match(id="m3", court_number=3, team1=["p4"], team2=["p_dummy"], status="in-progress"))
        
        # Now Available:
        # Top: p5, p6, p7 (3 players)
        # Bottom: p12, p13, p14 (3 players)
        # Total 6 players available.
        
        # Debug availability
        players_in_matches = set()
        for match in self.session.matches:
            if match.status in ['in-progress', 'waiting']:
                players_in_matches.update(match.team1 + match.team2)
        available = [p for p in self.session.active_players if p not in players_in_matches]
        print(f"TEST DEBUG: Available players ({len(available)}): {available}")
        
        # Strict logic:
        # Top needs 4. Have 3.
        # Bottom needs 4. Have 3.
        # No match.
        
        populate_empty_courts_competitive_variety(self.session)
        
        # Check new matches
        new_matches = [m for m in self.session.matches if m.status == 'waiting']
        
        # Should have found a match by crossing brackets (e.g. p5,p6,p12,p13)
        self.assertTrue(len(new_matches) > 0, 
                        f"Should create match crossing brackets when courts empty. Available: Top=[p5,p6,p7], Bot=[p12,p13,p14].")

if __name__ == '__main__':
    unittest.main()
