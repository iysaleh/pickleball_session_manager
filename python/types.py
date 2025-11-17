"""
Core data types for the Pickleball Session Manager
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Literal
from datetime import datetime

GameMode = Literal['king-of-court', 'round-robin', 'competitive-variety']
SessionType = Literal['doubles', 'singles']
MatchStatus = Literal['waiting', 'in-progress', 'completed', 'forfeited']


@dataclass
class Player:
    """Represents a player in the session"""
    id: str
    name: str


@dataclass
class PlayerStats:
    """Tracks statistics for a player"""
    player_id: str
    games_played: int = 0
    games_waited: int = 0
    wins: int = 0
    losses: int = 0
    partners_played: Set[str] = field(default_factory=set)
    opponents_played: Set[str] = field(default_factory=set)
    total_points_for: int = 0
    total_points_against: int = 0
    # For competitive variety: track game numbers when players were last played with/against
    partner_last_game: Dict[str, int] = field(default_factory=dict)  # partner_id -> last_game_number
    opponent_last_game: Dict[str, int] = field(default_factory=dict)  # opponent_id -> last_game_number
    # For inter-court mixing: track which courts this player has played on (in order)
    court_history: List[int] = field(default_factory=list)  # List of court numbers in chronological order


@dataclass
class Match:
    """Represents a single match/game"""
    id: str
    court_number: int
    team1: List[str]  # Player IDs
    team2: List[str]  # Player IDs
    status: MatchStatus
    score: Optional[Dict] = None  # {'team1_score': int, 'team2_score': int}
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class KingOfCourtConfig:
    """Configuration for King of the Court mode"""
    # ELO Rating System
    base_rating: float = 1500
    k_factor: float = 32
    min_rating: float = 800
    max_rating: float = 2200
    
    # Provisional Player Settings
    provisional_games_threshold: int = 2
    
    # Ranking Disparity
    ranking_range_percentage: float = 0.5
    
    # Matchmaking Constraints
    close_rank_threshold: int = 4
    very_close_rank_threshold: int = 3
    
    # Waiting Strategy
    max_consecutive_waits: int = 1
    min_completed_matches_for_waiting: int = 6
    min_busy_courts_for_waiting: int = 2
    
    # Repetition Control
    back_to_back_overlap_threshold: int = 3
    recent_match_check_count: int = 3
    single_court_loop_threshold: int = 2
    
    # Variety Optimization
    soft_repetition_frequency: int = 3
    high_repetition_threshold: float = 0.6
    
    # Team Assignment Penalties
    partnership_repeat_penalty: float = 80
    recent_partnership_penalty: float = 300
    opponent_repeat_penalty: float = 25
    recent_overlap_penalty: float = 200
    team_balance_penalty: float = 20


@dataclass
class RoundRobinConfig:
    """Configuration for Round Robin mode"""
    pass


@dataclass
class AdvancedConfig:
    """Advanced configuration settings"""
    king_of_court: KingOfCourtConfig = field(default_factory=KingOfCourtConfig)
    round_robin: RoundRobinConfig = field(default_factory=RoundRobinConfig)


@dataclass
class SessionConfig:
    """Configuration for a session"""
    mode: GameMode
    session_type: SessionType
    players: List[Player]
    courts: int
    banned_pairs: List[tuple] = field(default_factory=list)  # List of (player_id, player_id) tuples
    locked_teams: Optional[List[List[str]]] = None  # List of teams (each team is list of player IDs)
    randomize_player_order: bool = False
    advanced_config: Optional[AdvancedConfig] = None


@dataclass
class QueuedMatch:
    """A match queued to be played"""
    team1: List[str]  # Player IDs
    team2: List[str]  # Player IDs


@dataclass
class Session:
    """Represents a playing session"""
    id: str
    config: SessionConfig
    matches: List[Match] = field(default_factory=list)
    waiting_players: List[str] = field(default_factory=list)
    player_stats: Dict[str, PlayerStats] = field(default_factory=dict)
    active_players: Set[str] = field(default_factory=set)
    match_queue: List[QueuedMatch] = field(default_factory=list)
    max_queue_size: int = 100
    advanced_config: AdvancedConfig = field(default_factory=AdvancedConfig)
    # Competitive Variety Matchmaking tracking
    player_last_court: Dict[str, int] = field(default_factory=dict)  # player_id -> court_number
    court_players: Dict[int, List[str]] = field(default_factory=dict)  # court_number -> [player_ids]
    courts_mixed_history: Set[tuple] = field(default_factory=set)  # Set of (court_a, court_b) tuples that have mixed


@dataclass
class PlayerRanking:
    """Player ranking information"""
    player_id: str
    rank: int
    wins: int
    losses: int
    avg_point_differential: float
