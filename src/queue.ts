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
  
  // Track which exact matchups have been used (to avoid duplicates)
  const usedMatchups = new Set<string>();
  
  function getMatchupKey(team1: string[], team2: string[]): string {
    // Create a unique key for this matchup regardless of team order
    const sorted1 = [...team1].sort().join(',');
    const sorted2 = [...team2].sort().join(',');
    // Sort the two teams to ensure [A,B] vs [C,D] is same as [C,D] vs [A,B]
    return [sorted1, sorted2].sort().join('|');
  }
  
  // Generate all possible combinations
  const allCombinations = generateCombinations(playerIds, playersPerMatch);
  
  // Convert combinations to all possible team configurations
  const allMatchups: Array<{ team1: string[], team2: string[], combo: string[] }> = [];
  
  for (const combo of allCombinations) {
    // For doubles/teams, we need to consider all ways to split the combo into two teams
    if (playersPerTeam === 2) {
      // Generate all ways to partition 4 players into two teams of 2
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
      // Singles - only one way to split
      allMatchups.push({
        team1: [combo[0]],
        team2: [combo[1]],
        combo
      });
    }
  }
  
  // Continue generating matches until we've exhausted all unique matchups
  let iterations = 0;
  const maxIterations = allMatchups.length * 10; // Safety limit
  
  while (iterations < maxIterations) {
    // Score each matchup based on partner diversity
    const scoredMatchups = allMatchups.map(matchup => {
      const { team1, team2, combo } = matchup;
      
      // Check if this exact matchup was already used
      const matchupKey = getMatchupKey(team1, team2);
      if (usedMatchups.has(matchupKey)) {
        return { ...matchup, score: -1 };
      }
      
      // Check if valid (no banned pairs)
      if (!isValidTeamConfiguration(team1, team2, bannedPairs)) {
        return { ...matchup, score: -1 };
      }
      
      // Calculate diversity score (lower is better)
      let score = 0;
      
      // Score team partnerships (penalize repeat partnerships)
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
      
      return { ...matchup, score };
    });
    
    // Sort by score and select matches for this round
    const validMatchups = scoredMatchups
      .filter(m => m.score >= 0)
      .sort((a, b) => a.score - b.score);
    
    if (validMatchups.length === 0) {
      // No more valid matchups available
      break;
    }
    
    // Build one round of matches
    const usedPlayersThisRound = new Set<string>();
    let addedMatchesThisRound = false;
    
    for (const matchup of validMatchups) {
      // Check if any players in this match are already used this round
      const hasUsedPlayer = matchup.combo.some(id => usedPlayersThisRound.has(id));
      if (hasUsedPlayer) continue;
      
      // Add match
      matches.push({
        team1: matchup.team1,
        team2: matchup.team2
      });
      
      addedMatchesThisRound = true;
      
      // Mark this matchup as used permanently
      usedMatchups.add(getMatchupKey(matchup.team1, matchup.team2));
      
      // Mark players as used this round
      matchup.combo.forEach(id => usedPlayersThisRound.add(id));
      
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
    }
    
    if (!addedMatchesThisRound) {
      // No matches could be added this round
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
