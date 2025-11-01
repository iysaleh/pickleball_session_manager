import type { Player, Session, Match, PlayerStats, LockedTeam } from './types';
import { generateId, isPairBanned } from './utils';

/**
 * King of the Court scheduling algorithm
 * 
 * Goals:
 * 1. Equal play time - everyone gets roughly same number of games
 * 2. Minimize idle times - no one waits too many consecutive rounds
 * 3. Maximize opponent variety - face different people
 * 4. Maximize partner diversity (doubles) - partner with different people
 * 5. Winners move up, losers move down (with some flexibility)
 * 6. High win-rate players tend to face each other
 * 7. Deterministic given same results
 */



/**
 * Generate next round of matches for King of the Court
 */
export function generateKingOfCourtRound(
  session: Session
): Match[] {
  const { config, playerStats, activePlayers, matches } = session;
  const { courts, sessionType, bannedPairs, lockedTeams } = config;
  const playersPerTeam = sessionType === 'singles' ? 1 : 2;
  const playersPerMatch = playersPerTeam * 2;
  
  // If locked teams mode, use special logic
  if (lockedTeams && lockedTeams.length > 0) {
    return generateLockedTeamsKingOfCourtRound(session);
  }
  
  const activePlayerIds = Array.from(activePlayers);
  
  if (activePlayerIds.length < playersPerMatch) {
    return [];
  }
  
  // Sort all active players by priority: who needs to play most
  const sortedPlayers = sortPlayersByPriority(activePlayerIds, playerStats, matches);
  
  // Assign players to courts sequentially
  const newMatches: Match[] = [];
  const usedPlayers = new Set<string>();
  
  for (let courtNum = 1; courtNum <= courts; courtNum++) {
    // Get next available players
    const availablePlayers = sortedPlayers.filter(id => !usedPlayers.has(id));
    
    if (availablePlayers.length < playersPerMatch) {
      break; // Not enough players for another court
    }
    
    // Take first playersPerMatch players (highest priority)
    const selectedPlayers = availablePlayers.slice(0, playersPerMatch);
    
    // Divide into teams
    const teamAssignment = assignTeams(
      selectedPlayers,
      playersPerTeam,
      playerStats,
      matches,
      bannedPairs
    );
    
    if (!teamAssignment) {
      break;
    }
    
    const match = createKingOfCourtMatch(
      courtNum,
      teamAssignment.team1,
      teamAssignment.team2,
      playerStats
    );
    
    newMatches.push(match);
    
    // Mark these players as used
    selectedPlayers.forEach(id => usedPlayers.add(id));
  }
  
  return newMatches;
}

/**
 * Sort players by who needs to play most urgently
 */
function sortPlayersByPriority(
  playerIds: string[],
  playerStats: Map<string, PlayerStats>,
  matches: Match[]
): string[] {
  // Count consecutive waits for each player
  const consecutiveWaits = countConsecutiveWaits(playerIds, matches);
  
  return [...playerIds].sort((a, b) => {
    const statsA = playerStats.get(a)!;
    const statsB = playerStats.get(b)!;
    const waitsA = consecutiveWaits.get(a) || 0;
    const waitsB = consecutiveWaits.get(b) || 0;
    
    // 1. Prioritize by consecutive waits (higher = more priority)
    if (waitsA !== waitsB) {
      return waitsB - waitsA;
    }
    
    // 2. Prioritize by total games waited (higher = more priority)
    if (statsA.gamesWaited !== statsB.gamesWaited) {
      return statsB.gamesWaited - statsA.gamesWaited;
    }
    
    // 3. Prioritize by games played (lower = more priority)
    return statsA.gamesPlayed - statsB.gamesPlayed;
  });
}

/**
 * Count consecutive waits for each player from most recent round
 */
function countConsecutiveWaits(
  playerIds: string[],
  matches: Match[]
): Map<string, number> {
  const waits = new Map<string, number>();
  playerIds.forEach(id => waits.set(id, 0));
  
  const completedMatches = matches.filter(m => m.status === 'completed').reverse();
  const rounds = getLastNRounds(completedMatches, 10);
  
  // Count consecutive waits from most recent round backwards
  for (let roundIndex = 0; roundIndex < rounds.length; roundIndex++) {
    const round = rounds[roundIndex];
    const playersInRound = new Set<string>();
    
    round.forEach(match => {
      [...match.team1, ...match.team2].forEach(id => playersInRound.add(id));
    });
    
    // Update consecutive waits
    playerIds.forEach(id => {
      const currentWaits = waits.get(id)!;
      // Only count if they've been waiting consecutively
      if (currentWaits === roundIndex && !playersInRound.has(id)) {
        waits.set(id, currentWaits + 1);
      }
    });
  }
  
  return waits;
}

/**
 * Assign players to teams, trying to maximize variety and balance
 */
function assignTeams(
  players: string[],
  playersPerTeam: number,
  playerStats: Map<string, PlayerStats>,
  matches: Match[],
  bannedPairs: [string, string][]
): { team1: string[]; team2: string[] } | null {
  if (playersPerTeam === 1) {
    // Singles: simple 1v1
    return {
      team1: [players[0]],
      team2: [players[1]],
    };
  }
  
  // Doubles: try different configurations
  const recentPartnerships = getRecentPartnerships(players, matches, 1);
  const recentOpponents = getRecentOpponents(players, matches, 2);
  
  const configurations: Array<{ team1: string[]; team2: string[] }> = [
    { team1: [players[0], players[1]], team2: [players[2], players[3]] },
    { team1: [players[0], players[2]], team2: [players[1], players[3]] },
    { team1: [players[0], players[3]], team2: [players[1], players[2]] },
  ];
  
  let bestConfig: { team1: string[]; team2: string[]; score: number } | null = null;
  
  for (const config of configurations) {
    if (!isValidTeamConfiguration(config.team1, config.team2, bannedPairs)) {
      continue;
    }
    
    let score = 0;
    
    // Penalize recent partnerships
    if (recentPartnerships.has(`${config.team1[0]}-${config.team1[1]}`)) {
      score += 100;
    }
    if (recentPartnerships.has(`${config.team2[0]}-${config.team2[1]}`)) {
      score += 100;
    }
    
    // Penalize recent opponents
    for (const p1 of config.team1) {
      for (const p2 of config.team2) {
        if (recentOpponents.has(`${p1}-${p2}`) || recentOpponents.has(`${p2}-${p1}`)) {
          score += 30;
        }
      }
    }
    
    // Prefer balanced teams (similar win rates)
    const team1WinRate = config.team1.reduce((sum, id) => {
      const stats = playerStats.get(id)!;
      return sum + (stats.gamesPlayed > 0 ? stats.wins / stats.gamesPlayed : 0.5);
    }, 0) / config.team1.length;
    
    const team2WinRate = config.team2.reduce((sum, id) => {
      const stats = playerStats.get(id)!;
      return sum + (stats.gamesPlayed > 0 ? stats.wins / stats.gamesPlayed : 0.5);
    }, 0) / config.team2.length;
    
    score += Math.abs(team1WinRate - team2WinRate) * 20;
    
    if (bestConfig === null || score < bestConfig.score) {
      bestConfig = { ...config, score };
    }
  }
  
  return bestConfig || configurations[0];
}

/**
 * Get recent partnerships (within last N rounds)
 */
function getRecentPartnerships(
  players: string[],
  matches: Match[],
  rounds: number
): Set<string> {
  const partnerships = new Set<string>();
  const completedMatches = matches.filter(m => m.status === 'completed').reverse();
  const recentRounds = getLastNRounds(completedMatches, rounds);
  
  recentRounds.forEach(round => {
    round.forEach(match => {
      if (match.team1.length === 2) {
        const [p1, p2] = match.team1;
        if (players.includes(p1) && players.includes(p2)) {
          partnerships.add(`${p1}-${p2}`);
          partnerships.add(`${p2}-${p1}`);
        }
      }
      if (match.team2.length === 2) {
        const [p1, p2] = match.team2;
        if (players.includes(p1) && players.includes(p2)) {
          partnerships.add(`${p1}-${p2}`);
          partnerships.add(`${p2}-${p1}`);
        }
      }
    });
  });
  
  return partnerships;
}

/**
 * Get recent opponents (within last N rounds)
 */
function getRecentOpponents(
  players: string[],
  matches: Match[],
  rounds: number
): Set<string> {
  const opponents = new Set<string>();
  const completedMatches = matches.filter(m => m.status === 'completed').reverse();
  const recentRounds = getLastNRounds(completedMatches, rounds);
  
  recentRounds.forEach(round => {
    round.forEach(match => {
      match.team1.forEach(p1 => {
        match.team2.forEach(p2 => {
          if (players.includes(p1) && players.includes(p2)) {
            opponents.add(`${p1}-${p2}`);
            opponents.add(`${p2}-${p1}`);
          }
        });
      });
    });
  });
  
  return opponents;
}



/**
 * Split matches into rounds
 */
function getLastNRounds(matches: Match[], n: number): Match[][] {
  if (matches.length === 0) return [];
  
  const rounds: Match[][] = [];
  let currentRound: Match[] = [];
  let lastEndTime: number | undefined;
  
  matches.forEach(match => {
    if (!match.endTime) return;
    
    if (lastEndTime && (match.endTime - lastEndTime) > 5 * 60 * 1000) {
      // New round (more than 5 minutes apart)
      if (currentRound.length > 0) {
        rounds.push(currentRound);
        currentRound = [];
      }
    }
    
    currentRound.push(match);
    lastEndTime = match.endTime;
  });
  
  if (currentRound.length > 0) {
    rounds.push(currentRound);
  }
  
  return rounds.slice(0, n);
}



/**
 * Check if team configuration is valid (no banned pairs)
 */
function isValidTeamConfiguration(
  team1: string[],
  team2: string[],
  bannedPairs: [string, string][]
): boolean {
  // Check team1
  for (let i = 0; i < team1.length; i++) {
    for (let j = i + 1; j < team1.length; j++) {
      if (isPairBanned(team1[i], team1[j], bannedPairs)) {
        return false;
      }
    }
  }
  
  // Check team2
  for (let i = 0; i < team2.length; i++) {
    for (let j = i + 1; j < team2.length; j++) {
      if (isPairBanned(team2[i], team2[j], bannedPairs)) {
        return false;
      }
    }
  }
  
  return true;
}

/**
 * Create a match for King of Court
 */
function createKingOfCourtMatch(
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

/**
 * Generate King of Court round with locked teams
 */
function generateLockedTeamsKingOfCourtRound(session: Session): Match[] {
  const { config, playerStats, matches } = session;
  const { courts, lockedTeams } = config;
  
  if (!lockedTeams || lockedTeams.length < 2) {
    return [];
  }
  
  // Get team stats (aggregate from individual players)
  const teamStats = lockedTeams.map((team, idx) => {
    const totalGames = team.reduce((sum, playerId) => {
      const stats = playerStats.get(playerId);
      return sum + (stats?.gamesPlayed || 0);
    }, 0);
    
    const totalWaits = team.reduce((sum, playerId) => {
      const stats = playerStats.get(playerId);
      return sum + (stats?.gamesWaited || 0);
    }, 0);
    
    const totalWins = team.reduce((sum, playerId) => {
      const stats = playerStats.get(playerId);
      return sum + (stats?.wins || 0);
    }, 0);
    
    return {
      teamIdx: idx,
      team,
      gamesPlayed: totalGames / team.length,
      gamesWaited: totalWaits / team.length,
      wins: totalWins / team.length,
      winRate: totalGames > 0 ? totalWins / totalGames : 0.5,
    };
  });
  
  // Sort teams by priority (who needs to play)
  const sortedTeams = teamStats.sort((a, b) => {
    // Prioritize by waits
    if (a.gamesWaited !== b.gamesWaited) {
      return b.gamesWaited - a.gamesWaited;
    }
    // Then by games played
    return a.gamesPlayed - b.gamesPlayed;
  });
  
  // Track recent opponents
  const recentOpponents = getRecentTeamOpponents(lockedTeams, matches, 2);
  
  const newMatches: Match[] = [];
  const usedTeamIndices = new Set<number>();
  
  for (let courtNum = 1; courtNum <= courts; courtNum++) {
    const availableTeams = sortedTeams.filter(t => !usedTeamIndices.has(t.teamIdx));
    
    if (availableTeams.length < 2) {
      break;
    }
    
    // Take first team
    const team1Data = availableTeams[0];
    
    // Find best opponent for team1 (similar win rate, not recent opponent)
    let bestOpponent = availableTeams[1];
    let bestScore = Infinity;
    
    for (let i = 1; i < availableTeams.length; i++) {
      const team2Data = availableTeams[i];
      let score = 0;
      
      // Prefer balanced matchups (similar win rates)
      score += Math.abs(team1Data.winRate - team2Data.winRate) * 100;
      
      // Avoid recent opponents
      const oppKey = [team1Data.teamIdx, team2Data.teamIdx].sort().join('-');
      if (recentOpponents.has(oppKey)) {
        score += 500;
      }
      
      if (score < bestScore) {
        bestScore = score;
        bestOpponent = team2Data;
      }
    }
    
    const match = createKingOfCourtMatch(
      courtNum,
      team1Data.team,
      bestOpponent.team,
      playerStats
    );
    
    newMatches.push(match);
    usedTeamIndices.add(team1Data.teamIdx);
    usedTeamIndices.add(bestOpponent.teamIdx);
  }
  
  return newMatches;
}

/**
 * Get recent team opponent pairings
 */
function getRecentTeamOpponents(
  lockedTeams: string[][],
  matches: Match[],
  rounds: number
): Set<string> {
  const opponents = new Set<string>();
  const completedMatches = matches.filter(m => m.status === 'completed').reverse();
  const recentRounds = getLastNRounds(completedMatches, rounds);
  
  // Create team lookup map
  const teamIndexMap = new Map<string, number>();
  lockedTeams.forEach((team, idx) => {
    const key = [...team].sort().join(',');
    teamIndexMap.set(key, idx);
  });
  
  recentRounds.forEach(round => {
    round.forEach(match => {
      const team1Key = [...match.team1].sort().join(',');
      const team2Key = [...match.team2].sort().join(',');
      
      const team1Idx = teamIndexMap.get(team1Key);
      const team2Idx = teamIndexMap.get(team2Key);
      
      if (team1Idx !== undefined && team2Idx !== undefined) {
        const oppKey = [team1Idx, team2Idx].sort().join('-');
        opponents.add(oppKey);
      }
    });
  });
  
  return opponents;
}
