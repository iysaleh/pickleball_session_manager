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
        # Try to load from persistent storage first
        from .session_persistence import load_court_ordering
        saved_ordering = load_court_ordering(session.config.courts)
        
        if saved_ordering:
            # Update the session config with loaded ordering
            if session.config.king_of_court_config:
                session.config.king_of_court_config.court_ordering = saved_ordering
            else:
                koc_config = KingOfCourtConfig(court_ordering=saved_ordering)
                # Need to update the session config properly
                from .pickleball_types import SessionConfig
                new_config = SessionConfig(
                    mode=session.config.mode,
                    session_type=session.config.session_type,
                    players=session.config.players,
                    courts=session.config.courts,
                    banned_pairs=session.config.banned_pairs,
                    locked_teams=session.config.locked_teams,
                    first_bye_players=session.config.first_bye_players,
                    court_sliding_mode=getattr(session.config, 'court_sliding_mode', False),
                    randomize_player_order=session.config.randomize_player_order,
                    advanced_config=getattr(session.config, 'advanced_config', None),
                    pre_seeded_ratings=getattr(session.config, 'pre_seeded_ratings', {}),
                    king_of_court_config=koc_config
                )
                session.config = new_config
            return saved_ordering
        else:
            # Use default ordering: Court 1 = Kings, Court N = Bottom
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
        print("DEBUG: No matches found - not advancing")
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
    
    # STEP 1: Apply King of Court movement rules (winners up & split, losers down & split)
    court_player_assignments = apply_king_of_court_movement(session, court_ordering, court_winners, court_losers)
    
    # STEP 2: Handle waitlist rotation separately 
    court_player_assignments = apply_waitlist_rotation(session, court_player_assignments, court_ordering, players_per_court)
    
    # STEP 3: Create new matches from final assignments
    create_matches_from_final_assignments(session, court_player_assignments, players_per_court)
    
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


def apply_king_of_court_movement(session: Session, court_ordering: List[int], 
                               court_winners: Dict[int, List[str]], 
                               court_losers: Dict[int, List[str]]) -> Dict[int, List[str]]:
    """
    STEP 1: Apply pure King of Court movement rules
    - Winners move up one court and split (or stay at kings court)
    - Losers move down one court and split (or stay at bottom court)
    
    Returns: court_number -> [individual_player_ids] assignments after movement
    """
    court_assignments = {}  # court_number -> [player_ids]
    
    # Initialize all courts as empty
    for court_num in court_ordering:
        court_assignments[court_num] = []
    
    for i, court_num in enumerate(court_ordering):
        if court_num not in court_winners or court_num not in court_losers:
            continue  # No match on this court
        
        winners = court_winners[court_num] 
        losers = court_losers[court_num]
        
        # WINNERS: Move up one court (or stay if at kings court) AND SPLIT
        if i > 0:  # Not the kings court - winners move up
            target_court = court_ordering[i - 1]
        else:  # Kings court - winners stay
            target_court = court_num
        
        for winner_id in winners:
            court_assignments[target_court].append(winner_id)
            session.king_of_court_player_positions[winner_id] = target_court
        
        # LOSERS: Move down one court (or stay if at bottom court) AND SPLIT
        if i < len(court_ordering) - 1:  # Not the bottom court - losers move down
            target_court = court_ordering[i + 1]
        else:  # Bottom court - losers stay
            target_court = court_num
        
        for loser_id in losers:
            court_assignments[target_court].append(loser_id)
            session.king_of_court_player_positions[loser_id] = target_court
    
    return court_assignments


def apply_waitlist_rotation(session: Session, court_assignments: Dict[int, List[str]], 
                          court_ordering: List[int], players_per_court: int) -> Dict[int, List[str]]:
    """
    STEP 2: Handle waitlist rotation while preserving King of Court court assignments
    
    King of Court Waitlist Rules:
    1. Nobody waits twice until everyone has waited once
    2. Choose waiters from middle courts first, then bottom, then kings (only if everyone else waited)
    3. Try to place returning players in same position they were before
    
    CRITICAL: This must preserve the court assignments determined by King of Court movement!
    """
    total_court_capacity = len(court_ordering) * players_per_court
    
    # Get all players currently assigned to courts after movement
    all_assigned_players = []
    for players in court_assignments.values():
        all_assigned_players.extend(players)
    
    # Get all current waiters
    current_waiters = session.waiting_players.copy()
    
    # Total universe of active players
    all_active_players = all_assigned_players + current_waiters
    total_active_count = len(all_active_players)
    
    if total_active_count <= total_court_capacity:
        # Everyone can play - add all waiters to available spots
        session.waiting_players = []
        
        # Fill empty spots with previous waiters
        for court_num in court_ordering:
            if court_num not in court_assignments:
                court_assignments[court_num] = []
            while len(court_assignments[court_num]) < players_per_court and current_waiters:
                player_id = current_waiters.pop(0)
                court_assignments[court_num].append(player_id)
                session.king_of_court_player_positions[player_id] = court_num
        
        return court_assignments
    
    # Need to maintain waitlist - apply King of Court waitlist rules
    excess_players = total_active_count - total_court_capacity
    
    # Analyze wait counts for ALL active players
    wait_counts = {}
    for player_id in all_active_players:
        count = session.king_of_court_wait_counts.get(player_id, 0)
        if count not in wait_counts:
            wait_counts[count] = []
        wait_counts[count].append(player_id)
    
    # Apply rule: Nobody waits twice until everyone has waited once
    players_to_wait = []
    
    if 0 in wait_counts and len(wait_counts[0]) > 0:
        # Prioritize players who have never waited
        never_waited = wait_counts[0]
        
        if len(never_waited) >= excess_players:
            # Choose from those assigned to middle courts first, then bottom, then kings
            # If not enough from courts, include returning waiters
            candidates_by_priority = []
            
            # Middle courts first (from assigned players)
            middle_courts = court_ordering[1:-1] if len(court_ordering) > 2 else []
            for court_num in middle_courts:
                if court_num in court_assignments:
                    court_candidates = [p for p in court_assignments[court_num] if p in never_waited]
                    candidates_by_priority.extend(court_candidates)
            
            # Bottom court next (from assigned players)
            if court_ordering:
                bottom_court = court_ordering[-1]
                if bottom_court in court_assignments:
                    bottom_candidates = [p for p in court_assignments[bottom_court] if p in never_waited]
                    candidates_by_priority.extend(bottom_candidates)
            
            # If still need more, add returning waiters (if they never waited)
            if len(candidates_by_priority) < excess_players:
                never_waited_waiters = [p for p in current_waiters if p in never_waited]
                candidates_by_priority.extend(never_waited_waiters)
            
            # Kings court last (only if everyone else has waited)
            if len(candidates_by_priority) < excess_players and court_ordering:
                kings_court = court_ordering[0]
                if kings_court in court_assignments:
                    kings_candidates = [p for p in court_assignments[kings_court] if p in never_waited]
                    candidates_by_priority.extend(kings_candidates)
            
            players_to_wait = candidates_by_priority[:excess_players]
        else:
            # Not enough never-waited players - take all + some who waited once
            players_to_wait = never_waited.copy()
            remaining_needed = excess_players - len(players_to_wait)
            
            if 1 in wait_counts:
                waited_once = wait_counts[1]
                players_to_wait.extend(waited_once[:remaining_needed])
    else:
        # Everyone has waited at least once - use fair rotation based on waitlist history
        # Choose players who waited longest ago (first in history) to ensure long gaps between waits
        players_to_wait = select_players_for_fair_rotation(session, all_active_players, excess_players)
    
    # Update waitlist
    session.waiting_players = players_to_wait
    
    # Update waitlist history and counts
    for player_id in players_to_wait:
        # Update wait count
        session.king_of_court_wait_counts[player_id] = session.king_of_court_wait_counts.get(player_id, 0) + 1
        
        # Update waitlist history - add to end (most recent)
        if player_id in session.king_of_court_waitlist_history:
            # Remove from previous position
            session.king_of_court_waitlist_history.remove(player_id)
        session.king_of_court_waitlist_history.append(player_id)
        
        # CRITICAL: Remove waiters from court position data
        if player_id in session.king_of_court_player_positions:
            del session.king_of_court_player_positions[player_id]
    
    # Remove waiters from court assignments
    for court_num in court_assignments.keys():
        court_assignments[court_num] = [p for p in court_assignments[court_num] if p not in players_to_wait]
    
    # Add returning waiters who are not waiting to fill gaps
    returning_players = [p for p in current_waiters if p not in players_to_wait]
    
    for court_num in court_ordering:
        if court_num not in court_assignments:
            court_assignments[court_num] = []
            
        spots_needed = players_per_court - len(court_assignments[court_num])
        
        # Fill gaps with returning players
        for _ in range(spots_needed):
            if returning_players:
                player_id = returning_players.pop(0)
                court_assignments[court_num].append(player_id)
                session.king_of_court_player_positions[player_id] = court_num
    
    return court_assignments


def select_players_for_fair_rotation(session: Session, all_active_players: List[str], excess_players: int) -> List[str]:
    """
    When everyone has waited at least once, select players for waitlist based on fair rotation.
    Players who waited longest ago (first in history) get priority to wait again.
    This ensures maximum time between waits for each player.
    """
    players_to_wait = []
    
    # Get all players ordered by when they last waited (oldest first)
    waitlist_order = []
    
    # Start with players who have waited (in order they waited - oldest first)
    for player_id in session.king_of_court_waitlist_history:
        if player_id in all_active_players:
            waitlist_order.append(player_id)
    
    # Add any players who somehow aren't in history (shouldn't happen, but safety)
    for player_id in all_active_players:
        if player_id not in waitlist_order:
            waitlist_order.append(player_id)
    
    # Take the players who waited longest ago
    players_to_wait = waitlist_order[:excess_players]
    
    return players_to_wait


def create_matches_from_final_assignments(session: Session, court_assignments: Dict[int, List[str]], 
                                        players_per_court: int):
    """
    STEP 3: Create new matches from final court assignments with King of Court team splitting
    """
    for court_num, players in court_assignments.items():
        if len(players) == players_per_court:
            if players_per_court == 4:
                # Apply King of Court rule: previous teammates must be on opposite teams
                team1, team2 = enforce_king_of_court_team_splitting(players, session)
            else:  # singles
                import random
                random.shuffle(players)
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
        elif len(players) > 0:
            print(f"WARNING: Court {court_num} has {len(players)} players but needs {players_per_court}")


def enforce_king_of_court_team_splitting(players: List[str], session: Session) -> Tuple[List[str], List[str]]:
    """
    King of Court team splitting rule: Previous teammates must be on OPPOSITE teams
    
    This is the ONLY constraint applied - no partnership repetition concerns,
    just ensure recent teammates from the last match are split.
    """
    if len(players) != 4:
        import random
        random.shuffle(players)
        return players[:2], players[2:]
    
    # Find who was teammates in recently completed matches
    recent_teammates = set()
    
    # Check all completed matches, using the most recent batch
    completed_matches = [m for m in session.matches if m.status == 'completed']
    if completed_matches:
        # Get the most recent completed matches (likely the previous round)
        latest_completed_time = max(m.end_time for m in completed_matches if m.end_time)
        recent_completed = [m for m in completed_matches 
                          if m.end_time and abs((m.end_time - latest_completed_time).total_seconds()) < 60]
        
        for match in recent_completed:
            # Check if any of our players were teammates in this match
            for player in players:
                if player in match.team1:
                    teammate_candidates = [p for p in match.team1 if p != player and p in players]
                    for teammate in teammate_candidates:
                        recent_teammates.add((player, teammate))
                        recent_teammates.add((teammate, player))  # Bidirectional
                elif player in match.team2:
                    teammate_candidates = [p for p in match.team2 if p != player and p in players]
                    for teammate in teammate_candidates:
                        recent_teammates.add((player, teammate))
                        recent_teammates.add((teammate, player))  # Bidirectional
    
    # Try to arrange teams so recent teammates are on OPPOSITE teams
    import itertools
    import random
    
    best_arrangement = None
    min_violations = float('inf')
    
    for team1_indices in itertools.combinations(range(4), 2):
        team1 = [players[i] for i in team1_indices]
        team2 = [players[i] for i in range(4) if i not in team1_indices]
        
        # Count violations (recent teammates on same team)
        violations = 0
        if len(team1) == 2 and (team1[0], team1[1]) in recent_teammates:
            violations += 1
        if len(team2) == 2 and (team2[0], team2[1]) in recent_teammates:
            violations += 1
        
        if violations < min_violations:
            min_violations = violations
            best_arrangement = (team1, team2)
        
        # If we found perfect arrangement, use it
        if violations == 0:
            break
    
    if best_arrangement:
        return best_arrangement
    else:
        # Fallback: random arrangement
        random.shuffle(players)
        return players[:2], players[2:]


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
    
    # Save to persistent storage
    from .session_persistence import save_court_ordering
    save_court_ordering(court_ordering, session.config.courts)
    
    return session
