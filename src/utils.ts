import type { Player, TeamPair, PlayerStats } from './types';

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export function isPairBanned(
  player1Id: string,
  player2Id: string,
  bannedPairs: TeamPair[]
): boolean {
  return bannedPairs.some(
    ([p1, p2]) =>
      (p1 === player1Id && p2 === player2Id) ||
      (p1 === player2Id && p2 === player1Id)
  );
}

export function createPlayerStats(playerId: string): PlayerStats {
  return {
    playerId,
    gamesPlayed: 0,
    gamesWaited: 0,
    wins: 0,
    losses: 0,
    partnersPlayed: new Set(),
    opponentsPlayed: new Set(),
    totalPointsFor: 0,
    totalPointsAgainst: 0,
  };
}

export function getPlayersWithFewestGames(
  playerIds: string[],
  statsMap: Map<string, PlayerStats>
): string[] {
  if (playerIds.length === 0) return [];
  
  const minGames = Math.min(
    ...playerIds.map((id) => statsMap.get(id)?.gamesPlayed ?? 0)
  );
  
  return playerIds.filter((id) => {
    const stats = statsMap.get(id);
    return stats ? stats.gamesPlayed === minGames : true;
  });
}

export function getPlayersWhoWaitedMost(
  playerIds: string[],
  statsMap: Map<string, PlayerStats>
): string[] {
  if (playerIds.length === 0) return [];
  
  const maxWaits = Math.max(
    ...playerIds.map((id) => statsMap.get(id)?.gamesWaited ?? 0)
  );
  
  return playerIds.filter((id) => {
    const stats = statsMap.get(id);
    return stats ? stats.gamesWaited === maxWaits : true;
  });
}

export function calculatePartnerDiversity(
  player1Id: string,
  player2Id: string,
  statsMap: Map<string, PlayerStats>
): number {
  const stats1 = statsMap.get(player1Id);
  const stats2 = statsMap.get(player2Id);
  
  if (!stats1 || !stats2) return 0;
  
  const hasPlayedTogether =
    stats1.partnersPlayed.has(player2Id) || stats2.partnersPlayed.has(player1Id);
  
  return hasPlayedTogether ? -1 : 1;
}

export function calculatePlayerRankings(
  playerIds: string[],
  statsMap: Map<string, PlayerStats>
): Array<{ playerId: string; rank: number; wins: number; losses: number; avgPointDifferential: number }> {
  // Calculate rankings for players
  const playerData = playerIds
    .map(playerId => {
      const stats = statsMap.get(playerId);
      if (!stats) return null;
      
      // Calculate average point differential
      const totalGames = stats.gamesPlayed;
      const avgPointDifferential = totalGames > 0
        ? (stats.totalPointsFor - stats.totalPointsAgainst) / totalGames
        : 0;
      
      return {
        playerId,
        wins: stats.wins,
        losses: stats.losses,
        avgPointDifferential,
      };
    })
    .filter((data): data is NonNullable<typeof data> => data !== null);
  
  // Sort by wins (descending), then by average point differential (descending)
  playerData.sort((a, b) => {
    if (b.wins !== a.wins) {
      return b.wins - a.wins;
    }
    return b.avgPointDifferential - a.avgPointDifferential;
  });
  
  // Assign ranks (handle ties)
  const rankedPlayers: Array<{ playerId: string; rank: number; wins: number; losses: number; avgPointDifferential: number }> = [];
  
  for (let i = 0; i < playerData.length; i++) {
    const player = playerData[i];
    let rank = i + 1;
    
    // Check if tied with previous player
    if (i > 0) {
      const prev = rankedPlayers[i - 1];
      if (prev.wins === player.wins && prev.avgPointDifferential === player.avgPointDifferential) {
        rank = prev.rank; // Same rank as previous
      }
    }
    
    rankedPlayers.push({
      ...player,
      rank,
    });
  }
  
  return rankedPlayers;
}
