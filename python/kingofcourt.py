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
    
    # Mark that the first round has been initialized
    session.king_of_court_round_number = 1
    
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
        # Sort by rating (highest first) - use pre-seeded skill rating if available
        def get_rating(player):
            if player.skill_rating is not None and session.config.pre_seeded_ratings:
                return player.skill_rating
            else:
                return calculate_player_rating(session.player_stats.get(player.id, PlayerStats(player.id)))
        players.sort(key=get_rating, reverse=True)
    elif seeding == 'lowest_to_highest':
        # Sort by rating (lowest first) - use pre-seeded skill rating if available  
        def get_rating(player):
            if player.skill_rating is not None and session.config.pre_seeded_ratings:
                return player.skill_rating
            else:
                return calculate_player_rating(session.player_stats.get(player.id, PlayerStats(player.id)))
        players.sort(key=get_rating)
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
    
    # KING OF COURT CORE ALGORITHM:
    # 1. All winners split and move up one court (or stay if at kings court)
    # 2. All losers split and move down one court (or stay if at bottom court)  
    # 3. New teams are randomly formed from players now at each court level
    
    # Collect all individual players and their target court levels
    player_movements = {}  # player_id -> target_court_number
    
    for i, court_num in enumerate(court_ordering):
        if court_num in court_winners and court_num in court_losers:
            winners = court_winners[court_num] 
            losers = court_losers[court_num]
            
            # INDIVIDUAL WINNERS: Move up one court (or stay if at kings court)
            if i > 0:  # Not the kings court - winners move up
                target_court = court_ordering[i - 1]
                for winner_id in winners:
                    player_movements[winner_id] = target_court
                    session.king_of_court_player_positions[winner_id] = target_court
            else:  # Kings court - winners stay
                for winner_id in winners:
                    player_movements[winner_id] = court_num
                    session.king_of_court_player_positions[winner_id] = court_num
            
            # INDIVIDUAL LOSERS: Move down one court (or stay if at bottom court)
            if i < len(court_ordering) - 1:  # Not the bottom court - losers move down
                target_court = court_ordering[i + 1]
                for loser_id in losers:
                    player_movements[loser_id] = target_court
                    session.king_of_court_player_positions[loser_id] = target_court
            else:  # Bottom court - losers stay
                for loser_id in losers:
                    player_movements[loser_id] = court_num
                    session.king_of_court_player_positions[loser_id] = court_num
    
    # Group players by their target court
    new_court_assignments = {}  # court_number -> [player_ids]
    for player_id, target_court in player_movements.items():
        if target_court not in new_court_assignments:
            new_court_assignments[target_court] = []
        new_court_assignments[target_court].append(player_id)
    
    # Handle waitlist integration
    handle_waitlist_for_round(session, new_court_assignments, court_ordering, players_per_court)
    
    # Create new matches with randomized teams (winners and losers are now split)
    create_matches_from_assignments(session, new_court_assignments, players_per_court)


def handle_waitlist_for_round(session: Session, new_court_assignments: Dict[int, List[str]], 
                            court_ordering: List[int], players_per_court: int):
    """Handle waitlist logic for the new round"""
    total_court_capacity = len(court_ordering) * players_per_court
    total_active_players = len(session.active_players)
    
    if total_active_players <= total_court_capacity:
        # Everyone can play - bring everyone from waitlist
        while session.waiting_players:
            player_id = session.waiting_players.pop(0)
            # Find a court that needs players
            for court_num in court_ordering:
                if court_num not in new_court_assignments:
                    new_court_assignments[court_num] = []
                if len(new_court_assignments[court_num]) < players_per_court:
                    new_court_assignments[court_num].append(player_id)
                    session.king_of_court_player_positions[player_id] = court_num
                    break
        return
    
    # We have more players than court spots - need waitlist rotation
    excess_players = total_active_players - total_court_capacity
    
    # Get all players currently assigned to courts
    court_players = []
    for court_num, players in new_court_assignments.items():
        court_players.extend(players)
    
    # KING OF COURT WAITLIST RULE: Nobody waits twice until everyone has waited once
    
    # Find who should wait this round
    all_players = court_players + session.waiting_players
    
    # Check wait count distribution
    wait_counts = {}
    for player_id in all_players:
        count = session.king_of_court_wait_counts.get(player_id, 0)
        if count not in wait_counts:
            wait_counts[count] = []
        wait_counts[count].append(player_id)
    
    # Apply King of Court rule
    if 0 in wait_counts and len(wait_counts[0]) > 0:
        # There are players who have never waited - they should be prioritized for waiting
        never_waited = wait_counts[0]
        
        if len(never_waited) >= excess_players:
            # Choose from never-waited players, prefer middle court players for fairness
            middle_courts = court_ordering[1:-1] if len(court_ordering) > 2 else []
            courts_to_check = middle_courts + [court_ordering[-1]]
            
            candidates_by_court = []
            for court_num in courts_to_check:
                if court_num in new_court_assignments:
                    court_candidates = [p for p in new_court_assignments[court_num] if p in never_waited]
                    candidates_by_court.extend(court_candidates)
            
            # If not enough middle court candidates, add others
            if len(candidates_by_court) < excess_players:
                remaining_candidates = [p for p in never_waited if p not in candidates_by_court]
                candidates_by_court.extend(remaining_candidates)
            
            should_wait = candidates_by_court[:excess_players]
        else:
            # Not enough never-waited players - take all of them plus some who waited once
            should_wait = never_waited.copy()
            remaining_needed = excess_players - len(should_wait)
            
            # Take from players who waited once (if any)
            if 1 in wait_counts:
                should_wait.extend(wait_counts[1][:remaining_needed])
    else:
        # Everyone has waited at least once - use normal rotation
        # Prefer those who have waited the most
        max_wait_count = max(wait_counts.keys())
        should_wait = wait_counts[max_wait_count][:excess_players]
    
    should_play = [player_id for player_id in all_players if player_id not in should_wait]
    
    # Update waitlist
    session.waiting_players = should_wait
    
    # Update wait counts for those waiting
    for player_id in should_wait:
        session.king_of_court_wait_counts[player_id] = session.king_of_court_wait_counts.get(player_id, 0) + 1
    
    # Rebuild court assignments with only players who should play
    new_court_assignments.clear()
    
    # Distribute playing players across courts
    player_index = 0
    for court_num in court_ordering:
        new_court_assignments[court_num] = []
        for _ in range(players_per_court):
            if player_index < len(should_play):
                player_id = should_play[player_index]
                new_court_assignments[court_num].append(player_id)
                session.king_of_court_player_positions[player_id] = court_num
                player_index += 1


def create_matches_from_assignments(session: Session, court_assignments: Dict[int, List[str]], 
                                  players_per_court: int):
    """Create new matches from court assignments"""
    for court_num, players in court_assignments.items():
        if len(players) == players_per_court:
            # KING OF COURT RULE: Always randomize teams to ensure winners split
            if players_per_court == 4:
                import random
                shuffled_players = players.copy()
                random.shuffle(shuffled_players)
                team1 = shuffled_players[:2]
                team2 = shuffled_players[2:]
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
    
    # Initialize if first time (round 0 means not yet initialized)
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
