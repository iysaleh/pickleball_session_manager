import type { Player, TeamPair, PlayerStats, QueuedMatch, SessionType, LockedTeam } from './types';
import { isPairBanned } from './utils';

/**
 * Generate all possible round-robin matches for a set of players
 * Optimizes for maximum partner and opponent diversity
 */
export function generateRoundRobinQueue(
  players: Player[],
  sessionType: SessionType,
  bannedPairs: TeamPair[],
  maxMatches?: number,
  lockedTeams?: LockedTeam[]
): QueuedMatch[] {
  // If locked teams mode, use special generator
  if (lockedTeams && lockedTeams.length > 0) {
    return generateLockedTeamsRoundRobinQueue(lockedTeams, maxMatches);
  }
  
  const playersPerTeam = sessionType === 'singles' ? 1 : 2;
  const playersPerMatch = playersPerTeam * 2;
  
  if (players.length < playersPerMatch) {
    return [];
  }
  
  const matches: QueuedMatch[] = [];
  const playerIds = players.map(p => p.id);
  
  // Track partnerships and opponent interactions for diversity
  const partnershipCount = new Map<string, Map<string, number>>();
  const opponentCount = new Map<string, Map<string, number>>();
  const fourPlayerGroupCount = new Map<string, number>(); // Track when same 4 players meet
  const gamesPlayed = new Map<string, number>(); // Track total games per player
  
  playerIds.forEach(id => {
    partnershipCount.set(id, new Map());
    opponentCount.set(id, new Map());
    gamesPlayed.set(id, 0);
  });
  
  // Track which exact matchups have been used (to avoid duplicates)
  const usedMatchups = new Set<string>();
  
  function getMatchupKey(team1: string[], team2: string[]): string {
    const sorted1 = [...team1].sort().join(',');
    const sorted2 = [...team2].sort().join(',');
    return [sorted1, sorted2].sort().join('|');
  }
  
  function getFourPlayerGroupKey(team1: string[], team2: string[]): string {
    return [...team1, ...team2].sort().join(',');
  }
  
  // Generate all possible combinations
  const allCombinations = generateCombinations(playerIds, playersPerMatch);
  
  // Convert combinations to all possible team configurations
  const allMatchups: Array<{ team1: string[], team2: string[], combo: string[] }> = [];
  
  for (const combo of allCombinations) {
    if (playersPerTeam === 2) {
      const partitions = [
        { team1: [combo[0], combo[1]], team2: [combo[2], combo[3]] },
        { team1: [combo[0], combo[2]], team2: [combo[1], combo[3]] },
        { team1: [combo[0], combo[3]], team2: [combo[1], combo[2]] },
      ];
      
      for (const partition of partitions) {
        allMatchups.push({
          team1: partition.team1,
          team2: partition.team2,
          combo
        });
      }
    } else {
      allMatchups.push({
        team1: [combo[0]],
        team2: [combo[1]],
        combo
      });
    }
  }
  
  let iterations = 0;
  const maxIterations = allMatchups.length * 10;
  
  while (iterations < maxIterations && (!maxMatches || matches.length < maxMatches)) {
    const scoredMatchups = allMatchups.map(matchup => {
      const { team1, team2, combo } = matchup;
      
      const matchupKey = getMatchupKey(team1, team2);
      if (usedMatchups.has(matchupKey)) {
        return { ...matchup, score: -1 };
      }
      
      if (!isValidTeamConfiguration(team1, team2, bannedPairs)) {
        return { ...matchup, score: -1 };
      }
      
      // Calculate diversity score (lower is better)
      let score = 0;
      
      // PRIORITIZE players who have played fewer games (most important factor)
      const allPlayersInMatch = [...team1, ...team2];
      const totalGamesForPlayers = allPlayersInMatch.reduce((sum, id) => sum + (gamesPlayed.get(id) || 0), 0);
      score += totalGamesForPlayers * 1000;
      
      // HEAVILY penalize same 4-player groups meeting again soon
      const groupKey = getFourPlayerGroupKey(team1, team2);
      const groupCount = fourPlayerGroupCount.get(groupKey) || 0;
      score += groupCount * 500; // Heavy penalty
      
      // Penalize repeat partnerships
      for (let i = 0; i < team1.length; i++) {
        for (let j = i + 1; j < team1.length; j++) {
          const count = partnershipCount.get(team1[i])?.get(team1[j]) || 0;
          score += count * 100;
        }
      }
      
      for (let i = 0; i < team2.length; i++) {
        for (let j = i + 1; j < team2.length; j++) {
          const count = partnershipCount.get(team2[i])?.get(team2[j]) || 0;
          score += count * 100;
        }
      }
      
      // Penalize repeat opponent matchups (but less than partnerships)
      for (const p1 of team1) {
        for (const p2 of team2) {
          const count = opponentCount.get(p1)?.get(p2) || 0;
          score += count * 50;
        }
      }
      
      return { ...matchup, score };
    });
    
    const validMatchups = scoredMatchups
      .filter(m => m.score >= 0)
      .sort((a, b) => a.score - b.score);
    
    if (validMatchups.length === 0) {
      break;
    }
    
    const usedPlayersThisRound = new Set<string>();
    let addedMatchesThisRound = false;
    
    for (const matchup of validMatchups) {
      if (maxMatches && matches.length >= maxMatches) {
        break;
      }
      
      const hasUsedPlayer = matchup.combo.some(id => usedPlayersThisRound.has(id));
      if (hasUsedPlayer) continue;
      
      matches.push({
        team1: matchup.team1,
        team2: matchup.team2
      });
      
      addedMatchesThisRound = true;
      
      usedMatchups.add(getMatchupKey(matchup.team1, matchup.team2));
      matchup.combo.forEach(id => usedPlayersThisRound.add(id));
      
      // Update games played count
      matchup.combo.forEach(id => {
        gamesPlayed.set(id, (gamesPlayed.get(id) || 0) + 1);
      });
      
      // Update 4-player group count
      const groupKey = getFourPlayerGroupKey(matchup.team1, matchup.team2);
      fourPlayerGroupCount.set(groupKey, (fourPlayerGroupCount.get(groupKey) || 0) + 1);
      
      // Update partnership counts
      for (let i = 0; i < matchup.team1.length; i++) {
        for (let j = i + 1; j < matchup.team1.length; j++) {
          const p1 = matchup.team1[i];
          const p2 = matchup.team1[j];
          const count = partnershipCount.get(p1)?.get(p2) || 0;
          partnershipCount.get(p1)?.set(p2, count + 1);
          partnershipCount.get(p2)?.set(p1, count + 1);
        }
      }
      
      for (let i = 0; i < matchup.team2.length; i++) {
        for (let j = i + 1; j < matchup.team2.length; j++) {
          const p1 = matchup.team2[i];
          const p2 = matchup.team2[j];
          const count = partnershipCount.get(p1)?.get(p2) || 0;
          partnershipCount.get(p1)?.set(p2, count + 1);
          partnershipCount.get(p2)?.set(p1, count + 1);
        }
      }
      
      // Update opponent counts
      for (const p1 of matchup.team1) {
        for (const p2 of matchup.team2) {
          const count1 = opponentCount.get(p1)?.get(p2) || 0;
          const count2 = opponentCount.get(p2)?.get(p1) || 0;
          opponentCount.get(p1)?.set(p2, count1 + 1);
          opponentCount.get(p2)?.set(p1, count2 + 1);
        }
      }
    }
    
    if (!addedMatchesThisRound) {
      break;
    }
    
    if (maxMatches && matches.length >= maxMatches) {
      break;
    }
    
    iterations++;
  }
  
  return matches;
}

function generateCombinations(arr: string[], size: number): string[][] {
  const results: string[][] = [];
  
  function combine(start: number, combo: string[]) {
    if (combo.length === size) {
      results.push([...combo]);
      return;
    }
    
    for (let i = start; i < arr.length; i++) {
      combo.push(arr[i]);
      combine(i + 1, combo);
      combo.pop();
    }
  }
  
  combine(0, []);
  return results;
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

/**
 * Generate round-robin matches for locked teams
 * Teams stay together, only opponents change
 */
function generateLockedTeamsRoundRobinQueue(
  lockedTeams: LockedTeam[],
  maxMatches?: number
): QueuedMatch[] {
  const matches: QueuedMatch[] = [];
  
  if (lockedTeams.length < 2) {
    return [];
  }
  
  // Track which team pairings have been used
  const usedPairings = new Set<string>();
  const gamesPlayed = new Map<number, number>(); // team index -> games count
  const opponentCount = new Map<number, Map<number, number>>(); // team -> opponent -> count
  
  lockedTeams.forEach((_, idx) => {
    gamesPlayed.set(idx, 0);
    opponentCount.set(idx, new Map());
  });
  
  function getPairingKey(team1Idx: number, team2Idx: number): string {
    return [team1Idx, team2Idx].sort().join('-');
  }
  
  let iterations = 0;
  const maxIterations = lockedTeams.length * lockedTeams.length * 10;
  
  while (iterations < maxIterations && (!maxMatches || matches.length < maxMatches)) {
    // Score all possible pairings
    const scoredPairings: Array<{ team1Idx: number; team2Idx: number; score: number }> = [];
    
    for (let i = 0; i < lockedTeams.length; i++) {
      for (let j = i + 1; j < lockedTeams.length; j++) {
        const pairingKey = getPairingKey(i, j);
        
        if (usedPairings.has(pairingKey)) {
          continue;
        }
        
        // Calculate score (lower is better)
        let score = 0;
        
        // Prioritize teams with fewer games
        score += (gamesPlayed.get(i) || 0) * 1000;
        score += (gamesPlayed.get(j) || 0) * 1000;
        
        // Penalize teams that have played each other before
        const prevOpponentCount = opponentCount.get(i)?.get(j) || 0;
        score += prevOpponentCount * 500;
        
        scoredPairings.push({ team1Idx: i, team2Idx: j, score });
      }
    }
    
    if (scoredPairings.length === 0) {
      break;
    }
    
    // Sort by score and try to assign matches
    scoredPairings.sort((a, b) => a.score - b.score);
    
    const usedTeamsThisRound = new Set<number>();
    let addedMatchesThisRound = false;
    
    for (const pairing of scoredPairings) {
      if (maxMatches && matches.length >= maxMatches) {
        break;
      }
      
      if (usedTeamsThisRound.has(pairing.team1Idx) || usedTeamsThisRound.has(pairing.team2Idx)) {
        continue;
      }
      
      matches.push({
        team1: lockedTeams[pairing.team1Idx],
        team2: lockedTeams[pairing.team2Idx],
      });
      
      addedMatchesThisRound = true;
      usedPairings.add(getPairingKey(pairing.team1Idx, pairing.team2Idx));
      usedTeamsThisRound.add(pairing.team1Idx);
      usedTeamsThisRound.add(pairing.team2Idx);
      
      // Update tracking
      gamesPlayed.set(pairing.team1Idx, (gamesPlayed.get(pairing.team1Idx) || 0) + 1);
      gamesPlayed.set(pairing.team2Idx, (gamesPlayed.get(pairing.team2Idx) || 0) + 1);
      
      const count = opponentCount.get(pairing.team1Idx)?.get(pairing.team2Idx) || 0;
      opponentCount.get(pairing.team1Idx)?.set(pairing.team2Idx, count + 1);
      opponentCount.get(pairing.team2Idx)?.set(pairing.team1Idx, count + 1);
    }
    
    if (!addedMatchesThisRound) {
      break;
    }
    
    iterations++;
  }
  
  return matches;
}
