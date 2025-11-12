"""
Competitive Variety Matchmaking - ensures players mix with different opponents/partners each game
"""

from typing import List, Dict, Tuple, Set, Optional
from .types import Player, QueuedMatch, Session


def populate_empty_courts_competitive_variety(session: Session) -> None:
    """
    Populate empty courts using competitive variety matchmaking rules.
    
    Rules:
    1. At start: fill up to numberOfEmptyCourts*4 players with available players
    2. Same 4 players never make a game together on any court after just playing together
    3. After each match finishes, players must mix with players from another court or newcomers
    4. Track which courts have mixed together - they can't mix again until another court finishes
    5. In 3+ court situations (12+ players), courts cannot mix back-to-back with same court
    6. Prefer mixing with players who haven't played yet before those who have
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
    
    # At start of session, just fill courts from waitlist (don't make any matches for now)
    # Once the full algorithm is built, we'll fill from the queue
    pass


def build_match_for_court_competitive_variety(
    session: Session,
    court_number: int,
    available_players: List[str]
) -> Optional[QueuedMatch]:
    """
    Build a match for a specific court using competitive variety rules.
    Returns None if no valid match can be made.
    """
    if session.config.mode != 'competitive-variety':
        return None
    
    # For now, return None - shell implementation
    return None


def can_players_form_match_together(
    session: Session,
    player_ids: List[str]
) -> bool:
    """
    Check if these 4 players can form a match together based on variety rules.
    Returns False if they just played together or violate mixing rules.
    """
    if session.config.mode != 'competitive-variety':
        return True
    
    # For now, always return False - shell implementation
    return False


def update_variety_tracking_after_match(
    session: Session,
    court_number: int,
    team1: List[str],
    team2: List[str]
) -> None:
    """
    Update variety tracking after a match completes.
    Tracks which court each player last played on and which courts have mixed.
    """
    if session.config.mode != 'competitive-variety':
        return
    
    # Update player_last_court
    for player_id in team1 + team2:
        session.player_last_court[player_id] = court_number
    
    # Update court_players
    session.court_players[court_number] = team1 + team2


def get_available_players_for_mixing(
    session: Session,
    court_number: int,
    num_needed: int
) -> List[str]:
    """
    Get available players for mixing with a specific court.
    Prefers players who haven't played yet, then those from other courts.
    """
    if session.config.mode != 'competitive-variety':
        return []
    
    # For now, return empty list - shell implementation
    return []


def should_allow_court_mixing(
    session: Session,
    court_a: int,
    court_b: int
) -> bool:
    """
    Determine if two courts should be allowed to mix players.
    Enforces rules about back-to-back mixing in 3+ court situations.
    """
    if session.config.mode != 'competitive-variety':
        return False
    
    num_active_courts = len([m for m in session.matches if m.status == 'in-progress'])
    
    # With 3+ active courts, courts cannot mix back-to-back
    if num_active_courts >= 3:
        # Check if these courts have already mixed in the history
        mix_key_a = (min(court_a, court_b), max(court_a, court_b))
        mix_key_b = (max(court_a, court_b), min(court_a, court_b))
        
        # For now, just return False to be conservative
        return False
    
    return False
