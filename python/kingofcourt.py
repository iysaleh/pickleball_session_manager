"""
Rounds-based King of the Court matchmaking engine 
"""

from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from .pickleball_types import (
    Player, Session, PlayerStats, Match, KingOfCourtConfig, 
    KingOfCourtSeeding, SessionConfig
)
from .utils import generate_id
from .time_manager import now


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


def get_court_ordering(session: Session) -> List[int]:
    """Get the current court ordering (kings court first, bottom court last)"""
    if session.config.king_of_court_config and session.config.king_of_court_config.court_ordering:
        return session.config.king_of_court_config.court_ordering
    else:
        # Default ordering: Court 1 = kings, Court N = bottom
        return list(range(1, session.config.courts + 1))


def initialize_king_of_court_session(session: Session) -> Session:
    """Initialize a King of Court session with proper seeding"""
    if session.config.mode != 'king-of-court':
        return session
    
    koc_config = session.config.king_of_court_config
    if not koc_config:
        # Create default config
        court_ordering = list(range(1, session.config.courts + 1))
        koc_config = KingOfCourtConfig(court_ordering=court_ordering)
        
        # Update session config - need to recreate to modify immutable dataclass
        new_config = SessionConfig(
            mode=session.config.mode,
            session_type=session.config.session_type,
            players=session.config.players,
            courts=session.config.courts,
            banned_pairs=session.config.banned_pairs,
            locked_teams=session.config.locked_teams,
            first_bye_players=session.config.first_bye_players,
            court_sliding_mode=session.config.court_sliding_mode,
            randomize_player_order=session.config.randomize_player_order,
            advanced_config=session.config.advanced_config,
            pre_seeded_ratings=session.config.pre_seeded_ratings,
            king_of_court_config=koc_config
        )
        session.config = new_config
    
    # Get players minus first byes if any
    available_players = [p for p in session.config.players 
                        if p.id not in session.config.first_bye_players]
    
    # Seed players across courts based on seeding option
    court_ordering = get_court_ordering(session)
    seed_players_across_courts(session, available_players, court_ordering, koc_config.seeding_option)
    
    return session


def seed_players_across_courts(session: Session, players: List[Player], 
                             court_ordering: List[int], seeding: KingOfCourtSeeding):
    """Seed players across courts based on the selected seeding option"""
    players_per_court = 4  # Assuming doubles
    if session.config.session_type == 'singles':
        players_per_court = 2
    
    # Handle first byes - they go to waitlist
    if session.config.first_bye_players:
        session.waiting_players.extend(session.config.first_bye_players)
        for player_id in session.config.first_bye_players:
            session.king_of_court_wait_counts[player_id] = 1
    
    # Calculate how many players can fit on courts
    total_court_spots = len(court_ordering) * players_per_court
    available_count = len(players)
    
    # Put excess players in waiting list
    if available_count > total_court_spots:
        excess_count = available_count - total_court_spots
        # Random selection for waitlist
        import random
        waiting_list_players = random.sample(players, excess_count)
        for player in waiting_list_players:
            session.waiting_players.append(player.id)
            session.king_of_court_wait_counts[player.id] = 1
        
        # Remove waiting players from seeding
        players = [p for p in players if p.id not in session.waiting_players]
    
    # Sort players based on seeding option
    if seeding == 'highest_to_lowest':
        # Sort by rating (highest first)
        players.sort(key=lambda p: calculate_player_rating(session.player_stats.get(p.id, PlayerStats(p.id))), reverse=True)
    elif seeding == 'lowest_to_highest':
        # Sort by rating (lowest first)
        players.sort(key=lambda p: calculate_player_rating(session.player_stats.get(p.id, PlayerStats(p.id))))
    else:  # random
        import random
        random.shuffle(players)
    
    # Distribute players across courts
    player_index = 0
    for court_num in court_ordering:
        court_players = []
        for i in range(players_per_court):
            if player_index < len(players):
                player = players[player_index]
                court_players.append(player.id)
                session.king_of_court_player_positions[player.id] = court_num
                player_index += 1
        
        # Create a match for this court
        if len(court_players) == players_per_court:
            if players_per_court == 4:  # doubles
                team1 = court_players[:2]
                team2 = court_players[2:]
            else:  # singles
                team1 = [court_players[0]]
                team2 = [court_players[1]]
            
            # Randomize teams to avoid predictable partnerships
            import random
            if players_per_court == 4:
                random.shuffle(court_players)
                team1 = court_players[:2]
                team2 = court_players[2:]
            
            match = Match(
                id=generate_id(),
                court_number=court_num,
                team1=team1,
                team2=team2,
                status='waiting',
                start_time=now()
            )
            session.matches.append(match)


def can_form_teams_avoiding_repetition(players: List[str], session: Session) -> Optional[Tuple[List[str], List[str]]]:
    """
    Try to form teams from players avoiding recent partnerships
    Returns (team1, team2) or None if no good combination found
    """
    if len(players) != 4:
        return None
    
    import itertools
    
    # Try all possible team combinations
    best_combination = None
    min_recent_partnerships = float('inf')
    
    for team1_indices in itertools.combinations(range(4), 2):
        team1 = [players[i] for i in team1_indices]
        team2 = [players[i] for i in range(4) if i not in team1_indices]
        
        # Count recent partnerships
        recent_partnerships = count_recent_partnerships(team1, team2, session)
        
        if recent_partnerships < min_recent_partnerships:
            min_recent_partnerships = recent_partnerships
            best_combination = (team1, team2)
        
        # If we found a combination with no recent partnerships, use it
        if recent_partnerships == 0:
            break
    
    return best_combination


def count_recent_partnerships(team1: List[str], team2: List[str], session: Session) -> int:
    """Count recent partnerships in the proposed teams"""
    count = 0
    
    # Check team1 partnerships
    if len(team1) == 2:
        p1, p2 = team1
        if has_recent_partnership(p1, p2, session):
            count += 1
    
    # Check team2 partnerships
    if len(team2) == 2:
        p1, p2 = team2
        if has_recent_partnership(p1, p2, session):
            count += 1
    
    return count


def has_recent_partnership(player1: str, player2: str, session: Session) -> bool:
    """Check if two players have been partners recently (within last 2 matches)"""
    recent_matches = get_recent_matches(session, 2)
    
    for match in recent_matches:
        # Check if they were partners in team1 or team2
        if (player1 in match.team1 and player2 in match.team1) or \
           (player1 in match.team2 and player2 in match.team2):
            return True
    
    return False


def get_recent_matches(session: Session, count: int) -> List[Match]:
    """Get the most recent completed matches"""
    completed_matches = [m for m in session.matches if m.status == 'completed']
    return completed_matches[-count:] if len(completed_matches) >= count else completed_matches


def advance_round(session: Session) -> Session:
    """Advance to the next round after all current matches are completed"""
    if session.config.mode != 'king-of-court':
        return session
    
    # Check if all current matches are completed
    active_matches = [m for m in session.matches if m.status in ['waiting', 'in-progress']]
    if active_matches:
        return session  # Not ready to advance
    
    court_ordering = get_court_ordering(session)
    players_per_court = 4 if session.config.session_type == 'doubles' else 2
    
    # Process results from completed matches
    last_round_matches = get_matches_from_current_round(session)
    if not last_round_matches:
        return session
    
    # Track winners and losers by court position
    court_winners = {}  # court_number -> [player_ids]
    court_losers = {}   # court_number -> [player_ids]
    
    for match in last_round_matches:
        if match.status != 'completed' or not match.score:
            continue
        
        team1_score = match.score.get('team1_score', 0)
        team2_score = match.score.get('team2_score', 0)
        
        if team1_score > team2_score:
            court_winners[match.court_number] = match.team1
            court_losers[match.court_number] = match.team2
        else:
            court_winners[match.court_number] = match.team2
            court_losers[match.court_number] = match.team1
    
    # Create new round
    session.king_of_court_round_number += 1
    
    # Move players between courts and create new matches
    create_next_round_matches(session, court_ordering, court_winners, court_losers, players_per_court)
    
    return session


def get_matches_from_current_round(session: Session) -> List[Match]:
    """Get all matches from the current round"""
    # Find the most recent set of matches that were started together
    # For simplicity, get matches that were started most recently
    if not session.matches:
        return []
    
    # Get the latest start time
    latest_start = max(m.start_time for m in session.matches if m.start_time)
    
    # Return matches that started at the same time (within a small window)
    current_round_matches = []
    for match in session.matches:
        if match.start_time and abs((match.start_time - latest_start).total_seconds()) < 60:
            current_round_matches.append(match)
    
    return current_round_matches


def create_next_round_matches(session: Session, court_ordering: List[int], 
                            court_winners: Dict[int, List[str]], 
                            court_losers: Dict[int, List[str]], 
                            players_per_court: int):
    """Create matches for the next round based on winners and losers"""
    new_court_assignments = {}  # court_number -> [player_ids]
    
    for i, court_num in enumerate(court_ordering):
        if court_num in court_winners and court_num in court_losers:
            winners = court_winners[court_num]
            losers = court_losers[court_num]
            
            # Update player positions
            for player_id in winners:
                session.king_of_court_player_positions[player_id] = court_num
            for player_id in losers:
                session.king_of_court_player_positions[player_id] = court_num
            
            # Move winners up a court (unless at top)
            if i > 0:  # Not the kings court
                target_court = court_ordering[i - 1]
                if target_court not in new_court_assignments:
                    new_court_assignments[target_court] = []
                new_court_assignments[target_court].extend(winners)
            else:  # Kings court - winners stay
                if court_num not in new_court_assignments:
                    new_court_assignments[court_num] = []
                new_court_assignments[court_num].extend(winners)
            
            # Move losers down a court (unless at bottom)
            if i < len(court_ordering) - 1:  # Not the bottom court
                target_court = court_ordering[i + 1]
                if target_court not in new_court_assignments:
                    new_court_assignments[target_court] = []
                new_court_assignments[target_court].extend(losers)
            else:  # Bottom court - losers stay
                if court_num not in new_court_assignments:
                    new_court_assignments[court_num] = []
                new_court_assignments[court_num].extend(losers)
    
    # Handle waitlist integration
    handle_waitlist_for_round(session, new_court_assignments, court_ordering, players_per_court)
    
    # Create new matches
    create_matches_from_assignments(session, new_court_assignments, players_per_court)


def handle_waitlist_for_round(session: Session, new_court_assignments: Dict[int, List[str]], 
                            court_ordering: List[int], players_per_court: int):
    """Handle waitlist logic for the new round"""
    # Count current players on courts
    total_court_players = sum(len(players) for players in new_court_assignments.values())
    total_court_capacity = len(court_ordering) * players_per_court
    
    # Bring players from waitlist if there's room
    while len(session.waiting_players) > 0 and total_court_players < total_court_capacity:
        # Find a court that needs players
        for court_num in court_ordering:
            if court_num not in new_court_assignments:
                new_court_assignments[court_num] = []
            
            if len(new_court_assignments[court_num]) < players_per_court:
                # Add a waiting player
                player_id = session.waiting_players.pop(0)
                new_court_assignments[court_num].append(player_id)
                session.king_of_court_player_positions[player_id] = court_num
                total_court_players += 1
                break
    
    # If courts are full, move players to waitlist from middle courts first
    if total_court_players > total_court_capacity:
        # Prioritize middle courts for sending to waitlist
        middle_courts = court_ordering[1:-1] if len(court_ordering) > 2 else []
        courts_to_check = middle_courts + [court_ordering[-1]]  # Middle first, then bottom
        
        excess_players = total_court_players - total_court_capacity
        players_to_wait = []
        
        for court_num in courts_to_check:
            if court_num in new_court_assignments and len(new_court_assignments[court_num]) > 0:
                while excess_players > 0 and len(new_court_assignments[court_num]) > 0:
                    # Check if this player has waited before
                    court_players = new_court_assignments[court_num]
                    
                    # Find player who has waited least
                    min_wait_count = min(session.king_of_court_wait_counts.get(p, 0) for p in court_players)
                    
                    # Only send to waitlist if everyone else has waited at least once
                    global_min_wait = min(session.king_of_court_wait_counts.get(p, 0) 
                                        for p in session.active_players if p not in session.waiting_players)
                    
                    if min_wait_count <= global_min_wait:
                        # Find a player with minimum wait count
                        for player_id in court_players:
                            if session.king_of_court_wait_counts.get(player_id, 0) == min_wait_count:
                                new_court_assignments[court_num].remove(player_id)
                                players_to_wait.append(player_id)
                                session.king_of_court_wait_counts[player_id] = session.king_of_court_wait_counts.get(player_id, 0) + 1
                                excess_players -= 1
                                break
                        break
                    else:
                        break
        
        # Add to waitlist
        session.waiting_players.extend(players_to_wait)


def create_matches_from_assignments(session: Session, court_assignments: Dict[int, List[str]], 
                                  players_per_court: int):
    """Create new matches from court assignments"""
    for court_num, players in court_assignments.items():
        if len(players) == players_per_court:
            # Form teams avoiding recent partnerships
            if players_per_court == 4:
                team_assignment = can_form_teams_avoiding_repetition(players, session)
                if team_assignment:
                    team1, team2 = team_assignment
                else:
                    # Fallback to random assignment
                    import random
                    random.shuffle(players)
                    team1 = players[:2]
                    team2 = players[2:]
            else:  # singles
                team1 = [players[0]]
                team2 = [players[1]]
            
            match = Match(
                id=generate_id(),
                court_number=court_num,
                team1=team1,
                team2=team2,
                status='waiting',
                start_time=now()
            )
            session.matches.append(match)


def evaluate_king_of_court_session(session: Session) -> Session:
    """
    Main evaluation function for King of Court sessions
    """
    if session.config.mode != 'king-of-court':
        return session
    
    # Initialize if first time
    if session.king_of_court_round_number == 0:
        return initialize_king_of_court_session(session)
    
    # Check if we can advance to next round
    return advance_round(session)


def set_court_ordering(session: Session, court_ordering: List[int]) -> Session:
    """Update the court ordering for a King of Court session"""
    if session.config.king_of_court_config:
        # Update existing config
        koc_config = session.config.king_of_court_config
        new_koc_config = KingOfCourtConfig(
            base_rating=koc_config.base_rating,
            k_factor=koc_config.k_factor,
            min_rating=koc_config.min_rating,
            max_rating=koc_config.max_rating,
            provisional_games_threshold=koc_config.provisional_games_threshold,
            ranking_range_percentage=koc_config.ranking_range_percentage,
            close_rank_threshold=koc_config.close_rank_threshold,
            very_close_rank_threshold=koc_config.very_close_rank_threshold,
            max_consecutive_waits=koc_config.max_consecutive_waits,
            min_completed_matches_for_waiting=koc_config.min_completed_matches_for_waiting,
            min_busy_courts_for_waiting=koc_config.min_busy_courts_for_waiting,
            back_to_back_overlap_threshold=koc_config.back_to_back_overlap_threshold,
            recent_match_check_count=koc_config.recent_match_check_count,
            single_court_loop_threshold=koc_config.single_court_loop_threshold,
            soft_repetition_frequency=koc_config.soft_repetition_frequency,
            high_repetition_threshold=koc_config.high_repetition_threshold,
            partnership_repeat_penalty=koc_config.partnership_repeat_penalty,
            recent_partnership_penalty=koc_config.recent_partnership_penalty,
            opponent_repeat_penalty=koc_config.opponent_repeat_penalty,
            recent_overlap_penalty=koc_config.recent_overlap_penalty,
            team_balance_penalty=koc_config.team_balance_penalty,
            seeding_option=koc_config.seeding_option,
            court_ordering=court_ordering
        )
    else:
        new_koc_config = KingOfCourtConfig(court_ordering=court_ordering)
    
    # Update session config
    new_config = SessionConfig(
        mode=session.config.mode,
        session_type=session.config.session_type,
        players=session.config.players,
        courts=session.config.courts,
        banned_pairs=session.config.banned_pairs,
        locked_teams=session.config.locked_teams,
        first_bye_players=session.config.first_bye_players,
        court_sliding_mode=session.config.court_sliding_mode,
        randomize_player_order=session.config.randomize_player_order,
        advanced_config=session.config.advanced_config,
        pre_seeded_ratings=session.config.pre_seeded_ratings,
        king_of_court_config=new_koc_config
    )
    session.config = new_config
    
    return session
