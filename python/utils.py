"""
Utility functions for session management
"""

import uuid
import random
from typing import List, Dict, Set, Tuple, Optional
from .types import Player, PlayerStats, AdvancedConfig, KingOfCourtConfig, RoundRobinConfig


def generate_id() -> str:
    """Generate a unique ID"""
    return str(uuid.uuid4())


def get_default_advanced_config() -> AdvancedConfig:
    """Get default advanced configuration"""
    return AdvancedConfig(
        king_of_court=KingOfCourtConfig(),
        round_robin=RoundRobinConfig()
    )


def shuffle_list(items: List) -> List:
    """Shuffle a list and return a new list"""
    shuffled = items.copy()
    random.shuffle(shuffled)
    return shuffled


def is_pair_banned(player1_id: str, player2_id: str, banned_pairs: List[Tuple[str, str]]) -> bool:
    """Check if a pair of players is banned from playing together"""
    for p1, p2 in banned_pairs:
        if (p1 == player1_id and p2 == player2_id) or (p1 == player2_id and p2 == player1_id):
            return True
    return False


def create_player_stats(player_id: str) -> PlayerStats:
    """Create a new player stats object"""
    return PlayerStats(player_id=player_id)


def get_players_with_fewest_games(
    player_ids: List[str],
    stats_map: Dict[str, PlayerStats]
) -> List[str]:
    """Get players who have played the fewest games"""
    if not player_ids:
        return []
    
    min_games = min(stats_map.get(pid, PlayerStats(player_id=pid)).games_played for pid in player_ids)
    return [pid for pid in player_ids if stats_map.get(pid, PlayerStats(player_id=pid)).games_played == min_games]


def generate_combinations(items: List, r: int) -> List[Tuple]:
    """Generate all combinations of r items from list"""
    from itertools import combinations
    return list(combinations(items, r))


def calculate_partner_diversity(
    team: List[str],
    stats_map: Dict[str, PlayerStats]
) -> int:
    """Calculate diversity score for a team based on partner history"""
    if len(team) < 2:
        return 0
    
    # For doubles: check if these two players have played together before
    if len(team) == 2:
        player1_stats = stats_map.get(team[0])
        if player1_stats and team[1] in player1_stats.partners_played:
            return 0  # High repetition = low score
        return 100  # New partnership = high score
    
    return 0


def get_all_busy_courts(matches: List) -> int:
    """Count number of courts currently in use"""
    active_statuses = {'in-progress', 'waiting'}
    court_numbers = set()
    
    for match in matches:
        if match.status in active_statuses:
            court_numbers.add(match.court_number)
    
    return len(court_numbers)
