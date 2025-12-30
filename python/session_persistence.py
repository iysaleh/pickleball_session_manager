"""
Session persistence - save and load session state to/from files
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from .time_manager import now
from .pickleball_types import Player

# Session files locations
SESSIONS_DIR = Path.home() / ".pickleball"
LAST_SESSION_FILE = SESSIONS_DIR / "last_session.json"
PLAYER_HISTORY_FILE = SESSIONS_DIR / "player_history.json"
COURT_NAMES_FILE = SESSIONS_DIR / "court_names.json"


def ensure_session_dir():
    """Ensure the session directory exists"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_player_history(player_names: List[str], first_bye_players: List[str] = None, 
                       players_with_ratings: List[Player] = None, pre_seeded: bool = False,
                       game_mode: str = None, session_type: str = None):
    """Save the list of player names, first bye players, pre-seeded ratings, and game configuration to history"""
    ensure_session_dir()
    
    # Remove duplicates while preserving order
    seen = set()
    unique_players = []
    for name in player_names:
        if name not in seen:
            unique_players.append(name)
            seen.add(name)
    
    # Store pre-seeded ratings if available
    player_ratings = {}
    if pre_seeded and players_with_ratings:
        for player in players_with_ratings:
            if player.skill_rating is not None:
                player_ratings[player.name] = player.skill_rating
    
    history_data = {
        "players": unique_players,
        "first_bye_players": first_bye_players or [],
        "pre_seeded": pre_seeded,
        "player_ratings": player_ratings,
        "game_mode": game_mode,  # Store the game mode
        "session_type": session_type,  # Store session type (doubles/singles)
        "last_updated": now().isoformat()
    }
    
    try:
        with open(PLAYER_HISTORY_FILE, 'w') as f:
            json.dump(history_data, f, indent=2)
    except Exception as e:
        print(f"Error saving player history: {e}")


def load_player_history() -> List[str]:
    """Load the list of player names from history"""
    if not PLAYER_HISTORY_FILE.exists():
        return []
    
    try:
        with open(PLAYER_HISTORY_FILE, 'r') as f:
            data = json.load(f)
            return data.get("players", [])
    except Exception as e:
        print(f"Error loading player history: {e}")
        return []


def load_player_history_with_ratings() -> Dict:
    """Load complete player history including pre-seeded ratings and game configuration"""
    if not PLAYER_HISTORY_FILE.exists():
        return {
            "players": [], 
            "first_bye_players": [], 
            "pre_seeded": False, 
            "player_ratings": {},
            "game_mode": None,
            "session_type": None
        }
    
    try:
        with open(PLAYER_HISTORY_FILE, 'r') as f:
            data = json.load(f)
            return {
                "players": data.get("players", []),
                "first_bye_players": data.get("first_bye_players", []),
                "pre_seeded": data.get("pre_seeded", False),
                "player_ratings": data.get("player_ratings", {}),
                "game_mode": data.get("game_mode", None),
                "session_type": data.get("session_type", None)
            }
    except Exception as e:
        print(f"Error loading player history with ratings: {e}")
        return {
            "players": [], 
            "first_bye_players": [], 
            "pre_seeded": False, 
            "player_ratings": {},
            "game_mode": None,
            "session_type": None
        }


def load_first_bye_players() -> List[str]:
    """Load the list of first bye player names from history"""
    if not PLAYER_HISTORY_FILE.exists():
        return []
    
    try:
        with open(PLAYER_HISTORY_FILE, 'r') as f:
            data = json.load(f)
            return data.get("first_bye_players", [])
    except Exception as e:
        print(f"Error loading first bye players: {e}")
        return []


def serialize_session(session) -> Dict:
    """Convert session object to JSON-serializable dictionary"""
    from python.pickleball_types import Session, Match
    
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
            "partners_played": stats.partners_played,
            "opponents_played": stats.opponents_played,
            "total_points_for": stats.total_points_for,
            "total_points_against": stats.total_points_against,
            "partner_last_game": stats.partner_last_game,
            "opponent_last_game": stats.opponent_last_game,
            "court_history": stats.court_history,
            "total_wait_time": stats.total_wait_time,
            "wait_start_time": stats.wait_start_time.isoformat() if stats.wait_start_time else None
        }
    
    # Serialize queue
    queue_data = []
    for queued_match in session.match_queue:
        queue_data.append({
            "team1": queued_match.team1,
            "team2": queued_match.team2
        })
    
    # Serialize match history snapshots
    snapshots_data = []
    for snapshot in session.match_history_snapshots:
        snapshot_data = {
            "match_id": snapshot.match_id,
            "timestamp": snapshot.timestamp.isoformat(),
            "matches": snapshot.matches,
            "waiting_players": snapshot.waiting_players,
            "player_stats": snapshot.player_stats,
            "active_players": snapshot.active_players,
            "match_queue": snapshot.match_queue,
            "player_last_court": snapshot.player_last_court,
            "court_players": snapshot.court_players,
            "courts_mixed_history": snapshot.courts_mixed_history
        }
        snapshots_data.append(snapshot_data)
    
    return {
        "session_id": session.id,
        "config": {
            "mode": session.config.mode,
            "session_type": session.config.session_type,
            "players": [{"id": p.id, "name": p.name} for p in session.config.players],
            "courts": session.config.courts,
            "banned_pairs": session.config.banned_pairs,
            "locked_teams": session.config.locked_teams,
            "first_bye_players": session.config.first_bye_players,
            "randomize_player_order": session.config.randomize_player_order
        },
        "matches": matches_data,
        "waiting_players": session.waiting_players,
        "player_stats": stats_data,
        "active_players": list(session.active_players),
        "match_queue": queue_data,
        "match_history_snapshots": snapshots_data,
        "first_bye_used": session.first_bye_used,
        "competitive_variety_roaming_range_percent": session.competitive_variety_roaming_range_percent,
        "competitive_variety_partner_repetition_limit": session.competitive_variety_partner_repetition_limit,
        "competitive_variety_opponent_repetition_limit": session.competitive_variety_opponent_repetition_limit,
        "adaptive_balance_weight": session.adaptive_balance_weight,
        "adaptive_constraints_disabled": session.adaptive_constraints_disabled,
        "session_start_time": session.session_start_time.isoformat() if session.session_start_time else None,
        "saved_at": now().isoformat()
    }


def deserialize_session(data: Dict):
    """Convert JSON-serialized dictionary back to session object"""
    from python.pickleball_types import Session, SessionConfig, Player, Match, PlayerStats, QueuedMatch
    from python.utils import generate_id
    
    # Reconstruct config
    players = [Player(id=p["id"], name=p["name"]) for p in data["config"]["players"]]
    config = SessionConfig(
        mode=data["config"]["mode"],
        session_type=data["config"]["session_type"],
        players=players,
        courts=data["config"]["courts"],
        banned_pairs=data["config"]["banned_pairs"],
        locked_teams=data["config"]["locked_teams"],
        first_bye_players=data["config"].get("first_bye_players", []),
        randomize_player_order=data["config"]["randomize_player_order"]
    )
    
    # Reconstruct player stats
    player_stats = {}
    for player_id, stats_data in data["player_stats"].items():
        # Reconstruct wait_start_time if it exists
        wait_start_time = None
        if stats_data.get("wait_start_time"):
            from datetime import datetime as dt
            wait_start_time = dt.fromisoformat(stats_data["wait_start_time"])
        
        # Handle backward compatibility for stats (Set -> Dict)
        partners_data = stats_data["partners_played"]
        if isinstance(partners_data, list):
            partners_played = {pid: 1 for pid in partners_data}
        else:
            partners_played = partners_data

        opponents_data = stats_data["opponents_played"]
        if isinstance(opponents_data, list):
            opponents_played = {pid: 1 for pid in opponents_data}
        else:
            opponents_played = opponents_data

        player_stats[player_id] = PlayerStats(
            player_id=stats_data["player_id"],
            games_played=stats_data["games_played"],
            games_waited=stats_data["games_waited"],
            wins=stats_data["wins"],
            losses=stats_data["losses"],
            partners_played=partners_played,
            opponents_played=opponents_played,
            total_points_for=stats_data["total_points_for"],
            total_points_against=stats_data["total_points_against"],
            partner_last_game=stats_data.get("partner_last_game", {}),
            opponent_last_game=stats_data.get("opponent_last_game", {}),
            court_history=stats_data.get("court_history", []),
            total_wait_time=stats_data.get("total_wait_time", 0),
            wait_start_time=wait_start_time
        )
    
    # Reconstruct matches
    matches = []
    for match_data in data["matches"]:
        start_time = None
        if match_data.get("start_time"):
            from datetime import datetime as dt
            start_time = dt.fromisoformat(match_data["start_time"])
        
        end_time = None
        if match_data.get("end_time"):
            from datetime import datetime as dt
            end_time = dt.fromisoformat(match_data["end_time"])
        
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
        matches.append(match)
    
def deserialize_session(data: Dict):
    """Convert JSON-serialized dictionary back to session object"""
    from python.pickleball_types import Session, SessionConfig, Player, Match, PlayerStats, QueuedMatch, MatchSnapshot
    from python.utils import generate_id
    
    # Reconstruct config
    players = [Player(id=p["id"], name=p["name"]) for p in data["config"]["players"]]
    config = SessionConfig(
        mode=data["config"]["mode"],
        session_type=data["config"]["session_type"],
        players=players,
        courts=data["config"]["courts"],
        banned_pairs=data["config"]["banned_pairs"],
        locked_teams=data["config"]["locked_teams"],
        first_bye_players=data["config"].get("first_bye_players", []),
        randomize_player_order=data["config"]["randomize_player_order"]
    )
    
    # Reconstruct player stats
    player_stats = {}
    for player_id, stats_data in data["player_stats"].items():
        # Reconstruct wait_start_time if it exists
        wait_start_time = None
        if stats_data.get("wait_start_time"):
            from datetime import datetime as dt
            wait_start_time = dt.fromisoformat(stats_data["wait_start_time"])
        
        # Handle backward compatibility for stats (Set -> Dict)
        partners_data = stats_data["partners_played"]
        if isinstance(partners_data, list):
            partners_played = {pid: 1 for pid in partners_data}
        else:
            partners_played = partners_data

        opponents_data = stats_data["opponents_played"]
        if isinstance(opponents_data, list):
            opponents_played = {pid: 1 for pid in opponents_data}
        else:
            opponents_played = opponents_data

        player_stats[player_id] = PlayerStats(
            player_id=stats_data["player_id"],
            games_played=stats_data["games_played"],
            games_waited=stats_data["games_waited"],
            wins=stats_data["wins"],
            losses=stats_data["losses"],
            partners_played=partners_played,
            opponents_played=opponents_played,
            total_points_for=stats_data["total_points_for"],
            total_points_against=stats_data["total_points_against"],
            partner_last_game=stats_data.get("partner_last_game", {}),
            opponent_last_game=stats_data.get("opponent_last_game", {}),
            court_history=stats_data.get("court_history", []),
            total_wait_time=stats_data.get("total_wait_time", 0),
            wait_start_time=wait_start_time
        )
    
    # Reconstruct matches
    matches = []
    for match_data in data["matches"]:
        start_time = None
        if match_data.get("start_time"):
            from datetime import datetime as dt
            start_time = dt.fromisoformat(match_data["start_time"])
        
        end_time = None
        if match_data.get("end_time"):
            from datetime import datetime as dt
            end_time = dt.fromisoformat(match_data["end_time"])
        
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
        matches.append(match)
    
    # Reconstruct match queue
    match_queue = []
    for queue_data in data["match_queue"]:
        match_queue.append(QueuedMatch(team1=queue_data["team1"], team2=queue_data["team2"]))
    
    # Reconstruct match history snapshots
    match_history_snapshots = []
    for snapshot_data in data.get("match_history_snapshots", []):
        snapshot = MatchSnapshot(
            match_id=snapshot_data["match_id"],
            timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
            matches=snapshot_data["matches"],
            waiting_players=snapshot_data["waiting_players"],
            player_stats=snapshot_data["player_stats"],
            active_players=snapshot_data["active_players"],
            match_queue=snapshot_data["match_queue"],
            player_last_court=snapshot_data.get("player_last_court", {}),
            court_players=snapshot_data.get("court_players", {}),
            courts_mixed_history=snapshot_data.get("courts_mixed_history", [])
        )
        match_history_snapshots.append(snapshot)
    
    # Create session object
    session = Session(
        id=data["session_id"],
        config=config,
        matches=matches,
        waiting_players=data["waiting_players"],
        player_stats=player_stats,
        active_players=set(data["active_players"]),
        match_queue=match_queue,
        match_history_snapshots=match_history_snapshots
    )
    
    # Load first bye state if available
    if "first_bye_used" in data:
        session.first_bye_used = data["first_bye_used"]
    
    # Load competitive variety settings if available
    if "competitive_variety_roaming_range_percent" in data:
        session.competitive_variety_roaming_range_percent = data["competitive_variety_roaming_range_percent"]
    if "competitive_variety_partner_repetition_limit" in data:
        session.competitive_variety_partner_repetition_limit = data["competitive_variety_partner_repetition_limit"]
    if "competitive_variety_opponent_repetition_limit" in data:
        session.competitive_variety_opponent_repetition_limit = data["competitive_variety_opponent_repetition_limit"]
    if "adaptive_balance_weight" in data:
        session.adaptive_balance_weight = data["adaptive_balance_weight"]
    if "adaptive_constraints_disabled" in data:
        session.adaptive_constraints_disabled = data["adaptive_constraints_disabled"]
    
    # Load session start time if available
    if "session_start_time" in data and data["session_start_time"]:
        from datetime import datetime as dt
        session.session_start_time = dt.fromisoformat(data["session_start_time"])
    
    # Store the original data for later wait time adjustment
    session._original_serialized_data = data
    
    return session


def adjust_wait_times_after_time_manager_start(session):
    """
    Adjust wait and match times after time manager has been properly started.
    This should be called after deserializing a session and starting the time manager.
    """
    if not hasattr(session, '_original_serialized_data'):
        return  # Nothing to adjust
    
    _adjust_times_for_resume(session, session._original_serialized_data)
    
    # Clean up the temporary data
    delattr(session, '_original_serialized_data')


def _adjust_times_for_resume(session, original_data):
    """
    Adjust wait start times and match start times when resuming a session to preserve durations.
    
    When a session is saved and later loaded, any active timers need to be
    adjusted to work with the new session timeline while preserving elapsed time.
    """
    from python.time_manager import get_session_start_time, now
    from datetime import datetime as dt, timedelta
    
    # Get the original session start time 
    original_session_start = None
    if "session_start_time" in original_data and original_data["session_start_time"]:
        original_session_start = dt.fromisoformat(original_data["session_start_time"])
    
    # Get the time when the session was saved (in the original timeline)
    saved_at = None
    if "saved_at" in original_data and original_data["saved_at"]:
        saved_at = dt.fromisoformat(original_data["saved_at"])
    
    # If we don't have the necessary timestamps, we can't adjust
    if original_session_start is None or saved_at is None:
        # For each player with wait_start_time, clear it to avoid negative times
        for stats in session.player_stats.values():
            if stats.wait_start_time is not None:
                stats.wait_start_time = None
        
        # For each match with start_time, clear it to avoid negative durations
        for match in session.matches:
            if match.start_time is not None and match.status in ['waiting', 'in-progress']:
                match.start_time = None
        return
    
    current_session_start = get_session_start_time()
    if current_session_start is None:
        return
    
    # Adjust each player's wait start time
    for player_id, stats in session.player_stats.items():
        if stats.wait_start_time is not None:
            # Calculate how long this player had been waiting when the session was saved
            # (in the original timeline)
            wait_duration_at_save = (saved_at - stats.wait_start_time).total_seconds()
            
            if wait_duration_at_save < 0:
                # This shouldn't happen, but if it does, clear the wait timer
                stats.wait_start_time = None
                continue
            
            # Set the wait start time in the new timeline so that the current wait 
            # duration equals the duration they had already waited when saved
            new_wait_start_time = current_session_start - timedelta(seconds=wait_duration_at_save)
            stats.wait_start_time = new_wait_start_time
    
    # Adjust match start times for active matches
    for match in session.matches:
        if (match.start_time is not None and 
            match.status in ['waiting', 'in-progress'] and
            match.end_time is None):
            
            # Calculate how long this match had been running when the session was saved
            match_duration_at_save = (saved_at - match.start_time).total_seconds()
            
            if match_duration_at_save < 0:
                # This shouldn't happen, but if it does, reset the start time
                match.start_time = current_session_start
                continue
            
            # Set the match start time in the new timeline so that the current duration
            # equals the duration it had when saved
            new_match_start_time = current_session_start - timedelta(seconds=match_duration_at_save)
            match.start_time = new_match_start_time


def save_session(session) -> bool:
    """Save session state to file"""
    ensure_session_dir()
    
    try:
        session_data = serialize_session(session)
        
        with open(LAST_SESSION_FILE, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Also update player history with first bye players (convert IDs to names)
        player_names = [p.name for p in session.config.players if p.id in session.active_players]
        bye_player_names = []
        for bye_id in session.config.first_bye_players:
            for player in session.config.players:
                if player.id == bye_id:
                    bye_player_names.append(player.name)
                    break
        save_player_history(player_names, bye_player_names)
        
        return True
    except Exception as e:
        print(f"Error saving session: {e}")
        return False


def load_last_session() -> Optional:
    """Load the last saved session state"""
    if not LAST_SESSION_FILE.exists():
        return None
    
    try:
        with open(LAST_SESSION_FILE, 'r') as f:
            data = json.load(f)
            return deserialize_session(data)
    except Exception as e:
        print(f"Error loading last session: {e}")
        return None


def has_saved_session() -> bool:
    """Check if a saved session exists"""
    return LAST_SESSION_FILE.exists()


def clear_saved_session() -> bool:
    """Clear the saved session file"""
    try:
        if LAST_SESSION_FILE.exists():
            LAST_SESSION_FILE.unlink()
        return True
    except Exception as e:
        print(f"Error clearing saved session: {e}")
        return False


def save_court_names(court_names: Dict[int, str], num_courts: int) -> bool:
    """
    Save court names to persistent storage.
    
    Args:
        court_names: Dictionary mapping court number to custom name
        num_courts: Total number of courts in session
    
    Returns:
        True if saved successfully, False otherwise
    """
    ensure_session_dir()
    
    court_data = {
        "num_courts": num_courts,
        "court_names": court_names,
        "saved_at": now().isoformat()
    }
    
    try:
        with open(COURT_NAMES_FILE, 'w') as f:
            json.dump(court_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving court names: {e}")
        return False


def load_court_names(num_courts: int) -> Dict[int, str]:
    """
    Load court names from persistent storage.
    
    Args:
        num_courts: Number of courts in current session
        
    Returns:
        Dictionary mapping court number to custom name.
        Only returns names if the court count matches.
    """
    if not COURT_NAMES_FILE.exists():
        return {}
    
    try:
        with open(COURT_NAMES_FILE, 'r') as f:
            data = json.load(f)
        
        # Only load if the number of courts matches
        if data.get("num_courts") == num_courts:
            return data.get("court_names", {})
        else:
            return {}
            
    except Exception as e:
        print(f"Error loading court names: {e}")
        return {}


def get_saved_court_name(court_number: int, num_courts: int) -> Optional[str]:
    """
    Get the saved custom name for a specific court.
    
    Args:
        court_number: The court number (1, 2, 3, etc.)
        num_courts: Total number of courts in current session
        
    Returns:
        Custom name if saved and court count matches, None otherwise
    """
    court_names = load_court_names(num_courts)
    return court_names.get(str(court_number))  # JSON keys are strings


def save_single_court_name(court_number: int, custom_name: Optional[str], num_courts: int) -> bool:
    """
    Save or update the name for a single court.
    
    Args:
        court_number: The court number (1, 2, 3, etc.) 
        custom_name: The custom name, or None to use default
        num_courts: Total number of courts in current session
        
    Returns:
        True if saved successfully, False otherwise
    """
    # Load existing court names
    court_names = load_court_names(num_courts)
    
    # Update the specific court
    if custom_name is None:
        # Remove custom name (use default)
        court_names.pop(str(court_number), None)
    else:
        # Set custom name
        court_names[str(court_number)] = custom_name
    
    # Save back to file
    return save_court_names(court_names, num_courts)
