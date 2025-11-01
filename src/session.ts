import type { Session, SessionConfig, Match, Player, PlayerStats } from './types';
import { generateId, createPlayerStats, getPlayersWhoWaitedMost } from './utils';
import { selectPlayersForNextGame, createMatch } from './matchmaking';
import { generateRoundRobinQueue } from './queue';
import { generateKingOfCourtRound } from './kingofcourt';

export function createSession(config: SessionConfig, maxQueueSize: number = 100): Session {
  const playerStats = new Map<string, PlayerStats>();
  const activePlayers = new Set<string>();
  
  config.players.forEach((player) => {
    playerStats.set(player.id, createPlayerStats(player.id));
    activePlayers.add(player.id);
  });
  
  // Generate match queue for round-robin mode
  const matchQueue = config.mode === 'round-robin'
    ? generateRoundRobinQueue(config.players, config.sessionType, config.bannedPairs, maxQueueSize, config.lockedTeams)
    : [];
  
  return {
    id: generateId(),
    config,
    matches: [],
    waitingPlayers: [],
    playerStats,
    activePlayers,
    matchQueue,
    maxQueueSize,
  };
}

export function addPlayerToSession(session: Session, player: Player): Session {
  if (session.config.players.some((p) => p.id === player.id)) {
    return session;
  }
  
  const updatedPlayers = [...session.config.players, player];
  const newActivePlayers = new Set(session.activePlayers);
  newActivePlayers.add(player.id);
  session.playerStats.set(player.id, createPlayerStats(player.id));
  
  const updated = {
    ...session,
    config: {
      ...session.config,
      players: updatedPlayers,
    },
    activePlayers: newActivePlayers,
  };
  
  // For round-robin, regenerate the entire queue
  if (updated.config.mode === 'round-robin') {
    updated.matchQueue = generateRoundRobinQueue(
      updated.config.players.filter(p => updated.activePlayers.has(p.id)),
      updated.config.sessionType,
      updated.config.bannedPairs,
      updated.maxQueueSize,
      updated.config.lockedTeams
    );
  }
  
  // Automatically try to create new matches with the new player
  return evaluateAndCreateMatches(updated);
}

export function removePlayerFromSession(session: Session, playerId: string): Session {
  // Don't remove from config.players (keep historical record)
  // Just mark as inactive
  const newActivePlayers = new Set(session.activePlayers);
  newActivePlayers.delete(playerId);
  
  // Remove from waiting list
  const updatedWaiting = session.waitingPlayers.filter((id) => id !== playerId);
  
  // Forfeit any matches where this player is currently playing
  const updatedMatches = session.matches.map((match) => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      const hasPlayer = [...match.team1, ...match.team2].includes(playerId);
      if (hasPlayer) {
        return { ...match, status: 'forfeited' as const };
      }
    }
    return match;
  });
  
  const updated = {
    ...session,
    waitingPlayers: updatedWaiting,
    matches: updatedMatches,
    activePlayers: newActivePlayers,
  };
  
  // Re-evaluate to fill courts
  return evaluateAndCreateMatches(updated);
}

export function evaluateAndCreateMatches(session: Session): Session {
  // King of the court doesn't auto-create matches - waits for manual round start
  if (session.config.mode === 'king-of-court') {
    return session;
  }
  
  const playersPerTeam = session.config.sessionType === 'singles' ? 1 : 2;
  
  // Get all active players not currently playing
  const playingPlayers = new Set<string>();
  session.matches.forEach((match) => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      [...match.team1, ...match.team2].forEach((id) => playingPlayers.add(id));
    }
  });
  
  const availablePlayers = Array.from(session.activePlayers)
    .filter((id) => !playingPlayers.has(id));
  
  const newMatches: Match[] = [];
  const assignedPlayers = new Set<string>();
  
  // Create matches for available courts IN ORDER (1, 2, 3, ...)
  const occupiedCourts = new Set<number>();
  session.matches.forEach((match) => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      occupiedCourts.add(match.courtNumber);
    }
  });
  
  // Find available courts in ascending order
  const availableCourts: number[] = [];
  for (let courtNum = 1; courtNum <= session.config.courts; courtNum++) {
    if (!occupiedCourts.has(courtNum)) {
      availableCourts.push(courtNum);
    }
  }
  
  // For round-robin, use the queue
  if (session.config.mode === 'round-robin') {
    // Filter queue to only include matches with all active players
    const validQueueMatches = session.matchQueue.filter(qm => {
      const allPlayers = [...qm.team1, ...qm.team2];
      return allPlayers.every(id => session.activePlayers.has(id));
    });
    
    const usedMatchIndices = new Set<number>();
    
    for (const courtNum of availableCourts) {
      // Find next available match in queue that doesn't have conflicting players
      let foundMatch = false;
      
      for (let i = 0; i < validQueueMatches.length; i++) {
        if (usedMatchIndices.has(i)) continue;
        
        const queuedMatch = validQueueMatches[i];
        const matchPlayers = [...queuedMatch.team1, ...queuedMatch.team2];
        
        // Check if any players in this queued match are already playing
        if (matchPlayers.some(id => playingPlayers.has(id) || assignedPlayers.has(id))) {
          continue;
        }
        
        // This match is valid - use it
        const match = createMatch(courtNum, queuedMatch.team1, queuedMatch.team2, session.playerStats);
        newMatches.push(match);
        
        matchPlayers.forEach(id => assignedPlayers.add(id));
        usedMatchIndices.add(i);
        foundMatch = true;
        break;
      }
      
      if (!foundMatch) break;
    }
    
    // Remove used matches from queue - rebuild without used indices
    const updatedQueue = validQueueMatches.filter((_, idx) => !usedMatchIndices.has(idx));
    
    // Update waiting players stats
    const stillWaiting = availablePlayers.filter((id) => !assignedPlayers.has(id));
    stillWaiting.forEach((id) => {
      const stats = session.playerStats.get(id);
      if (stats) {
        stats.gamesWaited++;
      }
    });
    
    let updated = {
      ...session,
      matches: [...session.matches, ...newMatches],
      waitingPlayers: stillWaiting,
      matchQueue: updatedQueue,
    };
    
    // Check if we need to refill the queue
    updated = refillQueueIfNeeded(updated);
    
    return updated;
  }
  
  // For teams mode, use the original logic
  for (const courtNum of availableCourts) {
    const stillAvailable = availablePlayers.filter((id) => !assignedPlayers.has(id));
    
    const selectedPlayers = selectPlayersForNextGame(
      stillAvailable,
      playersPerTeam,
      session.playerStats,
      session.config.bannedPairs
    );
    
    if (!selectedPlayers) break;
    
    const team1 = selectedPlayers.slice(0, playersPerTeam);
    const team2 = selectedPlayers.slice(playersPerTeam);
    
    const match = createMatch(courtNum, team1, team2, session.playerStats);
    newMatches.push(match);
    
    selectedPlayers.forEach((id) => assignedPlayers.add(id));
  }
  
  // Update waiting players stats
  const stillWaiting = availablePlayers.filter((id) => !assignedPlayers.has(id));
  stillWaiting.forEach((id) => {
    const stats = session.playerStats.get(id);
    if (stats) {
      stats.gamesWaited++;
    }
  });
  
  return {
    ...session,
    matches: [...session.matches, ...newMatches],
    waitingPlayers: stillWaiting,
  };
}

export function startMatch(session: Session, matchId: string): Session {
  const updatedMatches = session.matches.map((match) =>
    match.id === matchId && match.status === 'waiting'
      ? { ...match, status: 'in-progress' as const }
      : match
  );
  
  return {
    ...session,
    matches: updatedMatches,
  };
}

export function completeMatch(
  session: Session,
  matchId: string,
  team1Score: number,
  team2Score: number
): Session {
  const match = session.matches.find((m) => m.id === matchId);
  if (!match) return session;
  
  // If match is already completed, this is an edit - need to recalculate stats
  const isEdit = match.status === 'completed';
  
  if (isEdit && match.score) {
    // Revert old stats
    const oldWinningTeam = match.score.team1Score > match.score.team2Score ? match.team1 : match.team2;
    const oldLosingTeam = match.score.team1Score > match.score.team2Score ? match.team2 : match.team1;
    
    oldWinningTeam.forEach((playerId) => {
      const stats = session.playerStats.get(playerId);
      if (stats) stats.wins--;
    });
    
    oldLosingTeam.forEach((playerId) => {
      const stats = session.playerStats.get(playerId);
      if (stats) stats.losses--;
    });
    
    // Revert point differential
    match.team1.forEach((playerId) => {
      const stats = session.playerStats.get(playerId);
      if (stats) {
        stats.totalPointsFor -= match.score!.team1Score;
        stats.totalPointsAgainst -= match.score!.team2Score;
      }
    });
    
    match.team2.forEach((playerId) => {
      const stats = session.playerStats.get(playerId);
      if (stats) {
        stats.totalPointsFor -= match.score!.team2Score;
        stats.totalPointsAgainst -= match.score!.team1Score;
      }
    });
  }
  
  // Update match
  const updatedMatches = session.matches.map((m) =>
    m.id === matchId
      ? {
          ...m,
          status: 'completed' as const,
          score: { team1Score, team2Score },
          endTime: Date.now(),
        }
      : m
  );
  
  // Update player stats with new scores
  const winningTeam = team1Score > team2Score ? match.team1 : match.team2;
  const losingTeam = team1Score > team2Score ? match.team2 : match.team1;
  
  winningTeam.forEach((playerId) => {
    const stats = session.playerStats.get(playerId);
    if (stats) stats.wins++;
  });
  
  losingTeam.forEach((playerId) => {
    const stats = session.playerStats.get(playerId);
    if (stats) stats.losses++;
  });
  
  // Update point differential
  match.team1.forEach((playerId) => {
    const stats = session.playerStats.get(playerId);
    if (stats) {
      stats.totalPointsFor += team1Score;
      stats.totalPointsAgainst += team2Score;
    }
  });
  
  match.team2.forEach((playerId) => {
    const stats = session.playerStats.get(playerId);
    if (stats) {
      stats.totalPointsFor += team2Score;
      stats.totalPointsAgainst += team1Score;
    }
  });
  
  // For king of the court mode, don't auto-create next matches
  // Wait for all games in round to complete, then start next round manually
  if (session.config.mode === 'king-of-court') {
    return {
      ...session,
      matches: updatedMatches,
    };
  }
  
  const updated = {
    ...session,
    matches: updatedMatches,
  };
  
  // Re-evaluate to create new matches (only if not an edit)
  return isEdit ? updated : evaluateAndCreateMatches(updated);
}

export function forfeitMatch(session: Session, matchId: string): Session {
  const match = session.matches.find((m) => m.id === matchId);
  if (!match) return session;
  
  // Update match status to forfeited (no stats changes)
  const updatedMatches = session.matches.map((m) =>
    m.id === matchId
      ? { ...m, status: 'forfeited' as const, endTime: Date.now() }
      : m
  );
  
  const updated = {
    ...session,
    matches: updatedMatches,
  };
  
  // Re-evaluate to create new matches with freed court
  return evaluateAndCreateMatches(updated);
}

export function checkForAvailableCourts(session: Session): number[] {
  const availableCourts: number[] = [];
  
  for (let courtNum = 1; courtNum <= session.config.courts; courtNum++) {
    const courtBusy = session.matches.some(
      (m) => m.courtNumber === courtNum && m.status !== 'completed' && m.status !== 'forfeited'
    );
    
    if (!courtBusy) {
      availableCourts.push(courtNum);
    }
  }
  
  return availableCourts;
}

export function canStartNextRound(session: Session): boolean {
  // Check if all courts are either completed or forfeited
  const activeMatches = session.matches.filter(
    m => m.status === 'in-progress' || m.status === 'waiting'
  );
  return activeMatches.length === 0;
}

export function startNextRound(session: Session): Session {
  if (!canStartNextRound(session)) {
    return session;
  }
  
  // For King of Court mode, use special algorithm
  if (session.config.mode === 'king-of-court') {
    const newMatches = generateKingOfCourtRound(session);
    
    // Update waiting players stats for those not selected
    const selectedPlayers = new Set<string>();
    newMatches.forEach(match => {
      [...match.team1, ...match.team2].forEach(id => selectedPlayers.add(id));
    });
    
    const waitingPlayers = Array.from(session.activePlayers)
      .filter(id => !selectedPlayers.has(id));
    
    waitingPlayers.forEach(id => {
      const stats = session.playerStats.get(id);
      if (stats) {
        stats.gamesWaited++;
      }
    });
    
    return {
      ...session,
      matches: [...session.matches, ...newMatches],
      waitingPlayers,
    };
  }
  
  return evaluateAndCreateMatches(session);
}

/**
 * Refill the match queue if it's below 80% of maxQueueSize
 */
export function refillQueueIfNeeded(session: Session): Session {
  if (session.config.mode !== 'round-robin') {
    return session;
  }
  
  const threshold = Math.floor(session.maxQueueSize * 0.8);
  
  if (session.matchQueue.length < threshold) {
    // Get active players
    const activePlayers = session.config.players.filter(p => session.activePlayers.has(p.id));
    
    // Generate more matches up to maxQueueSize
    const additionalMatches = generateRoundRobinQueue(
      activePlayers,
      session.config.sessionType,
      session.config.bannedPairs,
      session.maxQueueSize,
      session.config.lockedTeams
    );
    
    // Append new matches to existing queue
    return {
      ...session,
      matchQueue: [...session.matchQueue, ...additionalMatches],
    };
  }
  
  return session;
}

/**
 * Update the maxQueueSize and regenerate queue if necessary
 */
export function updateMaxQueueSize(session: Session, newMaxSize: number): Session {
  const updated = {
    ...session,
    maxQueueSize: newMaxSize,
  };
  
  // If current queue is larger than new max, keep it
  // If current queue is smaller and mode is round-robin, regenerate
  if (session.config.mode === 'round-robin' && session.matchQueue.length < newMaxSize) {
    const activePlayers = session.config.players.filter(p => session.activePlayers.has(p.id));
    updated.matchQueue = generateRoundRobinQueue(
      activePlayers,
      session.config.sessionType,
      session.config.bannedPairs,
      newMaxSize,
      session.config.lockedTeams
    );
  }
  
  return updated;
}
