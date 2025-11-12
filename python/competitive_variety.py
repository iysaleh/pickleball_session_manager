"""
Competitive Variety Matchmaking - ELO-based skill-balanced matchmaking with hard variety constraints
"""

from typing import List, Dict, Tuple, Set, Optional
from .types import Player, QueuedMatch, Session
import math
from itertools import combinations

# Constants for ELO system
BASE_RATING = 1500
PROVISIONAL_GAMES = 2  # Players are provisional for 2 games
MAX_RATING = 2200
MIN_RATING = 800

# Hard constraints for repetition
PARTNER_REPETITION_GAMES_REQUIRED = 2  # Must wait 2 games before playing with same partner
OPPONENT_REPETITION_GAMES_REQUIRED = 1  # Must wait 1 game before playing against same opponent


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


def get_allowed_matchmaking_bracket(session: Session, player_id: str) -> Tuple[int, int]:
    """
    Get the range of ranks a player can be matched with (50% rule).
    
    For 12+ players:
    - Top 50% players only play with top 50%
    - Bottom 50% players only play with bottom 50%
    - Provisional players can play with anyone
    
    Returns (min_rank, max_rank) inclusive.
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


def can_play_with_player(session: Session, player1: str, player2: str, role: str) -> bool:
    """
    Check if two players can play together in the given role.
    role = 'partner' or 'opponent'
    
    Hard constraints:
    - If partners: must wait PARTNER_REPETITION_GAMES_REQUIRED games (2 games minimum gap)
    - If opponents: must wait OPPONENT_REPETITION_GAMES_REQUIRED games (1 game minimum gap)
    - Must respect 50% matchmaking bracket for non-provisional players
    - Only applies when 12+ players (otherwise fewer constraints)
    """
    # Check bracket compatibility (50% rule) - only for 12+ players
    if len(session.active_players) >= 12:
        if not is_provisional(session, player1) or not is_provisional(session, player2):
            min1, max1 = get_allowed_matchmaking_bracket(session, player1)
            min2, max2 = get_allowed_matchmaking_bracket(session, player2)
            
            # Check if brackets overlap
            if max1 < min2 or max2 < min1:
                return False
    
    # Check repetition constraints
    if player1 not in session.player_stats or player2 not in session.player_stats:
        return True
    
    stats1 = session.player_stats[player1]
    # Current game number: count of completed matches (games that have finished)
    current_game_number = len([m for m in session.matches if m.status == 'completed'])
    
    if role == 'partner':
        # Hard cap: must wait 2 games since last playing together (for 12+ players)
        if len(session.active_players) >= 12 and player2 in stats1.partner_last_game:
            last_game = stats1.partner_last_game[player2]
            # Games that have happened AFTER they last played together
            games_elapsed = current_game_number - last_game
            if games_elapsed < PARTNER_REPETITION_GAMES_REQUIRED:
                return False
    elif role == 'opponent':
        # Hard cap: must wait 1 game since last playing against each other (for 12+ players)
        if len(session.active_players) >= 12 and player2 in stats1.opponent_last_game:
            last_game = stats1.opponent_last_game[player2]
            # Games that have happened AFTER they last played together
            games_elapsed = current_game_number - last_game
            if games_elapsed < OPPONENT_REPETITION_GAMES_REQUIRED:
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


def _can_form_valid_teams(session: Session, players: List[str]) -> bool:
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
        if not can_play_with_player(session, team1[0], team1[1], 'partner'):
            valid = False
        
        if valid and not can_play_with_player(session, team2[0], team2[1], 'partner'):
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
                        status='waiting'
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
                
                # First try selecting by ELO rating (best balanced players)
                player_ratings = [(p, calculate_elo_rating(session.player_stats.get(p, 
                                  type('', (), {'games_played': 0, 'wins': 0, 'total_points_for': 0, 'total_points_against': 0})()))) 
                                  for p in available_players]
                player_ratings.sort(key=lambda x: x[1], reverse=True)
                
                # Try combinations starting with top-rated players
                for combo in combinations([p[0] for p in player_ratings[:8]], 4):
                    if _can_form_valid_teams(session, list(combo)):
                        # Found a valid combination - use first config that works
                        configs = [
                            ([combo[0], combo[1]], [combo[2], combo[3]]),
                            ([combo[0], combo[2]], [combo[1], combo[3]]),
                            ([combo[0], combo[3]], [combo[1], combo[2]]),
                        ]
                        for team1, team2 in configs:
                            if (can_play_with_player(session, team1[0], team1[1], 'partner') and
                                can_play_with_player(session, team2[0], team2[1], 'partner')):
                                # Check all opponent pairs
                                valid = True
                                for p1 in team1:
                                    for p2 in team2:
                                        if not can_play_with_player(session, p1, p2, 'opponent'):
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
                        status='waiting'
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
    Returns False if they violate partnership or opponent repetition constraints.
    """
    if session.config.mode != 'competitive-variety' or len(player_ids) != 4:
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
                    session.player_stats[p1].partners_played.add(p2)
                    session.player_stats[p1].partner_last_game[p2] = current_game_number
    
    # Update opponent history for next games - track game numbers
    for p1 in team1:
        for p2 in team2:
            if p1 in session.player_stats and p2 in session.player_stats:
                session.player_stats[p1].opponents_played.add(p2)
                session.player_stats[p1].opponent_last_game[p2] = current_game_number
            if p2 in session.player_stats and p1 in session.player_stats:
                session.player_stats[p2].opponents_played.add(p1)
                session.player_stats[p2].opponent_last_game[p1] = current_game_number
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
