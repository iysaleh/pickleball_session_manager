"""
Core data types for the Pickleball Session Manager
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional, Literal, Any
from datetime import datetime

GameMode = Literal['king-of-court', 'round-robin', 'competitive-variety', 'competitive-round-robin', 'continuous-wave-flow']
SessionType = Literal['doubles', 'singles']
MatchStatus = Literal['waiting', 'in-progress', 'completed', 'forfeited']


@dataclass
class Player:
    """Represents a player in the session"""
    id: str
    name: str
    skill_rating: Optional[float] = None  # Pre-seeded skill rating (3.0, 3.25, 3.5, etc.)


@dataclass
class PlayerStats:
    """Tracks statistics for a player"""
    player_id: str
    games_played: int = 0
    games_waited: int = 0
    wins: int = 0
    losses: int = 0
    partners_played: Dict[str, int] = field(default_factory=dict)
    opponents_played: Dict[str, int] = field(default_factory=dict)
    total_points_for: int = 0
    total_points_against: int = 0
    # For competitive variety: track game numbers when players were last played with/against
    partner_last_game: Dict[str, int] = field(default_factory=dict)  # partner_id -> last_game_number
    opponent_last_game: Dict[str, int] = field(default_factory=dict)  # opponent_id -> last_game_number
    # For inter-court mixing: track which courts this player has played on (in order)
    court_history: List[int] = field(default_factory=list)  # List of court numbers in chronological order
    # Wait time tracking: when player entered waitlist (for current wait session)
    wait_start_time: Optional[datetime] = None
    # Total accumulated wait time in seconds
    total_wait_time: int = 0


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


KingOfCourtSeeding = Literal['random', 'highest_to_lowest', 'lowest_to_highest']


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
    
    # Rounds-based King of Court settings
    seeding_option: KingOfCourtSeeding = 'random'
    court_ordering: List[int] = field(default_factory=list)  # Court numbers in order from kings court to bottom court


@dataclass
class RoundRobinConfig:
    """Configuration for Round Robin mode"""
    pass


# Approval status for scheduled matches in Competitive Round Robin
ScheduledMatchStatus = Literal['pending', 'approved', 'rejected']


@dataclass
class ScheduledMatch:
    """
    A scheduled match in Competitive Round Robin mode.
    Tracks approval status for human-in-the-loop validation.
    """
    id: str
    team1: List[str]  # Player IDs
    team2: List[str]  # Player IDs
    status: ScheduledMatchStatus = 'pending'
    match_number: int = 0  # Position in scheduled order (1-indexed)
    balance_score: float = 0.0  # How well-balanced the teams are (higher = better)
    round_number: int = 0  # Round this match belongs to (0-indexed)
    
    def get_all_players(self) -> List[str]:
        """Return all 4 player IDs in this match"""
        return self.team1 + self.team2


@dataclass 
class CompetitiveRoundRobinConfig:
    """
    Configuration for Competitive Round Robin mode.
    
    This is a rounds-based mode where:
    - ALL matches for the session are pre-scheduled before starting
    - Each round, all courts play simultaneously
    - Courts do NOT populate until ALL courts finish
    - Fair waitlist rotation: nobody waits twice before everyone waits once
    - Admin can view/edit who waits in each round via Manage Matches UI
    """
    games_per_player: int = 8  # Target games per player
    num_rounds: int = 0  # Number of rounds to generate (0 = auto-calculate)
    max_partner_repeats: int = 0  # Maximum times to play with same partner (0 = never repeat)
    max_opponent_pair_repeats: int = 0  # Maximum times to face same opponent pair (0 = never repeat)
    max_individual_opponent_repeats: int = 2  # Maximum times to face same individual
    scheduled_matches: List[ScheduledMatch] = field(default_factory=list)  # Pre-approved matches
    scheduled_waiters: List[List[str]] = field(default_factory=list)  # Players waiting each round (List[round_index] -> List[player_ids])
    schedule_finalized: bool = False  # True when user has approved enough matches
    current_round: int = 0  # Current round number during play (0-indexed)


@dataclass
class ContinuousWaveFlowConfig:
    """
    Configuration for Continuous Wave Flow mode.
    
    This is a continuous mode where:
    - Only the FIRST round is pre-scheduled in Manage Matches
    - New matches are generated dynamically as each court finishes
    - Prioritizes players who have waited longest
    - Aims for best balance among selected players
    - Soft variety constraints (don't block matches)
    - Always swaps at least 2 players between matches
    """
    games_per_player: int = 8  # Target games per player (for first round scheduling)
    max_partner_repeats: int = 0  # Soft limit - try to avoid but don't block
    max_opponent_pair_repeats: int = 0  # Soft limit - try to avoid but don't block
    max_individual_opponent_repeats: int = 3  # Soft limit - try to avoid but don't block
    scheduled_matches: List[ScheduledMatch] = field(default_factory=list)  # First round matches only
    schedule_finalized: bool = False  # True when first round approved
    min_waitlist_warning_threshold: int = 2  # Warn if waitlist < this


@dataclass
class AdvancedConfig:
    """Advanced configuration settings"""
    king_of_court: KingOfCourtConfig = field(default_factory=KingOfCourtConfig)
    round_robin: RoundRobinConfig = field(default_factory=RoundRobinConfig)
    competitive_round_robin: CompetitiveRoundRobinConfig = field(default_factory=CompetitiveRoundRobinConfig)
    
    # Deterministic waitlist predictions
    waitlist_predictions: List[Any] = field(default_factory=list)  # WaitlistPrediction objects


@dataclass
class SessionConfig:
    """Configuration for a session"""
    mode: GameMode
    session_type: SessionType
    players: List[Player]
    courts: int
    banned_pairs: List[tuple] = field(default_factory=list)  # List of (player_id, player_id) tuples
    locked_teams: Optional[List[List[str]]] = None  # List of teams (each team is list of player IDs)
    first_bye_players: List[str] = field(default_factory=list)  # List of player IDs to sit out first match
    court_sliding_mode: Literal['None', 'Right to Left', 'Left to Right'] = 'Right to Left'
    randomize_player_order: bool = False
    advanced_config: Optional[AdvancedConfig] = None
    pre_seeded_ratings: bool = False  # Whether skill ratings were pre-seeded
    king_of_court_config: Optional[KingOfCourtConfig] = None  # King of Court specific settings
    competitive_round_robin_config: Optional[CompetitiveRoundRobinConfig] = None  # Competitive Round Robin settings
    continuous_wave_flow_config: Optional['ContinuousWaveFlowConfig'] = None  # Continuous Wave Flow settings


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
    # Match history snapshots for loading previous states
    match_history_snapshots: List['MatchSnapshot'] = field(default_factory=list)
    # Competitive Variety Settings
    competitive_variety_roaming_range_percent: float = 0.5  # Roaming range as percentage (0.35-1.0)
    competitive_variety_partner_repetition_limit: int = 3  # Games to wait before playing with same partner
    competitive_variety_opponent_repetition_limit: int = 2  # Games to wait before playing against same opponent
    adaptive_balance_weight: Optional[float] = None  # Manual override for adaptive balance weight (None = auto)
    adaptive_constraints_disabled: bool = False  # When True, adaptive constraints are completely disabled
    # First bye players (to sit out the first match)
    first_bye_used: bool = False  # Flag indicating if first bye players have been applied
    # Session timing
    session_start_time: Optional[datetime] = None  # When the session actually started playing
    # King of Court specific tracking
    king_of_court_round_number: int = 0  # Current round number
    king_of_court_player_positions: Dict[str, int] = field(default_factory=dict)  # player_id -> court_number where they last played
    king_of_court_wait_counts: Dict[str, int] = field(default_factory=dict)  # player_id -> number of times they've waited
    king_of_court_waitlist_history: List[str] = field(default_factory=list)  # ordered list of players who have waited (first = longest ago)
    king_of_court_waitlist_rotation_index: int = 0  # current position in waitlist history for fair rotation


@dataclass
class MatchSnapshot:
    """A snapshot of session state right before a match was completed"""
    match_id: str
    timestamp: datetime
    # Complete copy of the session state before this match was completed
    matches: List[Dict]  # Serialized matches
    waiting_players: List[str]
    player_stats: Dict  # Serialized player stats
    active_players: List[str]
    match_queue: List[Dict]  # Serialized queue
    player_last_court: Dict[str, int]
    court_players: Dict[int, List[str]]
    courts_mixed_history: List[tuple]


@dataclass
class PlayerRanking:
    """Player ranking information"""
    player_id: str
    rank: int
    wins: int
    losses: int
    avg_point_differential: float
