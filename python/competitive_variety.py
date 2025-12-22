"""
Competitive Variety Matchmaking - ELO-based skill-balanced matchmaking with adaptive variety constraints

Key feature: Constraints progressively relax as session advances to prioritize balance over variety.
"""

from typing import List, Dict, Tuple, Set, Optional
from datetime import datetime
from .types import Player, QueuedMatch, Session, Match
from .time_manager import now
import math
from itertools import combinations
from .wait_priority import get_priority_aware_candidates, should_prioritize_wait_differences

# Constants for ELO system
BASE_RATING = 1500
PROVISIONAL_GAMES = 2  # Players are provisional for 2 games
MAX_RATING = 2200
MIN_RATING = 800

# Hard constraints for repetition
PARTNER_REPETITION_GAMES_REQUIRED = 3  # Must wait 3 games before playing with same partner
OPPONENT_REPETITION_GAMES_REQUIRED = 2  # Must wait 2 games before playing against same opponent

# Roaming Range for Matchmaking
ROAMING_RANK_PERCENTAGE = 0.5  # Players can play with others within +/- 50% of total players range

# Profiles for Competitive Variety Settings
COMPETITIVENESS_PROFILES = {
    "ultra-competitive": 0.35,
    "competitive": 0.5,
    "semi-competitive": 0.65,
    "casual": 0.8
}

VARIETY_PROFILES = {
    "min": {
        "partner_repetition_limit": 1,
        "opponent_repetition_limit": 1
    },
    "balanced": {
        "partner_repetition_limit": 3,
        "opponent_repetition_limit": 2
    },
    "max": {
        "partner_repetition_limit": 4,
        "opponent_repetition_limit": 3
    }
}

# Dynamic session progression based on player game experience
def calculate_session_thresholds(session: Session) -> Dict[str, int]:
    """
    Calculate dynamic session progression thresholds based on player count and game experience.
    
    Logic:
    - Provisional: First 2 games for all players (exploration phase)
    - Early to Mid: Players average 2 more games (4 total - variety establishment)
    - Mid to Late: Players average 2 more games (6 total - balance prioritization)
    - Late+: Beyond 6 games per player (maximum balance focus)
    
    Returns thresholds for early_to_mid, mid_to_late transitions.
    """
    num_players = len(session.active_players)
    
    # Each round uses 8 players (4v4 doubles), so matches_per_round = num_players / 4
    # But we need to account for players sitting out
    matches_per_round = max(1, num_players // 4)
    
    # Provisional phase: 2 games per player on average
    # Total matches needed = (num_players * 2) / 4 players per match
    provisional_matches = (num_players * 2) // 4
    
    # Early to Mid transition: +2 more games per player (4 total)
    early_to_mid_matches = (num_players * 4) // 4
    
    # Mid to Late transition: +2 more games per player (6 total)
    mid_to_late_matches = (num_players * 6) // 4
    
    return {
        'early_to_mid': early_to_mid_matches,
        'mid_to_late': mid_to_late_matches
    }


def get_adaptive_constraints(session: Session) -> Dict[str, float]:
    """
    Get adaptive balance weighting based on session progression.
    
    Uses dynamic thresholds based on player count and average games played.
    MAINTAINS all variety constraints but reduces them minimally (never to 0).
    
    Returns:
        Dict with 'roaming_range', 'partner_repetition', 'opponent_repetition', 'balance_weight'
    """
    # Check if adaptive constraints are disabled
    if session.adaptive_constraints_disabled:
        return {
            'roaming_range': 0.65,           # Keep skill bracket quality
            'partner_repetition': 3,         # Standard constraints
            'opponent_repetition': 2,        # Standard constraints
            'balance_weight': 1.0            # Standard balance weighting
        }
    
    # Count completed matches as progress metric
    completed_matches = len([m for m in session.matches if m.status == 'completed'])
    
    # Calculate dynamic thresholds based on player count
    thresholds = calculate_session_thresholds(session)
    early_to_mid = thresholds['early_to_mid']
    mid_to_late = thresholds['mid_to_late']
    
    # Base constraints that maintain quality
    base_constraints = {
        'roaming_range': 0.65,     # ALWAYS maintain skill bracket quality
    }
    
    if completed_matches < early_to_mid:
        # Early session: Standard constraints and weighting
        return {
            **base_constraints,
            'partner_repetition': 3,    # Standard partner repetition
            'opponent_repetition': 2,   # Standard opponent repetition
            'balance_weight': 1.0       # Standard balance weighting
        }
    elif completed_matches < mid_to_late:
        # Mid session: Slight constraint relaxation, increased balance priority
        return {
            **base_constraints,
            'partner_repetition': 2,    # Reduced but not eliminated
            'opponent_repetition': 1,   # Reduced but not eliminated
            'balance_weight': 3.0       # 3x balance weighting
        }
    else:
        # Late session: Minimal constraints, maximum balance priority
        return {
            **base_constraints,
            'partner_repetition': 1,    # Minimum constraint (never 0)
            'opponent_repetition': 1,   # Minimum constraint (never 0)
            'balance_weight': 5.0       # 5x balance weighting
        }


def get_adaptive_phase_info(session: Session) -> Dict[str, any]:
    """
    Get information about the current adaptive phase.
    
    Returns:
        Dict with 'phase_name', 'phase_index', 'auto_balance_weight', 'effective_balance_weight',
        'early_threshold', 'late_threshold', 'completed_matches', 'avg_games_per_player'
    """
    completed_matches = len([m for m in session.matches if m.status == 'completed'])
    thresholds = calculate_session_thresholds(session)
    constraints = get_adaptive_constraints(session)
    
    # Check if disabled
    if session.adaptive_constraints_disabled:
        phase_name = "Disabled"
        phase_index = -1
    else:
        # Determine current phase
        if completed_matches < thresholds['early_to_mid']:
            phase_name = "Early"
            phase_index = 0
        elif completed_matches < thresholds['mid_to_late']:
            phase_name = "Mid"
            phase_index = 1
        else:
            phase_name = "Late"
            phase_index = 2
    
    # Calculate average games per player
    num_players = len(session.active_players)
    avg_games_per_player = (completed_matches * 4) / num_players if num_players > 0 else 0
    
    # Get effective balance weight (manual override or automatic)
    auto_balance_weight = constraints['balance_weight']
    effective_balance_weight = session.adaptive_balance_weight if session.adaptive_balance_weight is not None else auto_balance_weight
    
    return {
        'phase_name': phase_name,
        'phase_index': phase_index,
        'auto_balance_weight': auto_balance_weight,
        'effective_balance_weight': effective_balance_weight,
        'early_threshold': thresholds['early_to_mid'],
        'late_threshold': thresholds['mid_to_late'],
        'completed_matches': completed_matches,
        'avg_games_per_player': avg_games_per_player
    }


def apply_adaptive_constraints(session: Session) -> None:
    """
    Apply adaptive constraints to the session based on progression.
    Updates session settings to reflect current adaptive constraints.
    
    If session.adaptive_balance_weight is set (manual override), uses that value.
    Otherwise, calculates weight automatically based on session progression.
    """
    constraints = get_adaptive_constraints(session)
    
    # Update session settings (roaming range and repetition limits)
    session.competitive_variety_roaming_range_percent = constraints['roaming_range']
    session.competitive_variety_partner_repetition_limit = constraints['partner_repetition']
    session.competitive_variety_opponent_repetition_limit = constraints['opponent_repetition']
    
    # Determine effective balance weight but don't overwrite adaptive_balance_weight
    if session.adaptive_balance_weight is not None:
        # Manual override is active
        effective_weight = session.adaptive_balance_weight
    else:
        # Use automatic calculation  
        effective_weight = constraints['balance_weight']
    
    # Store the effective balance weight in a separate field for scoring function
    session._effective_adaptive_balance_weight = effective_weight


def calculate_elo_rating(player_stats) -> float:
    """
    Calculate ELO-style rating for a player using logarithmic scaling.
    
    Formula inspired by KOC_RANKING_ALGORITHM.md:
    rating = BASE_RATING + 
             log(1 + winRate * 9) * 200 - 200 +
             log(1 + |avgPointDiff|) * 50 * sign(avgPointDiff) +
             log(gamesPlayed) * 30 (if winRate >= 0.6)
    """
    if player_stats.games_played == 0:
        return BASE_RATING
    
    games = player_stats.games_played
    wins = player_stats.wins
    win_rate = wins / games
    
    # Win rate adjustment (logarithmic)
    rating = BASE_RATING + math.log(1 + win_rate * 9) * 200 - 200
    
    # Point differential adjustment
    if games > 0:
        avg_point_diff = (player_stats.total_points_for - player_stats.total_points_against) / games
        if avg_point_diff != 0:
            rating += math.log(1 + abs(avg_point_diff)) * 50 * (1 if avg_point_diff > 0 else -1)
    
    # Consistency bonus for strong players
    if win_rate >= 0.6 and games > 0:
        rating += math.log(games) * 30
    
    # Clamp to valid range
    return max(MIN_RATING, min(MAX_RATING, rating))


def get_player_ranking(session: Session, player_id: str) -> Tuple[int, float]:
    """
    Get a player's rank and rating.
    Returns (rank, rating) where rank is 1-based (1 = best).
    Ranks all active players by rating.
    """
    # Calculate ratings for all active players (sorted for determinism)
    ratings = []
    for pid in sorted(session.active_players):
        if pid in session.player_stats:
            rating = calculate_elo_rating(session.player_stats[pid])
        else:
            rating = BASE_RATING
        ratings.append((pid, rating))
    
    # Sort by rating descending (best first)
    ratings.sort(key=lambda x: x[1], reverse=True)
    
    # Find this player's rank
    for rank, (pid, rating) in enumerate(ratings, 1):
        if pid == player_id:
            return rank, rating
    
    return len(ratings) + 1, BASE_RATING


def is_provisional(session: Session, player_id: str) -> bool:
    """Check if a player is provisional (fewer than PROVISIONAL_GAMES)"""
    if player_id not in session.player_stats:
        return True
    return session.player_stats[player_id].games_played < PROVISIONAL_GAMES


def get_roaming_rank_range(session: Session, player_id: str) -> Tuple[int, int]:
    """
    Get the roaming range of ranks a player can be matched with (symmetric window rule).
    
    For competitive variety mode:
    - Each player can play with others within a symmetric roaming bracket
    - Bracket extends roaming_percent% of players ABOVE and roaming_percent% BELOW
    - Example: 16 players, 25% roaming: 4 above + 4 below + self = 9-player bracket
    - Example: rank #2 with 25% roaming: can play with ranks 1-6 (1 below + 4 above, capped)
    - Example: rank #8 with 25% roaming: can play with ranks 4-12 (4 below + 4 above)
    
    Uses session-level competitive_variety_roaming_range_percent setting.
    
    Returns (min_rank, max_rank) inclusive.
    Only applies when 12+ players.
    """
    total_players = len(session.active_players)
    
    player_rank, _ = get_player_ranking(session, player_id)
    roaming_percent = session.competitive_variety_roaming_range_percent
    
    # Calculate how many players can be above and below (symmetric)
    roaming_distance = max(0, int(total_players * roaming_percent))
    
    # Roaming window extends equally in both directions from player_rank
    min_rank = max(1, player_rank - roaming_distance)
    max_rank = min(player_rank + roaming_distance, total_players)
    
    return min_rank, max_rank


def get_allowed_matchmaking_bracket(session: Session, player_id: str) -> Tuple[int, int]:
    """
    Get the range of ranks a player can be matched with (50% rule - top/bottom split).
    
    For 12+ players:
    - Top 50% players only play with top 50%
    - Bottom 50% players only play with bottom 50%
    - Provisional players can play with anyone
    
    Returns (min_rank, max_rank) inclusive.
    
    Note: This maintains the old bracket logic for backwards compatibility.
    For new code, use get_roaming_rank_range() which uses a moving window instead.
    """
    if is_provisional(session, player_id):
        # Provisional players can play with anyone
        return 1, len(session.active_players)
    
    total_players = len(session.active_players)
    bracket_size = max(1, (total_players + 1) // 2)
    
    player_rank, _ = get_player_ranking(session, player_id)
    
    if player_rank <= bracket_size:
        # In top bracket - can only play with top bracket
        return 1, bracket_size
    else:
        # In bottom bracket - can only play with bottom bracket
        return bracket_size + 1, total_players
    
    return 1, total_players


def can_all_players_play_together(session: Session, player_ids: List[str]) -> bool:
    """
    Check if all players in a potential match can play together under roaming range rules.
    
    For competitive variety mode with 12+ players:
    - All 4 players must be within each other's roaming range
    - This ensures fair skill distribution within matches
    
    Returns True if all players can play together, False otherwise.
    """
    if session.config.mode != 'competitive-variety':
        return True
    
    # Check that all players are within roaming range of each other
    for player_id in player_ids:
        # Check if this player is provisional - they have no roaming restrictions
        if is_provisional(session, player_id):
            continue
        
        min_rank, max_rank = get_roaming_rank_range(session, player_id)
        
        # Check all other players are in this player's roaming range
        for other_player_id in player_ids:
            if other_player_id == player_id:
                continue
            
            other_rank, _ = get_player_ranking(session, other_player_id)
            
            # Other player must be within this player's roaming range
            if other_rank < min_rank or other_rank > max_rank:
                return False
    
    return True



def _get_last_played_info(session: Session, player_id: str) -> Tuple[Optional[Match], int]:
    """
    Get the last completed match a player played in, and its global game number.
    Returns (match, game_number). game_number is 1-based index of completed matches.
    Returns (None, -1) if player hasn't played.
    """
    completed_matches = [m for m in session.matches if m.status == 'completed']
    # Iterate backwards to find last match
    for i in range(len(completed_matches) - 1, -1, -1):
        match = completed_matches[i]
        if player_id in match.team1 or player_id in match.team2:
            return match, i + 1
    return None, -1


def can_play_with_player(session: Session, player1: str, player2: str, role: str, allow_cross_bracket: bool = False) -> bool:
    """
    Check if two players can play together in the given role.
    role = 'partner' or 'opponent'
    
    Hard constraints:
    - Banned pairs cannot be partners
    - Locked teams MUST be partners (and cannot be opponents)
    - If partners: must wait PARTNER_REPETITION_GAMES_REQUIRED games
    - If opponents: must wait OPPONENT_REPETITION_GAMES_REQUIRED games
    - Must respect 50% matchmaking bracket for non-provisional players (unless allow_cross_bracket=True)
    - Only applies when 12+ players (otherwise fewer constraints)
    """
    # 0. Check Locked Teams & Banned Pairs
    # Check Banned Pairs (only applies to partners)
    if role == 'partner' and session.config.banned_pairs:
        for banned in session.config.banned_pairs:
            if player1 in banned and player2 in banned:
                return False

    # Check Locked Teams
    if session.config.locked_teams:
        p1_locked_partner = None
        for team in session.config.locked_teams:
            if player1 in team:
                for member in team:
                    if member != player1:
                        p1_locked_partner = member
                        break
                break
        
        p2_locked_partner = None
        for team in session.config.locked_teams:
            if player2 in team:
                for member in team:
                    if member != player2:
                        p2_locked_partner = member
                        break
                break
        
        if role == 'partner':
            # If p1 is locked to someone else, cannot partner with p2
            if p1_locked_partner and p1_locked_partner != player2:
                return False
            # If p2 is locked to someone else, cannot partner with p1
            if p2_locked_partner and p2_locked_partner != player1:
                return False
            # If they are locked to each other, they CAN (and must) play together
            # This overrides partner repetition constraints
            if p1_locked_partner == player2:
                return True
        
        elif role == 'opponent':
            # If they are locked to each other, they CANNOT be opponents
            if p1_locked_partner == player2:
                return False

    # Check bracket compatibility (Roaming Range Rule)
    # Relaxed if allow_cross_bracket is True
    # NOTE: Provisional players are exempt from roaming range restrictions
    if not allow_cross_bracket and not (is_provisional(session, player1) or is_provisional(session, player2)):
        # Calculate rank difference limit using session's roaming range setting
        roaming_percent = getattr(session, 'competitive_variety_roaming_range_percent', ROAMING_RANK_PERCENTAGE)
        limit = int(len(session.active_players) * roaming_percent)
        
        # Get ranks
        rank1, _ = get_player_ranking(session, player1)
        rank2, _ = get_player_ranking(session, player2)
        
        # Check roaming range (applies in both directions)
        if abs(rank1 - rank2) > limit:
            return False
    
    # ---------------------------------------------------------
    # Repetition Constraints (Robust Two-Phase Check)
    # ---------------------------------------------------------
    
    completed_matches = [m for m in session.matches if m.status == 'completed']
    current_matches_count = len(completed_matches)
    
    # Check 1: Global Recency (The "Wait N Games" Rule)
    # If they played together/against in the last X matches globally, forbid it.
    
    if len(session.active_players) >= 8:
        # Check Partner Repetition (Last N Global Games - using session setting)
        if role == 'partner':
            partner_limit = session.competitive_variety_partner_repetition_limit
            matches_to_check = completed_matches[-partner_limit:] if partner_limit > 0 else []
            for m in matches_to_check:
                p1_t1 = player1 in m.team1
                p1_t2 = player1 in m.team2
                p2_t1 = player2 in m.team1
                p2_t2 = player2 in m.team2
                
                if (p1_t1 and p2_t1) or (p1_t2 and p2_t2):
                    return False

        # Check Opponent Repetition (Last N Global Games - using session setting)
        elif role == 'opponent':
            opponent_limit = session.competitive_variety_opponent_repetition_limit
            matches_to_check = completed_matches[-opponent_limit:] if opponent_limit > 0 else []
            for m in matches_to_check:
                p1_t1 = player1 in m.team1
                p1_t2 = player1 in m.team2
                p2_t1 = player2 in m.team1
                p2_t2 = player2 in m.team2
                
                if (p1_t1 and p2_t2) or (p1_t2 and p2_t1):
                    return False
    else:
        # For < 8 players, enforce at least 1 game gap globally (Immediate Back-to-Back Global)
        if completed_matches:
            last_match = completed_matches[-1]
            if role == 'partner':
                if (player1 in last_match.team1 and player2 in last_match.team1) or \
                   (player1 in last_match.team2 and player2 in last_match.team2):
                    return False
            elif role == 'opponent':
                if (player1 in last_match.team1 and player2 in last_match.team2) or \
                   (player1 in last_match.team2 and player2 in last_match.team1):
                    return False

    # Check 2: Player-Specific History Scan (The "Personal Gap" Rule)
    # We must scan back through the *player's own history* to find when they last played with this partner.
    # The number of *intervening games this player played* must be >= REQUIRED.
    
    player_matches = []
    # Collect all matches this player participated in, in order
    for m in completed_matches:
        if player1 in m.team1 or player1 in m.team2:
            player_matches.append(m)
            
    if player_matches:
        # Scan backwards through player's personal history
        last_played_together_idx = -1
        last_played_against_idx = -1
        
        for i in range(len(player_matches) - 1, -1, -1):
            m = player_matches[i]
            
            # Check Partnership
            if role == 'partner':
                if (player2 in m.team1 and player1 in m.team1) or \
                   (player2 in m.team2 and player1 in m.team2):
                    last_played_together_idx = i
                    break # Found the last time
            
            # Check Opponent
            elif role == 'opponent':
                if (player1 in m.team1 and player2 in m.team2) or \
                   (player1 in m.team2 and player2 in m.team1):
                    last_played_against_idx = i
                    break # Found the last time
        
        current_personal_game_count = len(player_matches)
        
        if role == 'partner' and last_played_together_idx != -1:
            # Games played SINCE that match
            # If I played in match index 0, and now count is 1. Gap is 1-0-1 = 0.
            # If I played in match index 0, then match index 1. Now count is 2.
            # Gap = 2 - 0 - 1 = 1 intervening game.
            intervening_games = current_personal_game_count - last_played_together_idx - 1
            
            # Apply constraint
            if len(session.active_players) >= 8:
                 partner_limit = session.competitive_variety_partner_repetition_limit
                 if intervening_games < partner_limit:
                     return False
            elif intervening_games < 1: # Basic back-to-back check for small groups
                 return False

        elif role == 'opponent' and last_played_against_idx != -1:
            intervening_games = current_personal_game_count - last_played_against_idx - 1
            
            if len(session.active_players) >= 8:
                 opponent_limit = session.competitive_variety_opponent_repetition_limit
                 if intervening_games < opponent_limit:
                     return False
            elif intervening_games < 1:
                 return False
    
    return True


def get_balance_threshold(session: Session) -> float:
    """
    Calculate the maximum acceptable team rating difference based on session progression.
    Balance constraints only activate when adaptive system kicks in (mid-late session).
    
    Returns maximum acceptable rating difference between teams.
    """
    constraints = get_adaptive_constraints(session)
    balance_weight = constraints['balance_weight']
    
    # Balance constraints only activate when adaptive system kicks in
    if balance_weight <= 1.0:  # Early session - no balance constraints
        return float('inf')  # No balance threshold in early session
    elif balance_weight >= 5.0:  # Late session
        return 200  # Very strict balance required
    elif balance_weight >= 3.0:  # Mid session  
        return 300  # Moderate balance required
    else:  # Transitional phase
        return 400  # Lenient balance threshold


def meets_balance_constraints(session: Session, team1: List[str], team2: List[str]) -> bool:
    """
    Check if a potential match meets hard balance constraints.
    As sessions progress and variety constraints relax, balance constraints get stricter.
    """
    # Calculate team ratings
    team1_rating = sum(calculate_elo_rating(session.player_stats.get(p, 
                       type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                       for p in team1)
    team2_rating = sum(calculate_elo_rating(session.player_stats.get(p, 
                       type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                       for p in team2)
    
    # Check if imbalance exceeds threshold
    rating_diff = abs(team1_rating - team2_rating)
    threshold = get_balance_threshold(session)
    
    return rating_diff <= threshold


def score_potential_match(session: Session, team1: List[str], team2: List[str]) -> float:
    """
    Score a potential match based on skill balance and variety.
    Higher score = better match.
    
    Factors:
    - Hard balance constraints (must meet threshold to be valid)
    - Skill balance (teams should be close in rating) - weighted by session progression  
    - Partnership variety (prefer new partnerships)
    - Opponent variety (prefer new opponents)
    - Homogeneous partnership bonus (encourages similar skill partnerships)
    
    Uses adaptive balance weighting and hard balance thresholds.
    Prefers Elite vs Elite, Strong vs Strong, etc. over mixed skill partnerships.
    """
    # First check: must meet hard balance constraints
    if not meets_balance_constraints(session, team1, team2):
        return -10000  # Severely penalize matches that violate balance constraints
    
    score = 0.0
    
    # Get effective adaptive balance weight (increases as session progresses)
    balance_weight = getattr(session, '_effective_adaptive_balance_weight', 1.0)
    
    # Calculate team ratings (total, not average, for better balance)
    team1_rating = sum(calculate_elo_rating(session.player_stats.get(p, 
                       type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                       for p in team1)
    team2_rating = sum(calculate_elo_rating(session.player_stats.get(p, 
                       type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                       for p in team2)
    
    # Calculate individual player ratings for partnership analysis
    team1_ratings = [calculate_elo_rating(session.player_stats.get(p, 
                     type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                     for p in team1]
    team2_ratings = [calculate_elo_rating(session.player_stats.get(p, 
                     type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                     for p in team2]
    
    # Penalize unbalanced teams (large skill difference)
    rating_diff = abs(team1_rating - team2_rating)
    balance_penalty = rating_diff * 2 * balance_weight
    score -= balance_penalty
    
    # Homogeneous Partnership Bonus (only activates when adaptive system kicks in)
    # Reward teams where partners have similar skill levels
    # Elite vs Elite, Strong vs Strong, etc. creates better pickleball experiences
    if balance_weight >= 3.0:  # Mid to late session - adaptive system active
        homogeneous_bonus = 0
        
        # Check each team for similar skill composition
        for team_ratings in [team1_ratings, team2_ratings]:
            skill_difference = max(team_ratings) - min(team_ratings)
            if skill_difference <= 150:  # Partners within 150 rating points (very similar)
                homogeneous_bonus += 75 * balance_weight
            elif skill_difference <= 250:  # Partners within 250 rating points (reasonably similar)
                homogeneous_bonus += 40 * balance_weight
        
        score += homogeneous_bonus
    
    # Penalty for mismatched partnerships (only when adaptive system active)
    # This discourages the "carry" dynamic that creates poor experiences
    if balance_weight >= 3.0:  # Mid to late session - adaptive system active
        mismatch_penalty = 0
        for team_ratings in [team1_ratings, team2_ratings]:
            skill_difference = max(team_ratings) - min(team_ratings)
            if skill_difference >= 400:  # Very large skill gap within team
                mismatch_penalty += 100 * balance_weight  # Heavy penalty
            elif skill_difference >= 300:  # Large skill gap within team  
                mismatch_penalty += 50 * balance_weight   # Moderate penalty
        
        score -= mismatch_penalty
    
    # Bonus for variety (reduced weight as session progresses to prioritize balance)
    variety_weight = max(1.0, 3.0 - (balance_weight - 1.0))  # Decreases from 3.0 to 1.0
    variety_bonus = 0
    
    # Partner variety bonus
    for team in [team1, team2]:
        p1, p2 = team
        if (p1 not in session.player_stats or p2 not in session.player_stats or 
            p2 not in session.player_stats[p1].partners_played):
            variety_bonus += 5 * variety_weight
    
    # Opponent variety bonus  
    for p1 in team1:
        for p2 in team2:
            if (p1 not in session.player_stats or p2 not in session.player_stats or
                p2 not in session.player_stats[p1].opponents_played):
                variety_bonus += 3 * variety_weight
    
    score += variety_bonus
    
    # Perfect balance bonus (extra reward for very close team ratings)
    if rating_diff <= 100:  # Very close teams
        score += 100 * balance_weight
    elif rating_diff <= 200:  # Close teams
        score += 50 * balance_weight
    
    # Skill tier matching bonus (only when adaptive system active)
    # Encourage matches between similar skill levels across teams
    if balance_weight >= 3.0:  # Mid to late session - adaptive system active
        avg_team1_rating = sum(team1_ratings) / 2
        avg_team2_rating = sum(team2_ratings) / 2
        team_avg_diff = abs(avg_team1_rating - avg_team2_rating)
        
        if team_avg_diff <= 100:  # Similar average team skill
            score += 75 * balance_weight
        elif team_avg_diff <= 200:  # Reasonably similar average team skill
            score += 40 * balance_weight
    
    return score


def _can_form_valid_teams(session: Session, players: List[str], allow_cross_bracket: bool = False) -> bool:
    """
    Check if 4 players can form valid teams respecting all competitive variety constraints.
    """
    if len(players) != 4:
        return False
    
    # First check: all players must be within roaming range of each other
    if not can_all_players_play_together(session, players):
        return False
    
    # Try different team configurations
    configs = [
        ([players[0], players[1]], [players[2], players[3]]),
        ([players[0], players[2]], [players[1], players[3]]),
        ([players[0], players[3]], [players[1], players[2]]),
    ]
    
    for team1, team2 in configs:
        valid = True
        
        # Check within-team partnerships
        if not can_play_with_player(session, team1[0], team1[1], 'partner', allow_cross_bracket):
            valid = False
        
        if valid and not can_play_with_player(session, team2[0], team2[1], 'partner', allow_cross_bracket):
            valid = False
        
        # Check cross-team opponents
        if valid:
            for p1 in team1:
                for p2 in team2:
                    if not can_play_with_player(session, p1, p2, 'opponent', allow_cross_bracket):
                        valid = False
                        break
                if not valid:
                    break
        
        if valid:
            return True
    
    return False


def populate_empty_courts_competitive_variety(session: Session) -> None:
    """
    Populate empty courts using competitive variety matchmaking with adaptive balance weighting.
    
    Features:
    1. Check match queue first (respects waitlist)
    2. Generate new matches from available players using ELO balance
    3. Maintains ALL variety constraints (roaming range, repetition limits) 
    4. Adaptive balance weighting: balance becomes increasingly important over time
    5. Preserves skill bracket quality throughout entire session
    
    Adaptive Philosophy:
    - Constraints stay constant (preserve variety and skill-appropriate matches)
    - Balance weighting increases progressively (1x → 3x → 5x → 8x)
    - Algorithm chooses the most balanced option among valid constraint-compliant matches
    """
    if session.config.mode != 'competitive-variety':
        return
    
    # Apply adaptive balance weighting (constraints stay the same)
    apply_adaptive_constraints(session)
    
    from .utils import generate_id
    from .types import Match, PlayerStats, QueuedMatch
    
    # Find empty courts
    occupied_courts = set()
    for match in session.matches:
        if match.status in ['in-progress', 'waiting']:
            occupied_courts.add(match.court_number)
    
    empty_courts = [c for c in range(1, session.config.courts + 1) if c not in occupied_courts]
    
    if not empty_courts:
        return
    
    # Handle first bye players: exclude them ONLY on the true first round
    # A match is "completed" once a winner is determined
    # The first round is specifically: no matches have been completed yet
    first_bye_players_set = set()
    if session.config.first_bye_players:
        # Count completed matches (matches where a winner was decided)
        completed_matches = [m for m in session.matches if m.status == 'completed']
        
        # If we're in the first round (no matches completed yet):
        # Exclude bye players to guarantee them a waiting spot
        if not completed_matches:
            # Check if applying the bye makes sense (will leave people waiting)
            active_count = len(session.active_players)
            players_in_active_matches = set()
            for match in session.matches:
                if match.status in ['in-progress', 'waiting']:
                    players_in_active_matches.update(match.team1 + match.team2)
            
            waiting_count = active_count - len(players_in_active_matches)
            courts_being_filled = len(empty_courts)
            players_these_courts_need = courts_being_filled * 4
            
            # Apply bye unless total players exactly fills all courts
            # Logic: if total players == courts * 4, then use everyone (no bye)
            # Otherwise, apply bye to guarantee bye players sit out first round
            total_court_capacity = courts_being_filled * 4
            
            # Apply bye unless we have exact fit for all courts
            if waiting_count != total_court_capacity:
                first_bye_players_set = set(session.config.first_bye_players)
    
    # Get players currently in active matches
    players_in_matches = set()
    for match in session.matches:
        if match.status in ['in-progress', 'waiting']:
            players_in_matches.update(match.team1 + match.team2)
    
    # First, try to assign matches from the queue (respects waitlist)
    matches_to_remove = []
    for court_idx, court_num in enumerate(empty_courts):
        assigned = False
        
        # Try to find a valid queue match for this court
        for queue_idx, queued_match in enumerate(session.match_queue):
            match_players = set(queued_match.team1 + queued_match.team2)
            
            # Check if all players are available
            if not (match_players & players_in_matches):
                # First check: all players must be within roaming range of each other
                all_players = list(match_players)
                valid = can_all_players_play_together(session, all_players)
                
                # Check competitive variety constraints
                if valid:
                    for p1 in queued_match.team1:
                        for p2 in queued_match.team1:
                            if p1 != p2 and not can_play_with_player(session, p1, p2, 'partner'):
                                valid = False
                                break
                        if not valid:
                            break
                
                if valid:
                    for p1 in queued_match.team1:
                        for p2 in queued_match.team2:
                            if not can_play_with_player(session, p1, p2, 'opponent'):
                                valid = False
                                break
                        if not valid:
                            break
                
                if valid:
                    # Create match from queue
                    match = Match(
                        id=generate_id(),
                        court_number=court_num,
                        team1=queued_match.team1,
                        team2=queued_match.team2,
                        status='waiting',
                        start_time=now()
                    )
                    session.matches.append(match)
                    players_in_matches.update(match_players)
                    matches_to_remove.append(queue_idx)
                    assigned = True
                    break
        
        # If no queue match assigned, try to generate one from available players
        if not assigned:
            # Count completed matches to detect first round
            completed_matches = [m for m in session.matches if m.status == 'completed']
            is_first_round = len(completed_matches) == 0
            
            if is_first_round:
                # First round: randomize player order for variety between sessions
                import random
                available_players = [p for p in session.active_players if p not in players_in_matches and p not in first_bye_players_set]
                random.shuffle(available_players)
            else:
                # Later rounds: use deterministic sorted order for consistency
                available_players = [p for p in sorted(session.active_players) if p not in players_in_matches and p not in first_bye_players_set]
            
            if len(available_players) >= 4:
                # Try to find any 4 players that can form valid teams
                best_team1 = None
                best_team2 = None
                
                # Prioritize Locked Teams
                locked_pairs = []
                if session.config.locked_teams:
                    for team in session.config.locked_teams:
                         if len(team) == 2 and all(p in available_players for p in team):
                             locked_pairs.append(team)
                
                if locked_pairs:
                    # Try to match locked pair vs locked pair first
                    if len(locked_pairs) >= 2:
                         for i in range(len(locked_pairs)):
                             for j in range(i + 1, len(locked_pairs)):
                                 pair1 = locked_pairs[i]
                                 pair2 = locked_pairs[j]
                                 
                                 # Check roaming range
                                 all_players = pair1 + pair2
                                 if not can_all_players_play_together(session, all_players):
                                     continue
                                 
                                 # Check validity of pair1 vs pair2
                                 valid_match = True
                                 for p1 in pair1:
                                     for p2 in pair2:
                                         if not can_play_with_player(session, p1, p2, 'opponent'):
                                             valid_match = False
                                             break
                                     if not valid_match:
                                         break
                                 
                                 if valid_match:
                                     best_team1 = list(pair1)
                                     best_team2 = list(pair2)
                                     break
                             if best_team1:
                                 break
                    
                    # If not found or only 1 locked pair, match vs best available
                    if not best_team1:
                        pair1 = locked_pairs[0]
                        remaining = [p for p in available_players if p not in pair1]
                        
                        # Sort remaining by rating
                        player_ratings = [(p, calculate_elo_rating(session.player_stats.get(p, 
                                          type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))) 
                                          for p in remaining]
                        player_ratings.sort(key=lambda x: x[1], reverse=True)

                        # Try to find a partner pair for opponents
                        # Check top candidates to find a valid pair
                        candidates = [p[0] for p in player_ratings[:8]]
                        found_opponent = False
                        
                        # Try to find a pair among candidates
                        for combo in combinations(candidates, 2):
                             pair2 = list(combo)
                             
                             # Check roaming range
                             all_players = pair1 + pair2
                             if not can_all_players_play_together(session, all_players):
                                 continue
                             
                             if can_play_with_player(session, pair2[0], pair2[1], 'partner'):
                                 # Check opponent validity
                                 valid_match = True
                                 for p1 in pair1:
                                     for p2 in pair2:
                                         if not can_play_with_player(session, p1, p2, 'opponent'):
                                             valid_match = False
                                             break
                                     if not valid_match:
                                         break
                                 
                                 if valid_match:
                                     best_team1 = list(pair1)
                                     best_team2 = list(pair2)
                                     found_opponent = True
                                     break
                        
                        if not found_opponent and len(remaining) >= 2:
                             # If we couldn't find a match in top candidates, try simpler fallback?
                             # Or just let it fall through to main logic which might break the lock 
                             # (but main logic doesn't support locks effectively unless we force it).
                             # Wait, if we don't pick the locked team here, the main logic 
                             # `_can_form_valid_teams` calls `can_play_with_player` which enforces locks.
                             # So if we fail here, the main logic MIGHT pick the locked team if it finds valid opponents.
                             # But main logic iterates combinations of top players. If locked players are low rated, they might be skipped.
                             pass

                if not best_team1:
                    # Detect if this is first round for special handling
                    completed_matches = [m for m in session.matches if m.status == 'completed']
                    is_first_round = len(completed_matches) == 0
                    
                    if is_first_round:
                        # First round: Use all available players to ensure we can fill all courts
                        # Since everyone has equal wait time, no need for priority filtering
                        candidates_for_matching = available_players
                        search_limit = len(candidates_for_matching)
                    else:
                        # Later rounds: Use sophisticated wait time priority system to select candidates
                        # This considers actual wait time, not just game counts
                        
                        # Calculate optimal number of candidates for matching
                        # Need enough for ELO mixing flexibility while prioritizing waiters
                        base_candidates = max(12, len(available_players) // 2)
                        max_candidates = min(16, max(12, base_candidates))
                        
                        # Get priority-aware candidates using the new wait time system
                        candidates_for_matching = get_priority_aware_candidates(
                            session, available_players, max_candidates
                        )
                        
                        # Limit combination search to maintain performance
                        # The candidates are already sorted by wait priority
                        search_limit = min(12, len(candidates_for_matching))
                    
                    # Maintain skill bracket quality - no cross-bracket matching
                    allow_cross = False
                    
                    for combo in combinations(candidates_for_matching[:search_limit], 4):
                        if _can_form_valid_teams(session, list(combo), allow_cross_bracket=allow_cross):
                            # Evaluate all valid team configurations and pick the most balanced
                            configs = [
                                ([combo[0], combo[1]], [combo[2], combo[3]]),
                                ([combo[0], combo[2]], [combo[1], combo[3]]),
                                ([combo[0], combo[3]], [combo[1], combo[2]]),
                            ]
                            
                            best_score = float('-inf')
                            best_config = None
                            
                            for team1, team2 in configs:
                                if (can_play_with_player(session, team1[0], team1[1], 'partner', allow_cross) and
                                    can_play_with_player(session, team2[0], team2[1], 'partner', allow_cross)):
                                    # Check all opponent pairs
                                    valid = True
                                    for p1 in team1:
                                        for p2 in team2:
                                            if not can_play_with_player(session, p1, p2, 'opponent', allow_cross):
                                                valid = False
                                                break
                                        if not valid:
                                            break
                                    
                                    if valid:
                                        # First check: Must meet hard balance constraints (filters out severely imbalanced matches)
                                        if meets_balance_constraints(session, team1, team2):
                                            # Score this configuration for balance and variety
                                            score = score_potential_match(session, team1, team2)
                                            if score > best_score:
                                                best_score = score
                                                best_config = (list(team1), list(team2))
                            
                            if best_config:
                                best_team1, best_team2 = best_config
                                break
                
                if best_team1 and best_team2:
                    match = Match(
                        id=generate_id(),
                        court_number=court_num,
                        team1=best_team1,
                        team2=best_team2,
                        status='waiting',
                        start_time=now()
                    )
                    
                    session.matches.append(match)
                    players_in_matches.update(set(best_team1 + best_team2))
                    
                    # Update stats if needed
                    for player_id in (best_team1 + best_team2):
                        if player_id not in session.player_stats:
                            session.player_stats[player_id] = PlayerStats(player_id=player_id)
    
    # Remove assigned matches from queue (in reverse order to maintain indices)
    for i in sorted(matches_to_remove, reverse=True):
        session.match_queue.pop(i)


def build_match_for_court_competitive_variety(
    session: Session,
    court_number: int,
    available_players: List[str]
) -> Optional[QueuedMatch]:
    """
    Build a match for a specific court using competitive variety rules.
    Returns None if no valid match can be made that respects hard constraints.
    """
    if session.config.mode != 'competitive-variety':
        return None
    
    if len(available_players) < 4:
        return None
    
    # Try to find 4 players that can play together
    from itertools import combinations
    
    for combo in combinations(available_players, 4):
        # Try different team configurations
        configs = [
            ([combo[0], combo[1]], [combo[2], combo[3]]),
            ([combo[0], combo[2]], [combo[1], combo[3]]),
            ([combo[0], combo[3]], [combo[1], combo[2]]),
        ]
        
        for team1, team2 in configs:
            # Check all constraints
            valid = True
            
            # Check within-team partnerships
            if len(team1) == 2:
                if not can_play_with_player(session, team1[0], team1[1], 'partner'):
                    valid = False
            
            if len(team2) == 2:
                if not can_play_with_player(session, team2[0], team2[1], 'partner'):
                    valid = False
            
            # Check cross-team opponents
            if valid:
                for p1 in team1:
                    for p2 in team2:
                        if not can_play_with_player(session, p1, p2, 'opponent'):
                            valid = False
                            break
                    if not valid:
                        break
            
            if valid:
                return QueuedMatch(team1=list(team1), team2=list(team2))
    
    return None


def can_players_form_match_together(
    session: Session,
    player_ids: List[str]
) -> bool:
    """
    Check if these 4 players can form a match together based on hard variety rules.
    Returns False if they violate partnership or opponent repetition constraints,
    or if they violate the roaming range rule.
    """
    if session.config.mode != 'competitive-variety' or len(player_ids) != 4:
        return False
    
    # First check: all players must be within roaming range of each other
    if not can_all_players_play_together(session, player_ids):
        return False
    
    # Try all possible team configurations
    configs = [
        ([player_ids[0], player_ids[1]], [player_ids[2], player_ids[3]]),
        ([player_ids[0], player_ids[2]], [player_ids[1], player_ids[3]]),
        ([player_ids[0], player_ids[3]], [player_ids[1], player_ids[2]]),
    ]
    
    for team1, team2 in configs:
        # Check within-team partnerships
        if len(team1) == 2:
            if not can_play_with_player(session, team1[0], team1[1], 'partner'):
                continue
        
        if len(team2) == 2:
            if not can_play_with_player(session, team2[0], team2[1], 'partner'):
                continue
        
        # Check cross-team opponents
        valid_opponents = True
        for p1 in team1:
            for p2 in team2:
                if not can_play_with_player(session, p1, p2, 'opponent'):
                    valid_opponents = False
                    break
            if not valid_opponents:
                break
        
        if valid_opponents:
            return True
    
    return False


def update_variety_tracking_after_match(
    session: Session,
    court_number: int,
    team1: List[str],
    team2: List[str]
) -> None:
    """
    Update variety tracking after a match completes.
    Tracks game numbers when players were last together/against each other.
    """
    if session.config.mode != 'competitive-variety':
        return
    
    # Get current game number BEFORE incrementing (this is the game that just completed)
    # Count games by completed matches + 1 (since we just finished one)
    completed_count = len([m for m in session.matches if m.status == 'completed'])
    current_game_number = completed_count  # This is the game number we just finished
    
    # Update player_last_court
    for player_id in team1 + team2:
        session.player_last_court[player_id] = court_number
        
        # Also track in court history for inter-court mixing
        if player_id in session.player_stats:
            history = session.player_stats[player_id].court_history
            if not history or history[-1] != court_number:
                history.append(court_number)
    
    # Update court_players
    session.court_players[court_number] = team1 + team2
    
    # Update partnership history for next games - track game numbers
    for p1 in team1:
        for p2 in team1:
            if p1 != p2:
                if p1 in session.player_stats and p2 in session.player_stats:
                    stats = session.player_stats[p1]
                    stats.partners_played[p2] = stats.partners_played.get(p2, 0) + 1
                    stats.partner_last_game[p2] = current_game_number
    
    # Update opponent history for next games - track game numbers
    for p1 in team1:
        for p2 in team2:
            if p1 in session.player_stats and p2 in session.player_stats:
                stats = session.player_stats[p1]
                stats.opponents_played[p2] = stats.opponents_played.get(p2, 0) + 1
                stats.opponent_last_game[p2] = current_game_number
            if p2 in session.player_stats and p1 in session.player_stats:
                stats = session.player_stats[p2]
                stats.opponents_played[p1] = stats.opponents_played.get(p1, 0) + 1
                stats.opponent_last_game[p1] = current_game_number
                session.player_stats[p2].opponent_last_game[p1] = current_game_number


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
    
    # Get players currently in active matches
    players_in_matches = set()
    for match in session.matches:
        if match.status in ['in-progress', 'waiting']:
            players_in_matches.update(match.team1 + match.team2)
    
    # Get available players from current court
    current_court_players = session.court_players.get(court_number, [])
    
    # Get candidates
    candidates = [p for p in sorted(session.active_players) if p not in players_in_matches]
    
    # Prefer players who haven't played yet
    never_played = [p for p in candidates if p not in session.player_stats or session.player_stats[p].games_played == 0]
    
    if len(never_played) >= num_needed:
        return never_played[:num_needed]
    
    # Otherwise, take mix of never-played and already-played
    result = never_played
    already_played = [p for p in candidates if p not in never_played]
    result.extend(already_played[:num_needed - len(result)])
    
    return result[:num_needed]


def should_allow_court_mixing(
    session: Session,
    court_a: int,
    court_b: int
) -> bool:
    """
    Determine if two courts should be allowed to mix players.
    Enforces rules about back-to-back mixing in 3+ court situations.
    
    In 3+ active court situations, same two courts cannot mix back-to-back.
    """
    if session.config.mode != 'competitive-variety':
        return False
    
    num_active_courts = len([m for m in session.matches if m.status == 'in-progress'])
    
    if num_active_courts < 3:
        # With fewer than 3 active courts, allow mixing
        return True
    
    # With 3+ active courts, check if these courts have mixed recently
    mix_key = (min(court_a, court_b), max(court_a, court_b))
    
    # If they just mixed in the last round, don't allow again
    if mix_key in session.courts_mixed_history:
        return False
    
    return True


def get_default_competitive_variety_settings(total_players: int, num_courts: int) -> Tuple[float, int, int]:
    """
    Get default competitive variety settings based on total players.
    
    Returns (roaming_range_percent, partner_repetition_limit, opponent_repetition_limit)
    
    - 13 or less players: Casual (80% roaming)
    - 14 players: Semi-Competitive (65% roaming)
    - 15 players: Semi-Competitive (65% roaming)
    - 16 players: Semi-Competitive (65% roaming)
    - 17 players: Casual (80% roaming)
    - 18 players: Semi-Competitive (65% roaming)
    - 19 or more players: Competitive (50% roaming)
    """
    # Default Variety is always Balanced
    variety_settings = VARIETY_PROFILES["balanced"]
    
    if total_players <= 13:
        roaming_percent = COMPETITIVENESS_PROFILES["casual"]
    elif total_players == 14:
        roaming_percent = COMPETITIVENESS_PROFILES["semi-competitive"]
    elif total_players == 15:
        roaming_percent = COMPETITIVENESS_PROFILES["semi-competitive"]
    elif total_players == 16:
        roaming_percent = COMPETITIVENESS_PROFILES["semi-competitive"]
    elif total_players == 17:
        roaming_percent = COMPETITIVENESS_PROFILES["casual"]
    elif total_players == 18:
        roaming_percent = COMPETITIVENESS_PROFILES["semi-competitive"]
    else: # 19 or more
        roaming_percent = COMPETITIVENESS_PROFILES["competitive"]
        
    return roaming_percent, variety_settings["partner_repetition_limit"], variety_settings["opponent_repetition_limit"]


def update_session_competitive_variety_settings(session: Session) -> None:
    """
    Update the session's competitive variety settings based on the current number of active players.
    This should be called when players are added or removed.
    """
    if session.config.mode != 'competitive-variety':
        return
        
    roaming, partner, opponent = get_default_competitive_variety_settings(
        len(session.active_players),
        session.config.courts
    )
    
    session.competitive_variety_roaming_range_percent = roaming
    session.competitive_variety_partner_repetition_limit = partner
    session.competitive_variety_opponent_repetition_limit = opponent
