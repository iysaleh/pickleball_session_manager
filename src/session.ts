import type { Session, SessionConfig, Match, Player, PlayerStats } from './types';
import { generateId, createPlayerStats, getPlayersWhoWaitedMost, shuffleArray } from './utils';
import { selectPlayersForNextGame, createMatch } from './matchmaking';
import { generateRoundRobinQueue } from './queue';
import { generateKingOfCourtRound } from './kingofcourt';

export function createSession(config: SessionConfig, maxQueueSize: number = 100): Session {
  const playerStats = new Map<string, PlayerStats>();
  const activePlayers = new Set<string>();
  
  // Randomize player order if requested
  const playersToUse = config.randomizePlayerOrder 
    ? shuffleArray(config.players)
    : config.players;
  
  playersToUse.forEach((player) => {
    playerStats.set(player.id, createPlayerStats(player.id));
    activePlayers.add(player.id);
  });
  
  // Update config with potentially shuffled players
  const finalConfig = config.randomizePlayerOrder
    ? { ...config, players: playersToUse }
    : config;
  
  // Generate match queue for round-robin mode
  const matchQueue = finalConfig.mode === 'round-robin'
    ? generateRoundRobinQueue(playersToUse, finalConfig.sessionType, finalConfig.bannedPairs, maxQueueSize, finalConfig.lockedTeams)
    : [];
  
  return {
    id: generateId(),
    config: finalConfig,
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
  
  // Create player stats with wait time set to max waited + 1
  const newStats = createPlayerStats(player.id);
  let maxWaited = 0;
  session.playerStats.forEach(stats => {
    if (stats.gamesWaited > maxWaited) {
      maxWaited = stats.gamesWaited;
    }
  });
  newStats.gamesWaited = maxWaited + 1;
  
  session.playerStats.set(player.id, newStats);
  
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

export function addTeamToSession(session: Session, player1: Player, player2: Player): Session {
  // Check if either player already exists
  const player1Exists = session.config.players.some((p) => p.id === player1.id);
  const player2Exists = session.config.players.some((p) => p.id === player2.id);
  
  if (player1Exists || player2Exists) {
    return session; // Don't add if either player already exists
  }
  
  const updatedPlayers = [...session.config.players, player1, player2];
  const newActivePlayers = new Set(session.activePlayers);
  newActivePlayers.add(player1.id);
  newActivePlayers.add(player2.id);
  
  // Create player stats with wait time set to max waited + 1 for both players
  const newStats1 = createPlayerStats(player1.id);
  const newStats2 = createPlayerStats(player2.id);
  let maxWaited = 0;
  session.playerStats.forEach(stats => {
    if (stats.gamesWaited > maxWaited) {
      maxWaited = stats.gamesWaited;
    }
  });
  newStats1.gamesWaited = maxWaited + 1;
  newStats2.gamesWaited = maxWaited + 1;
  
  session.playerStats.set(player1.id, newStats1);
  session.playerStats.set(player2.id, newStats2);
  
  // Add to locked teams
  const updatedLockedTeams = [...(session.config.lockedTeams || []), [player1.id, player2.id]];
  
  const updated = {
    ...session,
    config: {
      ...session.config,
      players: updatedPlayers,
      lockedTeams: updatedLockedTeams,
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
  
  // Automatically try to create new matches with the new team
  return evaluateAndCreateMatches(updated);
}

export function removeTeamFromSession(session: Session, player1Id: string, player2Id: string): Session {
  // Mark both players as inactive
  const newActivePlayers = new Set(session.activePlayers);
  newActivePlayers.delete(player1Id);
  newActivePlayers.delete(player2Id);
  
  // Remove from waiting list
  const updatedWaiting = session.waitingPlayers.filter(
    (id) => id !== player1Id && id !== player2Id
  );
  
  // Forfeit any matches where either player is currently playing
  const updatedMatches = session.matches.map((match) => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      const hasPlayer = [...match.team1, ...match.team2].some(
        id => id === player1Id || id === player2Id
      );
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
  // King of the court uses continuous flow - generate matches for available courts
  if (session.config.mode === 'king-of-court') {
    const newMatches = generateKingOfCourtRound(session);
    
    if (newMatches.length === 0) {
      return session;
    }
    
    // Update waiting players stats for those not selected
    const selectedPlayers = new Set<string>();
    newMatches.forEach(match => {
      [...match.team1, ...match.team2].forEach(id => selectedPlayers.add(id));
    });
    
    // Get players who are not currently in any match (active or new)
    const currentlyPlaying = new Set<string>();
    session.matches.forEach(match => {
      if (match.status === 'in-progress' || match.status === 'waiting') {
        [...match.team1, ...match.team2].forEach(id => currentlyPlaying.add(id));
      }
    });
    newMatches.forEach(match => {
      [...match.team1, ...match.team2].forEach(id => currentlyPlaying.add(id));
    });
    
    const waitingPlayers = Array.from(session.activePlayers)
      .filter(id => !currentlyPlaying.has(id));
    
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
  } else {
    // Not an edit - this is the first time completing this match
    // Increment gamesPlayed for all players
    [...match.team1, ...match.team2].forEach((playerId) => {
      const stats = session.playerStats.get(playerId);
      if (stats) stats.gamesPlayed++;
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
  
  const updated = {
    ...session,
    matches: updatedMatches,
  };
  
  // Re-evaluate to create new matches (only if not an edit)
  // For king of the court, this allows continuous flow - new matches as courts free up
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

/**
 * @deprecated King of the Court now uses continuous flow. Use evaluateAndCreateMatches instead.
 * Kept for backward compatibility with tests.
 */
export function canStartNextRound(session: Session): boolean {
  // Check if all courts are either completed or forfeited
  const activeMatches = session.matches.filter(
    m => m.status === 'in-progress' || m.status === 'waiting'
  );
  return activeMatches.length === 0;
}

/**
 * @deprecated King of the Court now uses continuous flow. Use evaluateAndCreateMatches instead.
 * Kept for backward compatibility with tests.
 */
export function startNextRound(session: Session): Session {
  // For continuous flow, just call evaluateAndCreateMatches
  // which will create matches for available courts
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
