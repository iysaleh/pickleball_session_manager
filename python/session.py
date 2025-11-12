"""
Session management for pickleball games
"""

from typing import List, Optional, Dict, Tuple
from datetime import datetime
from .types import (
    Session, SessionConfig, Player, Match, MatchStatus, PlayerStats, 
    QueuedMatch, AdvancedConfig
)
from .utils import generate_id, create_player_stats, shuffle_list, get_default_advanced_config
from .roundrobin import generate_round_robin_queue


def create_session(config: SessionConfig, max_queue_size: int = 100) -> Session:
    """Create a new session"""
    
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
        randomize_player_order=config.randomize_player_order,
        advanced_config=config.advanced_config
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
            player_stats
        )
    
    # Use provided advanced config or defaults
    advanced_config = config.advanced_config or get_default_advanced_config()
    
    return Session(
        id=generate_id(),
        config=final_config,
        matches=[],
        waiting_players=[],
        player_stats=player_stats,
        active_players=active_players,
        match_queue=match_queue,
        max_queue_size=max_queue_size,
        advanced_config=advanced_config
    )


def add_player_to_session(session: Session, player: Player) -> Session:
    """Add a player to an active session"""
    
    # Check if player already exists
    if any(p.id == player.id for p in session.config.players):
        return session
    
    # Add to players list
    updated_players = session.config.players + [player]
    active_players = session.active_players.copy()
    active_players.add(player.id)
    
    # Create stats with max waited + 1
    max_waited = 0
    for stats in session.player_stats.values():
        if stats.games_waited > max_waited:
            max_waited = stats.games_waited
    
    new_stats = create_player_stats(player.id)
    new_stats.games_waited = max_waited + 1
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
            session.matches
        )
    
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


def complete_match(session: Session, match_id: str, team1_score: int, team2_score: int) -> bool:
    """Complete a match with scores"""
    
    # Validate scores - winner must have higher score
    if team1_score == team2_score:
        return False
    
    # Find match
    match = None
    for m in session.matches:
        if m.id == match_id:
            match = m
            break
    
    if not match:
        return False
    
    # Update match
    match.status = 'completed'
    match.score = {'team1_score': team1_score, 'team2_score': team2_score}
    match.end_time = datetime.now()
    
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
            stats.opponents_played.add(opponent_id)
        for partner_id in match.team1:
            if partner_id != player_id:
                stats.partners_played.add(partner_id)
    
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
            stats.opponents_played.add(opponent_id)
        for partner_id in match.team2:
            if partner_id != player_id:
                stats.partners_played.add(partner_id)
    
    # Increment games_waited for all other active players
    for player_id in session.active_players:
        if player_id not in players_in_match:
            if player_id in session.player_stats:
                session.player_stats[player_id].games_waited += 1
    
    # Update variety tracking for competitive-variety mode
    if session.config.mode == 'competitive-variety':
        from .competitive_variety import update_variety_tracking_after_match
        update_variety_tracking_after_match(session, match.court_number, match.team1, match.team2)
    
    return True


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
    match.end_time = datetime.now()
    
    # Don't record any statistics for forfeits
    # Just mark partnership/opponent interactions
    for player_id in match.team1:
        stats = session.player_stats[player_id]
        for opponent_id in match.team2:
            stats.opponents_played.add(opponent_id)
        for partner_id in match.team1:
            if partner_id != player_id:
                stats.partners_played.add(partner_id)
    
    for player_id in match.team2:
        stats = session.player_stats[player_id]
        for opponent_id in match.team1:
            stats.opponents_played.add(opponent_id)
        for partner_id in match.team2:
            if partner_id != player_id:
                stats.partners_played.add(partner_id)
    
    return True


def evaluate_and_create_matches(session: Session) -> Session:
    """
    Evaluate current session state and create new matches.
    This should be called whenever state changes to potentially start new games.
    """
    
    # This is a placeholder - actual implementation will differ by game mode
    # For now, just return the session
    return session
