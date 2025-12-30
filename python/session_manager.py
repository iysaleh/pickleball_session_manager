#!/usr/bin/env python3

"""
Session Manager Service - Clean separation of business logic from GUI

This module provides the core session management API that the GUI delegates to.
All session advancement, match creation, and game mode logic is centralized here
for better testability and maintainability.

Key Principles:
- GUI is a thin presentation layer
- All business logic is testable in isolation  
- Clear separation of concerns
- Single responsibility for each service
"""

from typing import Dict, List, Tuple, Optional, Callable
from python.pickleball_types import Session, Match, Player
from python.session import evaluate_and_create_matches, complete_match, forfeit_match
from python.time_manager import now


class SessionEventHandler:
    """
    Centralized session event handler that manages all session state changes.
    
    This replaces the scattered GUI logic with a clean, testable service interface.
    The GUI only calls methods on this class and listens to callbacks.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.event_listeners: Dict[str, List[Callable]] = {
            'session_updated': [],
            'matches_changed': [],
            'court_populated': [],
            'match_completed': [],
            'match_forfeited': [],
            'round_advanced': [],
            'player_added': [],
            'player_removed': [],
            'waitlist_changed': []
        }
    
    def add_event_listener(self, event_type: str, callback: Callable):
        """Add a callback for specific session events"""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)
    
    def _emit_event(self, event_type: str, *args, **kwargs):
        """Emit an event to all registered listeners"""
        if event_type in self.event_listeners:
            for callback in self.event_listeners[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Warning: Event callback failed: {e}")
    
    def handle_match_completion(self, match_id: str, team1_score: int, team2_score: int) -> Tuple[bool, List]:
        """
        Handle match completion and all downstream effects.
        
        Returns:
            Tuple of (success, court_slides)
        """
        success, slides = complete_match(self.session, match_id, team1_score, team2_score)
        
        if success:
            self._emit_event('match_completed', match_id, team1_score, team2_score)
            
            # Trigger session evaluation and advancement
            self._evaluate_and_advance_session()
            
            self._emit_event('session_updated')
        
        return success, slides
    
    def handle_match_forfeit(self, match_id: str) -> bool:
        """
        Handle match forfeit and all downstream effects.
        
        Returns:
            Success status
        """
        success = forfeit_match(self.session, match_id)
        
        if success:
            self._emit_event('match_forfeited', match_id)
            
            # Trigger session evaluation and advancement
            self._evaluate_and_advance_session()
            
            self._emit_event('session_updated')
        
        return success
    
    def handle_player_addition(self, players: List[Player]):
        """
        Handle player addition and session re-evaluation.
        """
        for player in players:
            if player.id not in [p.id for p in self.session.config.players]:
                self.session.config.players.append(player)
                self.session.active_players.add(player.id)
        
        self._emit_event('player_added', players)
        
        # Re-evaluate session with new players
        self._evaluate_and_advance_session()
        
        self._emit_event('session_updated')
    
    def handle_player_removal(self, player_ids: List[str]):
        """
        Handle player removal and session re-evaluation.
        """
        for player_id in player_ids:
            # Remove from active players
            if player_id in self.session.active_players:
                self.session.active_players.remove(player_id)
            
            # Remove from waitlist if present
            if player_id in self.session.waiting_players:
                self.session.waiting_players.remove(player_id)
        
        self._emit_event('player_removed', player_ids)
        
        # Re-evaluate session after player removal
        self._evaluate_and_advance_session()
        
        self._emit_event('session_updated')
    
    def handle_settings_change(self, setting_type: str, **kwargs):
        """
        Handle various settings changes that require session re-evaluation.
        
        Args:
            setting_type: Type of setting change ('variety', 'balance', 'adaptive', etc.)
            **kwargs: Setting-specific parameters
        """
        if setting_type == 'variety':
            # Update roaming range as variety proxy
            self.session.competitive_variety_roaming_range_percent = kwargs.get('value', self.session.competitive_variety_roaming_range_percent)
            
        elif setting_type == 'balance':
            # Update adaptive balance weight as balance proxy
            if 'value' in kwargs:
                self.session.adaptive_balance_weight = kwargs['value']
            
        elif setting_type == 'adaptive':
            if 'enabled' in kwargs:
                self.session.adaptive_constraints_disabled = not kwargs['enabled']
            if 'weight' in kwargs:
                self.session.adaptive_balance_weight = kwargs.get('weight')
                
        elif setting_type == 'court_ordering' and self.session.config.mode == 'king-of-court':
            court_ordering = kwargs.get('ordering', [])
            if self.session.config.king_of_court_config:
                self.session.config.king_of_court_config.court_ordering = court_ordering
        
        # Re-evaluate session with new settings
        self._evaluate_and_advance_session()
        
        self._emit_event('session_updated')
    
    def handle_manual_match_creation(self, court_number: int, team1: List[str], team2: List[str]):
        """
        Handle manual match creation by user.
        """
        match = Match(
            id=self._generate_match_id(),
            court_number=court_number,
            team1=team1,
            team2=team2,
            status='waiting',
            start_time=now()
        )
        
        self.session.matches.append(match)
        
        # Update player positions
        for player_id in team1 + team2:
            if player_id in self.session.waiting_players:
                self.session.waiting_players.remove(player_id)
        
        self._emit_event('matches_changed')
        self._emit_event('session_updated')
    
    def force_session_evaluation(self):
        """
        Force a session evaluation without any specific trigger.
        Used for GUI refreshes, slider movements, etc.
        """
        self._evaluate_and_advance_session()
        self._emit_event('session_updated')
    
    def _evaluate_and_advance_session(self):
        """
        Internal method to evaluate session and advance if needed.
        This encapsulates the core session advancement logic.
        """
        try:
            evaluate_and_create_matches(self.session)
            self._emit_event('matches_changed')
        except Exception as e:
            print(f"Session evaluation failed: {e}")
            # Could emit error event here
    
    def _generate_match_id(self) -> str:
        """Generate unique match ID"""
        from python.utils import generate_id
        return generate_id()
    
    def get_session(self) -> Session:
        """Get current session state (read-only access for GUI)"""
        return self.session
    
    def get_session_summary(self) -> Dict:
        """Get session summary for display purposes"""
        from python.queue_manager import get_session_summary
        return get_session_summary(self.session)
    
    def get_waiting_players(self) -> List[str]:
        """Get current waiting players for display"""
        from python.queue_manager import get_waiting_players
        return get_waiting_players(self.session)
    
    def get_match_for_court(self, court_number: int) -> Optional[Match]:
        """Get current match for a specific court"""
        from python.queue_manager import get_match_for_court
        return get_match_for_court(self.session, court_number)


def create_session_manager(session: Session) -> SessionEventHandler:
    """
    Factory function to create a session manager for the given session.
    
    This is the main entry point for creating session management services.
    """
    return SessionEventHandler(session)