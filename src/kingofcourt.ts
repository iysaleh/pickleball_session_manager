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

// Base ELO rating for new players
const BASE_RATING = 1500;
const K_FACTOR = 32; // Standard ELO K-factor
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
export function calculatePlayerRating(stats: PlayerStats): number {
  if (stats.gamesPlayed === 0) {
    return BASE_RATING; // New players start at base rating
  }
  
  // Start with base rating
  let rating = BASE_RATING;
  
  // Adjust based on win rate with diminishing returns
  const winRate = stats.wins / stats.gamesPlayed;
  const winRateAdjustment = Math.log(1 + winRate * 9) * 200; // Logarithmic scaling
  rating += winRateAdjustment - 200; // Center around BASE_RATING for 50% win rate
  
  // Adjust based on point differential (quality of wins/losses)
  const avgPointDiff = (stats.totalPointsFor - stats.totalPointsAgainst) / stats.gamesPlayed;
  const pointDiffAdjustment = Math.log(1 + Math.abs(avgPointDiff)) * 50 * Math.sign(avgPointDiff);
  rating += pointDiffAdjustment;
  
  // Bonus for consistency (more games played with good win rate)
  if (stats.gamesPlayed >= 5 && winRate >= 0.6) {
    rating += Math.log(stats.gamesPlayed) * 30;
  }
  
  return Math.max(800, Math.min(2200, rating)); // Clamp between 800-2200
}

/**
 * Calculate rankings for all players
 */
function calculatePlayerRankings(
  playerIds: string[],
  playerStats: Map<string, PlayerStats>
): PlayerRating[] {
  const ratings: PlayerRating[] = playerIds.map(playerId => {
    const stats = playerStats.get(playerId)!;
    const rating = calculatePlayerRating(stats);
    const isProvisional = stats.gamesPlayed < 3; // Need 3+ games for stable ranking
    
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
  const player1TopHalf = player1Rank <= halfPool;
  const player2TopHalf = player2Rank <= halfPool;
  
  // Players must be in the same half
  if (player1TopHalf !== player2TopHalf) {
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
  const allRankings = calculatePlayerRankings(allActivePlayerIds, playerStats);
  
  // Get rankings for available players
  const availableRankings = allRankings.filter(r => availablePlayerIds.includes(r.playerId));
  
  // Check if we should wait for better matchups
  const shouldWait = shouldWaitForRankBasedMatchups(
    availableRankings,
    allRankings.length,
    playerStats,
    matches,
    occupiedCourts.size,
    playersPerMatch
  );
  
  if (shouldWait) {
    return []; // Wait for more courts to finish for better matchups
  }
  
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
    courts
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
 * Returns true if 3 or more of the same players were in the last match
 * 
 * Example violations:
 * - Last match: A, B, C, D
 * - Current match: A, B, C, E (3 overlapping - NOT ALLOWED)
 * - Current match: A, B, E, F (2 overlapping - ALLOWED)
 */
function isBackToBackGame(
  playerIds: string[],
  matches: Match[]
): boolean {
  // Get the most recent completed match
  const completedMatches = matches.filter(m => m.status === 'completed');
  if (completedMatches.length === 0) return false;
  
  // Sort by endTime to get the most recent
  const sortedMatches = [...completedMatches].sort((a, b) => {
    const timeA = a.endTime || 0;
    const timeB = b.endTime || 0;
    return timeB - timeA;
  });
  
  const lastMatch = sortedMatches[0];
  const lastMatchPlayers = new Set([...lastMatch.team1, ...lastMatch.team2]);
  
  // Count how many players from the proposed group were in the last match
  let overlapCount = 0;
  for (const playerId of playerIds) {
    if (lastMatchPlayers.has(playerId)) {
      overlapCount++;
    }
  }
  
  // Reject if 3 or more players are the same (75% overlap)
  // This ensures at least 2 new players in each match for good variety
  return overlapCount >= 3;
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
 * Determine if we should wait for more courts to finish before scheduling (ranking-based)
 */
function shouldWaitForRankBasedMatchups(
  availableRankings: PlayerRating[],
  totalActivePlayers: number,
  playerStats: Map<string, PlayerStats>,
  matches: Match[],
  numBusyCourts: number,
  playersPerMatch: number
): boolean {
  // Don't wait if no courts are busy (first round or all courts idle)
  if (numBusyCourts === 0) {
    return false;
  }
  
  // Don't wait if we don't have enough players for even one match
  if (availableRankings.length < playersPerMatch) {
    return false;
  }
  
  // Check if anyone has waited too long
  const availablePlayerIds = availableRankings.map(r => r.playerId);
  const consecutiveWaits = countConsecutiveWaits(availablePlayerIds, matches);
  const maxConsecutiveWaits = Math.max(...Array.from(consecutiveWaits.values()));
  
  // Never wait if someone has already waited 1+ times (reduced from 2)
  if (maxConsecutiveWaits >= 1) {
    return false;
  }
  
  // Don't wait if we have enough players for multiple matches (reduced from 3x to 2x)
  if (availableRankings.length >= playersPerMatch * 2) {
    return false;
  }
  
  // Need at least 6 completed matches to make meaningful ranking decisions (reduced from 12)
  const completedMatches = matches.filter(m => m.status === 'completed');
  if (completedMatches.length < 6) {
    return false;
  }
  
  // Only consider waiting if we have at least 2 busy courts (reduced from 3)
  if (numBusyCourts < 2) {
    return false;
  }
  
  // Check if we can make a valid rank-based match with current players
  const canMakeValidMatch = canCreateValidRankMatch(
    availableRankings,
    totalActivePlayers,
    playersPerMatch
  );
  
  // If we can't make a valid match at all, don't wait - just accept what we have
  if (!canMakeValidMatch) {
    return false;
  }
  
  // CRITICAL CHECK: Detect if we're in a "single court loop" scenario
  // (same small group playing repeatedly while other courts are idle)
  const inSingleCourtLoop = detectSingleCourtLoop(
    availableRankings.map(r => r.playerId),
    matches,
    numBusyCourts,
    playersPerMatch
  );
  
  // If we're in a single court loop AND have multiple busy courts, WAIT for other courts to finish
  // Lowered threshold from 4 to 2 busy courts to trigger waiting more often
  if (inSingleCourtLoop && numBusyCourts >= 2) {
    return true;
  }
  
  // NEW: Check for high-repetition matchups even if not a perfect "loop"
  // If the available players have very high overlap with recent matches, wait for variety
  const hasHighRepetition = detectHighRepetitionMatchup(
    availablePlayerIds,
    matches,
    numBusyCourts,
    playersPerMatch
  );
  
  // If we have high repetition AND multiple courts finishing soon, wait
  if (hasHighRepetition && numBusyCourts >= 2) {
    return true;
  }
  
  // Generally prefer to fill courts rather than wait for perfect matchups
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
  playersPerMatch: number
): boolean {
  // Only check if we have multiple courts and some are busy
  if (numBusyCourts < 2) return false;
  
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
  
  // If this group has played together 2+ times in last 10 matches, we're looping (reduced from 3)
  if (groupPlayCount >= 2) {
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
  playersPerMatch: number
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
  
  // If more than 60% of the pairs played together recently, we have high repetition
  // (This would catch cases like players 1 & 2 playing together 3 times in last 5 matches)
  if (totalPairsChecked > 0 && recentPairCount / totalPairsChecked > 0.6) {
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
  totalCourts: number
): Match[] {
  const newMatches: Match[] = [];
  const usedPlayers = new Set<string>();
  
  // Sort available players by wait priority
  const sortedRankings = [...availableRankings].sort((a, b) => {
    const statsA = playerStats.get(a.playerId)!;
    const statsB = playerStats.get(b.playerId)!;
    
    // Prioritize by games waited
    if (statsA.gamesWaited !== statsB.gamesWaited) {
      return statsB.gamesWaited - statsA.gamesWaited;
    }
    
    // Then by games played (fewer = higher priority)
    return statsA.gamesPlayed - statsB.gamesPlayed;
  });
  
  // Try to create matches for each available court
  for (let courtNum = 1; courtNum <= totalCourts; courtNum++) {
    if (occupiedCourts.has(courtNum)) {
      continue;
    }
    
    const remainingRankings = sortedRankings.filter(r => !usedPlayers.has(r.playerId));
    
    if (remainingRankings.length < playersPerMatch) {
      break;
    }
    
    // Try to select players for this match
    const selectedPlayers = selectPlayersForRankMatch(
      remainingRankings,
      totalActivePlayers,
      playersPerMatch,
      playerStats,
      matches
    );
    
    if (!selectedPlayers || selectedPlayers.length < playersPerMatch) {
      continue; // Try next court instead of breaking
    }
    
    // Divide into teams
    const teamAssignment = assignTeams(
      selectedPlayers,
      playersPerTeam,
      playerStats,
      matches,
      bannedPairs
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
    
    // Mark these players as used
    selectedPlayers.forEach(id => usedPlayers.add(id));
  }
  
  return newMatches;
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
  matches: Match[]
): string[] | null {
  if (availableRankings.length < playersPerMatch) {
    return null;
  }
  
  // CRITICAL: At session start (no completed matches), be very aggressive about filling courts
  // Rankings don't exist yet, so just take first available players
  const completedMatches = matches.filter(m => m.status === 'completed');
  if (completedMatches.length === 0) {
    // Simply take the first playersPerMatch available players
    return availableRankings.slice(0, playersPerMatch).map(r => r.playerId);
  }
  
  // Calculate soft preference frequency (used for scoring)
  // Try to avoid same person more than once per (totalPlayers/6) games, but don't hard block
  const softRepetitionFrequency = Math.max(3, Math.floor(totalActivePlayers / 6));
  
  // Strategy 1: Try to find a group of closely-ranked players (within 4 ranks) with variety constraints
  for (let i = 0; i < availableRankings.length; i++) {
    const anchor = availableRankings[i];
    const closeGroup: PlayerRating[] = [anchor];
    
    for (let j = 0; j < availableRankings.length; j++) {
      if (i === j) continue;
      const candidate = availableRankings[j];
      
      const rankDiff = Math.abs(anchor.rank - candidate.rank);
      
      // Check if close in rank and can play together
      if (rankDiff <= 4 && canPlayTogether(
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
      if (isBackToBackGame(groupPlayerIds.slice(0, playersPerMatch), matches)) {
        continue; // Skip this group
      }
      
      const varietyScore = calculateGroupVarietyScore(groupPlayerIds, matches);
      const closenessScore = calculateGroupClosenessScore(closeGroup);
      const repetitionScore = calculateGroupRepetitionScore(groupPlayerIds, matches, playerStats, softRepetitionFrequency);
      
      // If this is a good group (good variety OR close ranks AND reasonable repetition), use it
      if ((varietyScore > 0.5 || closenessScore < 3) && repetitionScore < 0.8) {
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
        if (isBackToBackGame(groupPlayerIds, matches)) {
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
      if (!isBackToBackGame(groupPlayerIds, matches)) {
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
    score += team1PartnerCount * 80;
    score += team2PartnerCount * 80;
    
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
            score += 300; // HEAVY penalty for recent partnership
          }
          if ((config.team2[0] === p1 && config.team2[1] === p2) ||
              (config.team2[0] === p2 && config.team2[1] === p1)) {
            score += 300; // HEAVY penalty for recent partnership
          }
        }
        
        // Check if team2 partnership was recent
        if (match.team2.length === 2) {
          const [p1, p2] = match.team2;
          if ((config.team1[0] === p1 && config.team1[1] === p2) ||
              (config.team1[0] === p2 && config.team1[1] === p1)) {
            score += 300; // HEAVY penalty for recent partnership
          }
          if ((config.team2[0] === p1 && config.team2[1] === p2) ||
              (config.team2[0] === p2 && config.team2[1] === p1)) {
            score += 300; // HEAVY penalty for recent partnership
          }
        }
        
        // Heavy penalty for recent opponent pairings
        const matchPlayers = [...match.team1, ...match.team2];
        const configPlayers = [...config.team1, ...config.team2];
        let overlapCount = 0;
        for (const p of configPlayers) {
          if (matchPlayers.includes(p)) overlapCount++;
        }
        // If 3+ players overlap with a recent match, penalize
        if (overlapCount >= 3) {
          score += 200; // Heavy penalty for playing with mostly same people recently
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
    score += totalOpponentCount * 25;
    
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
