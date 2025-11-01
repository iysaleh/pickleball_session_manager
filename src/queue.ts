import type { Player, TeamPair, PlayerStats, QueuedMatch, SessionType } from './types';
import { isPairBanned } from './utils';

/**
 * Generate all possible round-robin matches for a set of players
 * Optimizes for maximum partner diversity
 */
export function generateRoundRobinQueue(
  players: Player[],
  sessionType: SessionType,
  bannedPairs: TeamPair[]
): QueuedMatch[] {
  const playersPerTeam = sessionType === 'singles' ? 1 : 2;
  const playersPerMatch = playersPerTeam * 2;
  
  if (players.length < playersPerMatch) {
    return [];
  }
  
  const matches: QueuedMatch[] = [];
  const playerIds = players.map(p => p.id);
  
  // Track partnerships for diversity
  const partnershipCount = new Map<string, Map<string, number>>();
  playerIds.forEach(id => {
    partnershipCount.set(id, new Map());
  });
  
  // Generate all possible combinations
  const allCombinations = generateCombinations(playerIds, playersPerMatch);
  
  // Score each combination based on partner diversity
  const scoredCombinations = allCombinations.map(combo => {
    const team1 = combo.slice(0, playersPerTeam);
    const team2 = combo.slice(playersPerTeam);
    
    // Check if valid (no banned pairs)
    if (!isValidTeamConfiguration(team1, team2, bannedPairs)) {
      return { combo, team1, team2, score: -1 };
    }
    
    // Calculate diversity score (lower is better)
    let score = 0;
    
    // Score team partnerships
    for (let i = 0; i < team1.length; i++) {
      for (let j = i + 1; j < team1.length; j++) {
        const count = partnershipCount.get(team1[i])?.get(team1[j]) || 0;
        score += count * 10;
      }
    }
    
    for (let i = 0; i < team2.length; i++) {
      for (let j = i + 1; j < team2.length; j++) {
        const count = partnershipCount.get(team2[i])?.get(team2[j]) || 0;
        score += count * 10;
      }
    }
    
    return { combo, team1, team2, score };
  });
  
  // Sort by score and select matches
  const validCombinations = scoredCombinations
    .filter(c => c.score >= 0)
    .sort((a, b) => a.score - b.score);
  
  // Build match schedule
  const usedPlayers = new Set<string>();
  
  for (const combination of validCombinations) {
    // Check if any players in this match are already used
    const hasUsedPlayer = combination.combo.some(id => usedPlayers.has(id));
    if (hasUsedPlayer) continue;
    
    // Add match
    matches.push({
      team1: combination.team1,
      team2: combination.team2
    });
    
    // Mark players as used
    combination.combo.forEach(id => usedPlayers.add(id));
    
    // Update partnership counts
    for (let i = 0; i < combination.team1.length; i++) {
      for (let j = i + 1; j < combination.team1.length; j++) {
        const p1 = combination.team1[i];
        const p2 = combination.team1[j];
        const count = partnershipCount.get(p1)?.get(p2) || 0;
        partnershipCount.get(p1)?.set(p2, count + 1);
        partnershipCount.get(p2)?.set(p1, count + 1);
      }
    }
    
    for (let i = 0; i < combination.team2.length; i++) {
      for (let j = i + 1; j < combination.team2.length; j++) {
        const p1 = combination.team2[i];
        const p2 = combination.team2[j];
        const count = partnershipCount.get(p1)?.get(p2) || 0;
        partnershipCount.get(p1)?.set(p2, count + 1);
        partnershipCount.get(p2)?.set(p1, count + 1);
      }
    }
    
    // If we've used all players, reset for next round
    if (usedPlayers.size >= playerIds.length - (playerIds.length % playersPerMatch)) {
      usedPlayers.clear();
    }
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
