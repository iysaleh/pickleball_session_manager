"""
Team Competitive Variety Matchmaking
"""

from typing import List, Dict, Tuple, Set, Optional
from datetime import datetime
from .types import Player, QueuedMatch, Session, Match
from .competitive_variety import calculate_elo_rating

# Constants
OPPONENT_REPETITION_BUFFER_RATIO = 0.6  # 60% of teams

def populate_empty_courts_team_competitive_variety(session: Session) -> None:
    """
    Populate empty courts for team competitive variety mode.
    """
    if session.config.mode != 'team-competitive-variety':
        return

    from .utils import generate_id, create_player_stats
    
    # Identify locked teams
    if not session.config.locked_teams:
        return
        
    locked_teams = session.config.locked_teams
    total_teams = len(locked_teams)
    
    if total_teams < 2:
        return
    
    # Find empty courts
    occupied_courts = set()
    for match in session.matches:
        if match.status in ['in-progress', 'waiting']:
            occupied_courts.add(match.court_number)
            
    empty_courts = [c for c in range(1, session.config.courts + 1) if c not in occupied_courts]
    if not empty_courts:
        return

    # Identify available teams
    players_in_matches = set()
    for match in session.matches:
        if match.status in ['in-progress', 'waiting']:
            players_in_matches.update(match.team1 + match.team2)
            
    available_teams = []
    for team in locked_teams:
        if all(p not in players_in_matches for p in team):
            available_teams.append(team)
            
    if len(available_teams) < 2:
        return

    # Sort available teams by priority (max games waited)
    def get_team_priority(team):
        max_waited = -1
        games_played_sum = 0
        for p in team:
            stats = session.player_stats.get(p)
            if stats:
                max_waited = max(max_waited, stats.games_waited)
                games_played_sum += stats.games_played
            else:
                max_waited = max(max_waited, 0)
        # Prioritize high games_waited, then low games_played
        return (max_waited, -games_played_sum)
        
    available_teams.sort(key=get_team_priority, reverse=True)
    
    # Matchmaking Loop
    while empty_courts and len(available_teams) >= 2:
        court_num = empty_courts.pop(0)
        
        team1 = available_teams[0]
        best_team2 = None
        best_score = float('inf')
        
        # Calculate Team 1 ELO
        team1_elo = _calculate_team_elo(session, team1)
        
        # Determine opponent repetition buffer size
        # Buffer size = number of unique opponents to remember
        buffer_size = int(total_teams * OPPONENT_REPETITION_BUFFER_RATIO)
        # Ensure at least 1 if decent number of teams, but not if very few
        if buffer_size < 1 and total_teams >= 3:
            buffer_size = 1
            
        recent_opponents = _get_recent_opponents_for_team(session, team1, buffer_size)
        
        # Search for best opponent
        candidates = []
        
        # First pass: Non-recent opponents
        for team2 in available_teams[1:]:
            team2_tuple = tuple(sorted(team2))
            if team2_tuple not in recent_opponents:
                 candidates.append((team2, False)) # False = not repeated
        
        # If no non-recent opponents, consider repeats (if enabled/allowed)
        if not candidates:
             for team2 in available_teams[1:]:
                 candidates.append((team2, True)) # True = repeated
        
        for team2, is_repeat in candidates:
            team2_elo = _calculate_team_elo(session, team2)
            elo_diff = abs(team1_elo - team2_elo)
            
            # If strictly preferring non-repeats, we already filtered.
            # Just minimize ELO diff now.
            
            if elo_diff < best_score:
                best_score = elo_diff
                best_team2 = team2
        
        if best_team2:
            # Create Match
            match = Match(
                id=generate_id(),
                court_number=court_num,
                team1=team1,
                team2=best_team2,
                status='waiting',
                start_time=datetime.now()
            )
            session.matches.append(match)
            
            # Remove teams from available
            available_teams.pop(0) # Remove team1
            available_teams.remove(best_team2)
            
            # Initialize stats if needed
            for p in team1 + best_team2:
                if p not in session.player_stats:
                    session.player_stats[p] = create_player_stats(p)
        else:
            # Should not happen if we allow repeats fallback
            break

def _calculate_team_elo(session: Session, team: List[str]) -> float:
    if not team:
        return 1500.0
    total = 0
    for p in team:
        stats = session.player_stats.get(p)
        if stats:
            total += calculate_elo_rating(stats)
        else:
            total += 1500.0
    return total / len(team)

def _get_recent_opponents_for_team(session: Session, team: List[str], buffer_size: int) -> Set[Tuple[str, ...]]:
    """
    Get set of recent opponents for a team.
    Opponents are stored as sorted tuples of player IDs.
    Look back through match history.
    """
    completed_matches = [m for m in session.matches if m.status == 'completed']
    team_set = set(team)
    recent = set()
    
    # Iterate backwards
    count = 0
    for m in reversed(completed_matches):
        if count >= buffer_size:
            break
            
        t1_set = set(m.team1)
        t2_set = set(m.team2)
        
        opponent = None
        if t1_set == team_set:
            opponent = tuple(sorted(m.team2))
        elif t2_set == team_set:
            opponent = tuple(sorted(m.team1))
            
        if opponent:
            if opponent not in recent:
                recent.add(opponent)
                count += 1
            
    return recent

def update_team_variety_tracking_after_match(session: Session, court_number: int, team1: List[str], team2: List[str]) -> None:
    """
    Update tracking for team competitive variety.
    """
    if session.config.mode != 'team-competitive-variety':
        return

    # Update player_last_court
    for player_id in team1 + team2:
        session.player_last_court[player_id] = court_number
        if player_id in session.player_stats:
            history = session.player_stats[player_id].court_history
            if not history or history[-1] != court_number:
                history.append(court_number)
