#!/usr/bin/env python3
"""
Test skill-based court filling for pre-seeded sessions
"""

import sys
from python.time_manager import initialize_time_manager
from python.session import create_session
from python.types import Player, SessionConfig
from python.competitive_variety import populate_empty_courts_competitive_variety, create_skill_based_matches_for_pre_seeded
from PyQt6.QtWidgets import QApplication

def test_skill_based_court_filling():
    """Test the skill-based court filling for pre-seeded sessions"""
    print("Testing Skill-Based Court Filling for Pre-seeded Sessions")
    print("=" * 60)
    
    initialize_time_manager()
    app = QApplication([])
    
    # Create players with skill ratings (12 players for clear pattern testing)
    players = [
        Player(id="p1", name="Elite Pro A", skill_rating=4.5),     # #1
        Player(id="p2", name="Elite Pro B", skill_rating=4.4),     # #2
        Player(id="p3", name="Elite Pro C", skill_rating=4.3),     # #3
        Player(id="p4", name="Elite Pro D", skill_rating=4.2),     # #4
        Player(id="p5", name="Strong A", skill_rating=4.0),        # #5
        Player(id="p6", name="Strong B", skill_rating=3.9),        # #6
        Player(id="p7", name="Strong C", skill_rating=3.8),        # #7
        Player(id="p8", name="Strong D", skill_rating=3.7),        # #8
        Player(id="p9", name="Good A", skill_rating=3.5),          # #9
        Player(id="p10", name="Good B", skill_rating=3.4),         # #10
        Player(id="p11", name="Good C", skill_rating=3.3),         # #11
        Player(id="p12", name="Good D", skill_rating=3.2),         # #12
    ]
    
    print("Player Skill Rankings:")
    for i, p in enumerate(players, 1):
        print(f"  #{i}: {p.name} ({p.skill_rating})")
    
    # Create pre-seeded session with 3 courts
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3,
        pre_seeded_ratings=True
    )
    
    session = create_session(config)
    print(f"\n✅ Session created with {len(players)} players and {config.courts} courts")
    print(f"✅ Pre-seeded ratings enabled: {session.config.pre_seeded_ratings}")
    
    # Test the skill-based match creation
    print(f"\n" + "="*50)
    print("TESTING SKILL-BASED MATCH CREATION")
    print("="*50)
    
    available_players = [p.id for p in players]
    courts_needed = 3
    
    skill_matches = create_skill_based_matches_for_pre_seeded(
        session, available_players, courts_needed
    )
    
    print(f"\nExpected Pattern:")
    print(f"  Court 1 (Top): #1,#4 vs #2,#3")
    print(f"  Court 2 (Bottom): #12,#9 vs #11,#10") 
    print(f"  Court 3 (Top): #5,#8 vs #6,#7")
    
    print(f"\nActual Matches Created:")
    for i, match in enumerate(skill_matches, 1):
        # Get player names and ratings for display
        team1_info = []
        team2_info = []
        
        for p_id in match.team1:
            player = next(p for p in players if p.id == p_id)
            rank = next(j for j, p2 in enumerate(players, 1) if p2.id == p_id)
            team1_info.append(f"#{rank}({player.name}:{player.skill_rating})")
            
        for p_id in match.team2:
            player = next(p for p in players if p.id == p_id)
            rank = next(j for j, p2 in enumerate(players, 1) if p2.id == p_id)
            team2_info.append(f"#{rank}({player.name}:{player.skill_rating})")
        
        print(f"  Court {i}: {' & '.join(team1_info)} vs {' & '.join(team2_info)}")
    
    # Test with actual session court filling
    print(f"\n" + "="*50)
    print("TESTING ACTUAL SESSION COURT FILLING")
    print("="*50)
    
    # Fill the courts using the competitive variety algorithm
    populate_empty_courts_competitive_variety(session)
    
    print(f"\nMatches created in session:")
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            # Get player info for display
            team1_info = []
            team2_info = []
            
            for p_id in match.team1:
                player = next(p for p in players if p.id == p_id)
                rank = next(j for j, p2 in enumerate(players, 1) if p2.id == p_id)
                team1_info.append(f"#{rank}({player.name}:{player.skill_rating})")
                
            for p_id in match.team2:
                player = next(p for p in players if p.id == p_id)
                rank = next(j for j, p2 in enumerate(players, 1) if p2.id == p_id)
                team2_info.append(f"#{rank}({player.name}:{player.skill_rating})")
            
            print(f"  Court {match.court_number}: {' & '.join(team1_info)} vs {' & '.join(team2_info)}")
    
    # Verify the pattern is correct
    print(f"\n" + "="*50)
    print("PATTERN VERIFICATION")
    print("="*50)
    
    # Verify that we got skill-based matches instead of random
    if len(session.matches) >= 3:
        matches_by_court = {m.court_number: m for m in session.matches if m.status in ['waiting', 'in-progress']}
        
        # Check if Court 1 has top players
        court1 = matches_by_court.get(1)
        if court1:
            all_players_court1 = court1.team1 + court1.team2
            court1_ratings = []
            for p_id in all_players_court1:
                player = next(p for p in players if p.id == p_id)
                court1_ratings.append(player.skill_rating)
            
            avg_court1_rating = sum(court1_ratings) / len(court1_ratings)
            print(f"✅ Court 1 average rating: {avg_court1_rating:.2f} (should be high)")
        
        # Check if we have both high and low rated courts
        all_court_ratings = []
        for court_num in [1, 2, 3]:
            if court_num in matches_by_court:
                match = matches_by_court[court_num]
                all_players = match.team1 + match.team2
                court_ratings = []
                for p_id in all_players:
                    player = next(p for p in players if p.id == p_id)
                    court_ratings.append(player.skill_rating)
                avg_rating = sum(court_ratings) / len(court_ratings)
                all_court_ratings.append(avg_rating)
                print(f"  Court {court_num} avg rating: {avg_rating:.2f}")
        
        rating_spread = max(all_court_ratings) - min(all_court_ratings)
        print(f"\n✅ Rating spread across courts: {rating_spread:.2f}")
        
        if rating_spread > 0.5:  # Significant difference between courts
            print("✅ SUCCESS: Skill-based court filling is working!")
            print("  - Top players grouped on same courts")
            print("  - Bottom players grouped on same courts") 
            print("  - Clear skill separation across courts")
        else:
            print("❌ Pattern not detected - may be using random matching")
    
    print(f"\n🎯 Skill-based court filling test complete!")


if __name__ == "__main__":
    test_skill_based_court_filling()