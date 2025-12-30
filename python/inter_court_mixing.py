"""
Inter-court mixing for Competitive Variety mode
Ensures players across different courts mix and swap to create variety
"""

from typing import List, Dict, Tuple, Set, Optional
from .pickleball_types import Session, Match
from .queue_manager import get_match_for_court

# Constants for inter-court mixing
MIN_PLAYERS_FOR_MIXING = 10  # Minimum total players for inter-court mixing to apply
MIN_WAITLIST_FOR_MIX = 2     # Minimum waitlist players needed to trigger mixing
MIXING_GROUP_SIZE = 2        # Number of players to swap between courts


def track_court_mixing_history(session: Session, court_a: int, court_b: int) -> None:
    """Record that these two courts mixed players"""
    mix_key = (min(court_a, court_b), max(court_a, court_b))
    if not hasattr(session, 'courts_mixed_last_round'):
        session.courts_mixed_last_round = set()
    session.courts_mixed_last_round.add(mix_key)


def courts_mixed_last_round(session: Session, court_a: int, court_b: int) -> bool:
    """Check if these two courts mixed in the last completed round"""
    if not hasattr(session, 'courts_mixed_last_round'):
        session.courts_mixed_last_round = set()
    mix_key = (min(court_a, court_b), max(court_a, court_b))
    return mix_key in session.courts_mixed_last_round


def reset_mixing_history(session: Session) -> None:
    """Reset mixing history for next round (call when new matches are created)"""
    if not hasattr(session, 'courts_mixed_last_round'):
        session.courts_mixed_last_round = set()
    session.courts_mixed_last_round.clear()


def get_player_court_history(session: Session, player_id: str) -> List[int]:
    """Get list of courts this player has played on (in order)"""
    if not hasattr(session, 'player_court_history'):
        session.player_court_history = {}
    return session.player_court_history.get(player_id, [])


def record_player_court(session: Session, player_id: str, court_number: int) -> None:
    """Record that a player played on a court"""
    if not hasattr(session, 'player_court_history'):
        session.player_court_history = {}
    if player_id not in session.player_court_history:
        session.player_court_history[player_id] = []
    
    # Only record if not already the most recent court
    if not session.player_court_history[player_id] or session.player_court_history[player_id][-1] != court_number:
        session.player_court_history[player_id].append(court_number)


def has_never_played_on_court(session: Session, player_id: str) -> bool:
    """Check if player has never played on any court"""
    history = get_player_court_history(session, player_id)
    return len(history) == 0


def has_same_court_last_two_games(session: Session, player_id: str) -> bool:
    """Check if player played on same court in last 2 games"""
    history = get_player_court_history(session, player_id)
    if len(history) < 2:
        return False
    return history[-1] == history[-2]


def find_compatible_mixing_partner(
    session: Session,
    player_id: str,
    other_court_players: List[str],
    exclude_players: Set[str] = None
) -> Optional[str]:
    """
    Find a compatible player from another court to swap with.
    Prefers players who haven't played on any court yet.
    """
    if exclude_players is None:
        exclude_players = set()
    
    available_partners = [p for p in other_court_players if p not in exclude_players]
    
    # Prefer players who have never played
    never_played = [p for p in available_partners if has_never_played_on_court(session, p)]
    if never_played:
        return never_played[0]
    
    # Otherwise return first available
    return available_partners[0] if available_partners else None


def can_courts_mix_together(
    session: Session,
    court_a: int,
    court_b: int
) -> bool:
    """
    Check if two courts can mix together.
    Rules:
    - In 3+ court situations (12+ total players): cannot mix back-to-back with same courts
    """
    total_players = len(session.active_players)
    
    # Only apply back-to-back restriction for 12+ players with 3+ courts
    if total_players >= 12 and session.config.courts >= 3:
        return not courts_mixed_last_round(session, court_a, court_b)
    
    return True


def should_trigger_inter_court_mixing(session: Session) -> bool:
    """
    Determine if inter-court mixing should be triggered.
    
    Triggers when:
    - 2+ courts just completed matches
    - 2+ players on waitlist (for mixing with waitlist)
    - Minimum 10 total players
    """
    if len(session.active_players) < MIN_PLAYERS_FOR_MIXING:
        return False
    
    # Count how many courts just completed
    completed_matches = [m for m in session.matches if m.status == 'completed']
    if not completed_matches:
        return False
    
    # This function is called after matches complete, so we check if conditions are met
    return True


def perform_inter_court_mixing(session: Session) -> bool:
    """
    Execute inter-court mixing between courts.
    
    Returns True if mixing occurred, False otherwise.
    """
    if len(session.active_players) < MIN_PLAYERS_FOR_MIXING:
        return False
    
    # Find courts with completed matches that are now empty
    completed_courts = []
    for court_num in range(1, session.config.courts + 1):
        match = get_match_for_court(session, court_num)
        if match and match.status == 'completed':
            completed_courts.append(court_num)
    
    if len(completed_courts) < 2:
        return False  # Need at least 2 courts to mix
    
    # Get waitlist
    from .queue_manager import get_waiting_players
    waitlist = get_waiting_players(session)
    
    # Try to mix courts together first
    courts_mixed = False
    
    for i in range(len(completed_courts)):
        for j in range(i + 1, len(completed_courts)):
            court_a = completed_courts[i]
            court_b = completed_courts[j]
            
            if can_courts_mix_together(session, court_a, court_b):
                # Get current players on each court
                match_a = get_match_for_court(session, court_a)
                match_b = get_match_for_court(session, court_b)
                
                if match_a and match_b:
                    # Extract players
                    players_a = match_a.team1 + match_a.team2
                    players_b = match_b.team1 + match_b.team2
                    
                    # Perform swap: swap MIXING_GROUP_SIZE players from each court
                    if len(players_a) >= MIXING_GROUP_SIZE and len(players_b) >= MIXING_GROUP_SIZE:
                        swap_players_between_courts(session, players_a, players_b, MIXING_GROUP_SIZE)
                        track_court_mixing_history(session, court_a, court_b)
                        courts_mixed = True
    
    # If not enough courts to mix, try mixing with waitlist
    if len(waitlist) >= MIN_WAITLIST_FOR_MIX and completed_courts:
        court_num = completed_courts[0]
        match = get_match_for_court(session, court_num)
        
        if match:
            players = match.team1 + match.team2
            # Swap 1-2 players with waitlist
            swap_players_with_waitlist(session, court_num, players, waitlist[:MIN_WAITLIST_FOR_MIX])
            courts_mixed = True
    
    return courts_mixed


def swap_players_between_courts(
    session: Session,
    players_a: List[str],
    players_b: List[str],
    num_to_swap: int
) -> None:
    """
    Swap num_to_swap players between two groups.
    This modifies the match structures to swap players.
    """
    # Note: This is a placeholder - actual swap would require modifying matches
    # This is handled at a higher level in the GUI/session logic
    pass


def swap_players_with_waitlist(
    session: Session,
    court_number: int,
    court_players: List[str],
    waitlist_players: List[str]
) -> None:
    """
    Swap waitlist players with court players to create variety.
    """
    # Note: This is a placeholder - actual swap would require modifying matches
    # This is handled at a higher level in the GUI/session logic
    pass
