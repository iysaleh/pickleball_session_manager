import type { Player, TeamPair, Match, SessionType, PlayerStats } from './types';
import {
  generateId,
  isPairBanned,
  getPlayersWithFewestGames,
  calculatePartnerDiversity,
} from './utils';

export function selectPlayersForNextGame(
  availablePlayers: string[],
  playersPerTeam: number,
  statsMap: Map<string, PlayerStats>,
  bannedPairs: TeamPair[]
): string[] | null {
  const playersNeeded = playersPerTeam * 2;
  
  if (availablePlayers.length < playersNeeded) {
    return null;
  }
  
  // Prioritize players with fewest games
  const candidates = getPlayersWithFewestGames(availablePlayers, statsMap);
  
  // Try to find valid team combinations
  const selected = findValidTeamCombination(
    candidates.length >= playersNeeded ? candidates : availablePlayers,
    playersPerTeam,
    bannedPairs,
    statsMap
  );
  
  return selected;
}

function findValidTeamCombination(
  players: string[],
  playersPerTeam: number,
  bannedPairs: TeamPair[],
  statsMap: Map<string, PlayerStats>
): string[] | null {
  const totalPlayers = playersPerTeam * 2;
  
  // Try multiple random combinations to find a valid one
  for (let attempt = 0; attempt < 100; attempt++) {
    const shuffled = [...players].sort(() => Math.random() - 0.5);
    const selected = shuffled.slice(0, totalPlayers);
    
    const team1 = selected.slice(0, playersPerTeam);
    const team2 = selected.slice(playersPerTeam);
    
    if (isValidTeamConfiguration(team1, team2, bannedPairs)) {
      return selected;
    }
  }
  
  return null;
}

function isValidTeamConfiguration(
  team1: string[],
  team2: string[],
  bannedPairs: TeamPair[]
): boolean {
  // Check team1 for banned pairs
  for (let i = 0; i < team1.length; i++) {
    for (let j = i + 1; j < team1.length; j++) {
      if (isPairBanned(team1[i], team1[j], bannedPairs)) {
        return false;
      }
    }
  }
  
  // Check team2 for banned pairs
  for (let i = 0; i < team2.length; i++) {
    for (let j = i + 1; j < team2.length; j++) {
      if (isPairBanned(team2[i], team2[j], bannedPairs)) {
        return false;
      }
    }
  }
  
  return true;
}

export function createMatch(
  courtNumber: number,
  team1: string[],
  team2: string[],
  statsMap: Map<string, PlayerStats>
): Match {
  // Update stats
  [...team1, ...team2].forEach((playerId) => {
    const stats = statsMap.get(playerId);
    if (stats) {
      stats.gamesPlayed++;
      
      // Track partners
      const teammates = team1.includes(playerId) ? team1 : team2;
      teammates.forEach((partnerId) => {
        if (partnerId !== playerId) {
          stats.partnersPlayed.add(partnerId);
        }
      });
      
      // Track opponents
      const opponents = team1.includes(playerId) ? team2 : team1;
      opponents.forEach((opponentId) => {
        stats.opponentsPlayed.add(opponentId);
      });
    }
  });
  
  return {
    id: generateId(),
    courtNumber,
    team1,
    team2,
    status: 'waiting',
  };
}

export function generateRoundRobinMatches(
  players: Player[],
  sessionType: SessionType,
  statsMap: Map<string, PlayerStats>,
  bannedPairs: TeamPair[]
): string[][] {
  const playersPerTeam = sessionType === 'singles' ? 1 : 2;
  const playerIds = players.map((p) => p.id);
  
  // Generate all possible matchups optimizing for partner diversity
  const matches: string[][] = [];
  const usedPlayers = new Set<string>();
  
  while (usedPlayers.size < playerIds.length) {
    const available = playerIds.filter((id) => !usedPlayers.has(id));
    
    const selected = selectPlayersForNextGame(
      available,
      playersPerTeam,
      statsMap,
      bannedPairs
    );
    
    if (!selected) break;
    
    matches.push(selected);
    selected.forEach((id) => usedPlayers.add(id));
  }
  
  return matches;
}
