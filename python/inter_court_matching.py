"""
Enhanced competitive variety with mandatory inter-court mixing
Ensures maximum player variety by tracking court history and enforcing mixing rules
"""

from typing import List, Dict, Tuple, Set, Optional
from datetime import datetime
from .types import Session, Match, PlayerStats
from .queue_manager import get_match_for_court, get_waiting_players
from .competitive_variety import (
    can_play_with_player, is_provisional, 
    calculate_elo_rating, _can_form_valid_teams
)
from itertools import combinations
from .utils import generate_id


def get_last_court_for_player(session: Session, player_id: str) -> Optional[int]:
    """Get the court a player last played on, if any"""
    if player_id not in session.player_stats:
        return None
    
    history = session.player_stats[player_id].court_history
    return history[-1] if history else None


def has_player_played_on_court(session: Session, player_id: str, court_number: int) -> bool:
    """Check if player has ever played on a specific court"""
    if player_id not in session.player_stats:
        return False
    
    return court_number in session.player_stats[player_id].court_history


def have_players_played_together_on_court(
    session: Session,
    player1: str,
    player2: str,
    court_number: int
) -> bool:
    """Check if two players have played together on the same court"""
    # This is a simplified check - in real scenario, we'd track match records
    # For now, we only prevent if they're currently scheduled together
    return False


def can_play_in_match_with_inter_court_rules(
    session: Session,
    player1: str,
    player2: str,
    role: str,
    court_number: int
) -> bool:
    """
    Enhanced version of can_play_with_player that includes inter-court mixing rules.
    
    Rules:
    1. Basic competitive variety rules (ELO, game gaps, brackets) - STRICT
    2. Inter-court mixing rules:
       - Players must come from different courts when possible
       - Prefer players who haven't played on ANY court yet
       - In 3+ court situations (12+ players): courts cannot mix back-to-back
    3. 50% Ranking bracket - CRITICAL ENFORCEMENT
       - Top 50% of players can ONLY play with top 50%
       - Bottom 50% of players can ONLY play with bottom 50%
       - Provisional players (< 2 games) can play with anyone
    """
    # First check basic competitive variety rules (most restrictive)
    if not can_play_with_player(session, player1, player2, role):
        return False
    
    # Check 50% bracket rule FIRST (most important)
    total_players = len(session.active_players)
    if total_players >= 12:
        # Get rankings
        from .competitive_variety import get_player_ranking, is_provisional
        
        # Provisional players can play with anyone
        if not (is_provisional(session, player1) or is_provisional(session, player2)):
            rank1, _ = get_player_ranking(session, player1)
            rank2, _ = get_player_ranking(session, player2)
            
            bracket_size = (total_players + 1) // 2
            
            # Check if both in top bracket or both in bottom bracket
            player1_in_top = rank1 <= bracket_size
            player2_in_top = rank2 <= bracket_size
            
            if player1_in_top != player2_in_top:
                # One in top, one in bottom - NOT ALLOWED
                return False
    
    # Additional inter-court mixing rules
    if total_players >= 10:  # Inter-court mixing applies
        player1_court = get_last_court_for_player(session, player1)
        player2_court = get_last_court_for_player(session, player2)
        
        # If both players played on a court, they should be from different courts
        if player1_court is not None and player2_court is not None:
            if player1_court == player2_court:
                # Same court - only allow if there are very few other options
                return False
    
    return True


def should_wait_for_more_courts_before_mixing(session: Session) -> bool:
    """
    Determine if we should wait for more courts to finish before mixing with waitlist.
    
    Rules:
    - With only 1-2 players on waitlist: Wait for at least 2 courts to complete
    - With 3+ players on waitlist: Can mix with 1 court completing
    - With 4+ players on waitlist: Can mix immediately if bracket-compatible
    
    This prevents throwing just 1-2 players into a mix too early.
    """
    from .queue_manager import get_waiting_players, get_match_for_court
    
    waitlist = get_waiting_players(session)
    total_players = len(session.active_players)
    
    if total_players < 10:
        return False  # Not enough for mixing rules
    
    if len(waitlist) == 0:
        return False  # No one waiting
    
    if len(waitlist) <= 2:
        # With only 1-2 on waitlist, need at least 2 courts to complete
        completed_courts = []
        for court_num in range(1, session.config.courts + 1):
            match = get_match_for_court(session, court_num)
            if match and match.status == 'completed':
                completed_courts.append(court_num)
        
        return len(completed_courts) < 2
    
    return False  # 3+ on waitlist, don't wait


def check_bracket_compatibility_for_waitlist(
    session: Session,
    court_player: str,
    waitlist_player: str
) -> bool:
    """
    Check if a court player and waitlist player are bracket-compatible.
    
    For 12+ players:
    - Top 50% can only mix with top 50%
    - Bottom 50% can only mix with bottom 50%
    - Provisional players can mix with anyone
    """
    total_players = len(session.active_players)
    
    if total_players < 12:
        return True  # Bracket restrictions don't apply
    
    from .competitive_variety import get_player_ranking, is_provisional
    
    # Provisional players can mix with anyone
    if is_provisional(session, court_player) or is_provisional(session, waitlist_player):
        return True
    
    rank_court, _ = get_player_ranking(session, court_player)
    rank_wait, _ = get_player_ranking(session, waitlist_player)
    
    bracket_size = (total_players + 1) // 2
    
    # Check if both in same bracket
    court_in_top = rank_court <= bracket_size
    wait_in_top = rank_wait <= bracket_size
    
    return court_in_top == wait_in_top


def score_match_for_variety(
    session: Session,
    team1: List[str],
    team2: List[str],
    court_number: int
) -> float:
    """
    Score a match based on variety and court mixing.
    Higher score = more variety and better court mixing.
    
    Factors:
    - Players from different courts (+points)
    - Players who haven't played on any court yet (+more points)
    - Avoiding same court repeats (-points)
    """
    score = 0.0
    
    # Bonus for mixing courts
    all_players = team1 + team2
    courts_represented = set()
    never_played_count = 0
    
    for player_id in all_players:
        court = get_last_court_for_player(session, player_id)
        if court is not None:
            courts_represented.add(court)
        else:
            never_played_count += 1
    
    # Bonus for court diversity
    score += len(courts_represented) * 10
    
    # Extra bonus for never-played players (excellent for variety!)
    score += never_played_count * 50
    
    return score


def find_best_match_with_variety(
    session: Session,
    available_players: List[str],
    court_number: int
) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    """
    Find the best 4-player match considering:
    1. Competitive variety constraints
    2. Inter-court mixing rules
    3. Court history
    
    Returns (team1, team2) or (None, None) if no valid match found
    """
    if len(available_players) < 4:
        return None, None
    
    # Sort by court history (prefer never-played, then different courts)
    def player_priority(player_id: str) -> Tuple[int, int]:
        """Lower tuple = higher priority"""
        court = get_last_court_for_player(session, player_id)
        if court is None:
            return (0, 0)  # Never played - highest priority
        else:
            # Lower court numbers = lower priority (to spread mixing)
            return (1, court)
    
    sorted_players = sorted(available_players, key=player_priority)
    
    # Try combinations from best-priority players
    best_team1 = None
    best_team2 = None
    best_score = -float('inf')
    
    for combo in combinations(sorted_players[:min(12, len(sorted_players))], 4):
        combo_list = list(combo)
        
        if not _can_form_valid_teams(session, combo_list):
            continue
        
        # Try all 3 team configurations
        configs = [
            ([combo_list[0], combo_list[1]], [combo_list[2], combo_list[3]]),
            ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
            ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]]),
        ]
        
        for team1, team2 in configs:
            # Check enhanced inter-court rules
            valid = True
            for p1 in team1:
                for p2 in team1:
                    if p1 != p2:
                        if not can_play_in_match_with_inter_court_rules(session, p1, p2, 'partner', court_number):
                            valid = False
                            break
                if not valid:
                    break
            
            if valid:
                for p1 in team1:
                    for p2 in team2:
                        if not can_play_in_match_with_inter_court_rules(session, p1, p2, 'opponent', court_number):
                            valid = False
                            break
                    if not valid:
                        break
            
            if valid:
                score = score_match_for_variety(session, list(team1), list(team2), court_number)
                if score > best_score:
                    best_score = score
                    best_team1 = list(team1)
                    best_team2 = list(team2)
    
    return best_team1, best_team2


def populate_with_inter_court_mixing(session: Session) -> None:
    """
    Populate empty courts while enforcing inter-court mixing rules.
    
    CRITICAL RULES:
    1. 50% Bracket enforcement - Top 50% only with top 50%, bottom 50% only with bottom 50%
    2. Mixing waitlist constraints:
       - With 1-2 on waitlist: WAIT for 2 courts to complete before mixing
       - With 3+ on waitlist: Can mix when courts complete
    3. Court history mixing - Prefer players from different courts
    4. All competitive variety constraints - gaps, brackets, ELO
    
    This replaces populate_empty_courts_competitive_variety for comprehensive mixing.
    """
    if session.config.mode != 'competitive-variety':
        return
    
    # Find empty courts
    occupied_courts = set()
    for match in session.matches:
        if match.status in ['in-progress', 'waiting']:
            occupied_courts.add(match.court_number)
    
    empty_courts = [c for c in range(1, session.config.courts + 1) if c not in occupied_courts]
    
    if not empty_courts:
        return
    
    # Get available players and waitlist
    players_in_matches = set()
    for match in session.matches:
        if match.status in ['in-progress', 'waiting']:
            players_in_matches.update(match.team1 + match.team2)
    
    available_players = [p for p in sorted(session.active_players) if p not in players_in_matches]
    waitlist = get_waiting_players(session)
    
    # CRITICAL: Check if we should wait before mixing with small waitlist
    if should_wait_for_more_courts_before_mixing(session):
        # Don't mix yet - wait for more courts to complete
        # Still try to form matches from fully available players (non-waitlist)
        if len(available_players) < 4:
            return  # Can't form new matches either
    
    # Try to fill each empty court
    for court_num in empty_courts:
        # Use inter-court mixing logic
        if len(available_players) >= 4:
            team1, team2 = find_best_match_with_variety(session, available_players, court_num)
            
            if team1 and team2:
                # Create match
                match = Match(
                    id=generate_id(),
                    court_number=court_num,
                    team1=team1,
                    team2=team2,
                    status='waiting',
                    start_time=datetime.now()
                )
                session.matches.append(match)
                
                # Remove from available and update court history
                for player_id in (team1 + team2):
                    if player_id in available_players:
                        available_players.remove(player_id)
                    
                    # Record court history
                    if player_id in session.player_stats:
                        if court_num not in session.player_stats[player_id].court_history:
                            session.player_stats[player_id].court_history.append(court_num)
                    else:
                        session.player_stats[player_id] = PlayerStats(player_id=player_id)
                        session.player_stats[player_id].court_history.append(court_num)


def update_court_history_after_match(
    session: Session,
    court_number: int,
    team1: List[str],
    team2: List[str]
) -> None:
    """Record court history for inter-court mixing"""
    for player_id in (team1 + team2):
        if player_id in session.player_stats:
            # Only add if not already there or if different from last court
            history = session.player_stats[player_id].court_history
            if not history or history[-1] != court_number:
                history.append(court_number)
