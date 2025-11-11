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


def populate_empty_courts(session: Session) -> Session:
    """
    Fill empty courts with matches from the queue.
    
    Used in Round Robin mode to distribute queued matches to available courts.
    """
    if session.config.mode != 'round-robin':
        # Only auto-populate for round-robin for now
        return session
    
    if not session.match_queue:
        return session
    
    # Find empty courts
    empty_courts = get_empty_courts(session)
    
    # Assign matches to empty courts
    for court_num in empty_courts:
        if not session.match_queue:
            break
        
        queued_match = session.match_queue.pop(0)
        
        # Create match on this court
        match = Match(
            id=generate_id(),
            court_number=court_num,
            team1=queued_match.team1,
            team2=queued_match.team2,
            status='waiting'
        )
        
        session.matches.append(match)
    
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


# Import the missing function
from .session import get_active_matches, get_completed_matches
