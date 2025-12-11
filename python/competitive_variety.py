"""
Competitive Variety Matchmaking - ELO-based skill-balanced matchmaking with hard variety constraints
"""

from typing import List, Dict, Tuple, Set, Optional
from datetime import datetime
from .types import Player, QueuedMatch, Session, Match
import math
from itertools import combinations

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
    # Calculate ratings for all active players
    ratings = []
    for pid in session.active_players:
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
    Get the roaming range of ranks a player can be matched with (50% moving window rule).
    
    For competitive variety mode:
    - Each player can play with others in a range based on their rank
    - Range: player_rank to (player_rank + 50% of total active players)
    - Example: 20 players, player ranked #2: can play with ranks 2-12 (2 + 10 = 12)
    - Example: 20 players, player ranked #14: can play with ranks 14-24 (capped at 20)
    
    Returns (min_rank, max_rank) inclusive.
    Only applies when 12+ players.
    """
    total_players = len(session.active_players)
    
    if total_players < 12:
        # No roaming range restriction for small groups
        return 1, total_players
    
    player_rank, _ = get_player_ranking(session, player_id)
    roaming_distance = int(total_players * ROAMING_RANK_PERCENTAGE)
    
    # Roaming window goes from player_rank to (player_rank + roaming_distance)
    min_rank = player_rank
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
    if len(session.active_players) < 12 or session.config.mode != 'competitive-variety':
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


def can_play_with_player(session: Session, player1: str, player2: str, role: str) -> bool:
    """
    Check if two players can play together in the given role.
    role = 'partner' or 'opponent'
    
    Hard constraints:
    - Banned pairs cannot be partners
    - Locked teams MUST be partners (and cannot be opponents)
    - If partners: must wait PARTNER_REPETITION_GAMES_REQUIRED games (2 games minimum gap)
    - If opponents: must wait OPPONENT_REPETITION_GAMES_REQUIRED games (1 game minimum gap)
    - Must respect 50% matchmaking bracket for non-provisional players
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
                # Find the partner(s)
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

    # Check bracket compatibility (50% rule) - only for 12+ players
    if len(session.active_players) >= 12:
        if not is_provisional(session, player1) or not is_provisional(session, player2):
            min1, max1 = get_allowed_matchmaking_bracket(session, player1)
            min2, max2 = get_allowed_matchmaking_bracket(session, player2)
            
            # Check if brackets overlap
            if max1 < min2 or max2 < min1:
                return False
    
    # Check roaming range compatibility (moving window rule) - only for 12+ players
    if len(session.active_players) >= 12 and session.config.mode == 'competitive-variety':
        if not is_provisional(session, player1) or not is_provisional(session, player2):
            rank1, _ = get_player_ranking(session, player1)
            rank2, _ = get_player_ranking(session, player2)
            min1, max1 = get_roaming_rank_range(session, player1)
            min2, max2 = get_roaming_rank_range(session, player2)
            
            # Both players must be within each other's roaming range
            if rank2 < min1 or rank2 > max1:
                return False
            if rank1 < min2 or rank1 > max2:
                return False
    
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

    # Check bracket compatibility (Roaming 50% Rule) - only for 12+ players
    # Relaxed if allow_cross_bracket is True
    if not allow_cross_bracket and len(session.active_players) >= 12:
        if not is_provisional(session, player1) or not is_provisional(session, player2):
            # Calculate rank difference limit
            limit = int(len(session.active_players) * ROAMING_RANK_PERCENTAGE)
            
            # Get ranks
            rank1, _ = get_player_ranking(session, player1)
            rank2, _ = get_player_ranking(session, player2)
            
            # Check roaming range
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
        # Check Partner Repetition (Last 3 Global Games)
        if role == 'partner':
            matches_to_check = completed_matches[-PARTNER_REPETITION_GAMES_REQUIRED:] if PARTNER_REPETITION_GAMES_REQUIRED > 0 else []
            for m in matches_to_check:
                p1_t1 = player1 in m.team1
                p1_t2 = player1 in m.team2
                p2_t1 = player2 in m.team1
                p2_t2 = player2 in m.team2
                
                if (p1_t1 and p2_t1) or (p1_t2 and p2_t2):
                    return False

        # Check Opponent Repetition (Last 3 Global Games)
        elif role == 'opponent':
            matches_to_check = completed_matches[-OPPONENT_REPETITION_GAMES_REQUIRED:] if OPPONENT_REPETITION_GAMES_REQUIRED > 0 else []
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
                 if intervening_games < PARTNER_REPETITION_GAMES_REQUIRED:
                     return False
            elif intervening_games < 1: # Basic back-to-back check for small groups
                 return False

        elif role == 'opponent' and last_played_against_idx != -1:
            intervening_games = current_personal_game_count - last_played_against_idx - 1
            
            if len(session.active_players) >= 8:
                 if intervening_games < OPPONENT_REPETITION_GAMES_REQUIRED:
                     return False
            elif intervening_games < 1:
                 return False
    
    return True


def score_potential_match(session: Session, team1: List[str], team2: List[str]) -> float:
    """
    Score a potential match based on skill balance and variety.
    Higher score = better match.
    
    Factors:
    - Skill balance (teams should be close in rating)
    - Partnership variety (prefer new partnerships)
    - Opponent variety (prefer new opponents)
    """
    score = 0.0
    
    # Calculate team ratings
    team1_rating = sum(calculate_elo_rating(session.player_stats.get(p, 
                       type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                       for p in team1) / len(team1)
    team2_rating = sum(calculate_elo_rating(session.player_stats.get(p, 
                       type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))
                       for p in team2) / len(team2)
    
    # Penalize unbalanced teams (large skill difference)
    rating_diff = abs(team1_rating - team2_rating)
    score -= rating_diff * 2
    
    # Bonus for variety
    variety_bonus = 0
    for p1 in team1:
        for p2 in team2:
            if p1 not in session.player_stats or p2 not in session.player_stats:
                variety_bonus += 10
            elif p2 not in session.player_stats[p1].opponents_played:
                variety_bonus += 5
    score += variety_bonus
    
    return score


def _can_form_valid_teams(session: Session, players: List[str], allow_cross_bracket: bool = False) -> bool:
    """
    Check if 4 players can form valid teams respecting all competitive variety constraints.
    """
    if len(players) != 4:
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
    Populate empty courts using competitive variety matchmaking rules with ELO system.
    
    Rules:
    1. Check match queue first (respects waitlist)
    2. If no queue matches, generate new matches from available players
    3. Use ELO ratings to balance teams
    4. Hard constraints: never play with same partner within 2 games, never play against same opponent within 1 game
    5. Respect 50% matchmaking bracket (top/bottom split)
    6. Prefer new partnerships and opponents
    """
    if session.config.mode != 'competitive-variety':
        return
    
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
                # Check competitive variety constraints
                valid = True
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
                        start_time=datetime.now()
                    )
                    session.matches.append(match)
                    players_in_matches.update(match_players)
                    matches_to_remove.append(queue_idx)
                    assigned = True
                    break
        
        # If no queue match assigned, try to generate one from available players
        if not assigned:
            available_players = [p for p in session.active_players if p not in players_in_matches]
            
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
                    # Filter available players by priority (Wait Time / Last Played)
                    # Sort by:
                    # 1. Last Game Index (Ascending) - None/-1 comes first (never played)
                    # 2. Games Played (Ascending) - Tie breaker for never played
                    
                    player_priority = []
                    for p in available_players:
                        _, last_idx = _get_last_played_info(session, p)
                        games_played = session.player_stats.get(p, 
                            type('', (), {'games_played': 0})()).games_played if p in session.player_stats else 0
                        player_priority.append((p, last_idx, games_played))
                    
                    # Sort: -1 first, then small indices.
                    player_priority.sort(key=lambda x: (x[1], x[2]))
                    
                    # Take top candidates (enough to form a few matches, but filter out recent players if possible)
                    # If we need 4 players, taking top 12 gives good ELO mixing flexibility 
                    # while ensuring people who just played (high index) are excluded if others exist.
                    
                    # Logic: If we have many waiters, exclude the ones who just played.
                    num_candidates = max(12, len(available_players) // 2)
                    # Cap at 16 to prevent slowness, but ensure at least 12 if possible
                    num_candidates = min(16, max(12, num_candidates))
                    
                    # If we have distinct groups (waiters vs just played), we want to strictly pick waiters.
                    # The sort `(last_idx, games_played)` puts `(-1, 0)` at top, and `(10, 10)` at bottom.
                    # So picking top N will naturally exclude bottom.
                    
                    # Candidates sorted by PRIORITY (Wait Time)
                    candidates_for_matching = [x[0] for x in player_priority[:num_candidates]]
                    
                    # We do NOT sort by ELO here, because we want to prioritize Waiters.
                    # combinations() will pick the first 4 candidates (highest priority) first.
                    
                    # Limit combination search to top 12 of the filtered list to keep it fast
                    search_limit = min(12, len(candidates_for_matching))
                    
                    # Only one pass: Strict Bracketing (allow_cross_bracket=False)
                    allow_cross = False
                    for combo in combinations(candidates_for_matching[:search_limit], 4):
                        if _can_form_valid_teams(session, list(combo), allow_cross_bracket=allow_cross):
                            # Found a valid combination - use first config that works
                            configs = [
                                ([combo[0], combo[1]], [combo[2], combo[3]]),
                                ([combo[0], combo[2]], [combo[1], combo[3]]),
                                ([combo[0], combo[3]], [combo[1], combo[2]]),
                            ]
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
                                        best_team1 = list(team1)
                                        best_team2 = list(team2)
                                        break
                            if best_team1:
                                break
                
                if best_team1 and best_team2:
                    match = Match(
                        id=generate_id(),
                        court_number=court_num,
                        team1=best_team1,
                        team2=best_team2,
                        status='waiting',
                        start_time=datetime.now()
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
    candidates = [p for p in session.active_players if p not in players_in_matches]
    
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
