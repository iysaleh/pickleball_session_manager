"""
King of the Court matchmaking engine - ELO-based ranking system
(Phase 2 - Currently a skeleton, will be fully implemented next)
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from .types import Player, Session, PlayerStats, Match
from .utils import generate_id


def calculate_player_rating(
    stats: PlayerStats,
    base_rating: float = 1500,
    min_rating: float = 800,
    max_rating: float = 2200
) -> float:
    """
    Calculate ELO-style rating for a player based on match history
    
    Rating system:
    - New players start at base rating (1500)
    - Ratings adjusted based on win rate with logarithmic scaling
    - Clamped between min and max ratings
    """
    if stats.games_played == 0:
        return base_rating
    
    import math
    
    # Start with base rating
    rating = base_rating
    
    # Adjust based on win rate with logarithmic scaling
    win_rate = stats.wins / stats.games_played
    win_rate_adjustment = math.log(1 + win_rate * 9) * 200  # Logarithmic scaling
    rating += win_rate_adjustment - 200  # Center around baseRating for 50% win rate
    
    # Clamp to min/max
    rating = max(min_rating, min(rating, max_rating))
    
    return rating


def is_player_provisional(stats: PlayerStats, threshold: int = 2) -> bool:
    """Check if a player is still in provisional status"""
    return stats.games_played < threshold


def get_player_rank(
    player_id: str,
    all_player_stats: Dict[str, PlayerStats]
) -> int:
    """Get the rank of a player among all players (1-indexed, 1 is best)"""
    player_rating = calculate_player_rating(all_player_stats[player_id])
    
    # Count how many players have better ratings
    rank = 1
    for other_id, other_stats in all_player_stats.items():
        if other_id != player_id:
            other_rating = calculate_player_rating(other_stats)
            if other_rating > player_rating:
                rank += 1
    
    return rank


def get_players_in_matchmaking_range(
    player_id: str,
    all_players: List[Player],
    all_player_stats: Dict[str, PlayerStats],
    ranking_range_percentage: float = 0.5
) -> List[str]:
    """
    Get players in the matchmaking range for a specific player.
    
    In an 18-player game with 50% range:
    - Player #1 can play with #1-#9 (top half)
    - Player #18 can play with #10-#18 (bottom half)
    """
    # TODO: Implement full KOC matchmaking logic
    pass


def select_best_koc_match(
    available_players: List[str],
    available_courts: int,
    all_player_stats: Dict[str, PlayerStats],
    banned_pairs: List[Tuple[str, str]] = None
) -> Optional[Tuple[List[str], List[str]]]:
    """
    Select the best King of the Court match from available players.
    
    Returns (team1, team2) or None if no valid match possible.
    
    TODO: Implement KOC-specific selection logic:
    - Rank-based player filtering
    - Close-rank prioritization
    - Strategic waiting
    - Variety optimization
    - Ban pair validation
    """
    pass


def create_koc_match(
    court_number: int,
    team1: List[str],
    team2: List[str]
) -> Match:
    """Create a King of the Court match"""
    return Match(
        id=generate_id(),
        court_number=court_number,
        team1=team1,
        team2=team2,
        status='waiting',
        start_time=datetime.now()
    )


def evaluate_koc_session(session: Session) -> Session:
    """
    Evaluate a King of the Court session and create matches.
    
    This is the main loop that handles:
    - Ranking updates
    - New match creation
    - Fair waiting logic
    - Variety optimization
    
    TODO: Full implementation in Phase 2
    """
    # Placeholder implementation
    return session


# Phase 2 will implement:
# 1. Full ELO rating calculation with opponent strength weighting
# 2. Rank-based player filtering (50% rule, etc.)
# 3. Close-rank prioritization algorithm
# 4. Strategic waiting system
# 5. Variety tracking and optimization
# 6. Complex penalty system for bad matchups
# 7. Handle mixed skills (provisional vs established players)
# 8. Real-time ranking adjustments
