"""
Session persistence - save and load session state to/from files
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

# Session files locations
SESSIONS_DIR = Path.home() / ".pickleball"
LAST_SESSION_FILE = SESSIONS_DIR / "last_session.json"
PLAYER_HISTORY_FILE = SESSIONS_DIR / "player_history.json"


def ensure_session_dir():
    """Ensure the session directory exists"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_player_history(player_names: List[str], locked_teams: Optional[List[List[str]]] = None, banned_pairs: Optional[List[List[str]]] = None):
    """Save the list of player names and team configurations to history"""
    ensure_session_dir()
    
    # Remove duplicates while preserving order
    seen = set()
    unique_players = []
    for name in player_names:
        if name not in seen:
            unique_players.append(name)
            seen.add(name)
    
    history_data = {
        "players": unique_players,
        "locked_teams": locked_teams or [],
        "banned_pairs": banned_pairs or [],
        "last_updated": datetime.now().isoformat()
    }
    
    try:
        with open(PLAYER_HISTORY_FILE, 'w') as f:
            json.dump(history_data, f, indent=2)
    except Exception as e:
        print(f"Error saving player history: {e}")


def load_player_history() -> Dict:
    """Load the list of player names and configurations from history"""
    if not PLAYER_HISTORY_FILE.exists():
        return {"players": [], "locked_teams": [], "banned_pairs": []}
    
    try:
        with open(PLAYER_HISTORY_FILE, 'r') as f:
            data = json.load(f)
            
            # Backward compatibility - if file is a list (very old format)
            if isinstance(data, list):
                return {"players": data, "locked_teams": [], "banned_pairs": []}
            
            # If data is a dict (standard format)
            return {
                "players": data.get("players", []),
                "locked_teams": data.get("locked_teams", []),
                "banned_pairs": data.get("banned_pairs", [])
            }
    except Exception as e:
        print(f"Error loading player history: {e}")
        return {"players": [], "locked_teams": [], "banned_pairs": []}


def serialize_session(session) -> Dict:
    """Convert session object to JSON-serializable dictionary"""
    from python.types import Session, Match
    
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
    
    return {
        "session_id": session.id,
        "config": {
            "mode": session.config.mode,
            "session_type": session.config.session_type,
            "players": [{"id": p.id, "name": p.name} for p in session.config.players],
            "courts": session.config.courts,
            "banned_pairs": session.config.banned_pairs,
            "locked_teams": session.config.locked_teams,
            "randomize_player_order": session.config.randomize_player_order
        },
        "matches": matches_data,
        "waiting_players": session.waiting_players,
        "player_stats": stats_data,
        "active_players": list(session.active_players),
        "match_queue": queue_data,
        "saved_at": datetime.now().isoformat()
    }


def deserialize_session(data: Dict):
    """Convert JSON-serialized dictionary back to session object"""
    from python.types import Session, SessionConfig, Player, Match, PlayerStats, QueuedMatch
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
    
    # Create session object
    session = Session(
        id=data["session_id"],
        config=config,
        matches=matches,
        waiting_players=data["waiting_players"],
        player_stats=player_stats,
        active_players=set(data["active_players"]),
        match_queue=match_queue
    )
    
    return session


def save_session(session) -> bool:
    """Save session state to file"""
    ensure_session_dir()
    
    try:
        session_data = serialize_session(session)
        
        with open(LAST_SESSION_FILE, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Also update player history
        player_names = [p.name for p in session.config.players if p.id in session.active_players]
        
        # Convert locked_teams (IDs) to names
        locked_teams_names = []
        if session.config.locked_teams:
            for team in session.config.locked_teams:
                team_names = []
                for pid in team:
                    name = next((p.name for p in session.config.players if p.id == pid), None)
                    if name:
                        team_names.append(name)
                if team_names:
                    locked_teams_names.append(team_names)
                    
        # Convert banned_pairs (IDs) to names
        banned_pairs_names = []
        if session.config.banned_pairs:
             for pair in session.config.banned_pairs:
                 pair_names = []
                 for pid in pair:
                     name = next((p.name for p in session.config.players if p.id == pid), None)
                     if name:
                         pair_names.append(name)
                 if len(pair_names) == 2:
                     banned_pairs_names.append(pair_names)
        
        save_player_history(player_names, locked_teams_names, banned_pairs_names)
        
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
