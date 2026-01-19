"""
Session management for pickleball games
"""

from typing import List, Optional, Dict, Tuple
from datetime import datetime
from .pickleball_types import (
    Session, SessionConfig, Player, Match, MatchStatus, PlayerStats, 
    QueuedMatch, AdvancedConfig, MatchSnapshot
)
from .utils import generate_id, create_player_stats, shuffle_list, get_default_advanced_config
from .roundrobin import generate_round_robin_queue
from .time_manager import now


def create_session(config: SessionConfig, max_queue_size: int = 100) -> Session:
    """Create a new session"""
    from .time_manager import start_session as tm_start_session, get_session_start_time, now
    
    player_stats: Dict[str, PlayerStats] = {}
    active_players = set()
    
    # Randomize if requested
    players_to_use = shuffle_list(config.players) if config.randomize_player_order else config.players
    
    for player in players_to_use:
        player_stats[player.id] = create_player_stats(player.id)
        active_players.add(player.id)
    
    # Update config with potentially shuffled players
    final_config = SessionConfig(
        mode=config.mode,
        session_type=config.session_type,
        players=players_to_use,
        courts=config.courts,
        banned_pairs=config.banned_pairs,
        locked_teams=config.locked_teams,
        first_bye_players=config.first_bye_players,
        court_sliding_mode=config.court_sliding_mode,
        randomize_player_order=config.randomize_player_order,
        advanced_config=config.advanced_config,
        pre_seeded_ratings=config.pre_seeded_ratings,
        king_of_court_config=config.king_of_court_config,
        competitive_round_robin_config=config.competitive_round_robin_config,
        continuous_wave_flow_config=config.continuous_wave_flow_config
    )
    
    # Generate match queue for round-robin mode
    match_queue: List[QueuedMatch] = []
    if final_config.mode == 'round-robin':
        match_queue = generate_round_robin_queue(
            players_to_use,
            final_config.session_type,
            final_config.banned_pairs,
            max_queue_size,
            final_config.locked_teams,
            player_stats,
            None,  # active_matches (no active matches during session creation)
            final_config.first_bye_players  # first_bye_players
        )
    
    # Use provided advanced config or defaults
    advanced_config = config.advanced_config or get_default_advanced_config()
    
    # For competitive-variety, competitive-round-robin, competitive-continuous-round-robin, 
    # and continuous-wave-flow modes, start all players in waiting list
    waiting_players = []
    if final_config.mode in ('competitive-variety', 'competitive-round-robin', 'competitive-continuous-round-robin', 'continuous-wave-flow'):
        waiting_players = [p.id for p in players_to_use]
    
    # Start the session timing if not already started
    session_start_time = get_session_start_time()
    if session_start_time is None:
        tm_start_session()
        session_start_time = get_session_start_time()
    
    session = Session(
        id=generate_id(),
        config=final_config,
        matches=[],
        waiting_players=waiting_players,
        player_stats=player_stats,
        active_players=active_players,
        match_queue=match_queue,
        max_queue_size=max_queue_size,
        advanced_config=advanced_config,
        session_start_time=session_start_time
    )
    
    # Set default competitive variety settings based on waitlist size
    if final_config.mode == 'competitive-variety':
        from .competitive_variety import update_session_competitive_variety_settings
        update_session_competitive_variety_settings(session)
    
    # Initialize King of Court session
    if final_config.mode == 'king-of-court':
        from .kingofcourt import initialize_king_of_court_session
        session = initialize_king_of_court_session(session)
    
    return session


def add_player_to_session(session: Session, player: Player) -> Session:
    """Add a player to an active session"""
    
    # Check if player already exists
    if any(p.id == player.id for p in session.config.players):
        # If player exists but is inactive, reactivate them
        if player.id not in session.active_players:
            session.active_players.add(player.id)
            # Add to waiting list so they can get back into games
            if player.id not in session.waiting_players:
                session.waiting_players.append(player.id)
            
            # Regenerate queue if needed
            if session.config.mode == 'round-robin':
                updated_players = session.config.players
                active_player_objs = [p for p in updated_players if p.id in session.active_players]
                session.match_queue = generate_round_robin_queue(
                    active_player_objs,
                    session.config.session_type,
                    session.config.banned_pairs,
                    session.max_queue_size,
                    session.config.locked_teams,
                    session.player_stats,
                    session.matches,
                    []  # first_bye_players (empty for mid-session additions)
                )
        return session
    
    # Add to players list
    updated_players = session.config.players + [player]
    active_players = session.active_players.copy()
    active_players.add(player.id)
    
    # Create stats with max waited + 1 to give new player priority
    max_waited = 0
    max_courts_waited = 0
    for stats in session.player_stats.values():
        if stats.games_waited > max_waited:
            max_waited = stats.games_waited
        if stats.courts_completed_since_last_play > max_courts_waited:
            max_courts_waited = stats.courts_completed_since_last_play
    
    new_stats = create_player_stats(player.id)
    new_stats.games_waited = max_waited + 1
    # Give new player priority in the simple 2-court-wait system
    new_stats.courts_completed_since_last_play = max_courts_waited + 1
    session.player_stats[player.id] = new_stats
    
    # Update config
    session.config.players = updated_players
    session.active_players = active_players
    
    # Regenerate queue for round-robin
    if session.config.mode == 'round-robin':
        active_player_objs = [p for p in updated_players if p.id in active_players]
        session.match_queue = generate_round_robin_queue(
            active_player_objs,
            session.config.session_type,
            session.config.banned_pairs,
            session.max_queue_size,
            session.config.locked_teams,
            session.player_stats,
            session.matches,
            []  # first_bye_players (empty for mid-session additions)
        )
    
    # Update competitive variety settings if needed
    if session.config.mode == 'competitive-variety':
        from .competitive_variety import update_session_competitive_variety_settings
        update_session_competitive_variety_settings(session)
        
    return session


def remove_player_from_session(session: Session, player_id: str) -> Session:
    """Remove a player from an active session"""
    
    # Don't remove from config.players, just mark as inactive
    active_players = session.active_players.copy()
    active_players.discard(player_id)
    
    # Remove from waiting list
    waiting_players = [pid for pid in session.waiting_players if pid != player_id]
    
    session.active_players = active_players
    session.waiting_players = waiting_players
    
    # Update competitive variety settings if needed
    if session.config.mode == 'competitive-variety':
        from .competitive_variety import update_session_competitive_variety_settings
        update_session_competitive_variety_settings(session)
    
    return session


def get_active_player_names(session: Session) -> Dict[str, str]:
    """Get mapping of active player IDs to names"""
    result = {}
    for player in session.config.players:
        if player.id in session.active_players:
            result[player.id] = player.name
    return result


def get_player_name(session: Session, player_id: str) -> Optional[str]:
    """Get player name by ID"""
    for player in session.config.players:
        if player.id == player_id:
            return player.name
    return None


def get_matches_for_court(session: Session, court_number: int) -> List[Match]:
    """Get all matches for a specific court"""
    return [m for m in session.matches if m.court_number == court_number]


def get_active_matches(session: Session) -> List[Match]:
    """Get all active matches (waiting or in-progress)"""
    return [m for m in session.matches if m.status in ['waiting', 'in-progress']]


def get_completed_matches(session: Session) -> List[Match]:
    """Get all completed or forfeited matches"""
    return [m for m in session.matches if m.status in ['completed', 'forfeited']]


def _create_session_snapshot(session: Session, match_id: str) -> MatchSnapshot:
    """Create a snapshot of the current session state before a match is completed"""
    
    # Serialize matches
    matches_data = []
    for match in session.matches:
        match_data = {
            "id": match.id,
            "court_number": match.court_number,
            "team1": match.team1,
            "team2": match.team2,
            "status": match.status,
            "score": match.score,
            "start_time": match.start_time.isoformat() if match.start_time else None,
            "end_time": match.end_time.isoformat() if match.end_time else None
        }
        matches_data.append(match_data)
    
    # Serialize player stats
    stats_data = {}
    for player_id, stats in session.player_stats.items():
        stats_data[player_id] = {
            "player_id": stats.player_id,
            "games_played": stats.games_played,
            "games_waited": stats.games_waited,
            "wins": stats.wins,
            "losses": stats.losses,
            "partners_played": dict(stats.partners_played),
            "opponents_played": dict(stats.opponents_played),
            "total_points_for": stats.total_points_for,
            "total_points_against": stats.total_points_against,
            "partner_last_game": dict(stats.partner_last_game),
            "opponent_last_game": dict(stats.opponent_last_game),
            "court_history": list(stats.court_history),
            "total_wait_time": stats.total_wait_time,
            "wait_start_time": stats.wait_start_time.isoformat() if stats.wait_start_time else None,
            "courts_completed_since_last_play": stats.courts_completed_since_last_play
        }
    
    # Serialize queue
    queue_data = []
    for queued_match in session.match_queue:
        queue_data.append({
            "team1": queued_match.team1,
            "team2": queued_match.team2
        })
    
    return MatchSnapshot(
        match_id=match_id,
        timestamp=now(),
        matches=matches_data,
        waiting_players=list(session.waiting_players),
        player_stats=stats_data,
        active_players=list(session.active_players),
        match_queue=queue_data,
        player_last_court=dict(session.player_last_court),
        court_players={k: list(v) for k, v in session.court_players.items()},
        courts_mixed_history=list(session.courts_mixed_history)
    )


def load_session_from_snapshot(session: Session, snapshot: MatchSnapshot) -> bool:
    """Load session state from a snapshot (reverting to state before a match was completed)"""
    
    try:
        # Restore matches
        session.matches = []
        for match_data in snapshot.matches:
            start_time = None
            if match_data.get("start_time"):
                start_time = datetime.fromisoformat(match_data["start_time"])
            
            end_time = None
            if match_data.get("end_time"):
                end_time = datetime.fromisoformat(match_data["end_time"])
            
            match = Match(
                id=match_data["id"],
                court_number=match_data["court_number"],
                team1=match_data["team1"],
                team2=match_data["team2"],
                status=match_data["status"],
                score=match_data.get("score"),
                start_time=start_time,
                end_time=end_time
            )
            session.matches.append(match)
        
        # Restore player stats
        session.player_stats = {}
        for player_id, stats_data in snapshot.player_stats.items():
            wait_start_time = None
            if stats_data.get("wait_start_time"):
                wait_start_time = datetime.fromisoformat(stats_data["wait_start_time"])
            
            session.player_stats[player_id] = PlayerStats(
                player_id=stats_data["player_id"],
                games_played=stats_data["games_played"],
                games_waited=stats_data["games_waited"],
                wins=stats_data["wins"],
                losses=stats_data["losses"],
                partners_played=dict(stats_data["partners_played"]),
                opponents_played=dict(stats_data["opponents_played"]),
                total_points_for=stats_data["total_points_for"],
                total_points_against=stats_data["total_points_against"],
                partner_last_game=dict(stats_data["partner_last_game"]),
                opponent_last_game=dict(stats_data["opponent_last_game"]),
                court_history=list(stats_data["court_history"]),
                total_wait_time=stats_data["total_wait_time"],
                wait_start_time=wait_start_time,
                courts_completed_since_last_play=stats_data.get("courts_completed_since_last_play", 0)
            )
        
        # Restore waiting players
        session.waiting_players = list(snapshot.waiting_players)
        
        # Restore active players
        session.active_players = set(snapshot.active_players)
        
        # Restore match queue
        session.match_queue = []
        for queue_data in snapshot.match_queue:
            session.match_queue.append(QueuedMatch(
                team1=queue_data["team1"],
                team2=queue_data["team2"]
            ))
        
        # Restore competitive variety state
        session.player_last_court = dict(snapshot.player_last_court)
        session.court_players = {k: list(v) for k, v in snapshot.court_players.items()}
        session.courts_mixed_history = set(snapshot.courts_mixed_history)
        
        # Remove the snapshot that was just loaded (and all after it) from history
        # This preserves snapshots from before this point
        snapshot_idx = -1
        for idx, snap in enumerate(session.match_history_snapshots):
            if snap.match_id == snapshot.match_id:
                snapshot_idx = idx
                break
        
        if snapshot_idx >= 0:
            session.match_history_snapshots = session.match_history_snapshots[:snapshot_idx]
        
        return True
    except Exception as e:
        print(f"Error loading session from snapshot: {e}")
        return False


def complete_match(session: Session, match_id: str, team1_score: int, team2_score: int) -> Tuple[bool, List[Dict]]:
    """Complete a match with scores. Returns (success, list_of_slides)."""
    
    # Validate scores - winner must have higher score
    if team1_score == team2_score:
        return False, []
    
    # Find match
    match = None
    for m in session.matches:
        if m.id == match_id:
            match = m
            break
    
    if not match:
        return False, []
    
    # Create snapshot BEFORE updating match status (so we capture pre-completion state)
    snapshot = _create_session_snapshot(session, match_id)
    session.match_history_snapshots.append(snapshot)
    
    # Update match
    match.status = 'completed'
    match.score = {'team1_score': team1_score, 'team2_score': team2_score}
    match.end_time = now()
    
    # Determine winner and update stats
    team1_won = team1_score > team2_score
    
    # Get all players in this match
    players_in_match = set(match.team1 + match.team2)
    
    for player_id in match.team1:
        stats = session.player_stats[player_id]
        stats.games_played += 1
        stats.total_points_for += team1_score
        stats.total_points_against += team2_score
        if team1_won:
            stats.wins += 1
        else:
            stats.losses += 1
        
        for opponent_id in match.team2:
            stats.opponents_played[opponent_id] = stats.opponents_played.get(opponent_id, 0) + 1
        for partner_id in match.team1:
            if partner_id != player_id:
                stats.partners_played[partner_id] = stats.partners_played.get(partner_id, 0) + 1
    
    for player_id in match.team2:
        stats = session.player_stats[player_id]
        stats.games_played += 1
        stats.total_points_for += team2_score
        stats.total_points_against += team1_score
        if not team1_won:
            stats.wins += 1
        else:
            stats.losses += 1
        
        for opponent_id in match.team1:
            stats.opponents_played[opponent_id] = stats.opponents_played.get(opponent_id, 0) + 1
        for partner_id in match.team2:
            if partner_id != player_id:
                stats.partners_played[partner_id] = stats.partners_played.get(partner_id, 0) + 1
    
    # Increment games_waited for all other active players (legacy counter)
    # The actual wait time priority system uses total_wait_time + current wait
    for player_id in sorted(session.active_players):
        if player_id not in players_in_match:
            if player_id in session.player_stats:
                session.player_stats[player_id].games_waited += 1
                # Track courts completed since last play for simple 2-court-wait rule
                session.player_stats[player_id].courts_completed_since_last_play += 1
    
    # Reset courts_completed_since_last_play for players who just played
    for player_id in players_in_match:
        if player_id in session.player_stats:
            session.player_stats[player_id].courts_completed_since_last_play = 0
    
    # Update variety tracking for competitive-variety mode
    if session.config.mode == 'competitive-variety':
        from .competitive_variety import update_variety_tracking_after_match
        update_variety_tracking_after_match(session, match.court_number, match.team1, match.team2)
        
        # Update deterministic waitlist predictions
        from .deterministic_waitlist_v2 import calculate_waitlist_predictions_v2
        try:
            session.advanced_config.waitlist_predictions = calculate_waitlist_predictions_v2(session)
        except Exception as e:
            print(f"Warning: Could not update waitlist predictions: {e}")
            session.advanced_config.waitlist_predictions = []
    
    # Handle Court Sliding (skip for King of Court mode where court positions are meaningful)
    slides = []
    if session.config.court_sliding_mode != 'None' and session.config.mode != 'king-of-court':
        finished_court = match.court_number
        
        # Calculate row parity (assuming 2 columns per row)
        # 1-based index
        # 1,2 -> Row 0
        # 3,4 -> Row 1
        # Odd courts (1,3,5) are LEFT
        # Even courts (2,4,6) are RIGHT
        
        is_left_court = (finished_court % 2) != 0
        
        target_court = finished_court
        source_court = None
        
        if session.config.court_sliding_mode == 'Right to Left':
            # Right moves to Left.
            # If finished is Left (Odd), check Right (Even) neighbor (finished + 1)
            if is_left_court:
                 neighbor = finished_court + 1
                 if neighbor <= session.config.courts:
                     source_court = neighbor
            # If finished is Right (Even), no slide (nothing to its right in this row)
            
        elif session.config.court_sliding_mode == 'Left to Right':
             # Left moves to Right.
             # If finished is Right (Even), check Left (Odd) neighbor (finished - 1)
             if not is_left_court:
                 neighbor = finished_court - 1
                 if neighbor >= 1:
                     source_court = neighbor
             # If finished is Left (Odd), no slide
        
        if source_court:
            # Check for active match on source_court
            source_match = None
            for m in session.matches:
                if m.court_number == source_court and m.status in ['waiting', 'in-progress']:
                    source_match = m
                    break
            
            if source_match:
                # Move match to target_court
                source_match.court_number = target_court
                slides.append({
                    'from': source_court,
                    'to': target_court,
                    'match_id': source_match.id
                })
    
    return True, slides


def forfeit_match(session: Session, match_id: str) -> bool:
    """Forfeit a match without recording scores"""
    
    match = None
    for m in session.matches:
        if m.id == match_id:
            match = m
            break
    
    if not match:
        return False
    
    match.status = 'forfeited'
    match.end_time = now()
    
    # Don't record any statistics for forfeits
    # Just mark partnership/opponent interactions
    for player_id in match.team1:
        stats = session.player_stats[player_id]
        for opponent_id in match.team2:
            stats.opponents_played[opponent_id] = stats.opponents_played.get(opponent_id, 0) + 1
        for partner_id in match.team1:
            if partner_id != player_id:
                stats.partners_played[partner_id] = stats.partners_played.get(partner_id, 0) + 1
    
    for player_id in match.team2:
        stats = session.player_stats[player_id]
        for opponent_id in match.team1:
            stats.opponents_played[opponent_id] = stats.opponents_played.get(opponent_id, 0) + 1
        for partner_id in match.team2:
            if partner_id != player_id:
                stats.partners_played[partner_id] = stats.partners_played.get(partner_id, 0) + 1
    
    # Update variety tracking for competitive-variety mode to prevent immediate rescheduling
    if session.config.mode == 'competitive-variety':
        from .competitive_variety import update_variety_tracking_after_match
        update_variety_tracking_after_match(session, match.court_number, match.team1, match.team2)
    
    return True


def evaluate_and_create_matches(session: Session) -> Session:
    """
    Evaluate current session state and create new matches.
    This should be called whenever state changes to potentially start new games.
    For competitive-variety mode, re-populates courts based on current settings.
    For king-of-court mode, manages rounds-based progression.
    For competitive-round-robin mode, populates from pre-approved schedule (rounds-based).
    For continuous-wave-flow mode, dynamically generates matches as courts finish.
    """
    
    if session.config.mode == 'competitive-variety':
        from python.queue_manager import populate_empty_courts
        populate_empty_courts(session)
    elif session.config.mode == 'round-robin':
        from python.queue_manager import populate_empty_courts
        populate_empty_courts(session)
    elif session.config.mode == 'king-of-court':
        from python.kingofcourt import evaluate_king_of_court_session
        session = evaluate_king_of_court_session(session)
    elif session.config.mode == 'competitive-round-robin':
        from python.competitive_round_robin import populate_courts_from_schedule
        populate_courts_from_schedule(session)
    elif session.config.mode == 'competitive-continuous-round-robin':
        from python.competitive_round_robin import populate_courts_continuous
        populate_courts_continuous(session)
    elif session.config.mode == 'continuous-wave-flow':
        from python.continuous_wave_flow import populate_courts_continuous_wave_flow
        populate_courts_continuous_wave_flow(session)
    
    return session
    
    return session


def create_manual_match(session: Session, court_number: int, team1_ids: List[str], team2_ids: List[str]) -> Dict:
    """
    Manually create a match on a court, replacing any existing match.
    Used for 'Make Court' and 'Edit Court' features.
    
    Returns a dictionary with:
    - 'success': True if match was created, False otherwise
    - 'balance_analysis': Dictionary with balance information (always included)
    - 'error': Error message if success is False
    """
    # Validate players
    all_player_ids = set(team1_ids + team2_ids)
    for player_id in all_player_ids:
        if player_id not in session.active_players:
            return {
                'success': False,
                'error': f'Player {player_id} is not active in this session',
                'balance_analysis': None
            }
    
    # Check for duplicate players
    if len(all_player_ids) != len(team1_ids) + len(team2_ids):
        return {
            'success': False,
            'error': 'Duplicate players detected in teams',
            'balance_analysis': None
        }
    
    # Check court number validity
    if court_number < 1 or court_number > session.config.courts:
        return {
            'success': False,
            'error': f'Invalid court number {court_number}',
            'balance_analysis': None
        }
    
    # Analyze match balance before creating
    balance_analysis = analyze_match_balance(session, team1_ids, team2_ids)
    
    # Track players currently on this court before removing the match
    old_players_on_court = set()
    for match in session.matches:
        if match.court_number == court_number and match.status in ['waiting', 'in-progress']:
            old_players_on_court.update(match.team1 + match.team2)
    
    # Remove any existing match on this court
    for match in session.matches[:]:
        if match.court_number == court_number and match.status in ['waiting', 'in-progress']:
            match.status = 'forfeited'
            match.end_time = now()
    
    # Reset courts_completed_since_last_play for new players going INTO the match
    # They are now playing, so their wait counter resets
    for player_id in all_player_ids:
        if player_id in session.player_stats:
            session.player_stats[player_id].courts_completed_since_last_play = 0
    
    # Reset courts_completed_since_last_play for old players going ONTO the waitlist
    # They just played (or were about to), so their wait counter resets
    swapped_out_players = old_players_on_court - all_player_ids
    for player_id in swapped_out_players:
        if player_id in session.player_stats:
            session.player_stats[player_id].courts_completed_since_last_play = 0
    
    # Create new match
    match = Match(
        id=generate_id(),
        court_number=court_number,
        team1=team1_ids,
        team2=team2_ids,
        status='waiting',
        start_time=now()
    )
    
    session.matches.append(match)
    
    return {
        'success': True,
        'balance_analysis': balance_analysis,
        'error': None
    }


def update_match_teams(session: Session, match_id: str, team1_ids: List[str], team2_ids: List[str]) -> bool:
    """
    Update the teams for an existing match (for Edit Court).
    Returns True if successful, False otherwise.
    """
    # Validate players
    all_player_ids = set(team1_ids + team2_ids)
    for player_id in all_player_ids:
        if player_id not in session.active_players:
            return False
    
    # Check for duplicate players
    if len(all_player_ids) != len(team1_ids) + len(team2_ids):
        return False
    
    # Find match
    match = None
    for m in session.matches:
        if m.id == match_id:
            match = m
            break
    
    if not match or match.status not in ['waiting', 'in-progress']:
        return False
    
    # Track old players before update
    old_players = set(match.team1 + match.team2)
    
    # Update teams
    match.team1 = team1_ids
    match.team2 = team2_ids
    
    # Reset courts_completed_since_last_play for new players going INTO the match
    for player_id in all_player_ids:
        if player_id in session.player_stats:
            session.player_stats[player_id].courts_completed_since_last_play = 0
    
    # Reset courts_completed_since_last_play for old players going ONTO the waitlist
    swapped_out_players = old_players - all_player_ids
    for player_id in swapped_out_players:
        if player_id in session.player_stats:
            session.player_stats[player_id].courts_completed_since_last_play = 0
    
    return True


def analyze_match_balance(session: Session, team1_ids: List[str], team2_ids: List[str]) -> Dict:
    """
    Analyze the balance of a proposed match and suggest alternatives if available.
    
    Returns a dictionary with:
    - 'rating_difference': The ELO difference between teams
    - 'balance_quality': 'excellent', 'good', 'fair', 'poor', 'terrible' 
    - 'is_imbalanced': True if difference > 300 points
    - 'alternative_configs': List of better team configurations if available
    - 'constraints_violated': List of any constraint violations
    """
    from .competitive_variety import calculate_player_elo_rating, score_potential_match, can_play_with_player
    
    # Calculate team ratings using pre-seeded ratings if available
    team1_rating = sum(calculate_player_elo_rating(session, player_id) for player_id in team1_ids)
    team2_rating = sum(calculate_player_elo_rating(session, player_id) for player_id in team2_ids)
    
    rating_diff = abs(team1_rating - team2_rating)
    
    # Determine balance quality
    if rating_diff < 50:
        balance_quality = 'excellent'
    elif rating_diff < 150:
        balance_quality = 'good' 
    elif rating_diff < 300:
        balance_quality = 'fair'
    elif rating_diff < 500:
        balance_quality = 'poor'
    else:
        balance_quality = 'terrible'
    
    # Check constraints if in competitive variety mode
    constraints_violated = []
    if session.config.mode == 'competitive-variety':
        # Check partner constraints
        if len(team1_ids) == 2:
            if not can_play_with_player(session, team1_ids[0], team1_ids[1], 'partner'):
                constraints_violated.append(f"Team1 partners {team1_ids[0]} and {team1_ids[1]} played together too recently")
        
        if len(team2_ids) == 2:
            if not can_play_with_player(session, team2_ids[0], team2_ids[1], 'partner'):
                constraints_violated.append(f"Team2 partners {team2_ids[0]} and {team2_ids[1]} played together too recently")
        
        # Check opponent constraints
        for p1 in team1_ids:
            for p2 in team2_ids:
                if not can_play_with_player(session, p1, p2, 'opponent'):
                    constraints_violated.append(f"Opponents {p1} and {p2} played against each other too recently")
    
    # Find alternative configurations if current one is imbalanced
    alternative_configs = []
    if rating_diff > 300 and len(team1_ids) == 2 and len(team2_ids) == 2:
        all_players = team1_ids + team2_ids
        
        # Try other configurations
        configs = [
            ([all_players[0], all_players[2]], [all_players[1], all_players[3]]),
            ([all_players[0], all_players[3]], [all_players[1], all_players[2]])
        ]
        
        for alt_team1, alt_team2 in configs:
            # Calculate alternative rating difference
            # Calculate alternative team rating using pre-seeded ratings if available
            alt_team1_rating = sum(calculate_player_elo_rating(session, player_id) for player_id in alt_team1)
            alt_team2_rating = sum(calculate_player_elo_rating(session, player_id) for player_id in alt_team2)
            
            alt_rating_diff = abs(alt_team1_rating - alt_team2_rating)
            
            # If this alternative is significantly better, include it
            if alt_rating_diff < rating_diff * 0.7:  # At least 30% better
                # Check if alternative violates constraints
                alt_valid = True
                alt_constraints = []
                
                if session.config.mode == 'competitive-variety':
                    if not can_play_with_player(session, alt_team1[0], alt_team1[1], 'partner'):
                        alt_valid = False
                        alt_constraints.append("Partner constraint violated")
                    
                    if not can_play_with_player(session, alt_team2[0], alt_team2[1], 'partner'):
                        alt_valid = False
                        alt_constraints.append("Partner constraint violated")
                    
                    for p1 in alt_team1:
                        for p2 in alt_team2:
                            if not can_play_with_player(session, p1, p2, 'opponent'):
                                alt_valid = False
                                alt_constraints.append("Opponent constraint violated")
                                break
                        if not alt_valid:
                            break
                
                alternative_configs.append({
                    'team1': alt_team1,
                    'team2': alt_team2,
                    'rating_difference': alt_rating_diff,
                    'valid': alt_valid,
                    'constraints': alt_constraints
                })
    
    return {
        'team1_rating': team1_rating,
        'team2_rating': team2_rating,
        'rating_difference': rating_diff,
        'balance_quality': balance_quality,
        'is_imbalanced': rating_diff > 300,
        'alternative_configs': alternative_configs,
        'constraints_violated': constraints_violated
    }
