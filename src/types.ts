export type Player = {
  id: string;
  name: string;
};

export type GameMode = 'king-of-court' | 'round-robin';

export type SessionType = 'doubles' | 'singles';

export type TeamPair = [string, string]; // player IDs

export type LockedTeam = string[]; // 2 player IDs for doubles

export type Match = {
  id: string;
  courtNumber: number;
  team1: string[]; // player IDs
  team2: string[]; // player IDs
  status: 'waiting' | 'in-progress' | 'completed' | 'forfeited';
  score?: {
    team1Score: number;
    team2Score: number;
  };
  endTime?: number; // timestamp when match was completed/forfeited
};

export type KingOfCourtConfig = {
  // ELO Rating System
  baseRating: number; // Starting ELO rating for new players (default: 1500)
  kFactor: number; // ELO K-factor for rating adjustments (default: 32)
  minRating: number; // Minimum rating clamp (default: 800)
  maxRating: number; // Maximum rating clamp (default: 2200)
  
  // Provisional Player Settings
  provisionalGamesThreshold: number; // Games before player stops being provisional (default: 2)
  
  // Ranking Disparity
  rankingRangePercentage: number; // Percentage of player pool for matchmaking range (default: 0.5 = 50%)
  
  // Matchmaking Constraints
  closeRankThreshold: number; // Max rank difference for "close" matchups (default: 4)
  veryCloseRankThreshold: number; // Ideal rank difference (default: 3)
  
  // Waiting Strategy
  maxConsecutiveWaits: number; // Max waits before forcing a match (default: 1)
  minCompletedMatchesForWaiting: number; // Min completed matches before strategic waiting (default: 6)
  minBusyCourtsForWaiting: number; // Min busy courts before considering waiting (default: 2)
  
  // Repetition Control
  backToBackOverlapThreshold: number; // Max overlapping players for back-to-back (default: 3)
  recentMatchCheckCount: number; // Number of recent matches to check (default: 3)
  singleCourtLoopThreshold: number; // Times same group can play in recent history (default: 2)
  
  // Variety Optimization
  softRepetitionFrequency: number; // Target frequency for playing with same person (default: Math.floor(totalPlayers/6))
  highRepetitionThreshold: number; // Percentage threshold for high repetition (default: 0.6)
  
  // Team Assignment Penalties
  partnershipRepeatPenalty: number; // Penalty for repeated partnerships (default: 80)
  recentPartnershipPenalty: number; // Heavy penalty for recent partnerships (default: 300)
  opponentRepeatPenalty: number; // Penalty for repeated opponents (default: 25)
  recentOverlapPenalty: number; // Penalty for recent player overlap (default: 200)
  teamBalancePenalty: number; // Penalty for unbalanced teams (default: 20)
};

export type RoundRobinConfig = {
  // Currently round robin uses default random selection
  // Future: Add variety optimization settings here
};

export type AdvancedConfig = {
  kingOfCourt: KingOfCourtConfig;
  roundRobin: RoundRobinConfig;
};

export type SessionConfig = {
  mode: GameMode;
  sessionType: SessionType;
  players: Player[];
  courts: number;
  bannedPairs: TeamPair[];
  lockedTeams?: LockedTeam[]; // Optional locked teams for doubles only
  randomizePlayerOrder?: boolean; // Optional: randomize player order at session start
  advancedConfig?: AdvancedConfig; // Optional: advanced algorithm tuning
};

export type QueuedMatch = {
  team1: string[]; // player IDs
  team2: string[]; // player IDs
};

export type Session = {
  id: string;
  config: SessionConfig;
  matches: Match[];
  waitingPlayers: string[]; // player IDs
  playerStats: Map<string, PlayerStats>;
  activePlayers: Set<string>; // player IDs currently active in session
  matchQueue: QueuedMatch[]; // Pre-generated matches for round-robin
  maxQueueSize: number; // Maximum number of matches to pre-generate
  advancedConfig: AdvancedConfig; // Algorithm tuning configuration (always present with defaults)
};

export type PlayerStats = {
  playerId: string;
  gamesPlayed: number;
  gamesWaited: number;
  wins: number;
  losses: number;
  partnersPlayed: Set<string>; // player IDs
  opponentsPlayed: Set<string>; // player IDs
  totalPointsFor: number; // Total points scored
  totalPointsAgainst: number; // Total points allowed
};

export type PlayerRanking = {
  playerId: string;
  rank: number;
  wins: number;
  losses: number;
  avgPointDifferential: number; // Average point differential per game
};
