import type { Player, Session, Match, PlayerStats, LockedTeam } from './types';
import { generateId, isPairBanned } from './utils';

/**
 * King of the Court scheduling algorithm (Ranking-Based Matchmaking)
 * 
 * Core Principles:
 * 1. ELO-style ranking system - value of wins depends on opponent strength
 * 2. Strict rank-based matchmaking - players can only play within their ranking half
 * 3. Close-rank prioritization - prefer matches between similarly-ranked players
 * 4. Strategic waiting - wait for better matchups rather than rushing games
 * 5. New player integration - provisional rankings until sufficient games played
 * 6. Variety optimization - prefer opponents you haven't faced yet
 * 
 * Matchmaking Rules:
 * - In an 18-player game, #1 can only play ranks #2-#9
 * - In an 18-player game, #18 can only play ranks #10-#17
 * - Ideally, closely-ranked players (#16, #17, #18, #19) play together
 * - Wait if necessary to avoid mismatches between high/low ranked players
 * - New players (0 games) start with provisional middle ranking
 */

/**
 * Player rating and rank information
 */
interface PlayerRating {
  playerId: string;
  rating: number;
  rank: number;
  gamesPlayed: number;
  isProvisional: boolean;
}

/**
 * Calculate ELO-style rating for a player based on their match history
 * Exported for use in rankings display
 */
export function calculatePlayerRating(stats: PlayerStats, baseRating: number = 1500, minRating: number = 800, maxRating: number = 2200): number {
  if (stats.gamesPlayed === 0) {
    return baseRating; // New players start at base rating
  }
  
  // Start with base rating
  let rating = baseRating;
  
  // Adjust based on win rate with diminishing returns
  const winRate = stats.wins / stats.gamesPlayed;
  const winRateAdjustment = Math.log(1 + winRate * 9) * 200; // Logarithmic scaling
  rating += winRateAdjustment - 200; // Center around baseRating for 50% win rate
  
  // Adjust based on point differential (quality of wins/losses)
  const avgPointDiff = (stats.totalPointsFor - stats.totalPointsAgainst) / stats.gamesPlayed;
  const pointDiffAdjustment = Math.log(1 + Math.abs(avgPointDiff)) * 50 * Math.sign(avgPointDiff);
  rating += pointDiffAdjustment;
  
  // Bonus for consistency (more games played with good win rate)
  if (stats.gamesPlayed >= 5 && winRate >= 0.6) {
    rating += Math.log(stats.gamesPlayed) * 30;
  }
  
  return Math.max(minRating, Math.min(maxRating, rating)); // Clamp between min-max
}

/**
 * Calculate rankings for all players
 */
function calculatePlayerRankings(
  playerIds: string[],
  playerStats: Map<string, PlayerStats>,
  session: Session
): PlayerRating[] {
  const config = session.advancedConfig.kingOfCourt;
  const ratings: PlayerRating[] = playerIds.map(playerId => {
    const stats = playerStats.get(playerId)!;
    const rating = calculatePlayerRating(stats, config.baseRating, config.minRating, config.maxRating);
    const isProvisional = stats.gamesPlayed < config.provisionalGamesThreshold;
    
    return {
      playerId,
      rating,
      rank: 0, // Will be assigned after sorting
      gamesPlayed: stats.gamesPlayed,
      isProvisional,
    };
  });
  
  // Sort by rating (descending)
  ratings.sort((a, b) => b.rating - a.rating);
  
  // Assign ranks
  ratings.forEach((player, index) => {
    player.rank = index + 1;
  });
  
  return ratings;
}

/**
 * Get the valid matchmaking range for a player based on their rank
 * Players can only play with others in their half of the pool
 */
function getValidMatchmakingRange(rank: number, totalPlayers: number): { minRank: number; maxRank: number } {
  const halfPool = Math.ceil(totalPlayers / 2);
  
  if (rank <= halfPool) {
    // Top half: can play with ranks 1 to halfPool
    return { minRank: 1, maxRank: halfPool };
  } else {
    // Bottom half: can play with ranks (halfPool+1) to totalPlayers
    return { minRank: halfPool + 1, maxRank: totalPlayers };
  }
}

/**
 * Check if two players can be matched together based on rankings
 * CRITICAL: Players can only play within their ranking half
 * Provisional players get slightly more flexibility but MUST still respect half-pool boundaries
 */
function canPlayTogether(
  player1Rank: number,
  player2Rank: number,
  totalPlayers: number,
  player1Provisional: boolean,
  player2Provisional: boolean
): boolean {
  const halfPool = Math.ceil(totalPlayers / 2);
  
  // HARD RULE: Never allow top half (1 to halfPool) to play bottom half (halfPool+1 to totalPlayers)
  // EXCEPTION: If BOTH players are provisional (0-2 games), allow them to cross boundaries
  // since we don't have enough data to know their true skill level yet
  const player1TopHalf = player1Rank <= halfPool;
  const player2TopHalf = player2Rank <= halfPool;
  
  // Allow crossing if both players are truly new (very few games)
  const bothVeryNew = player1Provisional && player2Provisional;
  
  // Players must be in the same half (unless both are very new)
  if (!bothVeryNew && player1TopHalf !== player2TopHalf) {
    return false; // Cannot cross the half-pool boundary
  }
  
  // If both are provisional, allow them to play together within the same half
  if (player1Provisional && player2Provisional) {
    return true; // Same half, both provisional
  }
  
  // If one is provisional, allow slightly more flexibility (within same half)
  if (player1Provisional || player2Provisional) {
    // Provisional players can play with anyone in their half
    return true;
  }
  
  // Non-provisional players use strict range checking
  const range1 = getValidMatchmakingRange(player1Rank, totalPlayers);
  const range2 = getValidMatchmakingRange(player2Rank, totalPlayers);
  
  // Check if player2's rank is in player1's range AND vice versa
  return (
    player2Rank >= range1.minRank && player2Rank <= range1.maxRank &&
    player1Rank >= range2.minRank && player1Rank <= range2.maxRank
  );
}

/**
 * Generate matches for King of the Court (Ranking-Based Matchmaking)
 * Creates matches for available courts, with strict rank-based constraints
 * 
 * CRITICAL RULES:
 * 1. If ALL courts are empty and players are available, create matches immediately
 * 2. If we have enough players for 2+ courts, wait for courtSyncThreshold courts to finish
 * 3. Prioritize wait fairness (most-waited players play first)
 * 4. Create balanced matches from most-waited players
 */
export function generateKingOfCourtRound(
  session: Session
): Match[] {
  const { config, playerStats, activePlayers, matches } = session;
  const { courts, sessionType, bannedPairs, lockedTeams } = config;
  const playersPerTeam = sessionType === 'singles' ? 1 : 2;
  const playersPerMatch = playersPerTeam * 2;
  const algConfig = session.advancedConfig.kingOfCourt;

  // If locked teams mode, use special logic
  if (lockedTeams && lockedTeams.length > 0) {
    return generateLockedTeamsKingOfCourtRound(session);
  }

  // Get players currently in active matches (in-progress or waiting)
  const busyPlayers = new Set<string>();
  matches.forEach(match => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      [...match.team1, ...match.team2].forEach(id => busyPlayers.add(id));
    }
  });

  // Get currently occupied courts
  const occupiedCourts = new Set<number>();
  matches.forEach(match => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      occupiedCourts.add(match.courtNumber);
    }
  });

  // Get available players (active but not currently playing)
  const availablePlayerIds = Array.from(activePlayers).filter(id => !busyPlayers.has(id));

  if (availablePlayerIds.length < playersPerMatch) {
    return [];
  }

  // Calculate rankings for ALL active players (not just available)
  const allActivePlayerIds = Array.from(activePlayers);
  const allRankings = calculatePlayerRankings(allActivePlayerIds, playerStats, session);

  // Get rankings for available players
  const availableRankings = allRankings.filter(r => availablePlayerIds.includes(r.playerId));

  // CRITICAL: Determine how many courts we can potentially fill
  const possibleCourts = Math.min(
    Math.floor(availablePlayerIds.length / playersPerMatch),
    courts
  );
  
  // CRITICAL: If ALL courts are empty, create matches immediately (session stalled)
  const allCourtsEmpty = occupiedCourts.size === 0;
  
  if (allCourtsEmpty && availablePlayerIds.length >= playersPerMatch) {
    // SESSION STALLED: Create matches immediately to get things moving
    // But still respect wait fairness and create balanced matches
    const hasEmptyCourts = true; // All courts are empty
    const newMatches = generateRankingBasedMatches(
      availableRankings,
      allRankings.length,
      playersPerTeam,
      playersPerMatch,
      playerStats,
      matches,
      bannedPairs,
      occupiedCourts,
      courts,
      hasEmptyCourts,
      session
    );
    return newMatches;
  }

  // COURT UTILIZATION STRATEGY:
  // Priority 1: Wait fairness - players who waited longest MUST get priority
  // Priority 2: When we have enough players for 2+ courts, wait for multiple courts to finish for variety
  // Priority 3: When empty courts exist, fill them (but respect wait fairness)
  // Priority 4: Respect ranking constraints
  
  const hasEmptyCourts = occupiedCourts.size < courts;
  const emptyCourtCount = courts - occupiedCourts.size;
  
  // CRITICAL DECISION POINT: Should we create matches now or wait?
  
  // Check max wait times to determine if we must create a match immediately
  const maxWaits = Math.max(
    ...availableRankings.map(r => playerStats.get(r.playerId)?.gamesWaited || 0)
  );
  
  // CRITICAL: Check if we should wait for court synchronization
  // This applies whether we have 1 court's worth or 2+ courts' worth of available players
  if (occupiedCourts.size > 0 && availablePlayerIds.length >= playersPerMatch && maxWaits < algConfig.maxConsecutiveWaits) {
    // We have available players, courts are busy, and nobody has waited too long
    // Check if we should wait for other courts to finish
    const shouldWait = shouldWaitForRankBasedMatchups(
      availableRankings,
      allRankings.length,
      playerStats,
      matches,
      occupiedCourts.size,
      playersPerMatch,
      courts,
      session
    );
    
    if (shouldWait) {
      return []; // Wait for more courts to finish for better variety
    }
  }
  
  // Case 1: If we have enough players for 2+ courts AND multiple courts are busy,
  // check if we should wait for court synchronization (for variety)
  if (possibleCourts >= 2 && occupiedCourts.size >= algConfig.minBusyCourtsForWaiting) {
    // We have enough players for multiple courts AND courts are busy
    // Should we wait for more courts to finish for better variety?
    
    // Never wait if someone has waited maxConsecutiveWaits+ times
    if (maxWaits >= algConfig.maxConsecutiveWaits) {
      // Someone has waited too long - create a match immediately
      // Fall through to Case 3
    } else {
      // Check if we should wait for court synchronization
      const shouldWait = shouldWaitForRankBasedMatchups(
        availableRankings,
        allRankings.length,
        playerStats,
        matches,
        occupiedCourts.size,
        playersPerMatch,
        courts,
        session
      );

      if (shouldWait) {
        return []; // Wait for more courts to finish for better matchups
      }
    }
  }
  
  // Case 2: Special handling when adding a player creates enough for a 2nd court
  // If we have 1 court occupied and enough players for 2 courts, fill ONE more court
  if (occupiedCourts.size === 1 && possibleCourts >= 2 && emptyCourtCount > 0) {
    // Fill one additional court immediately
    const newMatches = generateRankingBasedMatches(
      availableRankings,
      allRankings.length,
      playersPerTeam,
      playersPerMatch,
      playerStats,
      matches,
      bannedPairs,
      occupiedCourts,
      courts,
      hasEmptyCourts,
      session,
      1 // maxMatchesToCreate = 1 (fill one court)
    );
    return newMatches;
  }

  // Case 3: Create matches for available courts
  // Generate matches with ranking-based constraints
  const newMatches = generateRankingBasedMatches(
    availableRankings,
    allRankings.length,
    playersPerTeam,
    playersPerMatch,
    playerStats,
    matches,
    bannedPairs,
    occupiedCourts,
    courts,
    hasEmptyCourts,
    session
  );

  return newMatches;
}

/**
 * Count how many times two players have played together
 */
function getPlayTogetherCount(
  player1Id: string,
  player2Id: string,
  matches: Match[]
): number {
  let count = 0;
  const completedMatches = matches.filter(m => m.status === 'completed');
  
  completedMatches.forEach(match => {
    const allPlayers = [...match.team1, ...match.team2];
    if (allPlayers.includes(player1Id) && allPlayers.includes(player2Id)) {
      count++;
    }
  });
  
  return count;
}

/**
 * Check if this group has too much overlap with the most recently completed match
 * Returns true if backToBackOverlapThreshold or more of the same players were in the last match
 * 
 * Example violations (with threshold=3):
 * - Last match: A, B, C, D
 * - Current match: A, B, C, E (3 overlapping - NOT ALLOWED)
 * - Current match: A, B, E, F (2 overlapping - ALLOWED)
 */
function isBackToBackGame(
  playerIds: string[],
  matches: Match[],
  backToBackOverlapThreshold: number = 3
): boolean {
  // Get the most recent completed match
  const completedMatches = matches.filter(m => m.status === 'completed');
  
  // If no completed matches, check against in-progress matches (for initial round)
  const matchesToCheck = completedMatches.length > 0 
    ? completedMatches 
    : matches.filter(m => m.status === 'in-progress' || m.status === 'waiting');
  
  if (matchesToCheck.length === 0) return false;
  
  // Sort by endTime to get the most recent
  const sortedMatches = [...matchesToCheck].sort((a, b) => {
    const timeA = a.endTime || 0;
    const timeB = b.endTime || 0;
    return timeB - timeA;
  });
  
  // Check if these EXACT 4 players played together recently
  const proposedSet = new Set(playerIds);
  
  // Look at the last 3 matches to see if this exact group played
  for (let i = 0; i < Math.min(3, sortedMatches.length); i++) {
    const match = sortedMatches[i];
    const matchPlayers = new Set([...match.team1, ...match.team2]);
    
    // Check if this is the exact same 4 players
    if (matchPlayers.size === proposedSet.size) {
      let allMatch = true;
      for (const playerId of proposedSet) {
        if (!matchPlayers.has(playerId)) {
          allMatch = false;
          break;
        }
      }
      
      if (allMatch) {
        return true; // Exact same 4 players played recently
      }
    }
  }
  
  return false;
}

/**
 * Count how many times two players have been partners (on same team)
 */
function getPartnershipCount(
  player1Id: string,
  player2Id: string,
  matches: Match[]
): number {
  let count = 0;
  const completedMatches = matches.filter(m => m.status === 'completed');
  
  completedMatches.forEach(match => {
    const onTeam1 = match.team1.includes(player1Id) && match.team1.includes(player2Id);
    const onTeam2 = match.team2.includes(player1Id) && match.team2.includes(player2Id);
    if (onTeam1 || onTeam2) {
      count++;
    }
  });
  
  return count;
}

/**
 * Count how many times two players have been opponents (on different teams)
 */
function getOpponentCount(
  player1Id: string,
  player2Id: string,
  matches: Match[]
): number {
  let count = 0;
  const completedMatches = matches.filter(m => m.status === 'completed');
  
  completedMatches.forEach(match => {
    const p1Team1 = match.team1.includes(player1Id);
    const p1Team2 = match.team2.includes(player1Id);
    const p2Team1 = match.team1.includes(player2Id);
    const p2Team2 = match.team2.includes(player2Id);
    
    if ((p1Team1 && p2Team2) || (p1Team2 && p2Team1)) {
      count++;
    }
  });
  
  return count;
}

/**
 * Check if creating a match with available players would cause immediate opponent repetition
 * OR if we're exhausting a small player pool
 */
function wouldCauseImmediateRepetition(
  availableRankings: PlayerRating[],
  matches: Match[],
  playersPerMatch: number,
  config: import('./types').KingOfCourtConfig
): boolean {
  if (availableRankings.length < playersPerMatch) {
    return false;
  }
  
  // Get the most recent completed match
  const completedMatches = matches.filter(m => m.status === 'completed');
  if (completedMatches.length === 0) {
    return false;
  }
  
  const sortedMatches = [...completedMatches].sort((a, b) => {
    const timeA = a.endTime || 0;
    const timeB = b.endTime || 0;
    return timeB - timeA;
  });
  
  const availablePlayerIds = availableRankings.map(r => r.playerId);
  
  // Check if we're exhausting a small player pool
  // Look at the last 3 completed matches and see what percentage of them
  // used only the currently available players
  const recentMatches = sortedMatches.slice(0, 3);
  if (recentMatches.length >= 2) {
    const availableSet = new Set(availablePlayerIds);
    let matchesFromSamePool = 0;
    
    for (const match of recentMatches) {
      const matchPlayers = [...match.team1, ...match.team2];
      const allFromAvailable = matchPlayers.every(id => availableSet.has(id));
      if (allFromAvailable) {
        matchesFromSamePool++;
      }
    }
    
    // If 2+ of the last 3 matches used only the currently available players,
    // we're burning through the same small pool - wait for variety
    if (matchesFromSamePool >= 2 && availablePlayerIds.length <= 8) {
      return true; // Same small pool being exhausted
    }
  }
  
  const lastMatch = sortedMatches[0];
  const lastMatchPlayers = [...lastMatch.team1, ...lastMatch.team2];
  
  // Check if any of the available players were in the last match
  // and if creating a match would have them face the same opponents
  const playersFromLastMatch = availablePlayerIds.filter(id => lastMatchPlayers.includes(id));
  const playersNotInLastMatch = availablePlayerIds.filter(id => !lastMatchPlayers.includes(id));
  
  // If we have 2+ new players available, they can mix with the old players for variety
  // This is especially important for provisional players (0 games)
  if (playersNotInLastMatch.length >= 2) {
    return false; // We have enough new players to create variety, don't wait
  }
  
  // If 2+ players from the last match are available, there's a risk of immediate repetition
  if (playersFromLastMatch.length >= 2) {
    // Check if these players were opponents in the last match
    const team1Players = playersFromLastMatch.filter(id => lastMatch.team1.includes(id));
    const team2Players = playersFromLastMatch.filter(id => lastMatch.team2.includes(id));
    
    // If we have players from both teams of the last match, and no new players to mix in,
    // creating a match now would likely cause them to face each other again immediately
    if (team1Players.length > 0 && team2Players.length > 0) {
      return true; // Would cause immediate opponent repetition
    }
  }
  
  return false;
}

/**
 * Determine if we should wait for more courts to finish before scheduling (ranking-based)
 */
function shouldWaitForRankBasedMatchups(
  availableRankings: PlayerRating[],
  totalActivePlayers: number,
  playerStats: Map<string, PlayerStats>,
  matches: Match[],
  numBusyCourts: number,
  playersPerMatch: number,
  totalCourts: number,
  session: Session
): boolean {
  const config = session.advancedConfig.kingOfCourt;
  
  // Don't wait if no courts are busy (first round or all courts idle)
  if (numBusyCourts === 0) {
    return false;
  }
  
  // CRITICAL: Court synchronization strategy to prevent same players from playing repeatedly
  // When multiple courts are running, wait for all to finish before creating new matches
  // This creates variety by batching match creation
  const possibleCourts = Math.floor(availableRankings.length / playersPerMatch);
  
  // Check if anyone has waited too long (would override waiting strategy)
  const playerIds = availableRankings.map(r => r.playerId);
  const waitsPerPlayer = countConsecutiveWaits(playerIds, matches);
  const maxWaitCount = Math.max(...Array.from(waitsPerPlayer.values()));
  
  // CRITICAL COURT SYNC LOGIC:
  // The key insight is that when we have multiple courts running (e.g., 2 courts with 8 players),
  // we should wait for BOTH courts to finish before creating new matches. This prevents the
  // same 4 players from playing repeatedly while the other 4 are stuck in their own loop.
  
  // Exception: Never wait if someone has waited too long
  if (maxWaitCount >= config.maxConsecutiveWaits) {
    return false; // Someone waited too long, create match now
  }
  
  // Key scenario: We have exactly 1 court's worth of players available (4 in doubles)
  // This means ONE court just finished. Check if we should wait for more courts.
  if (availableRankings.length === playersPerMatch) {
    // If ANY courts are still busy, WAIT
    // This ensures we don't immediately schedule the same 4 players again while other courts are still playing
    if (numBusyCourts >= 1) {
      return true; // Wait for other courts to finish for variety
    }
    // Otherwise, fill the court (all other courts are idle)
    return false;
  }
  
  // Key scenario: We have 2 courts' worth of players (8 in doubles) but some courts are still busy
  // This means some courts finished but not all. We should wait for the rest.
  if (possibleCourts >= 2) {
    // If we have players for 2+ courts AND courtSyncThreshold+ courts are busy, WAIT
    // This batches match creation for variety
    if (numBusyCourts >= config.courtSyncThreshold) {
      return true; // Wait for more courts to finish to create better variety
    }
  }
  
  // If we have fewer than 2 courts' worth, or fewer than courtSyncThreshold busy courts, don't wait
  return false;
}

/**
 * Detect if we're in a "single court loop" where the same small group
 * keeps playing each other while other courts are idle
 */
function detectSingleCourtLoop(
  availablePlayerIds: string[],
  matches: Match[],
  numBusyCourts: number,
  playersPerMatch: number,
  config: import('./types').KingOfCourtConfig
): boolean {
  // Only check if we have multiple courts and some are busy
  if (numBusyCourts < config.minBusyCourtsForWaiting) return false;
  
  if (availablePlayerIds.length !== playersPerMatch) {
    // Not a single-court-worth of players waiting
    return false;
  }
  
  const completedMatches = matches.filter(m => m.status === 'completed');
  if (completedMatches.length < 5) return false; // Need some history
  
  // Check how many times this exact group has played together in recent history
  const last10Matches = completedMatches.slice(-10);
  let groupPlayCount = 0;
  
  for (const match of last10Matches) {
    const matchPlayers = [...match.team1, ...match.team2];
    const allInGroup = availablePlayerIds.every(id => matchPlayers.includes(id));
    if (allInGroup) {
      groupPlayCount++;
    }
  }
  
  // If this group has played together X+ times in last 10 matches, we're looping
  if (groupPlayCount >= config.singleCourtLoopThreshold) {
    return true;
  }
  
  // Also check pairwise matchup counts
  let highRepeatPairs = 0;
  for (let i = 0; i < availablePlayerIds.length; i++) {
    for (let j = i + 1; j < availablePlayerIds.length; j++) {
      const playCount = getPlayTogetherCount(availablePlayerIds[i], availablePlayerIds[j], matches);
      if (playCount >= 3) {
        highRepeatPairs++;
      }
    }
  }
  
  // If most pairs have played together 3+ times, we're looping
  const totalPairs = (availablePlayerIds.length * (availablePlayerIds.length - 1)) / 2;
  if (highRepeatPairs >= totalPairs * 0.5) {
    return true;
  }
  
  return false;
}

/**
 * Detect if the available players would create a high-repetition matchup
 * This catches cases where 3+ players are waiting and would play with mostly the same people
 */
function detectHighRepetitionMatchup(
  availablePlayerIds: string[],
  matches: Match[],
  numBusyCourts: number,
  playersPerMatch: number,
  config: import('./types').KingOfCourtConfig
): boolean {
  // Only check if we have enough players waiting to warrant checking
  if (availablePlayerIds.length < playersPerMatch) {
    return false;
  }
  
  const completedMatches = matches.filter(m => m.status === 'completed');
  if (completedMatches.length < 4) return false; // Need some history
  
  // Check the last 5 matches for repetition patterns
  const last5Matches = completedMatches.slice(-5);
  
  // For each pair of available players, check how recently they played together
  let recentPairCount = 0;
  let totalPairsChecked = 0;
  
  for (let i = 0; i < availablePlayerIds.length && i < playersPerMatch; i++) {
    for (let j = i + 1; j < availablePlayerIds.length && j < playersPerMatch; j++) {
      totalPairsChecked++;
      const player1 = availablePlayerIds[i];
      const player2 = availablePlayerIds[j];
      
      // Check if these two played together in any of the last 5 matches
      for (const match of last5Matches) {
        const matchPlayers = [...match.team1, ...match.team2];
        if (matchPlayers.includes(player1) && matchPlayers.includes(player2)) {
          recentPairCount++;
          break; // Count each pair only once
        }
      }
    }
  }
  
  // If more than threshold% of the pairs played together recently, we have high repetition
  // (This would catch cases like players 1 & 2 playing together 3 times in last 5 matches)
  if (totalPairsChecked > 0 && recentPairCount / totalPairsChecked > config.highRepetitionThreshold) {
    return true;
  }
  
  // Also check: if ANY single player appears in 3+ of the last 5 matches with any of the waiting players
  for (const playerId of availablePlayerIds.slice(0, playersPerMatch)) {
    let appearanceCount = 0;
    
    for (const match of last5Matches) {
      const matchPlayers = [...match.team1, ...match.team2];
      
      // Check if this player AND at least one other waiting player were in this match
      const waitingPlayersInMatch = availablePlayerIds.filter(id => 
        id !== playerId && matchPlayers.includes(id)
      );
      
      if (matchPlayers.includes(playerId) && waitingPlayersInMatch.length > 0) {
        appearanceCount++;
      }
    }
    
    // If this player appeared with waiting partners in 3+ of last 5 matches, high repetition
    if (appearanceCount >= 3) {
      return true;
    }
  }
  
  return false;
}

/**
 * Check if we can create at least one valid rank-based match
 */
function canCreateValidRankMatch(
  availableRankings: PlayerRating[],
  totalActivePlayers: number,
  playersPerMatch: number
): boolean {
  for (let i = 0; i < availableRankings.length; i++) {
    let compatibleCount = 0;
    const player1 = availableRankings[i];
    
    for (let j = 0; j < availableRankings.length; j++) {
      if (i === j) continue;
      const player2 = availableRankings[j];
      
      if (canPlayTogether(
        player1.rank,
        player2.rank,
        totalActivePlayers,
        player1.isProvisional,
        player2.isProvisional
      )) {
        compatibleCount++;
      }
    }
    
    // Need at least (playersPerMatch - 1) compatible players to form a match
    if (compatibleCount >= playersPerMatch - 1) {
      return true;
    }
  }
  
  return false;
}

/**
 * Check if we have opportunities for close-rank matchups
 */
function hasCloseRankMatchups(
  availableRankings: PlayerRating[],
  totalActivePlayers: number,
  matches: Match[],
  playersPerMatch: number
): boolean {
  // Look for groups of closely-ranked players (within 3 ranks)
  for (let i = 0; i < availableRankings.length; i++) {
    const player1 = availableRankings[i];
    let closeRankCount = 0;
    
    for (let j = 0; j < availableRankings.length; j++) {
      if (i === j) continue;
      const player2 = availableRankings[j];
      
      // Check if ranks are close AND they can play together
      const rankDiff = Math.abs(player1.rank - player2.rank);
      if (rankDiff <= 3 && canPlayTogether(
        player1.rank,
        player2.rank,
        totalActivePlayers,
        player1.isProvisional,
        player2.isProvisional
      )) {
        closeRankCount++;
      }
    }
    
    // If we have enough close-ranked compatible players, we have good matchups
    if (closeRankCount >= playersPerMatch - 1) {
      return true;
    }
  }
  
  return false;
}

/**
 * Generate matches with ranking-based constraints
 */
function generateRankingBasedMatches(
  availableRankings: PlayerRating[],
  totalActivePlayers: number,
  playersPerTeam: number,
  playersPerMatch: number,
  playerStats: Map<string, PlayerStats>,
  matches: Match[],
  bannedPairs: [string, string][],
  occupiedCourts: Set<number>,
  totalCourts: number,
  hasEmptyCourts: boolean,
  session: Session,
  maxMatchesToCreate?: number // Optional: limit number of matches to create
): Match[] {
  const newMatches: Match[] = [];
  const usedPlayers = new Set<string>();
  
  // CRITICAL: Check if ALL courts are empty at the START
  // This determines if we should use lenient matching for ALL matches in this batch
  const allCourtsEmptyAtStart = occupiedCourts.size === 0;
  
  // CRITICAL: Check if players just finished a match
  // Find the most recently completed match and de-prioritize those players
  const recentlyPlayed = new Set<string>();
  const completedMatches = matches.filter(m => m.status === 'completed' && m.endTime);
  if (completedMatches.length > 0) {
    // Sort by endTime to find the most recent
    const sortedByEnd = [...completedMatches].sort((a, b) => (b.endTime || 0) - (a.endTime || 0));
    const mostRecentMatch = sortedByEnd[0];
    
    // Add players from the most recent match to recentlyPlayed set
    [...mostRecentMatch.team1, ...mostRecentMatch.team2].forEach(id => recentlyPlayed.add(id));
  }
  
  // Sort available players by wait priority
  const sortedRankings = [...availableRankings].sort((a, b) => {
    const statsA = playerStats.get(a.playerId)!;
    const statsB = playerStats.get(b.playerId)!;
    
    // HIGHEST PRIORITY: Prioritize by games waited (most-waited FIRST)
    if (statsA.gamesWaited !== statsB.gamesWaited) {
      return statsB.gamesWaited - statsA.gamesWaited;
    }
    
    // SECOND PRIORITY: De-prioritize players who just finished a match (as tiebreaker)
    const aRecentlyPlayed = recentlyPlayed.has(a.playerId);
    const bRecentlyPlayed = recentlyPlayed.has(b.playerId);
    if (aRecentlyPlayed !== bRecentlyPlayed) {
      return aRecentlyPlayed ? 1 : -1; // Non-recent players first
    }
    
    // THIRD PRIORITY: Then by games played (fewer = higher priority)
    return statsA.gamesPlayed - statsB.gamesPlayed;
  });
  
  // Try to create matches for each available court
  let matchesCreated = 0;
  for (let courtNum = 1; courtNum <= totalCourts; courtNum++) {
    if (occupiedCourts.has(courtNum)) {
      continue;
    }
    
    // Check if we've hit the max matches limit
    if (maxMatchesToCreate !== undefined && matchesCreated >= maxMatchesToCreate) {
      break;
    }
    
    const remainingRankings = sortedRankings.filter(r => !usedPlayers.has(r.playerId));
    
    if (remainingRankings.length < playersPerMatch) {
      break;
    }
    
    // Try to select players for this match
    // IMPORTANT: Pass allCourtsEmptyAtStart instead of checking dynamically
    // This ensures consistent lenient matching for all matches in this batch
    const allMatches = [...matches, ...newMatches];
    const selectedPlayers = selectPlayersForRankMatch(
      remainingRankings,
      totalActivePlayers,
      playersPerMatch,
      playerStats,
      allMatches,
      hasEmptyCourts,
      session,
      allCourtsEmptyAtStart  // NEW: Tell the function if all courts were empty at start
    );
    
    if (!selectedPlayers || selectedPlayers.length < playersPerMatch) {
      continue; // Try next court instead of breaking
    }
    
    // Divide into teams
    // Include newly created matches so team assignment can avoid repetition
    const teamAssignment = assignTeams(
      selectedPlayers,
      playersPerTeam,
      playerStats,
      allMatches,
      bannedPairs,
      session
    );
    
    if (!teamAssignment) {
      continue; // Try next court instead of breaking
    }
    
    const match = createKingOfCourtMatch(
      courtNum,
      teamAssignment.team1,
      teamAssignment.team2,
      playerStats
    );
    
    newMatches.push(match);
    matchesCreated++;
    
    // Mark these players as used
    selectedPlayers.forEach(id => usedPlayers.add(id));
  }
  
  return newMatches;
}

/**
 * Find the most balanced match from a pool of players
 * Used when all courts are idle to create fairest possible match
 */
function findMostBalancedMatch(
  playerRankings: PlayerRating[],
  playersPerMatch: number,
  playerStats: Map<string, PlayerStats>,
  matches: Match[],
  backToBackThreshold: number
): string[] | null {
  if (playerRankings.length < playersPerMatch) {
    return null;
  }
  
  // For singles (2 players), just pick the two most similar ratings
  if (playersPerMatch === 2) {
    let bestPair: string[] | null = null;
    let bestDiff = Infinity;
    
    for (let i = 0; i < playerRankings.length; i++) {
      for (let j = i + 1; j < playerRankings.length; j++) {
        const ratingDiff = Math.abs(playerRankings[i].rating - playerRankings[j].rating);
        const playerIds = [playerRankings[i].playerId, playerRankings[j].playerId];
        
        if (!isBackToBackGame(playerIds, matches, backToBackThreshold) && ratingDiff < bestDiff) {
          bestDiff = ratingDiff;
          bestPair = playerIds;
        }
      }
    }
    
    // If all pairs are back-to-back, just take the best rating match anyway
    if (!bestPair) {
      bestPair = [playerRankings[0].playerId, playerRankings[1].playerId];
    }
    
    return bestPair;
  }
  
  // For doubles (4 players), try to balance teams by rating
  let bestMatch: string[] | null = null;
  let bestBalance = Infinity;
  
  // Generate different 4-player combinations
  for (let i = 0; i < playerRankings.length && i < 10; i++) { // Limit combinations to avoid performance issues
    for (let j = i + 1; j < playerRankings.length && j < 11; j++) {
      for (let k = j + 1; k < playerRankings.length && k < 12; k++) {
        for (let l = k + 1; l < playerRankings.length && l < 13; l++) {
          const fourPlayers = [
            playerRankings[i],
            playerRankings[j],
            playerRankings[k],
            playerRankings[l]
          ];
          const playerIds = fourPlayers.map(p => p.playerId);
          
          // Skip if this is back-to-back with last match
          if (isBackToBackGame(playerIds, matches, backToBackThreshold)) {
            continue;
          }
          
          // Try all 3 possible team configurations
          const configs = [
            { team1: [fourPlayers[0], fourPlayers[1]], team2: [fourPlayers[2], fourPlayers[3]] },
            { team1: [fourPlayers[0], fourPlayers[2]], team2: [fourPlayers[1], fourPlayers[3]] },
            { team1: [fourPlayers[0], fourPlayers[3]], team2: [fourPlayers[1], fourPlayers[2]] },
          ];
          
          for (const config of configs) {
            const team1Avg = (config.team1[0].rating + config.team1[1].rating) / 2;
            const team2Avg = (config.team2[0].rating + config.team2[1].rating) / 2;
            const ratingBalance = Math.abs(team1Avg - team2Avg);
            
            // Factor in partnership variety
            // Count how many times these partnerships have happened
            const team1PartnerId1 = config.team1[0].playerId;
            const team1PartnerId2 = config.team1[1].playerId;
            const team2PartnerId1 = config.team2[0].playerId;
            const team2PartnerId2 = config.team2[1].playerId;
            
            const team1PartnerCount = getPartnershipCount(team1PartnerId1, team1PartnerId2, matches);
            const team2PartnerCount = getPartnershipCount(team2PartnerId1, team2PartnerId2, matches);
            const totalPartnerRepetition = team1PartnerCount + team2PartnerCount;
            
            // CRITICAL: Also count opponent repetition!
            // This prevents the same players from being in matches together too often
            let totalOpponentRepetition = 0;
            for (const p1 of config.team1) {
              for (const p2 of config.team2) {
                totalOpponentRepetition += getOpponentCount(p1.playerId, p2.playerId, matches);
              }
            }
            
            // Combined score: balance + partnership penalty + opponent penalty
            // Partnership repetition: 50 rating points per occurrence (teammates)
            // Opponent repetition: 30 rating points per occurrence (opponents)
            // Opponents can repeat more than partners, but still should have variety
            const combinedScore = ratingBalance + (totalPartnerRepetition * 50) + (totalOpponentRepetition * 30);
            
            if (combinedScore < bestBalance) {
              bestBalance = combinedScore;
              bestMatch = playerIds;
            }
          }
        }
      }
    }
  }
  
  // If we found a good balanced match, return it
  if (bestMatch) {
    return bestMatch;
  }
  
  // Fallback: just take first 4 that aren't back-to-back
  for (let i = 0; i <= playerRankings.length - playersPerMatch; i++) {
    const playerIds = playerRankings.slice(i, i + playersPerMatch).map(r => r.playerId);
    if (!isBackToBackGame(playerIds, matches, backToBackThreshold)) {
      return playerIds;
    }
  }
  
  // Last resort: take first players even if back-to-back
  return playerRankings.slice(0, playersPerMatch).map(r => r.playerId);
}

/**
 * Select players for a rank-based match
 * Prioritizes close-rank matchups and variety
 */
function selectPlayersForRankMatch(
  availableRankings: PlayerRating[],
  totalActivePlayers: number,
  playersPerMatch: number,
  playerStats: Map<string, PlayerStats>,
  matches: Match[],
  hasEmptyCourts: boolean,
  session: Session,
  allCourtsWereEmpty: boolean = false  // NEW: Were all courts empty when we started creating matches?
): string[] | null {
  const config = session.advancedConfig.kingOfCourt;

  if (availableRankings.length < playersPerMatch) {
    return null;
  }

  // CRITICAL: At session start (no completed matches), be very aggressive about filling courts
  // Rankings don't exist yet, so just take first available players
  const completedMatches = matches.filter(m => m.status === 'completed');
  if (completedMatches.length === 0) {
    // Try to find a group that doesn't duplicate the first match
    for (let i = 0; i < availableRankings.length - playersPerMatch + 1; i++) {
      const groupPlayerIds = availableRankings.slice(i, i + playersPerMatch).map(r => r.playerId);
      if (!isBackToBackGame(groupPlayerIds, matches, config.backToBackOverlapThreshold)) {
        return groupPlayerIds;
      }
    }
    // If all groups would be back-to-back (shouldn't happen), return first group anyway
    return availableRankings.slice(0, playersPerMatch).map(r => r.playerId);
  }

  // IMPORTANT: If courts are empty, prioritize filling them over perfect matchups
  // BUT: Always respect wait fairness - most-waited players MUST get priority
  if (hasEmptyCourts) {
    // CRITICAL: Check if players just finished a match (most recent completed match)
    // De-prioritize those players
    const recentlyPlayed = new Set<string>();
    const completedMatches = matches.filter(m => m.status === 'completed' && m.endTime);
    if (completedMatches.length > 0) {
      const sortedByEnd = [...completedMatches].sort((a, b) => (b.endTime || 0) - (a.endTime || 0));
      const mostRecentMatch = sortedByEnd[0];
      [...mostRecentMatch.team1, ...mostRecentMatch.team2].forEach(id => recentlyPlayed.add(id));
    }
    
    // Get wait counts and sort properly - THIS IS THE CRITICAL SORT
    const playersWithWaits = availableRankings.map(r => ({
      ranking: r,
      waits: playerStats.get(r.playerId)?.gamesWaited || 0,
      gamesPlayed: playerStats.get(r.playerId)?.gamesPlayed || 0,
      recentlyPlayed: recentlyPlayed.has(r.playerId)
    }));
    
    // Sort by: 1. Most waits FIRST (absolute priority), 2. Not recently played (tiebreaker), 3. Fewest games played
    playersWithWaits.sort((a, b) => {
      // HIGHEST PRIORITY: Most waits first (people who waited longer go first)
      if (b.waits !== a.waits) return b.waits - a.waits;
      // SECOND PRIORITY: De-prioritize recently played (tiebreaker for equal waits)
      if (a.recentlyPlayed !== b.recentlyPlayed) {
        return a.recentlyPlayed ? 1 : -1;
      }
      // THIRD PRIORITY: Fewest games played (new players get priority)
      return a.gamesPlayed - b.gamesPlayed;
    });
    
    // Now playersWithWaits is sorted by wait priority (most waits first)
    // CRITICAL: We need to ensure the top waiters ALL get to play
    // Strategy: Take all players with the MAX wait count (or within +/-1), then fill remaining slots
    
    if (playersWithWaits.length < playersPerMatch) {
      return null; // Not enough players
    }
    
    const maxWaits = playersWithWaits[0].waits;
    // CRITICAL FIX: Include players within maxWaits and maxWaits-1 as "top waiters"
    // This handles the 7-player case where 3 are waiting (some may have waited 1 time, some 2 times)
    const topWaiters = playersWithWaits.filter(p => p.waits >= maxWaits - 1 && p.waits > 0);
    
    // If no one has waited yet (session start), just take first available
    if (topWaiters.length === 0 || maxWaits === 0) {
      // Try to find a group that doesn't duplicate recent matches
      for (let i = 0; i <= playersWithWaits.length - playersPerMatch; i++) {
        const groupPlayerIds = playersWithWaits.slice(i, i + playersPerMatch).map(p => p.ranking.playerId);
        if (!isBackToBackGame(groupPlayerIds, matches, config.backToBackOverlapThreshold)) {
          return groupPlayerIds;
        }
      }
      // If all groups would be back-to-back, return first group anyway
      return playersWithWaits.slice(0, playersPerMatch).map(p => p.ranking.playerId);
    }
    
    // CRITICAL DECISION POINT:
    // If we have exactly playersPerMatch top waiters, use them (they all waited equally)
    if (topWaiters.length === playersPerMatch) {
      const playerIds = topWaiters.map(p => p.ranking.playerId);
      // Check if this would be back-to-back - if so, still allow it because wait fairness is paramount
      return playerIds;
    }
    
    // If we have MORE than playersPerMatch top waiters, find best balanced match from them
    if (topWaiters.length > playersPerMatch) {
      const bestMatch = findMostBalancedMatch(
        topWaiters.map(p => p.ranking),
        playersPerMatch,
        playerStats,
        matches,
        config.backToBackOverlapThreshold
      );
      
      if (bestMatch) {
        return bestMatch;
      }
      
      // Fallback: take first playersPerMatch top waiters (they all waited equally)
      return topWaiters.slice(0, playersPerMatch).map(p => p.ranking.playerId);
    }
    
    // If we have FEWER than playersPerMatch top waiters, include them all + fill remaining slots
    // CRITICAL: All top waiters MUST be included - wait fairness is PARAMOUNT
    const remainingSlots = playersPerMatch - topWaiters.length;
    const additionalPlayers = playersWithWaits.slice(topWaiters.length);
    
    // Check if all players are provisional (no games played yet or very few games)
    // If so, ignore rank constraints entirely - we don't have enough data for rankings yet
    const mostPlayersProvisional = playersWithWaits.filter(p => p.ranking.isProvisional).length >= playersWithWaits.length * 0.7;
    
    if (mostPlayersProvisional) {
      // At session start or with mostly provisional players: Just take top waiters + next players
      // Ignore rank constraints completely
      const selectedIds = [...topWaiters.map(p => p.ranking.playerId)];
      for (let i = 0; i < additionalPlayers.length && selectedIds.length < playersPerMatch; i++) {
        selectedIds.push(additionalPlayers[i].ranking.playerId);
      }
      if (selectedIds.length >= playersPerMatch) {
        return selectedIds.slice(0, playersPerMatch);
      }
    }
    
    // Try to find rank-compatible additional players
    const selectedPlayers = [...topWaiters];
    
    for (const additionalPlayer of additionalPlayers) {
      if (selectedPlayers.length >= playersPerMatch) break;
      
      // Check if this player can play with all selected top waiters (rank constraints)
      // For provisional players, be VERY lenient
      const allProvisional = selectedPlayers.every(p => p.ranking.isProvisional) && additionalPlayer.ranking.isProvisional;
      
      let canPlayWithAll = allProvisional; // If all provisional, allow
      if (!allProvisional) {
        // Check rank compatibility
        canPlayWithAll = true;
        for (const selectedPlayer of selectedPlayers) {
          if (!canPlayTogether(
            selectedPlayer.ranking.rank,
            additionalPlayer.ranking.rank,
            totalActivePlayers,
            selectedPlayer.ranking.isProvisional,
            additionalPlayer.ranking.isProvisional
          )) {
            canPlayWithAll = false;
            break;
          }
        }
      }
      
      if (canPlayWithAll) {
        selectedPlayers.push(additionalPlayer);
      }
    }
    
    // If we successfully found enough rank-compatible players, use them
    if (selectedPlayers.length >= playersPerMatch) {
      const playerIds = selectedPlayers.slice(0, playersPerMatch).map(p => p.ranking.playerId);
      return playerIds;
    }
    
    // ABSOLUTE LAST RESORT: If rank constraints prevent us from making a match,
    // FORCE all top waiters + next players, ignoring rank constraints
    // Wait fairness is MORE important than rank constraints when courts are empty
    const forcedSelection = [...topWaiters.map(p => p.ranking.playerId)];
    for (let i = topWaiters.length; i < playersWithWaits.length && forcedSelection.length < playersPerMatch; i++) {
      forcedSelection.push(playersWithWaits[i].ranking.playerId);
    }
    
    if (forcedSelection.length >= playersPerMatch) {
      return forcedSelection.slice(0, playersPerMatch);
    }
    
    // Edge case: Not enough players
    return null;
  }
  
  // Calculate soft preference frequency (used for scoring)
  // Try to avoid same person more than once per (totalPlayers/6) games, but don't hard block
  const softRepetitionFrequency = Math.max(config.softRepetitionFrequency, Math.floor(totalActivePlayers / 6));
  
  // Strategy 1: Try to find a group of closely-ranked players (within closeRankThreshold ranks) with variety constraints
  for (let i = 0; i < availableRankings.length; i++) {
    const anchor = availableRankings[i];
    const closeGroup: PlayerRating[] = [anchor];
    
    for (let j = 0; j < availableRankings.length; j++) {
      if (i === j) continue;
      const candidate = availableRankings[j];
      
      const rankDiff = Math.abs(anchor.rank - candidate.rank);
      
      // Check if close in rank and can play together
      if (rankDiff <= config.closeRankThreshold && canPlayTogether(
        anchor.rank,
        candidate.rank,
        totalActivePlayers,
        anchor.isProvisional,
        candidate.isProvisional
      )) {
        closeGroup.push(candidate);
      }
      
      if (closeGroup.length >= playersPerMatch) {
        break;
      }
    }
    
    if (closeGroup.length >= playersPerMatch) {
      // Score this group based on variety and closeness
      const groupPlayerIds = closeGroup.map(r => r.playerId);
      
      // HARD CONSTRAINT: Never allow back-to-back games with same exact players
      if (isBackToBackGame(groupPlayerIds.slice(0, playersPerMatch), matches, config.backToBackOverlapThreshold)) {
        continue; // Skip this group
      }
      
      const varietyScore = calculateGroupVarietyScore(groupPlayerIds, matches);
      const closenessScore = calculateGroupClosenessScore(closeGroup);
      const repetitionScore = calculateGroupRepetitionScore(groupPlayerIds, matches, playerStats, softRepetitionFrequency);
      
      // If this is a good group (good variety OR close ranks AND reasonable repetition), use it
      if ((varietyScore > 0.5 || closenessScore < config.veryCloseRankThreshold) && repetitionScore < 0.8) {
        return groupPlayerIds.slice(0, playersPerMatch);
      }
    }
  }
  
  // Strategy 2: Find any valid group that meets STRICT rank constraints and variety caps
  for (let i = 0; i < availableRankings.length; i++) {
    const anchor = availableRankings[i];
    const validGroup: PlayerRating[] = [anchor];
    
    for (let j = 0; j < availableRankings.length; j++) {
      if (i === j) continue;
      const candidate = availableRankings[j];
      
      // STRICT CHECK: All members must be able to play with candidate
      let canJoin = true;
      for (const member of validGroup) {
        if (!canPlayTogether(
          member.rank,
          candidate.rank,
          totalActivePlayers,
          member.isProvisional,
          candidate.isProvisional
        )) {
          canJoin = false;
          break;
        }
      }
      
      if (canJoin) {
        // ADDITIONAL CHECK: Candidate must be in valid range for ALL existing members
        let inValidRange = true;
        for (const member of validGroup) {
          const memberRange = getValidMatchmakingRange(member.rank, totalActivePlayers);
          if (candidate.rank < memberRange.minRank || candidate.rank > memberRange.maxRank) {
            inValidRange = false;
            break;
          }
        }
        
        if (inValidRange) {
          validGroup.push(candidate);
        }
      }
      
      if (validGroup.length >= playersPerMatch) {
        break;
      }
    }
    
    if (validGroup.length >= playersPerMatch) {
      // FINAL VALIDATION: Ensure all pairs in group can play together
      let allPairsValid = true;
      for (let a = 0; a < playersPerMatch; a++) {
        for (let b = a + 1; b < playersPerMatch; b++) {
          if (!canPlayTogether(
            validGroup[a].rank,
            validGroup[b].rank,
            totalActivePlayers,
            validGroup[a].isProvisional,
            validGroup[b].isProvisional
          )) {
            allPairsValid = false;
            break;
          }
        }
        if (!allPairsValid) break;
      }
      
      if (allPairsValid) {
        const groupPlayerIds = validGroup.slice(0, playersPerMatch).map(r => r.playerId);
        
        // HARD CONSTRAINT: Never allow back-to-back games with same exact players
        if (isBackToBackGame(groupPlayerIds, matches, config.backToBackOverlapThreshold)) {
          continue; // Skip this group
        }
        
        // Prefer groups with better variety, but don't hard block
        const repetitionScore = calculateGroupRepetitionScore(groupPlayerIds, matches, playerStats, softRepetitionFrequency);
        
        // Accept if repetition is not extreme (less than 90% of pairs are over-repeated)
        if (repetitionScore < 0.9) {
          return groupPlayerIds;
        }
      }
    }
  }
  
  // Last resort: if we have ANY valid rank-constrained group, use it (even with repetition)
  // But NEVER allow back-to-back with the exact same players
  for (let i = 0; i < availableRankings.length; i++) {
    const anchor = availableRankings[i];
    const validGroup: PlayerRating[] = [anchor];
    
    for (let j = 0; j < availableRankings.length; j++) {
      if (i === j) continue;
      const candidate = availableRankings[j];
      
      let canJoin = true;
      for (const member of validGroup) {
        if (!canPlayTogether(
          member.rank,
          candidate.rank,
          totalActivePlayers,
          member.isProvisional,
          candidate.isProvisional
        )) {
          canJoin = false;
          break;
        }
      }
      
      if (canJoin) {
        validGroup.push(candidate);
      }
      
      if (validGroup.length >= playersPerMatch) {
        break;
      }
    }
    
    if (validGroup.length >= playersPerMatch) {
      const groupPlayerIds = validGroup.slice(0, playersPerMatch).map(r => r.playerId);
      
      // HARD CONSTRAINT: Never allow back-to-back games with same exact players
      if (!isBackToBackGame(groupPlayerIds, matches, config.backToBackOverlapThreshold)) {
        return groupPlayerIds;
      }
    }
  }
  
  // HARD CONSTRAINT: Return null if no valid rank-constrained match exists
  return null;
}

/**
 * Calculate a repetition score for a group (0 = fresh matchups, 1 = all pairs over-repeated)
 * This is a soft preference, not a hard block
 * 
 * Example with 18 players (frequency = 3):
 * - Prefer not to play with same person more than once per 3 games
 * - But allow it if necessary to keep courts full
 */
function calculateGroupRepetitionScore(
  playerIds: string[],
  matches: Match[],
  playerStats: Map<string, PlayerStats>,
  targetFrequency: number
): number {
  let totalPairs = 0;
  let overRepeatedPairs = 0;
  
  // Check each pair of players in the group
  for (let i = 0; i < playerIds.length; i++) {
    const player1Stats = playerStats.get(playerIds[i]);
    if (!player1Stats) continue;
    
    const player1Games = player1Stats.gamesPlayed;
    
    for (let j = i + 1; j < playerIds.length; j++) {
      const player2Stats = playerStats.get(playerIds[j]);
      if (!player2Stats) continue;
      
      totalPairs++;
      
      const player2Games = player2Stats.gamesPlayed;
      const minGamesPlayed = Math.min(player1Games, player2Games);
      
      // Calculate ideal max plays together based on target frequency
      const idealMaxPlays = Math.floor(minGamesPlayed / targetFrequency) + 1;
      
      // Check if they've played together more than ideal
      const playTogetherCount = getPlayTogetherCount(playerIds[i], playerIds[j], matches);
      
      if (playTogetherCount > idealMaxPlays) {
        overRepeatedPairs++;
      }
    }
  }
  
  return totalPairs > 0 ? overRepeatedPairs / totalPairs : 0;
}

/**
 * Calculate variety score for a group (how many haven't played together)
 */
function calculateGroupVarietyScore(
  playerIds: string[],
  matches: Match[]
): number {
  if (playerIds.length < 2) return 1;
  
  let totalPairs = 0;
  let newPairs = 0;
  
  for (let i = 0; i < playerIds.length; i++) {
    for (let j = i + 1; j < playerIds.length; j++) {
      totalPairs++;
      const playCount = getPlayTogetherCount(playerIds[i], playerIds[j], matches);
      if (playCount === 0) {
        newPairs++;
      }
    }
  }
  
  return totalPairs > 0 ? newPairs / totalPairs : 1;
}

/**
 * Calculate average rank difference in a group (lower is better)
 */
function calculateGroupClosenessScore(
  rankings: PlayerRating[]
): number {
  if (rankings.length < 2) return 0;
  
  let totalDiff = 0;
  let pairs = 0;
  
  for (let i = 0; i < rankings.length; i++) {
    for (let j = i + 1; j < rankings.length; j++) {
      totalDiff += Math.abs(rankings[i].rank - rankings[j].rank);
      pairs++;
    }
  }
  
  return pairs > 0 ? totalDiff / pairs : 0;
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
  bannedPairs: [string, string][],
  session: Session
): { team1: string[]; team2: string[] } | null {
  const algConfig = session.advancedConfig.kingOfCourt;
  if (playersPerTeam === 1) {
    // Singles: simple 1v1
    return {
      team1: [players[0]],
      team2: [players[1]],
    };
  }
  
  // Doubles: try different configurations
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
    
    // Count actual partnership frequencies (all-time, not just recent)
    const team1PartnerCount = getPartnershipCount(config.team1[0], config.team1[1], matches);
    const team2PartnerCount = getPartnershipCount(config.team2[0], config.team2[1], matches);
    
    // Moderate penalty for repeated partnerships
    score += team1PartnerCount * algConfig.partnershipRepeatPenalty;
    score += team2PartnerCount * algConfig.partnershipRepeatPenalty;
    
    // CRITICAL: Check for recent partnerships (last 2 games per player)
    // This prevents the same people from playing together 3+ times in a row
    const completedMatches = matches.filter(m => m.status === 'completed');
    const recentRounds = getLastNRounds(completedMatches.reverse(), 2);
    
    // Heavy penalty for recent partnerships (within last 2 rounds)
    recentRounds.forEach(round => {
      round.forEach(match => {
        // Check if team1 partnership was recent
        if (match.team1.length === 2) {
          const [p1, p2] = match.team1;
          if ((config.team1[0] === p1 && config.team1[1] === p2) ||
              (config.team1[0] === p2 && config.team1[1] === p1)) {
            score += algConfig.recentPartnershipPenalty;
          }
          if ((config.team2[0] === p1 && config.team2[1] === p2) ||
              (config.team2[0] === p2 && config.team2[1] === p1)) {
            score += algConfig.recentPartnershipPenalty;
          }
        }
        
        // Check if team2 partnership was recent
        if (match.team2.length === 2) {
          const [p1, p2] = match.team2;
          if ((config.team1[0] === p1 && config.team1[1] === p2) ||
              (config.team1[0] === p2 && config.team1[1] === p1)) {
            score += algConfig.recentPartnershipPenalty;
          }
          if ((config.team2[0] === p1 && config.team2[1] === p2) ||
              (config.team2[0] === p2 && config.team2[1] === p1)) {
            score += algConfig.recentPartnershipPenalty;
          }
        }
        
        // Heavy penalty for recent opponent pairings
        const matchPlayers = [...match.team1, ...match.team2];
        const configPlayers = [...config.team1, ...config.team2];
        let overlapCount = 0;
        for (const p of configPlayers) {
          if (matchPlayers.includes(p)) overlapCount++;
        }
        // If backToBackOverlapThreshold+ players overlap with a recent match, penalize
        if (overlapCount >= algConfig.backToBackOverlapThreshold) {
          score += algConfig.recentOverlapPenalty;
        }
      });
    });
    
    // Count actual opponent frequencies (all-time, not just recent)
    let totalOpponentCount = 0;
    for (const p1 of config.team1) {
      for (const p2 of config.team2) {
        const opponentCount = getOpponentCount(p1, p2, matches);
        totalOpponentCount += opponentCount;
      }
    }
    
    // Lighter penalty for repeated opponent matchups
    score += totalOpponentCount * algConfig.opponentRepeatPenalty;
    
    // Prefer balanced teams (similar strength)
    // Calculate team strength using both win rate and point differential
    const getTeamStrength = (teamPlayers: string[]): number => {
      let totalStrength = 0;
      for (const playerId of teamPlayers) {
        const stats = playerStats.get(playerId)!;
        // Win rate contribution (0.5 to 1.0 range typically)
        const winRateStrength = stats.gamesPlayed > 0 ? stats.wins / stats.gamesPlayed : 0.5;
        // Point differential contribution (normalized)
        const pointDiff = stats.gamesPlayed > 0 ? 
          (stats.totalPointsFor - stats.totalPointsAgainst) / (stats.gamesPlayed * 11) : 0;
        // Combine: 70% win rate, 30% point differential for total strength
        const playerStrength = (winRateStrength * 0.7) + ((pointDiff * 0.5 + 0.5) * 0.3);
        totalStrength += playerStrength;
      }
      return totalStrength / teamPlayers.length;
    };
    
    const team1Strength = getTeamStrength(config.team1);
    const team2Strength = getTeamStrength(config.team2);
    const strengthDifference = Math.abs(team1Strength - team2Strength);
    
    // Apply HEAVY penalty for unbalanced teams (increased from basic win rate comparison)
    score += strengthDifference * algConfig.teamBalancePenalty * 2;
    
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
  // Track partners and opponents (but don't increment gamesPlayed until match is completed)
  [...team1, ...team2].forEach((playerId) => {
    const stats = statsMap.get(playerId);
    if (stats) {
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
 * Generate King of Court round with locked teams (continuous flow)
 */
function generateLockedTeamsKingOfCourtRound(session: Session): Match[] {
  const { config, playerStats, matches } = session;
  const { courts, lockedTeams } = config;
  
  if (!lockedTeams || lockedTeams.length < 2) {
    return [];
  }
  
  // Get teams currently in active matches
  const busyTeamIndices = new Set<number>();
  const teamIndexMap = new Map<string, number>();
  lockedTeams.forEach((team, idx) => {
    const key = [...team].sort().join(',');
    teamIndexMap.set(key, idx);
  });
  
  matches.forEach(match => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      const team1Key = [...match.team1].sort().join(',');
      const team2Key = [...match.team2].sort().join(',');
      
      const team1Idx = teamIndexMap.get(team1Key);
      const team2Idx = teamIndexMap.get(team2Key);
      
      if (team1Idx !== undefined) busyTeamIndices.add(team1Idx);
      if (team2Idx !== undefined) busyTeamIndices.add(team2Idx);
    }
  });
  
  // Get currently occupied courts
  const occupiedCourts = new Set<number>();
  matches.forEach(match => {
    if (match.status === 'in-progress' || match.status === 'waiting') {
      occupiedCourts.add(match.courtNumber);
    }
  });
  
  // Get team stats (aggregate from individual players) for available teams
  const teamStats = lockedTeams
    .map((team, idx) => {
      if (busyTeamIndices.has(idx)) return null;
      
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
    })
    .filter(t => t !== null) as Array<{
      teamIdx: number;
      team: string[];
      gamesPlayed: number;
      gamesWaited: number;
      wins: number;
      winRate: number;
    }>;
  
  if (teamStats.length < 2) {
    return [];
  }
  
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
  
  // Calculate rankings for locked teams based on win rate
  const rankedTeams = [...teamStats].sort((a, b) => {
    // Sort by win rate first
    if (b.winRate !== a.winRate) {
      return b.winRate - a.winRate;
    }
    // Then by total wins
    return b.wins - a.wins;
  });
  
  // Assign ranks
  rankedTeams.forEach((team, index) => {
    (team as any).rank = index + 1;
  });
  
  // Determine half-pool boundary
  const totalTeams = lockedTeams.length;
  const halfPool = Math.ceil(totalTeams / 2);
  
  // Check if we should enforce half-pool constraints
  // At the start of a session (no completed matches), rankings are arbitrary, so skip the constraint
  const completedMatchCount = matches.filter(m => m.status === 'completed').length;
  const enforceHalfPool = completedMatchCount >= Math.min(4, Math.floor(totalTeams / 2));
  
  const newMatches: Match[] = [];
  const usedTeamIndices = new Set<number>();
  
  for (let courtNum = 1; courtNum <= courts; courtNum++) {
    // Skip if court is occupied
    if (occupiedCourts.has(courtNum)) {
      continue;
    }
    
    const availableTeams = sortedTeams.filter(t => !usedTeamIndices.has(t.teamIdx));
    
    if (availableTeams.length < 2) {
      break;
    }
    
    // Take first team
    const team1Data = availableTeams[0];
    const team1Rank = (rankedTeams.find(t => t.teamIdx === team1Data.teamIdx) as any)?.rank || 1;
    const team1TopHalf = team1Rank <= halfPool;
    
    // Find best opponent for team1 (similar win rate, not recent opponent, same half)
    let bestOpponent = null;
    let bestScore = Infinity;
    
    for (let i = 1; i < availableTeams.length; i++) {
      const team2Data = availableTeams[i];
      const team2Rank = (rankedTeams.find(t => t.teamIdx === team2Data.teamIdx) as any)?.rank || 1;
      const team2TopHalf = team2Rank <= halfPool;
      
      // HARD CONSTRAINT: Teams must be in the same half (top vs top, bottom vs bottom)
      // BUT: Skip this constraint at the start of the session when rankings aren't established
      if (enforceHalfPool && team1TopHalf !== team2TopHalf) {
        continue; // Skip teams from different halves
      }
      
      // Check if this would be a back-to-back matchup (same 4 players as last match)
      const proposedPlayers = [...team1Data.team, ...team2Data.team];
      if (isBackToBackGame(proposedPlayers, matches)) {
        continue; // Skip back-to-back matchups
      }
      
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
    
    // If no valid opponent found (due to constraints), skip this court
    if (!bestOpponent) {
      continue;
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
