import type { Session, SessionConfig, Match, Player, PlayerStats } from './types';
import { generateId, createPlayerStats, getPlayersWhoWaitedMost } from './utils';
import { selectPlayersForNextGame, createMatch } from './matchmaking';

export function createSession(config: SessionConfig): Session {
  const playerStats = new Map<string, PlayerStats>();
  const activePlayers = new Set<string>();
  
  config.players.forEach((player) => {
    playerStats.set(player.id, createPlayerStats(player.id));
    activePlayers.add(player.id);
  });
  
  return {
    id: generateId(),
    config,
    matches: [],
    waitingPlayers: [],
    playerStats,
    activePlayers,
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
  
  // Create matches for available courts
  for (let courtNum = 1; courtNum <= session.config.courts; courtNum++) {
    const courtBusy = session.matches.some(
      (m) => m.courtNumber === courtNum && (m.status === 'in-progress' || m.status === 'waiting')
    );
    
    if (courtBusy) continue;
    
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
  }
  
  // Update match
  const updatedMatches = session.matches.map((m) =>
    m.id === matchId
      ? {
          ...m,
          status: 'completed' as const,
          score: { team1Score, team2Score },
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
  
  // For king of the court mode, winners stay on court (only on first completion, not edits)
  if (session.config.mode === 'king-of-court' && !isEdit) {
    // Winners stay, losers go to waiting
    const newWaiting = [...session.waitingPlayers, ...losingTeam];
    
    const updated = {
      ...session,
      matches: updatedMatches,
      waitingPlayers: newWaiting,
    };
    
    // Re-evaluate to create new matches
    return evaluateAndCreateMatches(updated);
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
      ? { ...m, status: 'forfeited' as const }
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
      (m) => m.courtNumber === courtNum && m.status !== 'completed'
    );
    
    if (!courtBusy) {
      availableCourts.push(courtNum);
    }
  }
  
  return availableCourts;
}
