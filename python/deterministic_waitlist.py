"""
Deterministic Waitlist Prediction System

Advanced system that evaluates current matches and predicts exactly which court 
outcomes will allow waiting players to enter their next game. Shows players
specific courts and required match outcomes (e.g., "Court 1R, Court 4RB").

This system analyzes:
1. Current ELO rankings and how they change based on match outcomes
2. Competitive variety constraints (partner/opponent repetition) 
3. Roaming range restrictions for skill-based matching
4. Wait time priorities and queue position changes

For each waiting player, calculates which specific court outcomes will create
a valid matchmaking opportunity for them.
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from .pickleball_types import Session, Match, Player
from .competitive_variety import (
    calculate_elo_rating, get_player_ranking, get_roaming_rank_range,
    can_play_with_player, is_provisional, populate_empty_courts_competitive_variety
)
from .wait_priority import sort_players_by_wait_priority, calculate_wait_priority_info
from .queue_manager import get_waiting_players
from .session import get_player_name
import copy

@dataclass
class PredictedMatch:
    """Represents a potential match that could be created for a waiting player"""
    court_number: int
    team1: List[str]  # Player IDs
    team2: List[str]  # Player IDs
    needed_outcome: str  # "red_wins", "blue_wins", or "either"
    probability_estimate: float = 0.5  # Estimated likelihood of this outcome

@dataclass  
class WaitlistPrediction:
    """Complete prediction for a waiting player"""
    player_id: str
    priority_rank: int  # Current position in wait priority queue
    predicted_matches: List[PredictedMatch]
    court_dependencies: Dict[int, List[str]]  # Court number -> list of outcomes
    estimated_wait_scenarios: Dict[str, int]  # "best_case", "worst_case" -> minutes


def simulate_match_outcome(session: Session, match: Match, team1_wins: bool) -> Session:
    """
    Create a copy of the session with a simulated match outcome.
    Updates ELO ratings and stats as if the match completed with given result.
    
    Args:
        session: Current session state
        match: Match to simulate completion
        team1_wins: True if team1 wins, False if team2 wins
        
    Returns:
        New session with simulated outcome applied
    """
    # Create deep copy to avoid modifying original
    sim_session = copy.deepcopy(session)
    
    # Find the corresponding match in the copy
    sim_match = None
    for m in sim_session.matches:
        if m.id == match.id:
            sim_match = m
            break
    
    if not sim_match:
        return sim_session
    
    # Simulate match completion with dummy scores
    if team1_wins:
        team1_score, team2_score = 11, 9
    else:
        team1_score, team2_score = 9, 11
    
    # Update match status
    sim_match.status = 'completed'
    sim_match.score = {'team1_score': team1_score, 'team2_score': team2_score}
    
    # Update player statistics
    players_in_match = set(sim_match.team1 + sim_match.team2)
    
    # Update team1 players
    for player_id in sim_match.team1:
        if player_id not in sim_session.player_stats:
            continue
        stats = sim_session.player_stats[player_id]
        stats.games_played += 1
        stats.total_points_for += team1_score
        stats.total_points_against += team2_score
        if team1_wins:
            stats.wins += 1
        else:
            stats.losses += 1
        
        # Update opponent tracking
        for opponent_id in sim_match.team2:
            stats.opponents_played[opponent_id] = stats.opponents_played.get(opponent_id, 0) + 1
        
        # Update partner tracking
        for partner_id in sim_match.team1:
            if partner_id != player_id:
                stats.partners_played[partner_id] = stats.partners_played.get(partner_id, 0) + 1
    
    # Update team2 players
    for player_id in sim_match.team2:
        if player_id not in sim_session.player_stats:
            continue
        stats = sim_session.player_stats[player_id]
        stats.games_played += 1
        stats.total_points_for += team2_score
        stats.total_points_against += team1_score
        if not team1_wins:
            stats.wins += 1
        else:
            stats.losses += 1
        
        # Update opponent tracking
        for opponent_id in sim_match.team1:
            stats.opponents_played[opponent_id] = stats.opponents_played.get(opponent_id, 0) + 1
        
        # Update partner tracking
        for partner_id in sim_match.team2:
            if partner_id != player_id:
                stats.partners_played[partner_id] = stats.partners_played.get(partner_id, 0) + 1
    
    # Update games_waited for players not in this match
    for player_id in sorted(sim_session.active_players):
        if player_id not in players_in_match:
            if player_id in sim_session.player_stats:
                sim_session.player_stats[player_id].games_waited += 1
    
    return sim_session


def find_potential_matches_for_player(session: Session, player_id: str) -> List[PredictedMatch]:
    """
    Find all potential matches a waiting player could enter if courts become available.
    
    Analyzes current rankings, constraints, and potential match combinations to determine
    which courts finishing with which outcomes would create valid matchmaking opportunities.
    
    Args:
        session: Current session state
        player_id: ID of waiting player to analyze
        
    Returns:
        List of PredictedMatch objects showing possible match scenarios
    """
    if session.config.mode != 'competitive-variety':
        return []
    
    # Get current waiting players
    waiting_players = get_waiting_players(session)
    if player_id not in waiting_players:
        return []
    
    # Get active matches that could finish
    active_matches = [m for m in session.matches if m.status == 'in-progress']
    if not active_matches:
        return []
    
    potential_matches = []
    
    # For each active match, simulate both possible outcomes
    for match in active_matches:
        court_num = match.court_number
        
        # Simulate team1 wins
        sim_session_t1 = simulate_match_outcome(session, match, team1_wins=True)
        matches_t1 = check_player_gets_match(sim_session_t1, player_id, court_num)
        for predicted_match in matches_t1:
            predicted_match.needed_outcome = "red_wins"  # team1 = red
            potential_matches.append(predicted_match)
        
        # Simulate team2 wins
        sim_session_t2 = simulate_match_outcome(session, match, team1_wins=False)
        matches_t2 = check_player_gets_match(sim_session_t2, player_id, court_num)
        for predicted_match in matches_t2:
            predicted_match.needed_outcome = "blue_wins"  # team2 = blue
            potential_matches.append(predicted_match)
    
    return potential_matches


def check_player_gets_match(sim_session: Session, player_id: str, court_num: int) -> List[PredictedMatch]:
    """
    Check if a player gets a match in the simulated session on the specified court.
    
    Args:
        sim_session: Session with simulated match outcome
        player_id: Player to check for
        court_num: Court number that just finished
        
    Returns:
        List of PredictedMatch if player gets assigned to that court
    """
    # Create a temporary copy to test match assignment
    test_session = copy.deepcopy(sim_session)
    
    # Remove the completed match from the specified court
    test_session.matches = [m for m in test_session.matches 
                           if not (m.court_number == court_num and m.status == 'completed')]
    
    # Try to populate the now-empty court
    initial_match_count = len([m for m in test_session.matches 
                              if m.court_number == court_num and m.status != 'completed'])
    
    # Use competitive variety algorithm to fill empty courts
    populate_empty_courts_competitive_variety(test_session)
    
    # Check if any new match on this court includes our player
    new_matches = [m for m in test_session.matches 
                  if m.court_number == court_num and m.status == 'waiting']
    
    predicted_matches = []
    for match in new_matches:
        if player_id in match.team1 or player_id in match.team2:
            predicted_matches.append(PredictedMatch(
                court_number=court_num,
                team1=match.team1,
                team2=match.team2,
                needed_outcome="",  # Will be set by caller
                probability_estimate=0.5
            ))
    
    return predicted_matches


def calculate_waitlist_predictions(session: Session) -> List[WaitlistPrediction]:
    """
    Calculate comprehensive waitlist predictions for all waiting players.
    
    For each waiting player, determines:
    1. Their current priority rank in the wait queue
    2. Which court outcomes could lead to them getting a match
    3. Estimated wait times under different scenarios
    
    Args:
        session: Current session state
        
    Returns:
        List of WaitlistPrediction objects, one per waiting player
    """
    waiting_players = get_waiting_players(session)
    if not waiting_players:
        return []
    
    # Sort waiting players by wait priority  
    sorted_waiters = sort_players_by_wait_priority(session, waiting_players, reverse=True)
    
    predictions = []
    
    for rank, player_id in enumerate(sorted_waiters, 1):
        # Find potential matches for this player
        potential_matches = find_potential_matches_for_player(session, player_id)
        
        # Group by court and outcome
        court_deps = {}
        for match in potential_matches:
            court = match.court_number
            if court not in court_deps:
                court_deps[court] = []
            if match.needed_outcome not in court_deps[court]:
                court_deps[court].append(match.needed_outcome)
        
        # Calculate estimated wait scenarios
        wait_scenarios = estimate_wait_times(session, player_id, potential_matches)
        
        prediction = WaitlistPrediction(
            player_id=player_id,
            priority_rank=rank,
            predicted_matches=potential_matches,
            court_dependencies=court_deps,
            estimated_wait_scenarios=wait_scenarios
        )
        
        predictions.append(prediction)
    
    return predictions


def estimate_wait_times(session: Session, player_id: str, 
                       potential_matches: List[PredictedMatch]) -> Dict[str, int]:
    """
    Estimate wait times under different scenarios.
    
    Args:
        session: Current session state
        player_id: Player to analyze
        potential_matches: Potential match opportunities
        
    Returns:
        Dictionary with "best_case", "worst_case", "expected" wait times in minutes
    """
    # Simplified estimation - in practice this would use match duration statistics
    base_match_time = 12  # Average match duration in minutes
    
    if not potential_matches:
        return {
            "best_case": base_match_time * 2,
            "worst_case": base_match_time * 4, 
            "expected": base_match_time * 3
        }
    
    # Best case: Next match to finish gives them a spot
    best_case = base_match_time
    
    # Worst case: All matches finish with wrong outcomes, wait for next round
    worst_case = base_match_time * 2
    
    # Expected: Average of scenarios weighted by probability
    expected = int((best_case + worst_case) / 2)
    
    return {
        "best_case": best_case,
        "worst_case": worst_case,
        "expected": expected
    }


def get_court_outcome_dependencies(session: Session, player_id: str) -> Dict[int, List[str]]:
    """
    Get the specific court outcomes a player depends on to get their next match.
    
    Args:
        session: Current session state
        player_id: Player ID to analyze
        
    Returns:
        Dictionary mapping court number to list of required outcomes
        Example: {1: ["red_wins"], 3: ["blue_wins", "red_wins"]}
    """
    potential_matches = find_potential_matches_for_player(session, player_id)
    
    court_deps = {}
    for match in potential_matches:
        court = match.court_number
        if court not in court_deps:
            court_deps[court] = []
        if match.needed_outcome not in court_deps[court]:
            court_deps[court].append(match.needed_outcome)
    
    return court_deps


def format_prediction_display(session: Session, prediction: WaitlistPrediction) -> str:
    """
    Format a waitlist prediction for display in the GUI.
    
    Generates compact display like: "Noah Taylor [Court 1R, Court 4RB]"
    Where R = red team wins, B = blue team wins, RB = either team wins
    
    Args:
        session: Current session state
        prediction: Prediction to format
        
    Returns:
        Formatted display string
    """
    player_name = get_player_name(session, prediction.player_id)
    
    if not prediction.court_dependencies:
        return f"{player_name} [No immediate opportunities]"
    
    court_strings = []
    for court_num in sorted(prediction.court_dependencies.keys()):
        outcomes = prediction.court_dependencies[court_num]
        
        # Convert outcome names to compact format
        outcome_chars = []
        if "red_wins" in outcomes:
            outcome_chars.append("R")
        if "blue_wins" in outcomes:
            outcome_chars.append("B")
        
        if len(outcome_chars) == 2:
            # Both outcomes work
            outcome_str = "RB"
        else:
            outcome_str = "".join(outcome_chars)
        
        court_strings.append(f"Court {court_num}{outcome_str}")
    
    dependencies_str = ", ".join(court_strings)
    return f"{player_name} [{dependencies_str}]"


def get_deterministic_waitlist_display(session: Session) -> List[str]:
    """
    Get the complete deterministic waitlist display for the GUI.
    
    Returns a list of formatted strings showing each waiting player and their
    court dependencies, ordered by wait priority.
    
    Args:
        session: Current session state
        
    Returns:
        List of display strings for the waitlist
    """
    predictions = calculate_waitlist_predictions(session)
    
    display_lines = []
    for prediction in predictions:
        display_line = format_prediction_display(session, prediction)
        display_lines.append(display_line)
    
    return display_lines


def update_waitlist_with_predictions(session: Session) -> None:
    """
    Update the session's waitlist display with deterministic predictions.
    
    This can be called whenever match state changes to refresh the predictions.
    
    Args:
        session: Session to update (modified in place)
    """
    # For now, just store predictions in session for GUI access
    # In practice, this might update a dedicated waitlist display field
    predictions = calculate_waitlist_predictions(session)
    
    # Store in session advanced config for GUI access
    if not hasattr(session.advanced_config, 'waitlist_predictions'):
        session.advanced_config.waitlist_predictions = predictions
    else:
        session.advanced_config.waitlist_predictions = predictions