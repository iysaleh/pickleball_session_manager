"""
Match queue management - handles distributing queued matches to courts
"""

from typing import List, Optional, Dict
from .types import Session, Match, QueuedMatch, MatchStatus
from .utils import generate_id


def get_empty_courts(session: Session) -> List[int]:
    """Get court numbers that are currently empty (no active match)"""
    active_courts = set()
    
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            active_courts.add(match.court_number)
    
    empty_courts = []
    for court_num in range(1, session.config.courts + 1):
        if court_num not in active_courts:
            empty_courts.append(court_num)
    
    return empty_courts


def get_match_for_court(session: Session, court_number: int) -> Optional[Match]:
    """Get the current active match for a court (if any)"""
    for match in session.matches:
        if match.court_number == court_number and match.status in ['waiting', 'in-progress']:
            return match
    
    return None


def get_players_in_active_matches(session: Session) -> set:
    """Get set of all player IDs currently in active matches"""
    players_in_matches = set()
    
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            players_in_matches.update(match.team1)
            players_in_matches.update(match.team2)
    
    return players_in_matches


def can_queue_match_be_assigned(queued_match: 'QueuedMatch', session: Session) -> bool:
    """Check if a queued match can be assigned without player conflicts"""
    players_in_matches = get_players_in_active_matches(session)
    match_players = set(queued_match.team1 + queued_match.team2)
    return not (match_players & players_in_matches)


def score_queued_match(queued_match: 'QueuedMatch', session: Session) -> float:
    """
    Score a queued match based on how long the players have waited.
    Higher score = players have waited longer = should play sooner.
    """
    total_wait = 0
    for player_id in queued_match.team1 + queued_match.team2:
        if player_id in session.player_stats:
            total_wait += session.player_stats[player_id].games_waited
    return total_wait


def calculate_match_repetition_penalty(team1: List[str], team2: List[str], session: Session) -> int:
    """
    Calculate a penalty score for a proposed match based on recent player pairings.
    Higher penalty = more repetition = worse match.
    
    Counts:
    - Direct partnerships (played together as teammates)
    - Direct oppositions (played against each other)
    
    Each counts as 1 repetition point.
    """
    penalty = 0
    
    # Count partnership repetitions within team1
    for i in range(len(team1)):
        for j in range(i + 1, len(team1)):
            p1, p2 = team1[i], team1[j]
            if p1 in session.player_stats and p2 in session.player_stats:
                if p2 in session.player_stats[p1].partners_played:
                    penalty += 1
    
    # Count partnership repetitions within team2
    for i in range(len(team2)):
        for j in range(i + 1, len(team2)):
            p1, p2 = team2[i], team2[j]
            if p1 in session.player_stats and p2 in session.player_stats:
                if p2 in session.player_stats[p1].partners_played:
                    penalty += 1
    
    # Count opponent repetitions
    for p1 in team1:
        for p2 in team2:
            if p1 in session.player_stats and p2 in session.player_stats:
                if p2 in session.player_stats[p1].opponents_played:
                    penalty += 1
    
    return penalty


def should_create_dynamic_match(session: Session) -> bool:
    """
    Determine if we should create a dynamic match from waiting players.
    
    Logic:
    - With 12+ players: Only create if we have enough variety options
      Return True if there ARE valid low-penalty matches available
      Return False if all waiting matches have high repetition
    - With 8-11 players: More lenient, allow repetition
    - With <8 players: Create immediately
    """
    total_players = len(session.active_players)
    
    if total_players < 12:
        # For small player counts, always try to create matches
        return True
    
    # For 12+ players, check if we have good variety options
    waiting_ids = get_waiting_players(session)
    
    if len(waiting_ids) < 4:
        # Not enough waiting players
        return False
    
    # Generate some potential matches from waiting players
    from python.roundrobin import generate_combinations
    combos = list(generate_combinations(waiting_ids, 4))
    
    if not combos:
        return False
    
    # Check the best (lowest penalty) match
    best_penalty = float('inf')
    
    for combo in combos[:10]:  # Check first 10 combos (don't need to check all)
        partitions = [
            ([combo[0], combo[1]], [combo[2], combo[3]]),
            ([combo[0], combo[2]], [combo[1], combo[3]]),
            ([combo[0], combo[3]], [combo[1], combo[2]]),
        ]
        for team1, team2 in partitions:
            penalty = calculate_match_repetition_penalty(list(team1), list(team2), session)
            best_penalty = min(best_penalty, penalty)
    
    # Threshold: If best available match has 0 or 1 repetitions, create it
    # Otherwise wait for more variety options
    return best_penalty <= 1


def should_prevent_immediate_matching(session: Session) -> bool:
    """
    Determine if we should wait for other courts to finish before creating new matches.
    
    This prevents repetitive matchups when there are enough players and courts.
    But allows immediate matching to keep courts busy.
    
    We wait only when there are many courts still actively playing, meaning
    we can afford to be picky about variety.
    
    Logic:
    - For 12+ players: Wait only if ALL courts are full (4 active)
      (fills immediately if even 1 court is empty)
    - For 8-11 players: Wait only if 3+ courts are active
    - For <8 players: Create matches immediately (limited options)
    """
    total_players = len(session.active_players)
    active_matches = len([m for m in session.matches if m.status in ['waiting', 'in-progress']])
    total_courts = session.config.courts
    
    if total_players >= 12:
        # With 12+ players and 4 courts full, we can wait
        # But fill immediately if even 1 court is empty
        return active_matches >= total_courts
    elif total_players >= 8:
        # With 8-11 players, wait only if most courts active
        return active_matches >= 3
    else:
        # With <8 players, fill immediately (limited options)
        return False


def generate_dynamic_matches(session: Session) -> List['QueuedMatch']:
    """
    Generate new matches from waiting players and available players.
    This allows us to create matches on-the-fly when courts become empty.
    
    Avoids excessive repetition by not pairing players who have just played together.
    """
    from python.roundrobin import generate_combinations
    from .types import QueuedMatch
    
    # Get players who are waiting (not in active matches)
    waiting_ids = get_waiting_players(session)
    
    if len(waiting_ids) < 4:
        # Need at least 4 players to form a match
        return []
    
    # Generate all possible 4-player combinations from waiting players
    combos = list(generate_combinations(waiting_ids, 4))
    
    # Convert to match pairs (team configurations)
    dynamic_matches = []
    for combo in combos:
        # Generate team pairings
        partitions = [
            ([combo[0], combo[1]], [combo[2], combo[3]]),
            ([combo[0], combo[2]], [combo[1], combo[3]]),
            ([combo[0], combo[3]], [combo[1], combo[2]]),
        ]
        for team1, team2 in partitions:
            dynamic_matches.append(QueuedMatch(team1=list(team1), team2=list(team2)))
    
    return dynamic_matches


def populate_empty_courts(session: Session) -> Session:
    """
    Fill empty courts with matches from the queue or dynamically generated matches.
    
    Used in Round Robin mode to distribute queued matches to available courts.
    Only assigns matches where no players are already in active games.
    Prioritizes matches with players who have waited longest.
    
    For Competitive Variety mode, uses specialized matching rules.
    
    For variety: With 12+ players, only creates dynamic matches if they have
    low repetition (0-1 prior pairings). Otherwise waits for queue matches.
    """
    # Handle competitive-variety mode separately
    if session.config.mode == 'competitive-variety':
        from .competitive_variety import populate_empty_courts_competitive_variety
        populate_empty_courts_competitive_variety(session)
        return session
    
    if session.config.mode != 'round-robin':
        # Only auto-populate for round-robin and competitive-variety for now
        return session
    
    # Find empty courts
    empty_courts = get_empty_courts(session)
    
    if not empty_courts:
        return session
    
    # Assign matches to empty courts, prioritizing by wait time
    matches_to_remove = []
    for court_num in empty_courts:
        # Try to find a match from the queue first
        valid_matches = []
        
        if session.match_queue:
            for i, queued_match in enumerate(session.match_queue):
                if can_queue_match_be_assigned(queued_match, session):
                    score = score_queued_match(queued_match, session)
                    valid_matches.append((score, i, queued_match, True))  # True = from queue
        
        # If no queue matches available, check if we should create dynamic matches
        if not valid_matches and should_create_dynamic_match(session):
            dynamic = generate_dynamic_matches(session)
            for queued_match in dynamic:
                if can_queue_match_be_assigned(queued_match, session):
                    penalty = calculate_match_repetition_penalty(queued_match.team1, queued_match.team2, session)
                    # Only add if penalty is low (0-1 repetitions)
                    if penalty <= 1:
                        score = score_queued_match(queued_match, session)
                        # Use negative penalty so lower repetition is prioritized
                        valid_matches.append((score - penalty * 100, -1, queued_match, False))  # False = dynamic
        
        if not valid_matches:
            # No valid matches available for this court
            break
        
        # Sort by score (highest first = players waited longest)
        valid_matches.sort(reverse=True, key=lambda x: x[0])
        score, match_idx, best_match, from_queue = valid_matches[0]
        
        # Create match on this court
        match = Match(
            id=generate_id(),
            court_number=court_num,
            team1=best_match.team1,
            team2=best_match.team2,
            status='waiting'
        )
        
        session.matches.append(match)
        
        # Only track queue removals (not dynamic matches)
        if from_queue and match_idx >= 0:
            matches_to_remove.append(match_idx)
    
    # Remove assigned matches from queue (in reverse order to maintain indices)
    for i in sorted(matches_to_remove, reverse=True):
        session.match_queue.pop(i)
    
    return session
    
    return session


def get_waiting_players(session: Session) -> List[str]:
    """Get list of players currently waiting (not in a match)"""
    players_in_matches = set()
    
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            players_in_matches.update(match.team1)
            players_in_matches.update(match.team2)
    
    waiting = []
    for player_id in session.active_players:
        if player_id not in players_in_matches:
            waiting.append(player_id)
    
    return waiting


def get_session_summary(session: Session) -> Dict:
    """Get a summary of the current session state"""
    active_matches = get_active_matches(session)
    completed_matches = get_completed_matches(session)
    waiting_players = get_waiting_players(session)
    
    return {
        'active_matches': len(active_matches),
        'completed_matches': len(completed_matches),
        'waiting_players': len(waiting_players),
        'total_players': len(session.active_players),
        'empty_courts': len(get_empty_courts(session)),
        'total_courts': session.config.courts,
        'queued_matches': len(session.match_queue),
    }


def advance_session(session: Session) -> Session:
    """
    Advance the session state by populating empty courts
    with matches from the queue.
    
    Call this whenever the state changes (match completed, player added, etc)
    """
    return populate_empty_courts(session)


def get_queued_matches_for_display(session: Session) -> List[tuple]:
    """Get queued matches formatted for display as (team1_str, team2_str) tuples"""
    from .session import get_player_name
    
    result = []
    for queued_match in session.match_queue:
        team1_names = [get_player_name(session, pid) for pid in queued_match.team1]
        team2_names = [get_player_name(session, pid) for pid in queued_match.team2]
        team1_str = ", ".join(team1_names)
        team2_str = ", ".join(team2_names)
        result.append((team1_str, team2_str))
    
    return result


# Import the missing functions
from .session import get_active_matches, get_completed_matches
