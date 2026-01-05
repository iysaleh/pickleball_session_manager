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
    
    ALGORITHM: Round-robin inspired approach
    1. Generate all possible unique partnership pairings
    2. Create matches by selecting compatible partnerships
    3. Ensure balanced games per player
    4. Apply skill-based team formation
    5. Respect first bye players
    
    Returns list of ScheduledMatch objects (all with 'pending' status).
    """
    if config is None:
        config = CompetitiveRoundRobinConfig()
    
    players = session.config.players
    num_players = len(players)
    
    if num_players < 4:
        return []
    
    # Get first bye players to exclude from initial matches
    first_bye_player_ids = set(session.config.first_bye_players or [])
    
    # Get player ratings and organize by skill
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
    
    scheduled_matches: List[ScheduledMatch] = []
    match_number = 0
    
    def get_team_rating(team: List[str]) -> float:
        """Get total rating of a team."""
        return sum(player_ratings.get(pid, 1500) for pid in team)
    
    def can_form_match(team1: List[str], team2: List[str]) -> bool:
        """Check if two teams can play against each other."""
        p1, p2 = team1
        p3, p4 = team2
        
        # Check if all players can still play
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
        
        for pid in [p1, p2, p3, p4]:
            games_per_player[pid] += 1
        
        partnership_used[p1].add(p2)
        partnership_used[p2].add(p1)
        partnership_used[p3].add(p4)
        partnership_used[p4].add(p3)
        
        for a in team1:
            for b in team2:
                individual_opponent_count[a][b] = individual_opponent_count[a].get(b, 0) + 1
                individual_opponent_count[b][a] = individual_opponent_count[b].get(a, 0) + 1
    
    def get_available_partners(player: str) -> List[str]:
        """Get players who can still partner with this player."""
        return [p for p in all_player_ids 
                if p != player 
                and p not in partnership_used[player]
                and games_per_player[p] < max_games]
    
    def players_needing_games() -> List[str]:
        """Get players who still need games, sorted by games needed."""
        need = [pid for pid in all_player_ids if games_per_player[pid] < target_games]
        need.sort(key=lambda p: (games_per_player[p], -player_ratings.get(p, 1500)))
        return need
    
    def try_create_match_for_player(player: str) -> Optional[Tuple[List[str], List[str]]]:
        """Try to create a balanced match including the given player."""
        partners = get_available_partners(player)
        if not partners:
            return None
        
        # Sort partners by games needed (prioritize underplayed) and skill similarity
        partners.sort(key=lambda p: (
            games_per_player[p],
            abs(player_ratings.get(p, 1500) - player_ratings.get(player, 1500))
        ))
        
        for partner in partners[:8]:  # Try top 8 potential partners
            team1 = [player, partner]
            team1_rating = get_team_rating(team1)
            
            # Find opponents
            available = [p for p in all_player_ids 
                        if p not in team1 
                        and games_per_player[p] < max_games]
            
            # Sort by skill similarity to create balanced match
            available.sort(key=lambda p: (
                games_per_player[p],
                -player_ratings.get(p, 1500)
            ))
            
            best_match = None
            best_balance = float('inf')
            
            # Try different opponent combinations
            for i, opp1 in enumerate(available[:10]):
                for opp2 in available[i+1:10]:
                    team2 = [opp1, opp2]
                    
                    if can_form_match(team1, team2):
                        # Score by balance
                        team2_rating = get_team_rating(team2)
                        balance = abs(team1_rating - team2_rating)
                        
                        if balance < best_balance:
                            best_balance = balance
                            best_match = (team1[:], team2[:])
            
            if best_match:
                return best_match
        
        return None
    
    # Main generation loop - round-robin style
    max_iterations = num_players * target_games * 2
    
    for iteration in range(max_iterations):
        # Get players who need games
        need = players_needing_games()
        
        if not need:
            break  # Everyone has enough games
        
        if len(need) < 4:
            break  # Can't form a match
        
        # Try to create match for most underplayed player
        result = None
        for player in need[:8]:  # Try most underplayed players
            result = try_create_match_for_player(player)
            if result:
                break
        
        if not result:
            # Try harder by relaxing some constraints
            # First, try ANY valid match among players who need games
            for combo in combinations(need[:16], 4):
                players_list = list(combo)
                # Try all team configurations
                configs = [
                    ([players_list[0], players_list[1]], [players_list[2], players_list[3]]),
                    ([players_list[0], players_list[2]], [players_list[1], players_list[3]]),
                    ([players_list[0], players_list[3]], [players_list[1], players_list[2]]),
                ]
                for team1, team2 in configs:
                    if can_form_match(team1, team2):
                        result = (team1, team2)
                        break
                if result:
                    break
        
        if not result:
            break  # Can't generate more matches
        
        team1, team2 = result
        record_match(team1, team2)
        match_number += 1
        
        # Create scheduled match
        balance_score = calculate_team_balance_score(session, team1, team2)
        scheduled_match = ScheduledMatch(
            id=f"scheduled_{uuid.uuid4().hex[:8]}",
            team1=team1,
            team2=team2,
            status='pending',
            match_number=match_number,
            balance_score=balance_score
        )
        scheduled_matches.append(scheduled_match)
    
    # Reorder for fair distribution (first bye players later in queue)
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
    
    Goals:
    - Players should be evenly distributed across the match queue
    - First bye players should not appear in early matches
    - Minimize consecutive matches for same player
    """
    if len(matches) <= 4:
        return matches
    
    reordered = []
    
    # Track when each player was last scheduled
    last_scheduled: Dict[str, int] = {pid: -999 for pid in all_player_ids}
    
    # Separate first-bye player matches from others
    non_first_bye_matches = []
    first_bye_matches = []
    
    for match in matches:
        match_players = set(match.get_all_players())
        if match_players & first_bye_player_ids:
            first_bye_matches.append(match)
        else:
            non_first_bye_matches.append(match)
    
    # If no first-bye players, just do simple fair distribution
    if not first_bye_matches:
        # Reorder based on player wait times for even distribution
        remaining = matches[:]
        while remaining:
            best_match = None
            best_score = -float('inf')
            
            for match in remaining:
                score = 0
                for pid in match.get_all_players():
                    wait = len(reordered) - last_scheduled[pid]
                    score += min(wait, 20)
                
                # Slight preference for original order (stability)
                score -= remaining.index(match) * 0.1
                
                if score > best_score:
                    best_score = score
                    best_match = match
            
            if best_match:
                remaining.remove(best_match)
                reordered.append(best_match)
                for pid in best_match.get_all_players():
                    last_scheduled[pid] = len(reordered)
        
        return reordered
    
    # With first-bye players: put some non-first-bye matches first, then mix in first-bye matches
    # Target: first bye players start appearing after ~1/4 of matches
    insert_point = max(1, len(non_first_bye_matches) // 4)
    
    # Add initial non-first-bye matches
    for i, match in enumerate(non_first_bye_matches[:insert_point]):
        reordered.append(match)
        for pid in match.get_all_players():
            last_scheduled[pid] = len(reordered)
    
    # Now interleave remaining matches based on player wait time
    remaining = non_first_bye_matches[insert_point:] + first_bye_matches
    
    while remaining:
        # Score each remaining match by how long its players have waited
        best_match = None
        best_score = -float('inf')
        
        for match in remaining:
            score = 0
            for pid in match.get_all_players():
                wait = len(reordered) - last_scheduled[pid]
                score += min(wait, 20)
            
            # Slight preference for original order (stability)
            score -= remaining.index(match) * 0.1
            
            if score > best_score:
                best_score = score
                best_match = match
        
        if best_match:
            remaining.remove(best_match)
            reordered.append(best_match)
            for pid in best_match.get_all_players():
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
