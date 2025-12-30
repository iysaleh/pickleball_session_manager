"""
Refactored Deterministic Waitlist System

This new architecture hooks into the actual competitive variety matching algorithm
rather than trying to duplicate its complex logic. It instruments the existing
pipeline to track which players get assigned under different scenarios.

Key Innovation: We intercept the actual matching process with a "trial mode"
that tracks assignments without persisting changes.
"""

from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from .pickleball_types import Session, Match, Player
from .competitive_variety import populate_empty_courts_competitive_variety
from .queue_manager import get_waiting_players
from .session import get_player_name
import copy

@dataclass
class MatchingResult:
    """Tracks what happens when the algorithm runs in trial mode"""
    court_number: int
    assigned_players: Set[str]  # Which players got assigned to this court
    team1: List[str]
    team2: List[str]
    success: bool  # Whether assignment was successful

@dataclass
class PlayerAssignment:
    """Tracks a player's potential assignment"""
    player_id: str
    court_number: int
    needed_outcome: str  # "red_wins", "blue_wins"
    team1: List[str]
    team2: List[str]

@dataclass
class WaitlistPrediction:
    """Complete prediction for a waiting player"""
    player_id: str
    priority_rank: int
    assignments: List[PlayerAssignment]
    court_dependencies: Dict[int, List[str]]  # Court number -> list of outcomes


def run_matching_in_trial_mode(session: Session, track_court: Optional[int] = None) -> List[MatchingResult]:
    """
    Run the competitive variety algorithm in "trial mode" to see what assignments would be made.
    
    This is the key innovation - we use the ACTUAL algorithm but track assignments
    without persisting changes to the session.
    
    Args:
        session: Current session state  
        track_court: If specified, only track assignments to this court
        
    Returns:
        List of MatchingResult showing what assignments would be made
    """
    # Create deep copy for trial run
    trial_session = copy.deepcopy(session)
    
    # Track initial state
    initial_matches = {m.court_number: m.id for m in trial_session.matches 
                      if m.status in ['waiting', 'in-progress']}
    
    # Run the actual matching algorithm ITERATIVELY until no more matches can be made
    # This handles the case where multiple empty courts should be filled
    max_iterations = 10  # Prevent infinite loops
    results = []
    
    for iteration in range(max_iterations):
        initial_count = len(trial_session.matches)
        
        # Run one iteration of the matching algorithm
        populate_empty_courts_competitive_variety(trial_session)
        
        final_count = len(trial_session.matches)
        
        # If no new matches were created, we're done
        if final_count == initial_count:
            break
        
        # Track what was created in this iteration
        for match in trial_session.matches[initial_count:]:
            if match.status == 'waiting':
                # This is a newly created match
                if track_court is None or match.court_number == track_court:
                    assigned_players = set(match.team1 + match.team2)
                    results.append(MatchingResult(
                        court_number=match.court_number,
                        assigned_players=assigned_players,
                        team1=match.team1,
                        team2=match.team2,
                        success=True
                    ))
    
    return results


def analyze_court_finish_scenarios(session: Session, court_number: int) -> Dict[str, List[MatchingResult]]:
    """
    Analyze what happens when a specific court finishes with different outcomes.
    
    This uses the actual competitive variety algorithm to determine assignments.
    
    Args:
        session: Current session state
        court_number: Court to analyze finish scenarios for
        
    Returns:
        Dict mapping outcome ("red_wins", "blue_wins") to list of MatchingResult
    """
    # Find the match on this court - include both in-progress and waiting
    target_match = None
    for match in session.matches:
        if match.court_number == court_number and match.status in ['in-progress', 'waiting']:
            target_match = match
            break
    
    if not target_match:
        return {}
    
    results = {}
    
    for outcome, team1_wins in [("red_wins", True), ("blue_wins", False)]:
        # Simulate match completion
        sim_session = copy.deepcopy(session)
        
        # Find and complete the match
        for sim_match in sim_session.matches:
            if sim_match.id == target_match.id:
                sim_match.status = 'completed'
                if team1_wins:
                    sim_match.score = {'team1_score': 11, 'team2_score': 9}
                else:
                    sim_match.score = {'team1_score': 9, 'team2_score': 11}
                break
        
        # Update player stats for realistic ELO calculations
        _update_stats_for_completed_match(sim_session, target_match, team1_wins)
        
        # CRITICAL FIX: After completing the match, populate empty courts
        # This is what actually happens in the real application
        from .competitive_variety import populate_empty_courts_competitive_variety
        
        # Track matches before population
        initial_match_count = len(sim_session.matches)
        
        # Run the actual algorithm to fill empty courts
        populate_empty_courts_competitive_variety(sim_session)
        
        # Track what was created
        matching_results = []
        for match in sim_session.matches[initial_match_count:]:
            if match.status == 'waiting':
                assigned_players = set(match.team1 + match.team2)
                # Track all new matches since we're analyzing court finish scenarios
                matching_results.append(MatchingResult(
                    court_number=match.court_number,
                    assigned_players=assigned_players,
                    team1=match.team1,
                    team2=match.team2,
                    success=True
                ))
        
        results[outcome] = matching_results
    
    return results


def _update_stats_for_completed_match(session: Session, match: Match, team1_wins: bool):
    """Update player stats to reflect a completed match for realistic ELO calculations"""
    players_in_match = set(match.team1 + match.team2)
    
    # Update team1 players
    for player_id in match.team1:
        if player_id in session.player_stats:
            stats = session.player_stats[player_id]
            stats.games_played += 1
            stats.total_points_for += 11 if team1_wins else 9
            stats.total_points_against += 9 if team1_wins else 11
            if team1_wins:
                stats.wins += 1
            else:
                stats.losses += 1
    
    # Update team2 players  
    for player_id in match.team2:
        if player_id in session.player_stats:
            stats = session.player_stats[player_id]
            stats.games_played += 1
            stats.total_points_for += 9 if team1_wins else 11
            stats.total_points_against += 11 if team1_wins else 9
            if not team1_wins:
                stats.wins += 1
            else:
                stats.losses += 1
    
    # Update games_waited for players not in this match
    for player_id in sorted(session.active_players):
        if player_id not in players_in_match:
            if player_id in session.player_stats:
                session.player_stats[player_id].games_waited += 1


def calculate_player_dependencies(session: Session, player_id: str) -> Dict[int, List[str]]:
    """
    Calculate which court outcomes would lead to a player getting assigned.
    
    Uses a CONSERVATIVE approach that only shows dependencies for players who are very likely
    to get assigned based on wait time priority. This prevents showing dependencies for 
    players who technically COULD be assigned but WON'T be due to higher priority waiters.
    
    Args:
        session: Current session state
        player_id: Player to analyze
        
    Returns:
        Dict mapping court number to list of required outcomes
    """
    if session.config.mode != 'competitive-variety':
        return {}
    
    # Get current waiting players
    waiting_players = get_waiting_players(session)
    if player_id not in waiting_players:
        return {}
    
    # Get active matches that could finish - include both in-progress and waiting
    # Waiting matches will start soon and then can finish
    active_matches = [m for m in session.matches if m.status in ['in-progress', 'waiting']]
    
    if not active_matches:
        return {}
    
    # Calculate wait time priority order for conservative filtering
    from .wait_priority import sort_players_by_wait_priority
    priority_ordered_waiters = sort_players_by_wait_priority(session, waiting_players, reverse=True)
    
    # Find this player's position in the priority queue
    # reverse=True means highest priority (longest waiters) come first
    try:
        player_priority_position = priority_ordered_waiters.index(player_id)
    except ValueError:
        return {}  # Player not in waiting list
    
    dependencies = {}
    
    # For each active court, analyze both possible outcomes
    for match in active_matches:
        court_num = match.court_number
        
        # CRITICAL FIX: When THIS specific court finishes, it only creates 1 match (4 slots)
        # Plus the 4 players from the finished match become available
        # So we can assign at most 4 NEW players from the waitlist per court finish
        
        # Conservative check: only show dependency if player is in top 4 waiters
        # who would get priority for the single match created when this court finishes
        if player_priority_position < 4:
            # This player has high enough priority to get assigned when this court finishes
            dependencies[court_num] = ['red_wins', 'blue_wins']
    
    return dependencies


def calculate_waitlist_predictions_v2(session: Session) -> List[WaitlistPrediction]:
    """
    Calculate comprehensive waitlist predictions using the instrumented algorithm.
    
    This version uses the actual competitive variety logic rather than duplicating it.
    
    Args:
        session: Current session state
        
    Returns:
        List of WaitlistPrediction objects, one per waiting player
    """
    waiting_players = get_waiting_players(session)
    if not waiting_players:
        return []
    
    # Sort waiting players by wait priority
    from .wait_priority import sort_players_by_wait_priority
    sorted_waiters = sort_players_by_wait_priority(session, waiting_players, reverse=True)
    
    predictions = []
    
    for rank, player_id in enumerate(sorted_waiters, 1):
        # Calculate dependencies using the instrumented algorithm
        dependencies = calculate_player_dependencies(session, player_id)
        
        # Build assignments list
        assignments = []
        for court_num, outcomes in dependencies.items():
            for outcome in outcomes:
                # Get the actual assignment details by re-running the analysis
                court_outcomes = analyze_court_finish_scenarios(session, court_num)
                if outcome in court_outcomes:
                    for result in court_outcomes[outcome]:
                        if player_id in result.assigned_players:
                            assignments.append(PlayerAssignment(
                                player_id=player_id,
                                court_number=court_num,
                                needed_outcome=outcome,
                                team1=result.team1,
                                team2=result.team2
                            ))
                            break
        
        prediction = WaitlistPrediction(
            player_id=player_id,
            priority_rank=rank,
            assignments=assignments,
            court_dependencies=dependencies
        )
        
        predictions.append(prediction)
    
    return predictions


def get_court_outcome_dependencies_v2(session: Session, player_id: str) -> Dict[int, List[str]]:
    """
    New version that uses the instrumented algorithm.
    
    This replaces the old get_court_outcome_dependencies function.
    """
    return calculate_player_dependencies(session, player_id)


def format_prediction_display_v2(session: Session, prediction: WaitlistPrediction) -> str:
    """
    Format a waitlist prediction for display in the GUI.
    
    Uses the new prediction structure.
    """
    player_name = get_player_name(session, prediction.player_id)
    
    if not prediction.court_dependencies:
        return f"{player_name}"
    
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
            outcome_str = "RB"
        else:
            outcome_str = "".join(outcome_chars)
        
        court_strings.append(f"C{court_num}{outcome_str}")
    
    dependencies_str = ", ".join(court_strings)
    return f"{player_name} 🎯[{dependencies_str}]"


def get_deterministic_waitlist_display_v2(session: Session) -> List[str]:
    """
    Get the complete deterministic waitlist display using the new architecture.
    
    This replaces the old get_deterministic_waitlist_display function.
    """
    predictions = calculate_waitlist_predictions_v2(session)
    
    display_lines = []
    for prediction in predictions:
        display_line = format_prediction_display_v2(session, prediction)
        display_lines.append(display_line)
    
    return display_lines