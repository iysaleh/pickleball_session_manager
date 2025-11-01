import type { Player, TeamPair, PlayerStats, QueuedMatch, SessionType } from './types';
import { isPairBanned } from './utils';

/**
 * Generate all possible round-robin matches for a set of players
 * Optimizes for maximum partner and opponent diversity
 */
export function generateRoundRobinQueue(
  players: Player[],
  sessionType: SessionType,
  bannedPairs: TeamPair[],
  maxMatches?: number
): QueuedMatch[] {
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
