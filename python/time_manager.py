"""
Centralized Time Manager for Pickleball Session Manager

This module provides relative timing functionality that persists across session saves/loads
and supports accelerated timing for testing purposes.

Key Features:
- Relative timing based on session start time, not system clock
- Persistence across session saves and loads
- Test mode acceleration (--test flag makes time run 15x faster)
- Drop-in replacement for datetime.now() calls throughout the application
"""

import time
from datetime import datetime, timedelta
from typing import Optional

class TimeManager:
    """
    Manages relative timing for the session with optional test acceleration.
    
    All times are calculated relative to a session start time, so pausing
    and resuming a session preserves all timer states exactly.
    """
    
    def __init__(self, test_mode: bool = False):
        """
        Initialize the time manager.
        
        Args:
            test_mode: If True, accelerate time by 15x for testing
        """
        self.test_mode = test_mode
        self.acceleration_factor = 15.0 if test_mode else 1.0
        
        # These track the "virtual" session time
        self._session_start_real_time: Optional[float] = None  # Real timestamp when session started
        self._session_start_virtual_time: Optional[datetime] = None  # Virtual session start time
        self._accumulated_pause_time: float = 0.0  # Real time spent paused
        self._pause_start_time: Optional[float] = None  # When current pause started
        
    def start_session(self, session_start_time: Optional[datetime] = None) -> None:
        """
        Start timing for a new session.
        
        Args:
            session_start_time: Optional fixed start time (for loading saved sessions)
        """
        current_real_time = time.time()
        
        if session_start_time is None:
            # New session - start at current time
            self._session_start_virtual_time = datetime.now()
        else:
            # Loading existing session - use provided start time
            self._session_start_virtual_time = session_start_time
            
        self._session_start_real_time = current_real_time
        self._accumulated_pause_time = 0.0
        self._pause_start_time = None
        
    def pause_session(self) -> None:
        """Pause the session timer."""
        if self._pause_start_time is None:
            self._pause_start_time = time.time()
    
    def resume_session(self) -> None:
        """Resume the session timer."""
        if self._pause_start_time is not None:
            pause_duration = time.time() - self._pause_start_time
            self._accumulated_pause_time += pause_duration
            self._pause_start_time = None
    
    def get_current_session_time(self) -> datetime:
        """
        Get the current virtual time within the session.
        
        This is the main function used throughout the app as a replacement
        for datetime.now().
        
        Returns:
            Current virtual session time
        """
        if self._session_start_real_time is None or self._session_start_virtual_time is None:
            # No session started - fall back to system time
            return datetime.now()
        
        current_real_time = time.time()
        
        # Calculate actual elapsed real time
        current_pause_time = 0.0
        if self._pause_start_time is not None:
            current_pause_time = current_real_time - self._pause_start_time
            
        total_pause_time = self._accumulated_pause_time + current_pause_time
        active_real_time = current_real_time - self._session_start_real_time - total_pause_time
        
        # Apply acceleration factor for test mode
        virtual_elapsed_seconds = active_real_time * self.acceleration_factor
        
        # Calculate virtual session time
        virtual_time = self._session_start_virtual_time + timedelta(seconds=virtual_elapsed_seconds)
        
        return virtual_time
    
    def get_session_start_time(self) -> Optional[datetime]:
        """Get the virtual start time of the current session."""
        return self._session_start_virtual_time
    
    def get_elapsed_session_time(self) -> timedelta:
        """Get the total virtual time elapsed since session start."""
        if self._session_start_virtual_time is None:
            return timedelta(0)
        
        current_time = self.get_current_session_time()
        return current_time - self._session_start_virtual_time
    
    def is_session_active(self) -> bool:
        """Check if a session is currently active."""
        return self._session_start_real_time is not None
    
    def is_paused(self) -> bool:
        """Check if the session is currently paused."""
        return self._pause_start_time is not None


# Global time manager instance
_time_manager: Optional[TimeManager] = None


def initialize_time_manager(test_mode: bool = False) -> TimeManager:
    """
    Initialize the global time manager.
    
    Args:
        test_mode: If True, enable 15x acceleration for testing
        
    Returns:
        The initialized TimeManager instance
    """
    global _time_manager
    _time_manager = TimeManager(test_mode=test_mode)
    return _time_manager


def get_time_manager() -> TimeManager:
    """
    Get the global time manager instance.
    
    Returns:
        The global TimeManager instance
        
    Raises:
        RuntimeError: If time manager hasn't been initialized
    """
    if _time_manager is None:
        raise RuntimeError("Time manager not initialized. Call initialize_time_manager() first.")
    return _time_manager


def now() -> datetime:
    """
    Get the current session time.
    
    This is the main function used as a drop-in replacement for datetime.now()
    throughout the application.
    
    Returns:
        Current virtual session time
    """
    try:
        return get_time_manager().get_current_session_time()
    except RuntimeError:
        # Fallback to system time if time manager not initialized
        return datetime.now()


def start_session(session_start_time: Optional[datetime] = None) -> None:
    """
    Start timing for a new session.
    
    Args:
        session_start_time: Optional fixed start time (for loading saved sessions)
    """
    get_time_manager().start_session(session_start_time)


def pause_session() -> None:
    """Pause the session timer."""
    get_time_manager().pause_session()


def resume_session() -> None:
    """Resume the session timer.""" 
    get_time_manager().resume_session()


def get_session_start_time() -> Optional[datetime]:
    """Get the virtual start time of the current session."""
    return get_time_manager().get_session_start_time()


def get_elapsed_session_time() -> timedelta:
    """Get the total virtual time elapsed since session start."""
    return get_time_manager().get_elapsed_session_time()