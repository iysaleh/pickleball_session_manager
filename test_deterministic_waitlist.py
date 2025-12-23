#!/usr/bin/env python3

"""
Test for Deterministic Waitlist System

Tests the advanced waitlist prediction system that shows players exactly 
which courts they're waiting for and what match outcomes will get them 
into their next game.
"""

import sys
sys.path.append('.')

from python.session import create_session
from python.types import SessionConfig, Player, Match
from python.deterministic_waitlist import (
    PredictedMatch, WaitlistPrediction, calculate_waitlist_predictions,
    format_prediction_display, get_court_outcome_dependencies
)
from python.competitive_variety import calculate_elo_rating
from python.utils import create_player_stats
from python.time_manager import initialize_time_manager

# Initialize time manager for tests
initialize_time_manager()

def test_basic_waitlist_prediction():
    """Test basic waitlist prediction with simple scenario"""
    print("=== Test Basic Waitlist Prediction ===")
    
    # Create players with different skill levels
    players = [
        Player("alice", "Alice", 4.0),  # Strong
        Player("bob", "Bob", 3.5),      # Average
        Player("charlie", "Charlie", 3.0), # Weak
        Player("diana", "Diana", 3.8),   # Good
        Player("eve", "Eve", 3.2),       # Weak-Average
        Player("frank", "Frank", 4.2),   # Very Strong
        Player("grace", "Grace", 3.6),   # Average-Good
        Player("henry", "Henry", 2.8),   # Very Weak
        Player("ivan", "Ivan", 3.9),     # Good-Strong
        Player("julia", "Julia", 3.1),   # Weak
        Player("kevin", "Kevin", 3.7),   # Average-Good
        Player("laura", "Laura", 4.1),   # Strong
    ]
    
    # Create session with competitive variety
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=3,
        pre_seeded_ratings=True
    )
    session = create_session(config)
    
    # Simulate some matches in progress
    # Court 1: Strong vs Average players
    court1_match = Match(
        id="match1",
        court_number=1,
        team1=["alice", "bob"],      # Alice (4.0) + Bob (3.5) = 7.5 avg
        team2=["diana", "charlie"],   # Diana (3.8) + Charlie (3.0) = 6.8 avg
        status="in-progress"
    )
    
    # Court 2: Mixed skill levels
    court2_match = Match(
        id="match2", 
        court_number=2,
        team1=["frank", "eve"],      # Frank (4.2) + Eve (3.2) = 7.4 avg
        team2=["grace", "henry"],    # Grace (3.6) + Henry (2.8) = 6.4 avg
        status="in-progress"
    )
    
    session.matches = [court1_match, court2_match]
    
    # Waiting players: ivan, julia, kevin, laura (4 players waiting for court 3)
    # Expected rankings: laura (4.1), ivan (3.9), kevin (3.7), julia (3.1)
    
    # Calculate predictions
    predictions = calculate_waitlist_predictions(session)
    
    print(f"Number of predictions generated: {len(predictions)}")
    
    # Check that we have predictions for each waiting player
    waiting_players = ["ivan", "julia", "kevin", "laura"]
    for player in waiting_players:
        player_predictions = [p for p in predictions if p.player_id == player]
        assert len(player_predictions) > 0, f"No prediction for {player}"
        print(f"\n{player.title()} predictions:")
        for pred in player_predictions:
            print(f"  {format_prediction_display(session, pred)}")
    
    print("\n✅ Basic waitlist prediction test passed")


def test_complex_scenario_prediction():
    """Test complex scenario with multiple match outcomes affecting different players"""
    print("\n=== Test Complex Scenario Prediction ===")
    
    # Create 16 players for fuller scenario
    players = []
    skill_ratings = [4.5, 4.0, 3.8, 3.5, 3.3, 3.0, 2.8, 2.5, 4.2, 3.9, 3.6, 3.4, 3.1, 2.9, 2.7, 4.1]
    for i, rating in enumerate(skill_ratings):
        players.append(Player(f"player{i+1}", f"Player{i+1}", rating))
    
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=4,
        pre_seeded_ratings=True
    )
    session = create_session(config)
    
    # Create matches on all 4 courts with different skill distributions
    matches = []
    
    # Court 1: Top players
    matches.append(Match(
        id="court1_match",
        court_number=1,
        team1=["player1", "player4"],    # 4.5, 3.5
        team2=["player2", "player3"],    # 4.0, 3.8
        status="in-progress"
    ))
    
    # Court 2: Mid-tier players
    matches.append(Match(
        id="court2_match", 
        court_number=2,
        team1=["player5", "player8"],    # 3.3, 2.5
        team2=["player6", "player7"],    # 3.0, 2.8
        status="in-progress"
    ))
    
    # Court 3: Mixed players
    matches.append(Match(
        id="court3_match",
        court_number=3,
        team1=["player9", "player12"],   # 4.2, 3.4
        team2=["player10", "player11"],  # 3.9, 3.6
        status="in-progress"
    ))
    
    # Court 4: Lower tier
    matches.append(Match(
        id="court4_match",
        court_number=4,
        team1=["player13", "player15"],  # 3.1, 2.7
        team2=["player14", "player16"],  # 2.9, 4.1 (note: mixed!)
        status="in-progress"
    ))
    
    session.matches = matches
    
    # Calculate predictions for all waiting players
    predictions = calculate_waitlist_predictions(session)
    
    # Group predictions by player
    player_predictions = {}
    for pred in predictions:
        if pred.player_id not in player_predictions:
            player_predictions[pred.player_id] = []
        player_predictions[pred.player_id].append(pred)
    
    print(f"Total predictions: {len(predictions)}")
    print(f"Players with predictions: {len(player_predictions)}")
    
    # Display predictions for each waiting player
    for player_id in sorted(player_predictions.keys()):
        player_name = next(p.name for p in players if p.id == player_id)
        skill = next(p.skill_rating for p in players if p.id == player_id)
        print(f"\n{player_name} (Skill: {skill}):")
        
        for pred in player_predictions[player_id]:
            display = format_prediction_display(session, pred)
            print(f"  {display}")
    
    print("\n✅ Complex scenario prediction test passed")


def test_court_outcome_dependencies():
    """Test the court outcome dependency analysis"""
    print("\n=== Test Court Outcome Dependencies ===")
    
    # Create simple 8-player scenario
    players = [
        Player(f"p{i}", f"Player{i}", 3.0 + i*0.2) 
        for i in range(8)
    ]
    
    config = SessionConfig(
        mode='competitive-variety', 
        session_type='doubles',
        players=players,
        courts=2,
        pre_seeded_ratings=True
    )
    session = create_session(config)
    
    # Court 1 match in progress
    court1_match = Match(
        id="c1_match",
        court_number=1,
        team1=["p0", "p1"],
        team2=["p2", "p3"], 
        status="in-progress"
    )
    
    # Court 2 match in progress  
    court2_match = Match(
        id="c2_match",
        court_number=2,
        team1=["p4", "p5"],
        team2=["p6", "p7"],
        status="in-progress"
    )
    
    session.matches = [court1_match, court2_match]
    
    # Test dependencies for each waiting player
    # (No players waiting in this scenario - all on courts)
    # Let's modify to have some waiting
    
    # Remove p6 and p7 from court 2, so they're waiting
    court2_match.team2 = ["p6"]  # Invalid match, but for testing
    
    dependencies = get_court_outcome_dependencies(session, "p7")  # p7 is waiting
    print(f"Dependencies for p7: {dependencies}")
    
    # Dependencies should show which courts p7 is waiting for
    assert len(dependencies) > 0, "Should have court dependencies for waiting player"
    
    print("\n✅ Court outcome dependencies test passed")


def test_prediction_formatting():
    """Test the prediction display formatting"""
    print("\n=== Test Prediction Formatting ===")
    
    # Create minimal session for testing formatting
    players = [Player("alice", "Alice"), Player("bob", "Bob")]
    config = SessionConfig(mode='competitive-variety', session_type='doubles', players=players, courts=1)
    session = create_session(config)
    
    # Create sample prediction
    predicted_match = PredictedMatch(
        court_number=1,
        team1=["alice"],
        team2=["bob"],
        needed_outcome="red_wins"
    )
    
    prediction = WaitlistPrediction(
        player_id="alice",
        priority_rank=1,
        predicted_matches=[predicted_match],
        court_dependencies={1: ["red_wins"]},
        estimated_wait_scenarios={"best_case": 10, "worst_case": 20, "expected": 15}
    )
    
    # Test formatting
    display = format_prediction_display(session, prediction)
    print(f"Sample format: {display}")
    
    # Should contain court number and outcome
    assert "Court 1" in display, "Should contain court number"
    assert "R" in display or "B" in display, "Should contain team indicator"
    
    print("\n✅ Prediction formatting test passed")


if __name__ == "__main__":
    test_basic_waitlist_prediction()
    test_complex_scenario_prediction()
    test_court_outcome_dependencies()
    test_prediction_formatting()
    print("\n🎉 All deterministic waitlist tests passed!")