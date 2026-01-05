"""
Competitive Round Robin Algorithm - Pre-scheduled skill-balanced matches with human approval

This mode generates all matches for a session upfront, allowing the organizer to review,
approve, reject, or swap players before the session begins. Key features:
- Each player plays exactly N games (default 8)
- No repeat partnerships allowed
- Opponent pair repeats not allowed  
- Individual opponent repeats limited (max 3x)
- Skill-balanced team formation using ELO ratings
- Wait priority integration during runtime
- First bye support
- Fair distribution of matches across the queue
"""

from typing import List, Dict, Tuple, Optional, Set
from itertools import combinations
from dataclasses import dataclass
import random
import math
import uuid
import json

from .pickleball_types import (
    Player, Session, ScheduledMatch, CompetitiveRoundRobinConfig, 
    QueuedMatch, Match, PlayerStats
)


# Constants
DEFAULT_GAMES_PER_PLAYER = 8
MAX_PARTNER_REPEATS = 0  # Never repeat partners
MAX_OPPONENT_PAIR_REPEATS = 0  # Never face same pair twice
MAX_INDIVIDUAL_OPPONENT_REPEATS = 3  # Can face same person up to 3 times


@dataclass
class ScheduleConstraintViolation:
    """Tracks a constraint violation for a scheduled match"""
    violation_type: str  # 'partner_repeat', 'opponent_pair_repeat', 'individual_opponent_exceed'
    players_involved: List[str]  # Player IDs involved in violation
    count: int  # How many times this occurs
    limit: int  # What the limit is


@dataclass
class ScheduleValidationResult:
    """Result of validating a schedule"""
    is_valid: bool
    violations: List[ScheduleConstraintViolation]
    games_per_player: Dict[str, int]  # player_id -> number of games scheduled
    
    
def get_player_skill_rating(session: Session, player_id: str) -> float:
    """Get ELO-style skill rating for a player."""
    # First check for pre-seeded rating
    for player in session.config.players:
        if player.id == player_id and player.skill_rating is not None:
            # Convert skill rating (3.0-5.0+) to ELO scale
            # 3.0 = 1200, 3.5 = 1500, 4.0 = 1800, 4.5 = 2100, 5.0+ = 2200
            return min(2200, max(800, 1200 + (player.skill_rating - 3.0) * 600))
    
    # Fall back to calculated rating from stats
    player_stats = session.player_stats.get(player_id)
    if not player_stats or player_stats.games_played == 0:
        return 1500  # Default base rating
    
    games = player_stats.games_played
    wins = player_stats.wins
    win_rate = wins / games
    
    rating = 1500 + math.log(1 + win_rate * 9) * 200 - 200
    
    if games > 0:
        avg_point_diff = (player_stats.total_points_for - player_stats.total_points_against) / games
        if avg_point_diff != 0:
            rating += math.log(1 + abs(avg_point_diff)) * 50 * (1 if avg_point_diff > 0 else -1)
    
    return max(800, min(2200, rating))


def get_skill_bracket(rating: float) -> str:
    """Categorize player into skill bracket based on ELO rating."""
    if rating >= 2000:
        return 'elite'
    elif rating >= 1700:
        return 'advanced'  
    elif rating >= 1400:
        return 'intermediate'
    elif rating >= 1100:
        return 'beginner'
    else:
        return 'novice'


def calculate_team_balance_score(session: Session, team1: List[str], team2: List[str]) -> float:
    """
    Calculate how balanced a match is (higher = more balanced).
    
    Improved scoring that prefers homogeneous skill matches:
    - 4 high-level players together is GOOD
    - 4 low-level players together is GOOD
    - Mixed high+low vs high+low is acceptable but less preferred
    """
    # Get team ratings
    team1_ratings = [get_player_skill_rating(session, p) for p in team1]
    team2_ratings = [get_player_skill_rating(session, p) for p in team2]
    all_ratings = team1_ratings + team2_ratings
    
    team1_avg = sum(team1_ratings) / len(team1_ratings)
    team2_avg = sum(team2_ratings) / len(team2_ratings)
    
    # Base score - inverse of rating difference (lower diff = higher score)
    rating_diff = abs(team1_avg - team2_avg)
    balance_score = 1000 - rating_diff
    
    # IMPROVED: Bonus for homogeneous skill level in the entire match
    # This encourages matches where all 4 players are similar skill
    all_ratings_range = max(all_ratings) - min(all_ratings)
    
    if all_ratings_range < 200:
        balance_score += 300  # Excellent: all players very similar
    elif all_ratings_range < 400:
        balance_score += 150  # Good: reasonably similar
    elif all_ratings_range > 800:
        balance_score -= 200  # Penalty for very wide skill range
    
    # Bonus for within-team similarity (players on same team are similar)
    team1_gap = max(team1_ratings) - min(team1_ratings) if len(team1_ratings) > 1 else 0
    team2_gap = max(team2_ratings) - min(team2_ratings) if len(team2_ratings) > 1 else 0
    
    # Strong bonus for teams with similar players (e.g., 4.0+4.0 vs 3.5+3.5)
    if team1_gap < 150 and team2_gap < 150:
        balance_score += 200  # Both teams are homogeneous
    elif team1_gap < 300 and team2_gap < 300:
        balance_score += 100
    
    # Penalty for large within-team gaps (e.g., 4.5+3.0 teams)
    balance_score -= (team1_gap + team2_gap) * 0.3
    
    # Bonus for bracket-matched teams
    team1_brackets = [get_skill_bracket(r) for r in team1_ratings]
    team2_brackets = [get_skill_bracket(r) for r in team2_ratings]
    
    if sorted(team1_brackets) == sorted(team2_brackets):
        balance_score += 100  # Perfect bracket match
    
    # Extra bonus if all 4 players are same bracket
    if len(set(team1_brackets + team2_brackets)) == 1:
        balance_score += 200  # All same bracket - excellent match
    
    return balance_score


def validate_schedule(
    session: Session,
    scheduled_matches: List[ScheduledMatch],
    config: CompetitiveRoundRobinConfig
) -> ScheduleValidationResult:
    """
    Validate a schedule against all constraints.
    Returns validation result with any violations found.
    """
    violations = []
    games_per_player: Dict[str, int] = {}
    partnership_count: Dict[str, Dict[str, int]] = {}  # player -> partner -> count
    opponent_pair_count: Dict[str, int] = {}  # "p1,p2" sorted -> count faced
    individual_opponent_count: Dict[str, Dict[str, int]] = {}  # player -> opponent -> count
    
    # Initialize tracking for all players
    for player in session.config.players:
        pid = player.id
        games_per_player[pid] = 0
        partnership_count[pid] = {}
        individual_opponent_count[pid] = {}
    
    # Process each approved match
    approved_matches = [m for m in scheduled_matches if m.status == 'approved']
    
    for match in approved_matches:
        all_players = match.get_all_players()
        
        # Count games per player
        for pid in all_players:
            games_per_player[pid] = games_per_player.get(pid, 0) + 1
        
        # Track partnerships (within teams)
        for team in [match.team1, match.team2]:
            if len(team) == 2:
                p1, p2 = team
                partnership_count.setdefault(p1, {})
                partnership_count.setdefault(p2, {})
                partnership_count[p1][p2] = partnership_count[p1].get(p2, 0) + 1
                partnership_count[p2][p1] = partnership_count[p2].get(p1, 0) + 1
        
        # Track opponent pairs
        opp_pair_key = ','.join(sorted(match.team2))  # team2 as opponent pair
        opponent_pair_count[opp_pair_key] = opponent_pair_count.get(opp_pair_key, 0) + 1
        
        opp_pair_key2 = ','.join(sorted(match.team1))  # team1 as opponent pair  
        opponent_pair_count[opp_pair_key2] = opponent_pair_count.get(opp_pair_key2, 0) + 1
        
        # Track individual opponents
        for p1 in match.team1:
            for p2 in match.team2:
                individual_opponent_count.setdefault(p1, {})
                individual_opponent_count.setdefault(p2, {})
                individual_opponent_count[p1][p2] = individual_opponent_count[p1].get(p2, 0) + 1
                individual_opponent_count[p2][p1] = individual_opponent_count[p2].get(p1, 0) + 1
    
    # Check partnership violations
    for p1, partners in partnership_count.items():
        for p2, count in partners.items():
            if count > config.max_partner_repeats + 1:  # +1 because first is allowed
                violations.append(ScheduleConstraintViolation(
                    violation_type='partner_repeat',
                    players_involved=[p1, p2],
                    count=count,
                    limit=config.max_partner_repeats + 1
                ))
    
    # Check individual opponent violations
    for p1, opponents in individual_opponent_count.items():
        for p2, count in opponents.items():
            if count > config.max_individual_opponent_repeats:
                violations.append(ScheduleConstraintViolation(
                    violation_type='individual_opponent_exceed',
                    players_involved=[p1, p2],
                    count=count,
                    limit=config.max_individual_opponent_repeats
                ))
    
    # Deduplicate violations (each pair reports twice)
    seen_violations = set()
    unique_violations = []
    for v in violations:
        key = (v.violation_type, tuple(sorted(v.players_involved)), v.count)
        if key not in seen_violations:
            seen_violations.add(key)
            unique_violations.append(v)
    
    return ScheduleValidationResult(
        is_valid=len(unique_violations) == 0,
        violations=unique_violations,
        games_per_player=games_per_player
    )


def generate_initial_schedule(
    session: Session,
    config: Optional[CompetitiveRoundRobinConfig] = None
) -> List[ScheduledMatch]:
    """
    Generate an initial schedule of matches for Competitive Round Robin.
    
    ALGORITHM: Round-based generation with variety mixing
    1. Generate matches in "rounds" where each round fills all courts simultaneously
    2. No player appears twice in the same round (guarantees all courts can be used)
    3. Mix skill levels for variety while keeping matches balanced
    4. Track which groups of 4 have played together to avoid repetition
    5. Respects partnership constraints and opponent limits
    
    Returns list of ScheduledMatch objects (all with 'pending' status).
    """
    if config is None:
        config = CompetitiveRoundRobinConfig()
    
    players = session.config.players
    num_players = len(players)
    num_courts = session.config.courts
    
    if num_players < 4:
        return []
    
    # Get first bye players to exclude from initial matches
    first_bye_player_ids = set(session.config.first_bye_players or [])
    
    # Get player ratings
    player_ratings: Dict[str, float] = {}
    for player in players:
        player_ratings[player.id] = get_player_skill_rating(session, player.id)
    
    # Sort players by rating (high to low)
    sorted_players = sorted(players, key=lambda p: player_ratings[p.id], reverse=True)
    all_player_ids = [p.id for p in sorted_players]
    
    target_games = config.games_per_player
    max_games = target_games + 2  # Allow slight overage
    
    # Track constraints
    games_per_player: Dict[str, int] = {pid: 0 for pid in all_player_ids}
    partnership_used: Dict[str, Set[str]] = {pid: set() for pid in all_player_ids}
    individual_opponent_count: Dict[str, Dict[str, int]] = {pid: {} for pid in all_player_ids}
    sit_out_count: Dict[str, int] = {pid: 0 for pid in all_player_ids}
    
    # Track which groups of 4 players have played together (to avoid repetition)
    groups_played: Set[frozenset] = set()
    
    # Track how many times each pair of players has been in the same match (as partners OR opponents)
    pair_match_count: Dict[frozenset, int] = {}
    
    scheduled_matches: List[ScheduledMatch] = []
    match_number = 0
    
    def get_team_rating(team: List[str]) -> float:
        """Get total rating of a team."""
        return sum(player_ratings.get(pid, 1500) for pid in team)
    
    def get_group_key(players_list: List[str]) -> frozenset:
        """Get a hashable key for a group of 4 players."""
        return frozenset(players_list)
    
    def get_pair_key(p1: str, p2: str) -> frozenset:
        """Get a hashable key for a pair of players."""
        return frozenset([p1, p2])
    
    def can_form_match(team1: List[str], team2: List[str]) -> bool:
        """Check if two teams can play against each other."""
        p1, p2 = team1
        p3, p4 = team2
        
        # Check if all players can still play more games
        for pid in [p1, p2, p3, p4]:
            if games_per_player[pid] >= max_games:
                return False
        
        # Check partnership constraint
        if p2 in partnership_used[p1]:
            return False
        if p4 in partnership_used[p3]:
            return False
        
        # Check individual opponent limits
        for a in team1:
            for b in team2:
                if individual_opponent_count[a].get(b, 0) >= config.max_individual_opponent_repeats:
                    return False
        
        return True
    
    def record_match(team1: List[str], team2: List[str]) -> None:
        """Record that a match was played."""
        p1, p2 = team1
        p3, p4 = team2
        all_four = team1 + team2
        
        for pid in all_four:
            games_per_player[pid] += 1
        
        partnership_used[p1].add(p2)
        partnership_used[p2].add(p1)
        partnership_used[p3].add(p4)
        partnership_used[p4].add(p3)
        
        for a in team1:
            for b in team2:
                individual_opponent_count[a][b] = individual_opponent_count[a].get(b, 0) + 1
                individual_opponent_count[b][a] = individual_opponent_count[b].get(a, 0) + 1
        
        # Track this group of 4
        groups_played.add(get_group_key(all_four))
        
        # Track all pairs in this match
        for i, p1 in enumerate(all_four):
            for p2 in all_four[i+1:]:
                key = get_pair_key(p1, p2)
                pair_match_count[key] = pair_match_count.get(key, 0) + 1
    
    def score_match_variety(team1: List[str], team2: List[str]) -> float:
        """
        Score a potential match based on variety factors.
        Higher score = more variety (better).
        Used in VARIETY rounds to maximize mixing.
        
        ELO scale: 3.0 skill = ~1300, 4.5 skill = ~1700
        So 0.25 skill = ~67 ELO, 0.5 skill = ~133 ELO
        """
        all_four = team1 + team2
        score = 0.0
        
        # PENALTY: If this exact group of 4 has played before
        group_key = get_group_key(all_four)
        if group_key in groups_played:
            score -= 500  # Heavy penalty for same 4 players
        
        # PENALTY: For pairs that have been in many matches together
        for i, p1 in enumerate(all_four):
            for p2 in all_four[i+1:]:
                pair_key = get_pair_key(p1, p2)
                times_together = pair_match_count.get(pair_key, 0)
                score -= times_together * 40  # Stronger penalty for frequent pairings
        
        # BONUS: For skill mixing (different ratings in the match)
        ratings = [player_ratings.get(pid, 1500) for pid in all_four]
        rating_spread = max(ratings) - min(ratings)
        
        # Reward moderate spread - encourage mixing!
        if 150 <= rating_spread <= 350:  # ~0.5 to 1.25 skill level difference
            score += 150  # Strong bonus for good variety
        elif 70 <= rating_spread < 150:  # ~0.25 to 0.5 skill level difference
            score += 75  # Good bonus  
        elif rating_spread < 70:  # Too homogeneous (<0.25 level difference)
            score -= 100  # Penalty for same-skill matches in variety rounds
        
        # BONUS: For balanced teams with mixed skills
        # E.g., 4.0+3.5 vs 4.0+3.5 is more interesting than 4.0+4.0 vs 3.5+3.5
        team1_ratings = sorted([player_ratings.get(pid, 1500) for pid in team1])
        team2_ratings = sorted([player_ratings.get(pid, 1500) for pid in team2])
        
        # Check if each team has mixed ratings
        team1_spread = team1_ratings[1] - team1_ratings[0]
        team2_spread = team2_ratings[1] - team2_ratings[0]
        
        if team1_spread > 100 and team2_spread > 100:  # Both teams have good variety
            score += 150  # Strong bonus for mixed teams
        elif team1_spread > 50 and team2_spread > 50:  # Both teams have some variety
            score += 50  # Small bonus
        
        return score
    
    def score_match_skill_focused(team1: List[str], team2: List[str]) -> float:
        """
        Score a potential match emphasizing similar skill levels.
        Higher score = more competitive (similar skill players).
        Used in SKILL rounds to create tight competitive matches.
        
        ELO scale: 3.0 skill = ~1300, 4.5 skill = ~1700
        So 0.25 skill = ~67 ELO, 0.5 skill = ~133 ELO
        """
        all_four = team1 + team2
        score = 0.0
        
        # PENALTY: If this exact group of 4 has played before (always apply)
        group_key = get_group_key(all_four)
        if group_key in groups_played:
            score -= 500  # Heavy penalty for same 4 players
        
        # PENALTY: For pairs that have been in many matches together (lighter than variety)
        for i, p1 in enumerate(all_four):
            for p2 in all_four[i+1:]:
                pair_key = get_pair_key(p1, p2)
                times_together = pair_match_count.get(pair_key, 0)
                score -= times_together * 15  # Lighter penalty - skill matters more
        
        # STRONG BONUS: For similar skill levels (tight competitive matches)
        ratings = [player_ratings.get(pid, 1500) for pid in all_four]
        rating_spread = max(ratings) - min(ratings)
        
        # Aggressive bonuses for homogeneous skill groups
        if rating_spread < 70:  # Very similar skills (~0.25 level difference)
            score += 300  # Very strong bonus for tight competitive matches
        elif rating_spread < 140:  # Similar skills (~0.5 level difference)
            score += 150  # Strong bonus
        elif rating_spread < 200:  # Decent spread (~0.75 level difference)
            score += 50  # Small bonus
        elif rating_spread > 300:  # Wide skill gap (1+ level difference)
            score -= 200  # Strong penalty for mismatched skills
        
        # STRONG BONUS: For homogeneous teams (same skill partners)
        # E.g., 4.0+4.0 vs 3.75+3.75 for tight competitive matches
        team1_ratings = sorted([player_ratings.get(pid, 1500) for pid in team1])
        team2_ratings = sorted([player_ratings.get(pid, 1500) for pid in team2])
        
        team1_spread = team1_ratings[1] - team1_ratings[0]
        team2_spread = team2_ratings[1] - team2_ratings[0]
        
        # Reward teams with similar skill partners (both under 0.25 skill level)
        if team1_spread < 70 and team2_spread < 70:  
            score += 200  # Strong bonus for competitive team composition
        elif team1_spread < 100 and team2_spread < 100:
            score += 75  # Good bonus
        
        return score
    
    def find_best_match(pool: Set[str], preferred_players: Set[str], style: str, debug_court: int = -1) -> Optional[Tuple[List[str], List[str]]]:
        """
        Find the best valid match from a pool of players.
        
        Args:
            pool: Set of available player IDs
            preferred_players: Players to prefer (for court continuity bonus)
            style: 'skill' or 'variety' for scoring
            debug_court: If >= 0, print debug info for this court
            
        Returns:
            (team1, team2) tuple or None if no valid match found
        """
        if len(pool) < 4:
            return None
        
        best_match = None
        best_score = -float('inf')
        
        search_pool = sorted(pool, key=lambda p: (games_per_player[p], -player_ratings.get(p, 1500)))[:12]
        
        for combo in combinations(search_pool, 4):
            combo_list = list(combo)
            
            if get_group_key(combo_list) in groups_played:
                continue
            
            for team1, team2 in [
                ([combo_list[0], combo_list[1]], [combo_list[2], combo_list[3]]),
                ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
                ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]]),
            ]:
                if not can_form_match(team1, team2):
                    continue
                
                balance = abs(get_team_rating(team1) - get_team_rating(team2))
                balance_score = 500 - balance
                
                if style == 'skill':
                    style_score = score_match_skill_focused(team1, team2)
                else:
                    style_score = score_match_variety(team1, team2)
                
                # Bonus for using preferred players (court continuity)
                continuity = sum(1 for p in combo_list if p in preferred_players)
                continuity_bonus = continuity * 50
                
                # CRITICAL: Strong bonus/penalty for games balance
                # This is the most important factor for fair distribution
                games_balance_score = 0
                for p in combo_list:
                    games_deficit = target_games - games_per_player[p]
                    if games_deficit > 0:
                        # Strong bonus for under-played players
                        # deficit=1 -> 100, deficit=2 -> 250, deficit=3 -> 450, deficit=4 -> 700
                        games_balance_score += games_deficit * 50 + (games_deficit ** 2) * 25
                    elif games_deficit < 0:
                        # Penalty for over-played players (they shouldn't play more)
                        games_balance_score -= abs(games_deficit) * 100
                
                total_score = balance_score + style_score + continuity_bonus + games_balance_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_match = (team1[:], team2[:])
        
        return best_match
    
    def generate_round(available_players: List[str], matches_needed: int, round_style: str = 'variety') -> List[Tuple[List[str], List[str]]]:
        """
        Generate a single round of matches where no player appears twice.
        
        Args:
            available_players: Players available for this round
            matches_needed: Number of matches to generate (typically = num_courts)
            round_style: 'skill' for competitive similar-skill matches,
                        'variety' for mixed skill social matches
        """
        round_matches = []
        used_in_round: Set[str] = set()
        
        # Choose scoring function based on round style
        score_style_func = score_match_skill_focused if round_style == 'skill' else score_match_variety
        
        # Create candidate pool - order by games needed, then by rating
        candidates = available_players[:]
        if round_style == 'skill':
            # For skill rounds, group similar ratings together
            candidates.sort(key=lambda p: (games_per_player[p], player_ratings.get(p, 1500)))
        else:
            # For variety rounds, interleave ratings
            candidates.sort(key=lambda p: (games_per_player[p], -player_ratings.get(p, 1500)))
        
        for match_idx in range(matches_needed):
            # Get players not yet used in this round
            remaining = [p for p in candidates if p not in used_in_round and games_per_player[p] < max_games]
            
            if len(remaining) < 4:
                break
            
            best_match = None
            best_score = -float('inf')
            
            # Sample different combinations of 4 players
            search_pool = remaining[:min(16, len(remaining))]
            
            combos_tried = 0
            max_combos = 50  # Limit for performance
            
            for combo in combinations(search_pool, 4):
                if combos_tried >= max_combos:
                    break
                combos_tried += 1
                
                combo_list = list(combo)
                
                # Skip if this exact group has played before
                if get_group_key(combo_list) in groups_played:
                    continue
                
                # Try all team configurations
                team_configs = [
                    ([combo_list[0], combo_list[1]], [combo_list[2], combo_list[3]]),
                    ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
                    ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]]),
                ]
                
                for team1, team2 in team_configs:
                    if not can_form_match(team1, team2):
                        continue
                    
                    # Calculate score with balance and style-specific scoring
                    balance = abs(get_team_rating(team1) - get_team_rating(team2))
                    balance_score = 500 - balance  # Balance component (max 500)
                    
                    style_score = score_style_func(team1, team2)
                    
                    # Bonus for players who need more games
                    games_needed_score = sum((target_games - games_per_player[pid]) * 20 
                                            for pid in combo_list)
                    
                    total_score = balance_score + style_score + games_needed_score
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_match = (team1[:], team2[:])
            
            if best_match:
                round_matches.append(best_match)
                used_in_round.update(best_match[0] + best_match[1])
            else:
                # Fallback: try any valid match
                for combo in combinations(remaining[:12], 4):
                    combo_list = list(combo)
                    for team1, team2 in [
                        ([combo_list[0], combo_list[1]], [combo_list[2], combo_list[3]]),
                        ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
                        ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]]),
                    ]:
                        if can_form_match(team1, team2):
                            round_matches.append((team1, team2))
                            used_in_round.update(team1 + team2)
                            break
                    else:
                        continue
                    break
        
        return round_matches
    
    def select_players_for_round(num_needed: int) -> List[str]:
        """
        Select players for a round, fairly rotating who sits out.
        
        Args:
            num_needed: Number of players needed (courts * 4)
        
        Returns:
            List of player IDs selected for this round
        """
        # Get players who still need games
        eligible = [pid for pid in all_player_ids if games_per_player[pid] < target_games]
        
        if len(eligible) < num_needed:
            # Include players who have reached target but not max
            eligible = [pid for pid in all_player_ids if games_per_player[pid] < max_games]
        
        if len(eligible) <= num_needed:
            return eligible
        
        # Sort by: 1) fewest games played, 2) fewest times sat out, 3) rating
        eligible.sort(key=lambda p: (
            games_per_player[p],
            sit_out_count[p],
            -player_ratings.get(p, 1500)
        ))
        
        # Select top N players, rest sit out
        selected = eligible[:num_needed]
        sitting_out = eligible[num_needed:]
        
        # Track who sat out
        for pid in sitting_out:
            sit_out_count[pid] += 1
        
        return selected
    
    # =========================================================================
    # CONTINUOUS FLOW SCHEDULING
    # =========================================================================
    # Key insight: For continuous flow, when Court 1 finishes Match 1, 
    # Match 5 should be able to start immediately.
    #
    # This means Match 5 should use:
    # - Some players from Match 1 (who just finished)
    # - Some players from the waiting pool (who were waiting during Match 1)
    #
    # Match 5 should NOT depend on players from Matches 2, 3, or 4 (still playing).
    #
    # APPROACH: Generate schedule in "waves" where each wave has num_courts matches.
    # Within each wave, ensure each match primarily uses players from the SAME
    # court position in the previous wave, plus waiters.
    # =========================================================================
    
    players_per_match = 4
    total_matches_needed = (num_players * target_games) // 4
    
    # Initialize waiting pool
    available_for_games = [p for p in all_player_ids if p not in first_bye_player_ids]
    first_bye_pool = [p for p in all_player_ids if p in first_bye_player_ids]
    
    # Court state: tracks which players were in the last match on each court
    court_last_players: List[List[str]] = [[] for _ in range(num_courts)]
    
    # Waiting pool: players not currently on a court
    initial_on_courts = min(num_courts * players_per_match, len(available_for_games))
    waiting_pool: Set[str] = set(available_for_games[initial_on_courts:]) | set(first_bye_pool)
    
    scheduled_matches: List[ScheduledMatch] = []
    round_styles = ['skill', 'variety']
    
    # ===== WAVE 0: Initial matches =====
    for court_idx in range(num_courts):
        start_idx = court_idx * players_per_match
        end_idx = start_idx + players_per_match
        court_players = available_for_games[start_idx:end_idx]
        
        if len(court_players) < 4:
            continue
        
        # Find best team configuration
        best_match = None
        best_score = -float('inf')
        
        for team1, team2 in [
            ([court_players[0], court_players[1]], [court_players[2], court_players[3]]),
            ([court_players[0], court_players[2]], [court_players[1], court_players[3]]),
            ([court_players[0], court_players[3]], [court_players[1], court_players[2]]),
        ]:
            if can_form_match(team1, team2):
                balance = abs(get_team_rating(team1) - get_team_rating(team2))
                score = 500 - balance
                if score > best_score:
                    best_score = score
                    best_match = (team1, team2)
        
        if best_match:
            record_match(best_match[0], best_match[1])
            match_number += 1
            court_last_players[court_idx] = list(best_match[0] + best_match[1])
            
            balance_score = calculate_team_balance_score(session, best_match[0], best_match[1])
            scheduled_matches.append(ScheduledMatch(
                id=f"scheduled_{uuid.uuid4().hex[:8]}",
                team1=best_match[0],
                team2=best_match[1],
                status='pending',
                match_number=match_number,
                balance_score=balance_score
            ))
    
    # ===== SUBSEQUENT WAVES =====
    # CONTINUOUS FLOW OPTIMIZATION:
    # Goal: When Court N finishes, Match N+4 can start immediately
    # 
    # Strategy:
    # 1. Each court's next match prefers players from that court + waiters
    # 2. If not enough players (no waiters), swap pairs between adjacent courts
    # 3. This creates 2-match dependencies instead of 4-match dependencies
    max_waves = (total_matches_needed // num_courts) + 5
    
    for wave_num in range(1, max_waves):
        if match_number >= total_matches_needed:
            break
        
        current_style = round_styles[wave_num % 2]
        
        # Get all available players for this wave
        wave_available = set(waiting_pool)
        for court_idx in range(num_courts):
            wave_available.update(court_last_players[court_idx])
        wave_available = set(p for p in wave_available if games_per_player[p] < max_games)
        
        if len(wave_available) < 4:
            break
        
        # Distribute waiters evenly across courts
        waiters_list = sorted(waiting_pool, key=lambda p: (games_per_player[p], -player_ratings.get(p, 1500)))
        waiters_per_court = len(waiters_list) // num_courts if num_courts > 0 else 0
        
        court_waiters: Dict[int, Set[str]] = {c: set() for c in range(num_courts)}
        for i, waiter in enumerate(waiters_list):
            court_idx = i % num_courts
            court_waiters[court_idx].add(waiter)
        
        # CRITICAL: Identify players who are significantly behind on games
        # These players should be prioritized in ALL pools to ensure fair distribution
        avg_games = sum(games_per_player.values()) / len(games_per_player) if games_per_player else 0
        underplayed_players = set(p for p, g in games_per_player.items() 
                                   if g < avg_games - 1 and g < max_games)
        
        matches_needed_this_wave = min(num_courts, total_matches_needed - match_number)
        wave_matches: List[Tuple[int, List[str], List[str]]] = []
        used_in_wave: Set[str] = set()
        
        # PHASE 1: Try each court with optimal flow (own players + waiters + underplayed)
        for court_idx in range(num_courts):
            if match_number + len(wave_matches) >= total_matches_needed:
                break
            
            prev_court_players = set(court_last_players[court_idx]) if court_last_players[court_idx] else set()
            my_waiters = court_waiters[court_idx] - used_in_wave
            
            # Optimal pool: previous court players + assigned waiters + underplayed players
            # Adding underplayed players ensures they get opportunities even with tight continuity
            court_pool = (prev_court_players | my_waiters | underplayed_players) - used_in_wave
            court_pool = set(p for p in court_pool if games_per_player[p] < max_games)
            
            # Track which phase succeeded
            match_phase = None
            
            if len(court_pool) >= 4:
                # Try to form match from optimal pool
                match_result = find_best_match(court_pool, prev_court_players, current_style)
                if match_result:
                    team1, team2 = match_result
                    all_four = set(team1 + team2)
                    used_in_wave.update(all_four)
                    wave_matches.append((court_idx, team1, team2))
                    match_phase = 'PHASE1_OPTIMAL'
            
            if match_phase is None:
                # PHASE 2: Expand to adjacent court (creates 2-match dependency)
                # Court 0 borrows from Court 1, Court 1 from Court 2, etc.
                adjacent_court = (court_idx + 1) % num_courts
                adjacent_players = set(court_last_players[adjacent_court]) if court_last_players[adjacent_court] else set()
                
                expanded_pool = (prev_court_players | my_waiters | adjacent_players) - used_in_wave
                expanded_pool = set(p for p in expanded_pool if games_per_player[p] < max_games)
                
                if len(expanded_pool) >= 4:
                    match_result = find_best_match(expanded_pool, prev_court_players, current_style)
                    if match_result:
                        team1, team2 = match_result
                        all_four = set(team1 + team2)
                        used_in_wave.update(all_four)
                        wave_matches.append((court_idx, team1, team2))
                        match_phase = 'PHASE2_ADJACENT'
            
            if match_phase is None:
                # PHASE 3: Use all available players (worst case - multi-match dependency)
                full_pool = wave_available - used_in_wave
                if len(full_pool) >= 4:
                    match_result = find_best_match(full_pool, prev_court_players, current_style)
                    if match_result:
                        team1, team2 = match_result
                        all_four = set(team1 + team2)
                        used_in_wave.update(all_four)
                        wave_matches.append((court_idx, team1, team2))
                        match_phase = 'PHASE3_FULL'
        
        # Commit all matches from this wave
        if not wave_matches:
            break  # No matches could be created - we're stuck
        
        for court_idx, team1, team2 in wave_matches:
            all_four = team1 + team2
            prev_court_players = court_last_players[court_idx] if court_last_players[court_idx] else []
            
            # Update waiting pool
            for p in prev_court_players:
                if p not in all_four:
                    waiting_pool.add(p)
            for p in all_four:
                waiting_pool.discard(p)
            
            # Record match
            record_match(team1, team2)
            match_number += 1
            court_last_players[court_idx] = list(all_four)
            
            balance_score = calculate_team_balance_score(session, team1, team2)
            scheduled_matches.append(ScheduledMatch(
                id=f"scheduled_{uuid.uuid4().hex[:8]}",
                team1=team1,
                team2=team2,
                status='pending',
                match_number=match_number,
                balance_score=balance_score
            ))
    
    # Reorder to handle first bye players (they appear later)
    scheduled_matches = _reorder_for_fair_distribution(scheduled_matches, all_player_ids, first_bye_player_ids)
    
    # Renumber matches after reordering
    for i, match in enumerate(scheduled_matches):
        match.match_number = i + 1
    
    return scheduled_matches


def _reorder_for_fair_distribution(
    matches: List[ScheduledMatch], 
    all_player_ids: List[str],
    first_bye_player_ids: Set[str]
) -> List[ScheduledMatch]:
    """
    Reorder matches to ensure fair distribution of play time.
    
    IMPORTANT: Preserves wave structure for continuous flow.
    Matches are only reordered WITHIN each wave (groups of num_courts matches).
    This ensures M5-M8 still depend on M1-M4, not random earlier matches.
    
    Goals:
    - Players should be evenly distributed across the match queue
    - First bye players should not appear in early matches
    - Minimize consecutive matches for same player
    - PRESERVE WAVE STRUCTURE for continuous flow
    """
    if len(matches) <= 4:
        return matches
    
    # Determine wave size (typically 4 for 4 courts)
    # Infer from match pattern - matches in same wave have no player overlap
    wave_size = 4  # Default to 4 courts
    
    # Handle first-bye players specially
    if not first_bye_player_ids:
        # No reordering needed - wave structure already optimal
        return matches
    
    # With first-bye players, we need to delay their matches
    # But we must preserve wave structure
    
    reordered = []
    num_waves = (len(matches) + wave_size - 1) // wave_size
    
    # Track when each player was last scheduled
    last_scheduled: Dict[str, int] = {pid: -999 for pid in all_player_ids}
    
    for wave_num in range(num_waves):
        wave_start = wave_num * wave_size
        wave_end = min(wave_start + wave_size, len(matches))
        wave_matches = matches[wave_start:wave_end]
        
        # For wave 0-1, put non-first-bye matches first
        if wave_num < 2:
            non_fb = [m for m in wave_matches if not (set(m.get_all_players()) & first_bye_player_ids)]
            fb = [m for m in wave_matches if set(m.get_all_players()) & first_bye_player_ids]
            wave_matches = non_fb + fb
        
        # Add wave matches in order (preserve wave continuity)
        for match in wave_matches:
            reordered.append(match)
            for pid in match.get_all_players():
                last_scheduled[pid] = len(reordered)
    
    return reordered


def regenerate_match(
    session: Session,
    current_schedule: List[ScheduledMatch],
    rejected_match_index: int,
    config: CompetitiveRoundRobinConfig
) -> Optional[ScheduledMatch]:
    """
    Regenerate a single match to replace a rejected one.
    
    Considers:
    - Already approved matches (constraints from those are fixed)
    - Need to maintain games_per_player balance
    - All constraints must still be met
    
    Returns new ScheduledMatch or None if no valid replacement found.
    """
    rejected_match = current_schedule[rejected_match_index]
    rejected_players = set(rejected_match.get_all_players())
    
    # Get players from rejected match who still need games
    players = session.config.players
    player_ids = [p.id for p in players]
    
    # Calculate current state from approved matches only
    approved_matches = [m for m in current_schedule if m.status == 'approved']
    
    games_per_player: Dict[str, int] = {pid: 0 for pid in player_ids}
    partnership_used: Dict[str, Set[str]] = {pid: set() for pid in player_ids}
    opponent_pair_used: Set[str] = set()
    individual_opponent_count: Dict[str, Dict[str, int]] = {pid: {} for pid in player_ids}
    
    for match in approved_matches:
        for pid in match.get_all_players():
            games_per_player[pid] += 1
        
        if len(match.team1) == 2:
            partnership_used[match.team1[0]].add(match.team1[1])
            partnership_used[match.team1[1]].add(match.team1[0])
        if len(match.team2) == 2:
            partnership_used[match.team2[0]].add(match.team2[1])
            partnership_used[match.team2[1]].add(match.team2[0])
        
        opponent_pair_used.add(','.join(sorted(match.team1)))
        opponent_pair_used.add(','.join(sorted(match.team2)))
        
        for p1 in match.team1:
            for p2 in match.team2:
                individual_opponent_count[p1][p2] = individual_opponent_count[p1].get(p2, 0) + 1
                individual_opponent_count[p2][p1] = individual_opponent_count[p2].get(p1, 0) + 1
    
    # Find candidates - prioritize players from rejected match, then those needing games
    target_games = config.games_per_player
    available = [
        pid for pid in player_ids 
        if games_per_player[pid] < target_games
    ]
    
    if len(available) < 4:
        return None
    
    # Sort by games played (ascending)
    player_ratings = {p.id: get_player_skill_rating(session, p.id) for p in players}
    available.sort(key=lambda p: (games_per_player[p], -player_ratings[p]))
    
    # Try to find best replacement match
    best_match = None
    best_score = -float('inf')
    
    search_pool = available[:min(20, len(available))]
    
    for combo in combinations(search_pool, 4):
        combo_list = list(combo)
        
        team_configs = [
            (combo_list[0:2], combo_list[2:4]),
            ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
            ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]])
        ]
        
        for team1, team2 in team_configs:
            # Check constraints
            if team1[1] in partnership_used[team1[0]]:
                continue
            if team2[1] in partnership_used[team2[0]]:
                continue
            
            opp_pair1 = ','.join(sorted(team1))
            opp_pair2 = ','.join(sorted(team2))
            if opp_pair1 in opponent_pair_used or opp_pair2 in opponent_pair_used:
                continue
            
            valid = True
            for p1 in team1:
                for p2 in team2:
                    count = individual_opponent_count[p1].get(p2, 0)
                    if count >= config.max_individual_opponent_repeats:
                        valid = False
                        break
                if not valid:
                    break
            
            if not valid:
                continue
            
            score = calculate_team_balance_score(session, team1, team2)
            
            # Bonus for including players from rejected match
            for pid in combo_list:
                if pid in rejected_players:
                    score += 200
                games_deficit = target_games - games_per_player[pid]
                score += games_deficit * 50
            
            if score > best_score:
                best_score = score
                best_match = (team1, team2)
    
    if best_match is None:
        return None
    
    team1, team2 = best_match
    return ScheduledMatch(
        id=f"scheduled_{uuid.uuid4().hex[:8]}",
        team1=list(team1),
        team2=list(team2),
        status='pending',
        match_number=rejected_match.match_number,
        balance_score=best_score
    )


def swap_player_in_match(
    session: Session,
    match: ScheduledMatch,
    old_player_id: str,
    new_player_id: str,
    current_schedule: List[ScheduledMatch],
    config: CompetitiveRoundRobinConfig
) -> Tuple[bool, Optional[ScheduledMatch], str]:
    """
    Swap a player in a match with another player.
    
    Returns:
        (success, new_match, error_message)
    """
    if old_player_id not in match.get_all_players():
        return False, None, f"Player {old_player_id} not in this match"
    
    if new_player_id in match.get_all_players():
        return False, None, f"Player {new_player_id} already in this match"
    
    # Create new teams with swap
    new_team1 = [new_player_id if p == old_player_id else p for p in match.team1]
    new_team2 = [new_player_id if p == old_player_id else p for p in match.team2]
    
    # Validate the new match configuration against existing approved matches
    approved_matches = [m for m in current_schedule if m.status == 'approved' and m.id != match.id]
    
    partnership_used: Dict[str, Set[str]] = {p.id: set() for p in session.config.players}
    individual_opponent_count: Dict[str, Dict[str, int]] = {p.id: {} for p in session.config.players}
    
    for m in approved_matches:
        if len(m.team1) == 2:
            partnership_used[m.team1[0]].add(m.team1[1])
            partnership_used[m.team1[1]].add(m.team1[0])
        if len(m.team2) == 2:
            partnership_used[m.team2[0]].add(m.team2[1])
            partnership_used[m.team2[1]].add(m.team2[0])
        
        for p1 in m.team1:
            for p2 in m.team2:
                individual_opponent_count[p1][p2] = individual_opponent_count[p1].get(p2, 0) + 1
                individual_opponent_count[p2][p1] = individual_opponent_count[p2].get(p1, 0) + 1
    
    # Check partnership constraint for new teams
    if len(new_team1) == 2:
        if new_team1[1] in partnership_used.get(new_team1[0], set()):
            return False, None, f"Partnership {new_team1[0]}-{new_team1[1]} already used"
    if len(new_team2) == 2:
        if new_team2[1] in partnership_used.get(new_team2[0], set()):
            return False, None, f"Partnership {new_team2[0]}-{new_team2[1]} already used"
    
    # Check individual opponent limits
    for p1 in new_team1:
        for p2 in new_team2:
            count = individual_opponent_count.get(p1, {}).get(p2, 0)
            if count >= config.max_individual_opponent_repeats:
                return False, None, f"Opponent limit exceeded: {p1} vs {p2}"
    
    # Create new match
    new_match = ScheduledMatch(
        id=match.id,
        team1=new_team1,
        team2=new_team2,
        status=match.status,
        match_number=match.match_number,
        balance_score=calculate_team_balance_score(session, new_team1, new_team2)
    )
    
    return True, new_match, ""


def get_available_swaps(
    session: Session,
    match: ScheduledMatch,
    player_to_replace: str,
    current_schedule: List[ScheduledMatch],
    config: CompetitiveRoundRobinConfig
) -> List[Tuple[str, str, float]]:
    """
    Get list of players that can be swapped into a match position.
    
    Returns list of (player_id, player_name, balance_score_delta) tuples,
    sorted by balance score improvement.
    """
    current_players = set(match.get_all_players())
    all_player_ids = {p.id for p in session.config.players}
    
    # Players not in this match
    candidates = all_player_ids - current_players
    
    valid_swaps = []
    original_balance = match.balance_score
    
    for candidate_id in candidates:
        success, new_match, _ = swap_player_in_match(
            session, match, player_to_replace, candidate_id, 
            current_schedule, config
        )
        
        if success and new_match:
            balance_delta = new_match.balance_score - original_balance
            
            # Find player name
            player_name = candidate_id
            for p in session.config.players:
                if p.id == candidate_id:
                    player_name = p.name
                    break
            
            valid_swaps.append((candidate_id, player_name, balance_delta))
    
    # Sort by balance improvement (descending)
    valid_swaps.sort(key=lambda x: x[2], reverse=True)
    
    return valid_swaps


def get_schedule_summary(
    session: Session,
    scheduled_matches: List[ScheduledMatch],
    config: CompetitiveRoundRobinConfig
) -> Dict:
    """
    Get summary statistics about the current schedule.
    """
    approved = [m for m in scheduled_matches if m.status == 'approved']
    pending = [m for m in scheduled_matches if m.status == 'pending']
    rejected = [m for m in scheduled_matches if m.status == 'rejected']
    
    validation = validate_schedule(session, scheduled_matches, config)
    
    # Calculate average balance score
    avg_balance = 0.0
    if approved:
        avg_balance = sum(m.balance_score for m in approved) / len(approved)
    
    return {
        'total_matches': len(scheduled_matches),
        'approved': len(approved),
        'pending': len(pending),
        'rejected': len(rejected),
        'is_valid': validation.is_valid,
        'violations': len(validation.violations),
        'games_per_player': validation.games_per_player,
        'average_balance_score': avg_balance,
        'target_games_per_player': config.games_per_player
    }


def populate_courts_from_schedule(session: Session) -> None:
    """
    Populate empty courts from approved scheduled matches.
    
    Also adds all unplayed approved matches to the match queue so users
    can see what's coming up.
    """
    if session.config.mode != 'competitive-round-robin':
        return
    
    config = session.config.competitive_round_robin_config
    if not config or not config.schedule_finalized:
        return
    
    # Get approved matches
    approved_matches = [
        m for m in config.scheduled_matches 
        if m.status == 'approved'
    ]
    
    # Find which scheduled matches have already been played or are currently on courts
    played_or_active_ids = set()
    for match in session.matches:
        # Check if any session match corresponds to a scheduled match
        for sm in config.scheduled_matches:
            if (set(match.team1) == set(sm.team1) and 
                set(match.team2) == set(sm.team2)):
                played_or_active_ids.add(sm.id)
    
    # Get unplayed approved matches (sorted by match number for queue order)
    unplayed = [m for m in approved_matches if m.id not in played_or_active_ids]
    unplayed.sort(key=lambda m: m.match_number)
    
    if not unplayed:
        return
    
    # Add all unplayed approved matches to the match queue (if not already there)
    from .pickleball_types import QueuedMatch
    
    # Build set of existing queued matches for comparison
    existing_queued = set()
    for qm in session.match_queue:
        key = (frozenset(qm.team1), frozenset(qm.team2))
        existing_queued.add(key)
    
    for scheduled_match in unplayed:
        key = (frozenset(scheduled_match.team1), frozenset(scheduled_match.team2))
        if key not in existing_queued:
            queued_match = QueuedMatch(
                team1=scheduled_match.team1[:],
                team2=scheduled_match.team2[:]
            )
            session.match_queue.append(queued_match)
            existing_queued.add(key)
    
    # Find empty courts
    from .queue_manager import get_empty_courts
    empty_courts = get_empty_courts(session)
    
    if not empty_courts:
        return
    
    # Check player availability (not in active match)
    active_players = set()
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            active_players.update(match.team1)
            active_players.update(match.team2)
    
    # Assign matches to courts from the queue
    from .pickleball_types import Match
    from .time_manager import now
    import uuid
    
    matches_to_remove = []
    
    for court_number in empty_courts:
        for i, queued_match in enumerate(session.match_queue):
            match_players = set(queued_match.team1 + queued_match.team2)
            
            # All players must be available
            if match_players & active_players:
                continue
            
            # All players must be active in session
            if not match_players.issubset(session.active_players):
                continue
            
            # Create actual match
            match = Match(
                id=f"match_{uuid.uuid4().hex[:8]}",
                court_number=court_number,
                team1=queued_match.team1[:],
                team2=queued_match.team2[:],
                status='waiting',
                start_time=now()
            )
            session.matches.append(match)
            
            # Mark for removal from queue
            matches_to_remove.append(i)
            
            # Mark players as active
            active_players.update(match_players)
            break
    
    # Remove assigned matches from queue (in reverse order to maintain indices)
    for i in sorted(matches_to_remove, reverse=True):
        session.match_queue.pop(i)


def swap_players_within_match(
    session: Session,
    match: ScheduledMatch,
    player1_id: str,
    player2_id: str,
    current_schedule: List[ScheduledMatch],
    config: CompetitiveRoundRobinConfig
) -> Tuple[bool, Optional[ScheduledMatch], str]:
    """
    Swap two players within the same match (between teams).
    
    This allows moving a player from team1 to team2 and vice versa.
    
    Returns:
        (success, new_match, error_message)
    """
    match_players = match.get_all_players()
    
    if player1_id not in match_players:
        return False, None, f"Player {player1_id} not in this match"
    if player2_id not in match_players:
        return False, None, f"Player {player2_id} not in this match"
    if player1_id == player2_id:
        return False, None, "Cannot swap player with themselves"
    
    # Check if players are on the same team (not allowed - use different swap)
    p1_in_team1 = player1_id in match.team1
    p2_in_team1 = player2_id in match.team1
    
    if p1_in_team1 == p2_in_team1:
        return False, None, "Players are on the same team - use partner swap instead"
    
    # Create new teams by swapping the players between teams
    new_team1 = list(match.team1)
    new_team2 = list(match.team2)
    
    if p1_in_team1:
        # player1 is in team1, player2 is in team2
        new_team1 = [player2_id if p == player1_id else p for p in match.team1]
        new_team2 = [player1_id if p == player2_id else p for p in match.team2]
    else:
        # player1 is in team2, player2 is in team1
        new_team1 = [player1_id if p == player2_id else p for p in match.team1]
        new_team2 = [player2_id if p == player1_id else p for p in match.team2]
    
    # Validate the new configuration against existing approved matches
    approved_matches = [m for m in current_schedule if m.status == 'approved' and m.id != match.id]
    
    partnership_used: Dict[str, Set[str]] = {p.id: set() for p in session.config.players}
    individual_opponent_count: Dict[str, Dict[str, int]] = {p.id: {} for p in session.config.players}
    
    for m in approved_matches:
        if len(m.team1) == 2:
            partnership_used[m.team1[0]].add(m.team1[1])
            partnership_used[m.team1[1]].add(m.team1[0])
        if len(m.team2) == 2:
            partnership_used[m.team2[0]].add(m.team2[1])
            partnership_used[m.team2[1]].add(m.team2[0])
        
        for p1 in m.team1:
            for p2 in m.team2:
                individual_opponent_count[p1][p2] = individual_opponent_count[p1].get(p2, 0) + 1
                individual_opponent_count[p2][p1] = individual_opponent_count[p2].get(p1, 0) + 1
    
    # Check partnership constraint for new teams
    if len(new_team1) == 2:
        if new_team1[1] in partnership_used.get(new_team1[0], set()):
            return False, None, f"Partnership already used in other matches"
    if len(new_team2) == 2:
        if new_team2[1] in partnership_used.get(new_team2[0], set()):
            return False, None, f"Partnership already used in other matches"
    
    # Check individual opponent limits
    for p1 in new_team1:
        for p2 in new_team2:
            count = individual_opponent_count.get(p1, {}).get(p2, 0)
            if count >= config.max_individual_opponent_repeats:
                return False, None, f"Opponent limit exceeded"
    
    # Create new match
    new_match = ScheduledMatch(
        id=match.id,
        team1=new_team1,
        team2=new_team2,
        status=match.status,
        match_number=match.match_number,
        balance_score=calculate_team_balance_score(session, new_team1, new_team2)
    )
    
    return True, new_match, ""


def export_schedule_to_json(
    session: Session,
    scheduled_matches: List[ScheduledMatch],
    config: CompetitiveRoundRobinConfig
) -> str:
    """
    Export scheduled matches to JSON format for backup/sharing.
    """
    # Build player name map
    player_map = {p.id: {'name': p.name, 'rating': p.skill_rating} 
                  for p in session.config.players}
    
    export_data = {
        'version': '1.0',
        'export_type': 'competitive_round_robin_schedule',
        'config': {
            'games_per_player': config.games_per_player,
            'max_partner_repeats': config.max_partner_repeats,
            'max_opponent_pair_repeats': config.max_opponent_pair_repeats,
            'max_individual_opponent_repeats': config.max_individual_opponent_repeats
        },
        'players': [
            {'id': p.id, 'name': p.name, 'skill_rating': p.skill_rating}
            for p in session.config.players
        ],
        'matches': [
            {
                'id': m.id,
                'match_number': m.match_number,
                'team1': [player_map[pid]['name'] for pid in m.team1],
                'team2': [player_map[pid]['name'] for pid in m.team2],
                'team1_ids': m.team1,
                'team2_ids': m.team2,
                'status': m.status,
                'balance_score': m.balance_score
            }
            for m in scheduled_matches
        ]
    }
    
    return json.dumps(export_data, indent=2)


def import_schedule_from_json(
    session: Session,
    json_str: str,
    config: CompetitiveRoundRobinConfig
) -> Tuple[bool, List[ScheduledMatch], str]:
    """
    Import scheduled matches from JSON format.
    
    Returns:
        (success, matches, error_message)
    """
    try:
        data = json.loads(json_str)
        
        if data.get('export_type') != 'competitive_round_robin_schedule':
            return False, [], "Invalid export type"
        
        # Build name-to-id map from current session players
        name_to_id = {p.name: p.id for p in session.config.players}
        
        imported_matches = []
        for match_data in data.get('matches', []):
            # Try to map by name first, then fall back to stored IDs
            team1 = []
            team2 = []
            
            for name in match_data.get('team1', []):
                if name in name_to_id:
                    team1.append(name_to_id[name])
                else:
                    return False, [], f"Player '{name}' not found in current session"
            
            for name in match_data.get('team2', []):
                if name in name_to_id:
                    team2.append(name_to_id[name])
                else:
                    return False, [], f"Player '{name}' not found in current session"
            
            if len(team1) != 2 or len(team2) != 2:
                return False, [], "Invalid team size in imported match"
            
            match = ScheduledMatch(
                id=match_data.get('id', f"imported_{uuid.uuid4().hex[:8]}"),
                team1=team1,
                team2=team2,
                status=match_data.get('status', 'pending'),
                match_number=match_data.get('match_number', len(imported_matches) + 1),
                balance_score=match_data.get('balance_score', 0.0)
            )
            imported_matches.append(match)
        
        return True, imported_matches, ""
        
    except json.JSONDecodeError as e:
        return False, [], f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, [], f"Import error: {str(e)}"


def export_players_with_ratings(players: List[Player]) -> Dict:
    """
    Export player list with skill ratings to JSON format.
    Returns a dict that can be dumped to JSON.
    """
    export_data = {
        'version': '1.0',
        'export_type': 'player_list_with_ratings',
        'players': [
            {
                'name': p.name,
                'skill_rating': p.skill_rating
            }
            for p in players
        ]
    }
    
    return export_data


def import_players_with_ratings(data: Dict) -> Tuple[List[Player], bool]:
    """
    Import player list with skill ratings from JSON format.
    
    Args:
        data: Parsed JSON dict
    
    Returns:
        (player_list, has_ratings)
        
    player_list is a list of Player objects.
    has_ratings is True if any player had a skill rating.
    """
    if data.get('export_type') != 'player_list_with_ratings':
        raise ValueError("Invalid export type - expected 'player_list_with_ratings'")
    
    players = []
    has_ratings = False
    
    from .time_manager import now
    
    for i, p_data in enumerate(data.get('players', [])):
        name = p_data.get('name', '').strip()
        if not name:
            continue
        
        rating = p_data.get('skill_rating')
        if rating is not None:
            try:
                rating = float(rating)
                has_ratings = True
            except (ValueError, TypeError):
                rating = None
        
        player = Player(
            id=f"player_{i}_{now().timestamp()}",
            name=name,
            skill_rating=rating
        )
        players.append(player)
    
    return players, has_ratings


def get_player_display_info(session: Session, player_id: str) -> Dict:
    """Get display information for a player in the schedule UI."""
    player_name = player_id
    skill_rating = None
    elo_rating = get_player_skill_rating(session, player_id)
    bracket = get_skill_bracket(elo_rating)
    
    for player in session.config.players:
        if player.id == player_id:
            player_name = player.name
            skill_rating = player.skill_rating
            break
    
    return {
        'id': player_id,
        'name': player_name,
        'skill_rating': skill_rating,
        'elo_rating': round(elo_rating),
        'bracket': bracket
    }
