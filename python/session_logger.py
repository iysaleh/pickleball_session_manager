"""
Session Logger - per-session log file for debugging and auditing.

Creates a uniquely-named log file for each session that records every user
action and system action with timestamps flushed immediately to disk.
"""

import logging
import os
from datetime import datetime
from typing import Optional, List


_session_logger: Optional['SessionLogger'] = None


class SessionLogger:
    """Manages a per-session log file with immediate flush."""
    
    def __init__(self, log_dir: str = '.'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = os.path.join(log_dir, f'pickleball_log_{timestamp}.log')
        
        self._logger = logging.getLogger(f'pickleball_session_{timestamp}')
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        
        # Remove any existing handlers
        self._logger.handlers.clear()
        
        handler = logging.FileHandler(self.filename, mode='w', encoding='utf-8')
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(handler)
        
        self._handler = handler
    
    def _ts(self) -> str:
        """Get formatted timestamp for log entries."""
        try:
            from python.time_manager import now
            return now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _write(self, message: str):
        """Write a log entry and flush immediately."""
        self._logger.info(f'[{self._ts()}] {message}')
        self._handler.flush()
    
    def log(self, message: str):
        """Write a generic log entry."""
        self._write(message)
    
    # --- Session lifecycle ---
    
    def log_session_started(self, mode: str, num_players: int, num_courts: int, player_names: List[str]):
        self._write(f'SESSION STARTED | Mode: {mode} | Players: {num_players} | Courts: {num_courts}')
        self._write(f'PLAYER ROSTER | {", ".join(player_names)}')
    
    def log_session_ended(self):
        self._write('SESSION ENDED')
    
    # --- Match lifecycle ---
    
    def log_match_scheduled(self, match_id: str, court: int, team1_names: List[str], team2_names: List[str]):
        t1 = ', '.join(team1_names)
        t2 = ', '.join(team2_names)
        self._write(f'MATCH SCHEDULED | Match {match_id} on Court {court} | {t1} vs {t2}')
    
    def log_match_queued(self, match_id: str, team1_names: List[str], team2_names: List[str]):
        t1 = ', '.join(team1_names)
        t2 = ', '.join(team2_names)
        self._write(f'MATCH QUEUED | Match {match_id} | {t1} vs {t2}')
    
    def log_score_input(self, match_id: str, team1_score: int, team2_score: int):
        self._write(f'SCORE INPUT | Match {match_id} | User entered: {team1_score}-{team2_score}')
    
    def log_match_completed(self, match_id: str, team1_names: List[str], team2_names: List[str],
                            team1_score: int, team2_score: int):
        t1 = ', '.join(team1_names)
        t2 = ', '.join(team2_names)
        if team1_score > team2_score:
            self._write(f'MATCH COMPLETED | Match {match_id} | {t1} ({team1_score}) def. {t2} ({team2_score})')
        else:
            self._write(f'MATCH COMPLETED | Match {match_id} | {t2} ({team2_score}) def. {t1} ({team1_score})')
    
    def log_match_forfeited(self, match_id: str, team1_names: List[str], team2_names: List[str]):
        t1 = ', '.join(team1_names)
        t2 = ', '.join(team2_names)
        self._write(f'MATCH FORFEITED | Match {match_id} | {t1} vs {t2}')
    
    def log_manual_match_created(self, court: int, team1_names: List[str], team2_names: List[str]):
        t1 = ', '.join(team1_names)
        t2 = ', '.join(team2_names)
        self._write(f'MANUAL MATCH CREATED | Court {court} | {t1} vs {t2}')
    
    def log_court_slide(self, match_id: str, from_court: int, to_court: int):
        self._write(f'COURT SLIDE | Match {match_id} slid from Court {from_court} to Court {to_court}')
    
    # --- Player management ---
    
    def log_player_added(self, player_name: str):
        self._write(f'PLAYER ADDED | {player_name}')
    
    def log_player_removed(self, player_name: str):
        self._write(f'PLAYER REMOVED | {player_name}')
    
    def log_first_bye_changed(self, player_names: List[str]):
        names = ', '.join(player_names) if player_names else '(none)'
        self._write(f'FIRST BYE CHANGED | {names}')
    
    # --- Settings ---
    
    def log_slider_changed(self, slider_name: str, old_value, new_value):
        self._write(f'SLIDER CHANGED | {slider_name}: {old_value} → {new_value}')
    
    def log_court_ordering_changed(self, new_ordering: list):
        self._write(f'COURT ORDERING CHANGED | {new_ordering}')
    
    def log_locked_team(self, player1_name: str, player2_name: str):
        self._write(f'LOCKED TEAM | {player1_name} + {player2_name}')
    
    def log_banned_pair(self, player1_name: str, player2_name: str):
        self._write(f'BANNED PAIR | {player1_name} + {player2_name}')
    
    # --- Round robin / King of Court ---
    
    def log_round_advanced(self, round_number: int, mode: str):
        self._write(f'ROUND ADVANCED | {mode} Round {round_number}')
    
    def log_schedule_generated(self, num_matches: int):
        self._write(f'SCHEDULE GENERATED | {num_matches} matches')
    
    # --- Export ---
    
    def log_export(self, filename: str):
        self._write(f'EXPORT | Saved to {filename}')
    
    def close(self):
        """Close the log file handler."""
        self._handler.flush()
        self._handler.close()
        self._logger.removeHandler(self._handler)


def initialize_session_logger(log_dir: str = '.') -> SessionLogger:
    """Initialize the global session logger. Returns the logger instance."""
    global _session_logger
    # Close previous logger if exists
    if _session_logger is not None:
        try:
            _session_logger.close()
        except Exception:
            pass
    _session_logger = SessionLogger(log_dir)
    return _session_logger


def get_session_logger() -> Optional[SessionLogger]:
    """Get the global session logger, or None if not initialized."""
    return _session_logger


def session_log(message: str):
    """Convenience: write a log entry if logger is initialized."""
    if _session_logger is not None:
        _session_logger.log(message)
