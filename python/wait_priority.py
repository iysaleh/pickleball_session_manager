"""
Wait Time Priority System for Pickleball Session Manager

This module implements sophisticated wait time priority logic that considers:
1. Total accumulated wait time (historical + current session)
2. Dynamic thresholds to determine when wait time differences matter
3. Extensible priority calculation framework

The system ensures players who have waited significantly longer are prioritized
for match placement, while avoiding micro-optimization when all players have
similar wait times.
"""

from typing import List, Tuple, Dict, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from .types import Session, PlayerStats
from .utils import get_current_wait_time

# Configuration constants for wait priority thresholds
MINIMUM_PRIORITY_GAP_SECONDS = 120  # 2 minutes - minimum gap to matter
SIGNIFICANT_WAIT_THRESHOLD_SECONDS = 720  # 12 minutes - when wait becomes "significant"
EXTREME_WAIT_THRESHOLD_SECONDS = 1200  # 20 minutes - when wait becomes "extreme"

@dataclass
class WaitPriorityInfo:
    """Container for a player's wait priority information"""
    player_id: str
    total_wait_seconds: int  # accumulated + current wait time
    current_wait_seconds: int  # just current session wait
    priority_tier: int  # 0=extreme, 1=significant, 2=normal
    games_waited: int  # legacy counter for backward compatibility
    
    @property
    def is_extreme_waiter(self) -> bool:
        """True if player has waited extremely long"""
        return self.total_wait_seconds >= EXTREME_WAIT_THRESHOLD_SECONDS
    
    @property
    def is_significant_waiter(self) -> bool:
        """True if player has waited significantly long"""
        return self.total_wait_seconds >= SIGNIFICANT_WAIT_THRESHOLD_SECONDS
    
    def priority_gap_from(self, other: 'WaitPriorityInfo') -> int:
        """Calculate priority gap in seconds from another player"""
        return abs(self.total_wait_seconds - other.total_wait_seconds)


def calculate_wait_priority_info(session: Session, player_id: str) -> WaitPriorityInfo:
    """
    Calculate comprehensive wait priority information for a player.
    
    Args:
        session: The current session
        player_id: ID of the player to analyze
        
    Returns:
        WaitPriorityInfo containing all priority calculation data
    """
    stats = session.player_stats.get(player_id)
    if not stats:
        # New player - no wait time
        return WaitPriorityInfo(
            player_id=player_id,
            total_wait_seconds=0,
            current_wait_seconds=0,
            priority_tier=2,  # normal
            games_waited=0
        )
    
    current_wait = get_current_wait_time(stats)
    total_wait = stats.total_wait_time + current_wait
    
    # Determine priority tier based on total wait time
    if total_wait >= EXTREME_WAIT_THRESHOLD_SECONDS:
        tier = 0  # extreme priority
    elif total_wait >= SIGNIFICANT_WAIT_THRESHOLD_SECONDS:
        tier = 1  # significant priority  
    else:
        tier = 2  # normal priority
    
    return WaitPriorityInfo(
        player_id=player_id,
        total_wait_seconds=total_wait,
        current_wait_seconds=current_wait,
        priority_tier=tier,
        games_waited=stats.games_waited
    )


def get_wait_priority_groups(session: Session, player_ids: List[str]) -> Dict[int, List[str]]:
    """
    Group players by wait priority tier.
    
    Args:
        session: The current session
        player_ids: List of player IDs to analyze
        
    Returns:
        Dictionary mapping priority tier (0=extreme, 1=significant, 2=normal) to player lists
    """
    groups = {0: [], 1: [], 2: []}
    
    for player_id in player_ids:
        priority_info = calculate_wait_priority_info(session, player_id)
        groups[priority_info.priority_tier].append(player_id)
    
    return groups


def should_prioritize_wait_differences(wait_infos: List[WaitPriorityInfo]) -> bool:
    """
    Determine if wait time differences are significant enough to affect match priority.
    
    This implements the threshold logic where small differences in wait time
    (< 2 minutes) are ignored to avoid micro-optimization.
    
    Args:
        wait_infos: List of WaitPriorityInfo objects to analyze
        
    Returns:
        True if wait time differences should influence matching priority
    """
    if len(wait_infos) < 2:
        return False
    
    # Check if any player has extreme/significant wait time
    has_extreme = any(info.is_extreme_waiter for info in wait_infos)
    has_significant = any(info.is_significant_waiter for info in wait_infos)
    
    if has_extreme or has_significant:
        return True
    
    # Check if the gap between max and min wait times exceeds threshold
    wait_times = [info.total_wait_seconds for info in wait_infos]
    max_wait = max(wait_times)
    min_wait = min(wait_times)
    
    return (max_wait - min_wait) >= MINIMUM_PRIORITY_GAP_SECONDS


def sort_players_by_wait_priority(session: Session, player_ids: List[str], 
                                reverse: bool = True) -> List[str]:
    """
    Sort players by wait priority using the sophisticated wait time algorithm.
    
    Primary sort key: Priority tier (0=extreme > 1=significant > 2=normal)
    Secondary sort key: Total wait time within tier
    Tertiary sort key: Games waited (legacy fallback)
    
    Args:
        session: The current session
        player_ids: List of player IDs to sort
        reverse: If True, highest priority first (default)
        
    Returns:
        List of player IDs sorted by wait priority
    """
    priority_infos = [calculate_wait_priority_info(session, pid) for pid in player_ids]
    
    # Sort by (priority_tier, -total_wait_seconds, -games_waited)
    # Lower tier number = higher priority, higher wait time = higher priority
    priority_infos.sort(
        key=lambda info: (
            info.priority_tier,  # 0 (extreme) comes first
            -info.total_wait_seconds,  # longer wait comes first within tier
            -info.games_waited  # legacy fallback
        ),
        reverse=False  # Lower tuple values come first
    )
    
    result = [info.player_id for info in priority_infos]
    return result if not reverse else result


def get_priority_aware_candidates(session: Session, available_players: List[str], 
                                max_candidates: int = 16) -> List[str]:
    """
    Select match candidates with wait time priority awareness.
    
    This function implements the core logic for selecting which players should
    be considered for matches, prioritizing those who have waited longest while
    maintaining reasonable candidate pool sizes for match generation.
    
    Args:
        session: The current session
        available_players: List of all available player IDs
        max_candidates: Maximum number of candidates to return
        
    Returns:
        List of player IDs sorted by priority (highest first)
    """
    if len(available_players) <= max_candidates:
        return sort_players_by_wait_priority(session, available_players, reverse=True)
    
    # Get wait priority information for all players
    priority_infos = [calculate_wait_priority_info(session, pid) for pid in available_players]
    
    # Group by priority tiers
    groups = {0: [], 1: [], 2: []}
    for info in priority_infos:
        groups[info.priority_tier].append(info)
    
    # Select candidates prioritizing higher tiers
    candidates = []
    remaining_slots = max_candidates
    
    # Take all extreme waiters first
    if groups[0] and remaining_slots > 0:
        extreme_sorted = sorted(groups[0], key=lambda x: -x.total_wait_seconds)
        take_count = min(len(extreme_sorted), remaining_slots)
        candidates.extend([info.player_id for info in extreme_sorted[:take_count]])
        remaining_slots -= take_count
    
    # Then significant waiters
    if groups[1] and remaining_slots > 0:
        significant_sorted = sorted(groups[1], key=lambda x: -x.total_wait_seconds)
        take_count = min(len(significant_sorted), remaining_slots)
        candidates.extend([info.player_id for info in significant_sorted[:take_count]])
        remaining_slots -= take_count
    
    # Fill remaining slots with normal priority players
    if groups[2] and remaining_slots > 0:
        normal_sorted = sorted(groups[2], key=lambda x: -x.total_wait_seconds)
        take_count = min(len(normal_sorted), remaining_slots)
        candidates.extend([info.player_id for info in normal_sorted[:take_count]])
    
    return candidates


def get_legacy_wait_priority_key(session: Session, player_id: str) -> Tuple[int, int]:
    """
    Get legacy wait priority key for backward compatibility.
    
    This maintains the old (games_waited, -games_played) sorting behavior
    for code that hasn't been migrated to the new system yet.
    
    Args:
        session: The current session
        player_id: Player ID to get priority for
        
    Returns:
        Tuple of (games_waited, -games_played) for sorting
    """
    stats = session.player_stats.get(player_id)
    if not stats:
        return (0, 0)
    return (stats.games_waited, -stats.games_played)


def format_wait_time_display(total_seconds: int) -> str:
    """
    Format wait time for display in UI.
    
    Args:
        total_seconds: Total wait time in seconds
        
    Returns:
        Human-readable string like "5m 30s" or "1h 15m"
    """
    if total_seconds < 60:
        return f"{total_seconds}s"
    
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    if minutes < 60:
        if seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {seconds}s"
    
    hours = minutes // 60
    minutes = minutes % 60
    
    if minutes == 0:
        return f"{hours}h"
    return f"{hours}h {minutes}m"
