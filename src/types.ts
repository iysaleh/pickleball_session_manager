export type Player = {
  id: string;
  name: string;
};

export type GameMode = 'king-of-court' | 'round-robin' | 'teams';

export type SessionType = 'doubles' | 'singles';

export type TeamPair = [string, string]; // player IDs

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

export type SessionConfig = {
  mode: GameMode;
  sessionType: SessionType;
  players: Player[];
  courts: number;
  bannedPairs: TeamPair[];
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
};

export type PlayerStats = {
  playerId: string;
  gamesPlayed: number;
  gamesWaited: number;
  wins: number;
  losses: number;
  partnersPlayed: Set<string>; // player IDs
  opponentsPlayed: Set<string>; // player IDs
};
