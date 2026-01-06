"""
Continuous Wave Flow Algorithm - Dynamic skill-balanced matchmaking with continuous court flow

This mode generates the first round of matches for review, then dynamically creates
new matches as courts become available. Key features:
- First round only is pre-scheduled in Manage Matches
- New matches generated dynamically when each court finishes
- Prioritizes players who have waited longest
- Optimizes for balance among selected players
- Soft variety constraints (don't block matches, just prefer variety)
- Always swaps at least 2 players between matches
- Warns when waitlist has fewer than 2 players
"""

from typing import List, Dict, Tuple, Optional, Set
from itertools import combinations
from dataclasses import dataclass
import random
import math
import uuid
import json

from .pickleball_types import (
    Player, Session, ScheduledMatch, ContinuousWaveFlowConfig, 
    QueuedMatch, Match, PlayerStats
)


# Constants
DEFAULT_GAMES_PER_PLAYER = 8
MAX_PARTNER_REPEATS = 0  # Soft limit - prefer to avoid
MAX_OPPONENT_PAIR_REPEATS = 0  # Soft limit - prefer to avoid
MAX_INDIVIDUAL_OPPONENT_REPEATS = 3  # Soft limit - prefer to avoid


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
    
    # Bonus for homogeneous skill level in the entire match
    all_ratings_range = max(all_ratings) - min(all_ratings)
    
    if all_ratings_range < 200:
        balance_score += 300  # Excellent: all players very similar
    elif all_ratings_range < 400:
        balance_score += 150  # Good: reasonably similar
    elif all_ratings_range > 800:
        balance_score -= 200  # Penalty for very wide skill range
    
    # Bonus for within-team similarity
    team1_gap = max(team1_ratings) - min(team1_ratings) if len(team1_ratings) > 1 else 0
    team2_gap = max(team2_ratings) - min(team2_ratings) if len(team2_ratings) > 1 else 0
    
    if team1_gap < 150 and team2_gap < 150:
        balance_score += 200  # Both teams are homogeneous
    elif team1_gap < 300 and team2_gap < 300:
        balance_score += 100
    
    balance_score -= (team1_gap + team2_gap) * 0.3
    
    return balance_score


def get_player_wait_priority(session: Session, player_id: str) -> float:
    """
    Calculate wait priority for a player.
    Higher value = waited longer = higher priority.
    """
    stats = session.player_stats.get(player_id)
    if not stats:
        return 0.0
    
    # Use total wait time + current wait time if waiting
    total_wait = stats.total_wait_time
    
    if stats.wait_start_time:
        from .time_manager import now
        current_wait = (now() - stats.wait_start_time).total_seconds()
        total_wait += current_wait
    
    # Also factor in games_waited as secondary metric
    return total_wait + (stats.games_waited * 60)  # Each game wait = 60 seconds


def calculate_variety_penalty(session: Session, team1: List[str], team2: List[str]) -> float:
    """
    Calculate a penalty for variety constraint violations.
    Higher penalty = worse (more repetition).
    
    This is a SOFT constraint - we don't block matches, just prefer variety.
    """
    penalty = 0.0
    
    # Check partnerships
    for team in [team1, team2]:
        if len(team) == 2:
            p1, p2 = team
            stats1 = session.player_stats.get(p1)
            if stats1 and p2 in stats1.partners_played:
                partner_count = stats1.partners_played[p2]
                penalty += partner_count * 100  # 100 per repeat
    
    # Check opponents
    for p1 in team1:
        for p2 in team2:
            stats1 = session.player_stats.get(p1)
            if stats1 and p2 in stats1.opponents_played:
                opp_count = stats1.opponents_played[p2]
                if opp_count > MAX_INDIVIDUAL_OPPONENT_REPEATS:
                    penalty += (opp_count - MAX_INDIVIDUAL_OPPONENT_REPEATS) * 50
    
    return penalty


def generate_first_round_schedule(
    session: Session,
    config: Optional[ContinuousWaveFlowConfig] = None
) -> List[ScheduledMatch]:
    """
    Generate the first round of matches for Continuous Wave Flow mode.
    Only generates enough matches to fill all courts once.
    """
    if config is None:
        config = ContinuousWaveFlowConfig()
    
    players = session.config.players
    num_players = len(players)
    num_courts = session.config.courts
    
    if num_players < 4:
        return []
    
    # Get first bye players to exclude from first round
    first_bye_player_ids = set(session.config.first_bye_players or [])
    
    # Get player ratings
    player_ratings: Dict[str, float] = {}
    for player in players:
        player_ratings[player.id] = get_player_skill_rating(session, player.id)
    
    # Available players (excluding first byes)
    available_players = [p.id for p in players if p.id not in first_bye_player_ids]
    
    # Sort by rating for balanced initial distribution
    available_players.sort(key=lambda p: player_ratings.get(p, 1500), reverse=True)
    
    scheduled_matches: List[ScheduledMatch] = []
    used_players: Set[str] = set()
    
    # Generate matches for each court
    for court_idx in range(num_courts):
        remaining = [p for p in available_players if p not in used_players]
        
        if len(remaining) < 4:
            break
        
        # Select top 4 remaining by interleaving skill levels
        # Take 2 high, 2 lower skill
        pool_size = min(8, len(remaining))
        candidates = remaining[:pool_size]
        
        best_match = None
        best_score = -float('inf')
        
        # Try all 4-player combinations from candidates
        for combo in combinations(candidates, 4):
            combo_list = list(combo)
            
            # Try all team configurations
            for team1, team2 in [
                ([combo_list[0], combo_list[1]], [combo_list[2], combo_list[3]]),
                ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
                ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]]),
            ]:
                balance_score = calculate_team_balance_score(session, team1, team2)
                
                if balance_score > best_score:
                    best_score = balance_score
                    best_match = (team1[:], team2[:])
        
        if best_match:
            team1, team2 = best_match
            used_players.update(team1 + team2)
            
            scheduled_matches.append(ScheduledMatch(
                id=f"scheduled_{uuid.uuid4().hex[:8]}",
                team1=team1,
                team2=team2,
                status='pending',
                match_number=len(scheduled_matches) + 1,
                balance_score=best_score
            ))
    
    return scheduled_matches


def generate_next_match_for_court(
    session: Session,
    court_number: int,
    just_finished_players: Set[str]
) -> Optional[Tuple[List[str], List[str]]]:
    """
    Generate the next match for a court that just finished.
    
    Args:
        session: Current session state
        court_number: The court that needs a new match
        just_finished_players: Player IDs from the match that just finished
        
    Returns:
        (team1, team2) tuple or None if not enough players
        
    Rules:
    1. Prioritize players who have waited longest
    2. Must swap at least 2 players from the previous match
    3. Optimize for best balance among selected players
    4. Use soft variety constraints (prefer variety but don't block)
    """
    from .queue_manager import get_players_in_active_matches
    
    # Get all players in active matches (excluding the court we're filling)
    players_in_matches = get_players_in_active_matches(session)
    
    # Available players = active players not in other matches
    available_ids = [
        p_id for p_id in session.active_players 
        if p_id not in players_in_matches
    ]
    
    if len(available_ids) < 4:
        return None
    
    # Sort by wait priority (highest first)
    available_ids.sort(key=lambda p: get_player_wait_priority(session, p), reverse=True)
    
    # Select top 4 waiters (prioritize longest waiters)
    selected_players = available_ids[:4]
    
    # Check if we're swapping at least 2 players
    carried_over = set(selected_players) & just_finished_players
    if len(carried_over) > 2:
        # Need to swap more players - replace some carried over with other waiters
        non_carried = [p for p in available_ids if p not in just_finished_players]
        to_replace = len(carried_over) - 2  # Need to swap at least 2 more
        
        if len(non_carried) >= to_replace:
            # Remove some carried-over players and add waiters
            kept_carried = list(carried_over)[:2]  # Keep only 2 from previous match
            selected_players = kept_carried + non_carried[:4 - len(kept_carried)]
    
    if len(selected_players) < 4:
        # Not enough unique players, use what we have
        selected_players = available_ids[:4]
    
    # Find best team configuration among selected players
    best_match = None
    best_score = -float('inf')
    
    combo_list = selected_players[:4]
    
    for team1, team2 in [
        ([combo_list[0], combo_list[1]], [combo_list[2], combo_list[3]]),
        ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
        ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]]),
    ]:
        balance_score = calculate_team_balance_score(session, team1, team2)
        variety_penalty = calculate_variety_penalty(session, team1, team2)
        
        total_score = balance_score - variety_penalty
        
        if total_score > best_score:
            best_score = total_score
            best_match = (team1[:], team2[:])
    
    return best_match


def check_waitlist_warning(session: Session) -> Optional[str]:
    """
    Check if the waitlist is too small for optimal continuous wave flow.
    
    Returns warning message if waitlist < 2, None otherwise.
    """
    from .queue_manager import get_players_in_active_matches
    
    players_in_matches = get_players_in_active_matches(session)
    waiting_count = len(session.active_players) - len(players_in_matches)
    
    config = session.config.continuous_wave_flow_config
    threshold = config.min_waitlist_warning_threshold if config else 2
    
    if waiting_count < threshold:
        return (
            f"⚠️ Warning: Only {waiting_count} player(s) waiting. "
            f"Continuous Wave Flow works best with at least {threshold} players waiting "
            f"to ensure proper player rotation between matches."
        )
    
    return None


def populate_courts_continuous_wave_flow(session: Session) -> None:
    """
    Populate empty courts using Continuous Wave Flow algorithm.
    Called when matches complete to fill courts dynamically.
    """
    from .queue_manager import get_empty_courts, get_players_in_active_matches
    from .pickleball_types import Match
    from .utils import generate_id
    from .time_manager import now
    
    config = session.config.continuous_wave_flow_config
    if not config:
        return
    
    # First round: use pre-scheduled matches
    if not config.schedule_finalized:
        return
    
    # Check for approved matches to play
    if config.scheduled_matches:
        approved_unplayed = [
            m for m in config.scheduled_matches 
            if m.status == 'approved'
        ]
        
        # Check if any approved matches haven't been converted to active matches yet
        existing_match_keys = set()
        for match in session.matches:
            key = frozenset(match.team1 + match.team2)
            existing_match_keys.add(key)
        
        for scheduled in approved_unplayed:
            key = frozenset(scheduled.team1 + scheduled.team2)
            if key not in existing_match_keys:
                # This is a first-round match that needs to be started
                empty_courts = get_empty_courts(session)
                if not empty_courts:
                    break
                
                # Check player availability
                players_in_matches = get_players_in_active_matches(session)
                match_players = set(scheduled.team1 + scheduled.team2)
                
                if not (match_players & players_in_matches):
                    court_num = empty_courts[0]
                    match = Match(
                        id=generate_id(),
                        court_number=court_num,
                        team1=scheduled.team1[:],
                        team2=scheduled.team2[:],
                        status='waiting',
                        start_time=now()
                    )
                    session.matches.append(match)
        
        # After first round matches are done, clear scheduled matches
        # so we generate dynamically
        active_scheduled = any(
            m.status == 'approved' and 
            frozenset(m.team1 + m.team2) not in existing_match_keys
            for m in config.scheduled_matches
        )
        
        if not active_scheduled:
            # First round complete, now generate dynamically
            config.scheduled_matches = []
    
    # Dynamic match generation for subsequent rounds
    empty_courts = get_empty_courts(session)
    
    for court_num in empty_courts:
        # Find the last match on this court
        court_matches = [
            m for m in session.matches 
            if m.court_number == court_num and m.status in ['completed', 'forfeited']
        ]
        
        just_finished_players = set()
        if court_matches:
            last_match = max(court_matches, key=lambda m: m.end_time or now())
            just_finished_players = set(last_match.team1 + last_match.team2)
        
        # Generate next match
        result = generate_next_match_for_court(session, court_num, just_finished_players)
        
        if result:
            team1, team2 = result
            match = Match(
                id=generate_id(),
                court_number=court_num,
                team1=team1,
                team2=team2,
                status='waiting',
                start_time=now()
            )
            session.matches.append(match)


def validate_schedule(
    session: Session,
    scheduled_matches: List[ScheduledMatch],
    config: ContinuousWaveFlowConfig
) -> ScheduleValidationResult:
    """Validate the first round schedule."""
    violations = []
    games_per_player: Dict[str, int] = {}
    
    for player in session.config.players:
        games_per_player[player.id] = 0
    
    for match in scheduled_matches:
        if match.status == 'approved':
            for pid in match.team1 + match.team2:
                games_per_player[pid] = games_per_player.get(pid, 0) + 1
    
    return ScheduleValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        games_per_player=games_per_player
    )


def get_schedule_summary(
    session: Session,
    scheduled_matches: List[ScheduledMatch],
    config: ContinuousWaveFlowConfig
) -> Dict:
    """Get summary statistics about the first round schedule."""
    approved = [m for m in scheduled_matches if m.status == 'approved']
    pending = [m for m in scheduled_matches if m.status == 'pending']
    rejected = [m for m in scheduled_matches if m.status == 'rejected']
    
    avg_balance = 0.0
    if approved:
        avg_balance = sum(m.balance_score for m in approved) / len(approved)
    
    return {
        'total_matches': len(scheduled_matches),
        'approved': len(approved),
        'pending': len(pending),
        'rejected': len(rejected),
        'is_valid': True,
        'violations': 0,
        'average_balance_score': avg_balance,
        'note': 'First round only - subsequent matches generated dynamically'
    }


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


def regenerate_match(
    session: Session,
    current_schedule: List[ScheduledMatch],
    rejected_match_index: int,
    config: ContinuousWaveFlowConfig
) -> Optional[ScheduledMatch]:
    """Regenerate a single rejected match for the first round."""
    if rejected_match_index < 0 or rejected_match_index >= len(current_schedule):
        return None
    
    rejected_match = current_schedule[rejected_match_index]
    rejected_players = set(rejected_match.team1 + rejected_match.team2)
    
    # Find used players in approved matches
    used_players: Set[str] = set()
    for i, m in enumerate(current_schedule):
        if i != rejected_match_index and m.status == 'approved':
            used_players.update(m.team1 + m.team2)
    
    # Get available players
    available = [
        p.id for p in session.config.players 
        if p.id not in used_players
    ]
    
    if len(available) < 4:
        return None
    
    # Prefer rejected players if available
    priority_players = [p for p in rejected_players if p in available]
    other_players = [p for p in available if p not in rejected_players]
    candidates = priority_players + other_players
    
    best_match = None
    best_score = -float('inf')
    
    for combo in combinations(candidates[:8], 4):
        combo_list = list(combo)
        
        for team1, team2 in [
            ([combo_list[0], combo_list[1]], [combo_list[2], combo_list[3]]),
            ([combo_list[0], combo_list[2]], [combo_list[1], combo_list[3]]),
            ([combo_list[0], combo_list[3]], [combo_list[1], combo_list[2]]),
        ]:
            score = calculate_team_balance_score(session, team1, team2)
            
            if score > best_score:
                best_score = score
                best_match = (team1[:], team2[:])
    
    if best_match:
        team1, team2 = best_match
        return ScheduledMatch(
            id=f"scheduled_{uuid.uuid4().hex[:8]}",
            team1=team1,
            team2=team2,
            status='pending',
            match_number=rejected_match.match_number,
            balance_score=best_score
        )
    
    return None


def swap_player_in_match(
    session: Session,
    match: ScheduledMatch,
    old_player_id: str,
    new_player_id: str,
    current_schedule: List[ScheduledMatch],
    config: ContinuousWaveFlowConfig
) -> Tuple[bool, Optional[ScheduledMatch], str]:
    """Swap a player in a first round match with another player."""
    if old_player_id not in match.team1 + match.team2:
        return False, None, f"Player {old_player_id} not in this match"
    
    if new_player_id in match.team1 + match.team2:
        return False, None, f"Player {new_player_id} already in this match"
    
    # Create new teams with swap
    new_team1 = [new_player_id if p == old_player_id else p for p in match.team1]
    new_team2 = [new_player_id if p == old_player_id else p for p in match.team2]
    
    new_balance = calculate_team_balance_score(session, new_team1, new_team2)
    
    new_match = ScheduledMatch(
        id=match.id,
        team1=new_team1,
        team2=new_team2,
        status=match.status,
        match_number=match.match_number,
        balance_score=new_balance
    )
    
    return True, new_match, ""


def export_schedule_to_json(
    session: Session,
    scheduled_matches: List[ScheduledMatch],
    config: ContinuousWaveFlowConfig
) -> str:
    """Export first round matches to JSON format."""
    player_map = {p.id: {'name': p.name, 'rating': p.skill_rating} 
                  for p in session.config.players}
    
    export_data = {
        'version': '1.0',
        'export_type': 'continuous_wave_flow_schedule',
        'config': {
            'games_per_player': config.games_per_player,
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
    config: ContinuousWaveFlowConfig
) -> Tuple[bool, List[ScheduledMatch], str]:
    """Import first round matches from JSON format."""
    try:
        data = json.loads(json_str)
        
        if data.get('export_type') != 'continuous_wave_flow_schedule':
            return False, [], "Invalid export type"
        
        name_to_id = {p.name: p.id for p in session.config.players}
        
        imported_matches = []
        for match_data in data.get('matches', []):
            team1 = []
            team2 = []
            
            for name in match_data.get('team1', []):
                if name in name_to_id:
                    team1.append(name_to_id[name])
                else:
                    return False, [], f"Player '{name}' not found"
            
            for name in match_data.get('team2', []):
                if name in name_to_id:
                    team2.append(name_to_id[name])
                else:
                    return False, [], f"Player '{name}' not found"
            
            if len(team1) != 2 or len(team2) != 2:
                return False, [], "Invalid team size"
            
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
