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
"""

from typing import List, Dict, Tuple, Optional, Set
from itertools import combinations
from dataclasses import dataclass
import random
import math
import uuid

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
    
    Uses team rating difference - smaller difference = better balance.
    Also considers within-team skill gap for fairness.
    """
    # Get team ratings
    team1_ratings = [get_player_skill_rating(session, p) for p in team1]
    team2_ratings = [get_player_skill_rating(session, p) for p in team2]
    
    team1_avg = sum(team1_ratings) / len(team1_ratings)
    team2_avg = sum(team2_ratings) / len(team2_ratings)
    
    # Base score - inverse of rating difference (lower diff = higher score)
    rating_diff = abs(team1_avg - team2_avg)
    balance_score = 1000 - rating_diff
    
    # Bonus for similar within-team skill levels (prevents elite+novice vs elite+novice)
    team1_gap = max(team1_ratings) - min(team1_ratings) if len(team1_ratings) > 1 else 0
    team2_gap = max(team2_ratings) - min(team2_ratings) if len(team2_ratings) > 1 else 0
    
    # Penalty for large within-team gaps
    balance_score -= (team1_gap + team2_gap) * 0.5
    
    # Bonus for bracket-matched teams (both teams have similar composition)
    team1_brackets = [get_skill_bracket(r) for r in team1_ratings]
    team2_brackets = [get_skill_bracket(r) for r in team2_ratings]
    
    if sorted(team1_brackets) == sorted(team2_brackets):
        balance_score += 100  # Perfect bracket match
    
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
    
    Algorithm:
    1. Group players by skill brackets
    2. Generate matches ensuring each player gets target games
    3. Prioritize skill-balanced teams
    4. Avoid partnership repeats
    5. Limit opponent repeats
    
    Returns list of ScheduledMatch objects (all with 'pending' status).
    """
    if config is None:
        config = CompetitiveRoundRobinConfig()
    
    players = session.config.players
    num_players = len(players)
    
    if num_players < 4:
        return []
    
    # Target number of matches needed
    # Each match uses 4 players, so total_matches = (num_players * games_per_player) / 4
    target_games = config.games_per_player
    total_matches_needed = (num_players * target_games) // 4
    
    # Get player ratings and sort by skill
    player_ratings: Dict[str, float] = {}
    for player in players:
        player_ratings[player.id] = get_player_skill_rating(session, player.id)
    
    # Sort players by rating
    sorted_players = sorted(players, key=lambda p: player_ratings[p.id], reverse=True)
    player_ids = [p.id for p in sorted_players]
    
    # Track constraints
    games_per_player: Dict[str, int] = {pid: 0 for pid in player_ids}
    partnership_used: Dict[str, Set[str]] = {pid: set() for pid in player_ids}
    opponent_pair_used: Set[str] = set()
    individual_opponent_count: Dict[str, Dict[str, int]] = {pid: {} for pid in player_ids}
    
    scheduled_matches: List[ScheduledMatch] = []
    match_number = 0
    
    # Generate matches round by round
    max_iterations = total_matches_needed * 20  # Safety limit
    iterations = 0
    
    while len(scheduled_matches) < total_matches_needed and iterations < max_iterations:
        iterations += 1
        
        # Find players who need more games (sorted by games needed, then by rating)
        available = [
            pid for pid in player_ids 
            if games_per_player[pid] < target_games
        ]
        
        if len(available) < 4:
            break  # Not enough players who need games
        
        # Sort by games played (ascending) then by rating
        available.sort(key=lambda p: (games_per_player[p], -player_ratings[p]))
        
        # Try to find best match from available players
        best_match = None
        best_score = -float('inf')
        
        # Try combinations prioritizing those with fewest games
        # Limit search space for performance
        search_pool = available[:min(16, len(available))]  # Top candidates by need
        
        for combo in combinations(search_pool, 4):
            combo_list = list(combo)
            
            # Try all 3 possible team configurations
            team_configs = [
                (combo_list[0:2], combo_list[2:4]),
                ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
                ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]])
            ]
            
            for team1, team2 in team_configs:
                # Check partnership constraint
                if team1[1] in partnership_used[team1[0]] or team1[0] in partnership_used[team1[1]]:
                    continue
                if team2[1] in partnership_used[team2[0]] or team2[0] in partnership_used[team2[1]]:
                    continue
                
                # Check opponent pair constraint
                opp_pair1 = ','.join(sorted(team1))
                opp_pair2 = ','.join(sorted(team2))
                if opp_pair1 in opponent_pair_used or opp_pair2 in opponent_pair_used:
                    continue
                
                # Check individual opponent limits
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
                
                # Score this configuration
                score = calculate_team_balance_score(session, team1, team2)
                
                # Bonus for players with fewer games
                for pid in combo_list:
                    games_deficit = target_games - games_per_player[pid]
                    score += games_deficit * 50  # Prioritize underplayed
                
                if score > best_score:
                    best_score = score
                    best_match = (team1, team2)
        
        if best_match is None:
            # Relax constraints if no valid match found
            # Try again with expanded search pool
            search_pool = available
            
            for combo in combinations(search_pool, 4):
                combo_list = list(combo)
                
                team_configs = [
                    (combo_list[0:2], combo_list[2:4]),
                    ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
                    ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]])
                ]
                
                for team1, team2 in team_configs:
                    # Only enforce partnership constraint (hard)
                    if team1[1] in partnership_used[team1[0]]:
                        continue
                    if team2[1] in partnership_used[team2[0]]:
                        continue
                    
                    score = calculate_team_balance_score(session, team1, team2)
                    
                    for pid in combo_list:
                        games_deficit = target_games - games_per_player[pid]
                        score += games_deficit * 50
                    
                    if score > best_score:
                        best_score = score
                        best_match = (team1, team2)
                
                if best_match:
                    break
        
        if best_match is None:
            break  # Cannot generate more valid matches
        
        team1, team2 = best_match
        match_number += 1
        
        # Create scheduled match
        scheduled_match = ScheduledMatch(
            id=f"scheduled_{uuid.uuid4().hex[:8]}",
            team1=list(team1),
            team2=list(team2),
            status='pending',
            match_number=match_number,
            balance_score=best_score
        )
        scheduled_matches.append(scheduled_match)
        
        # Update tracking
        for pid in team1 + team2:
            games_per_player[pid] += 1
        
        # Track partnerships
        if len(team1) == 2:
            partnership_used[team1[0]].add(team1[1])
            partnership_used[team1[1]].add(team1[0])
        if len(team2) == 2:
            partnership_used[team2[0]].add(team2[1])
            partnership_used[team2[1]].add(team2[0])
        
        # Track opponent pairs
        opponent_pair_used.add(','.join(sorted(team1)))
        opponent_pair_used.add(','.join(sorted(team2)))
        
        # Track individual opponents
        for p1 in team1:
            for p2 in team2:
                individual_opponent_count[p1][p2] = individual_opponent_count[p1].get(p2, 0) + 1
                individual_opponent_count[p2][p1] = individual_opponent_count[p2].get(p1, 0) + 1
    
    return scheduled_matches


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
    
    Uses wait priority to determine which approved matches to start next.
    """
    if session.config.mode != 'competitive-round-robin':
        return
    
    config = session.config.competitive_round_robin_config
    if not config or not config.schedule_finalized:
        return
    
    # Get approved, unplayed matches
    approved_matches = [
        m for m in config.scheduled_matches 
        if m.status == 'approved'
    ]
    
    # Find which scheduled matches have already been played
    played_match_ids = set()
    for match in session.matches:
        # Check if any session match corresponds to a scheduled match
        for sm in config.scheduled_matches:
            if (set(match.team1) == set(sm.team1) and 
                set(match.team2) == set(sm.team2)):
                played_match_ids.add(sm.id)
    
    # Get unplayed approved matches
    unplayed = [m for m in approved_matches if m.id not in played_match_ids]
    
    if not unplayed:
        return
    
    # Find empty courts
    from .session import get_empty_courts
    empty_courts = get_empty_courts(session)
    
    if not empty_courts:
        return
    
    # Sort unplayed matches by wait priority of players involved
    # Players who have waited longer get priority
    from .wait_priority import calculate_wait_priority_info
    
    def match_wait_priority(scheduled_match: ScheduledMatch) -> float:
        """Calculate combined wait priority for all players in match."""
        total_priority = 0.0
        for player_id in scheduled_match.get_all_players():
            if player_id in session.active_players:
                info = calculate_wait_priority_info(session, player_id)
                total_priority += info.total_wait_seconds
        return total_priority
    
    # Sort by total wait time (highest first)
    unplayed.sort(key=match_wait_priority, reverse=True)
    
    # Check player availability (not in active match)
    active_players = set()
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            active_players.update(match.team1)
            active_players.update(match.team2)
    
    # Assign matches to courts
    from .session import create_match
    
    for court_number in empty_courts:
        for scheduled_match in unplayed:
            match_players = set(scheduled_match.get_all_players())
            
            # All players must be available
            if match_players & active_players:
                continue
            
            # All players must be active in session
            if not match_players.issubset(session.active_players):
                continue
            
            # Create actual match
            create_match(
                session,
                court_number,
                scheduled_match.team1,
                scheduled_match.team2
            )
            
            # Mark players as active
            active_players.update(match_players)
            
            # Remove from unplayed list
            unplayed.remove(scheduled_match)
            break


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
