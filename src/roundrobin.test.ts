import { describe, it, expect } from 'vitest';
import { generateRoundRobinQueue } from './queue';
import type { Player, TeamPair, QueuedMatch } from './types';

function createTestPlayers(count: number): Player[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `player${i + 1}`,
    name: `Player ${i + 1}`,
  }));
}

function analyzePartnerDiversity(matches: QueuedMatch[]): Map<string, Map<string, number>> {
  const partnerCounts = new Map<string, Map<string, number>>();
  
  for (const match of matches) {
    // Track team1 partnerships
    for (let i = 0; i < match.team1.length; i++) {
      for (let j = i + 1; j < match.team1.length; j++) {
        const p1 = match.team1[i];
        const p2 = match.team1[j];
        
        if (!partnerCounts.has(p1)) partnerCounts.set(p1, new Map());
        if (!partnerCounts.has(p2)) partnerCounts.set(p2, new Map());
        
        const count1 = partnerCounts.get(p1)!.get(p2) || 0;
        const count2 = partnerCounts.get(p2)!.get(p1) || 0;
        
        partnerCounts.get(p1)!.set(p2, count1 + 1);
        partnerCounts.get(p2)!.set(p1, count2 + 1);
      }
    }
    
    // Track team2 partnerships
    for (let i = 0; i < match.team2.length; i++) {
      for (let j = i + 1; j < match.team2.length; j++) {
        const p1 = match.team2[i];
        const p2 = match.team2[j];
        
        if (!partnerCounts.has(p1)) partnerCounts.set(p1, new Map());
        if (!partnerCounts.has(p2)) partnerCounts.set(p2, new Map());
        
        const count1 = partnerCounts.get(p1)!.get(p2) || 0;
        const count2 = partnerCounts.get(p2)!.get(p1) || 0;
        
        partnerCounts.get(p1)!.set(p2, count1 + 1);
        partnerCounts.get(p2)!.set(p1, count2 + 1);
      }
    }
  }
  
  return partnerCounts;
}

function analyzeOpponentDiversity(matches: QueuedMatch[]): Map<string, Map<string, number>> {
  const opponentCounts = new Map<string, Map<string, number>>();
  
  for (const match of matches) {
    // Each player in team1 plays against each player in team2
    for (const p1 of match.team1) {
      for (const p2 of match.team2) {
        if (!opponentCounts.has(p1)) opponentCounts.set(p1, new Map());
        const count = opponentCounts.get(p1)!.get(p2) || 0;
        opponentCounts.get(p1)!.set(p2, count + 1);
      }
    }
    
    // Each player in team2 plays against each player in team1
    for (const p1 of match.team2) {
      for (const p2 of match.team1) {
        if (!opponentCounts.has(p1)) opponentCounts.set(p1, new Map());
        const count = opponentCounts.get(p1)!.get(p2) || 0;
        opponentCounts.get(p1)!.set(p2, count + 1);
      }
    }
  }
  
  return opponentCounts;
}

function getMaxPartnerRepetitions(partnerCounts: Map<string, Map<string, number>>): number {
  let max = 0;
  for (const partners of partnerCounts.values()) {
    for (const count of partners.values()) {
      max = Math.max(max, count);
    }
  }
  return max;
}

function getUniquePartnersAfterNGames(
  partnerCounts: Map<string, Map<string, number>>,
  playerIds: string[],
  nGames: number,
  matches: QueuedMatch[]
): Map<string, Set<string>> {
  const uniquePartners = new Map<string, Set<string>>();
  playerIds.forEach(id => uniquePartners.set(id, new Set()));
  
  const limitedMatches = matches.slice(0, nGames);
  
  for (const match of limitedMatches) {
    // Track team1 partnerships
    for (let i = 0; i < match.team1.length; i++) {
      for (let j = i + 1; j < match.team1.length; j++) {
        uniquePartners.get(match.team1[i])?.add(match.team1[j]);
        uniquePartners.get(match.team1[j])?.add(match.team1[i]);
      }
    }
    
    // Track team2 partnerships
    for (let i = 0; i < match.team2.length; i++) {
      for (let j = i + 1; j < match.team2.length; j++) {
        uniquePartners.get(match.team2[i])?.add(match.team2[j]);
        uniquePartners.get(match.team2[j])?.add(match.team2[i]);
      }
    }
  }
  
  return uniquePartners;
}

describe('Round Robin Algorithm - Doubles', () => {
  it('should generate matches for 4 players', () => {
    const players = createTestPlayers(4);
    const matches = generateRoundRobinQueue(players, 'doubles', []);
    
    expect(matches.length).toBeGreaterThan(0);
    expect(matches[0].team1.length).toBe(2);
    expect(matches[0].team2.length).toBe(2);
  });
  
  it('should maximize partner diversity in first few games (4 players)', () => {
    const players = createTestPlayers(4);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 10);
    
    const partnerCounts = analyzePartnerDiversity(matches);
    
    // With 4 players, each player should partner with each other player
    // Player1 should partner with Player2, Player3, and Player4 at some point
    const player1Partners = partnerCounts.get('player1');
    expect(player1Partners?.size).toBe(3); // Should have 3 different partners
  });
  
  it('should maximize partner diversity early (6 players)', () => {
    const players = createTestPlayers(6);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 20);
    
    // Analyze first 6 games
    const firstSixGames = matches.slice(0, 6);
    const partnerCounts = analyzePartnerDiversity(firstSixGames);
    
    // After 6 games with 6 players, we should see good diversity
    // Each player should ideally have multiple unique partners
    const avgUniquePartners = Array.from(partnerCounts.values())
      .map(partners => partners.size)
      .reduce((sum, count) => sum + count, 0) / partnerCounts.size;
    
    // Each player should have partnered with multiple people early on
    expect(avgUniquePartners).toBeGreaterThan(1.5);
  });
  
  it('should maximize partner diversity early (8 players)', () => {
    const players = createTestPlayers(8);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 30);
    
    // Check diversity after first 10 games
    const first10Games = matches.slice(0, 10);
    const partnerCounts = analyzePartnerDiversity(first10Games);
    
    // With 8 players over 10 games, each player should have partnered with several others
    const avgUniquePartners = Array.from(partnerCounts.values())
      .map(partners => partners.size)
      .reduce((sum, count) => sum + count, 0) / partnerCounts.size;
    
    expect(avgUniquePartners).toBeGreaterThan(2);
  });
  
  it('should minimize repeat partnerships (8 players)', () => {
    const players = createTestPlayers(8);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 30);
    
    const partnerCounts = analyzePartnerDiversity(matches);
    const maxRepetitions = getMaxPartnerRepetitions(partnerCounts);
    
    // Over 30 games with 8 players, no partnership should repeat excessively
    // With perfect distribution, each pair would play together about 8-10 times
    expect(maxRepetitions).toBeLessThan(15);
  });
  
  it('should avoid duplicate matchups', () => {
    const players = createTestPlayers(6);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 50);
    
    const matchupKeys = new Set<string>();
    let duplicates = 0;
    
    for (const match of matches) {
      const sorted1 = [...match.team1].sort().join(',');
      const sorted2 = [...match.team2].sort().join(',');
      const key = [sorted1, sorted2].sort().join('|');
      
      if (matchupKeys.has(key)) {
        duplicates++;
      }
      matchupKeys.add(key);
    }
    
    expect(duplicates).toBe(0);
  });
  
  it('should respect banned pairs', () => {
    const players = createTestPlayers(6);
    const bannedPairs: TeamPair[] = [['player1', 'player2']];
    const matches = generateRoundRobinQueue(players, 'doubles', bannedPairs, 30);
    
    for (const match of matches) {
      const team1HasBanned = 
        match.team1.includes('player1') && match.team1.includes('player2');
      const team2HasBanned = 
        match.team2.includes('player1') && match.team2.includes('player2');
      
      expect(team1HasBanned).toBe(false);
      expect(team2HasBanned).toBe(false);
    }
  });
  
  it('should distribute games evenly across players (8 players)', () => {
    const players = createTestPlayers(8);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 20);
    
    const gamesPerPlayer = new Map<string, number>();
    players.forEach(p => gamesPerPlayer.set(p.id, 0));
    
    for (const match of matches) {
      [...match.team1, ...match.team2].forEach(playerId => {
        gamesPerPlayer.set(playerId, (gamesPerPlayer.get(playerId) || 0) + 1);
      });
    }
    
    const gameCounts = Array.from(gamesPerPlayer.values());
    const maxGames = Math.max(...gameCounts);
    const minGames = Math.min(...gameCounts);
    
    // Games should be relatively evenly distributed
    expect(maxGames - minGames).toBeLessThanOrEqual(2);
  });
  
  it('should prioritize new partnerships over repeated ones (12 players)', () => {
    const players = createTestPlayers(12);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 30);
    
    // Check first 20 games for diversity
    const first20 = matches.slice(0, 20);
    const partnerCounts = analyzePartnerDiversity(first20);
    
    // Count how many partnerships have repeated
    let repeatedPartnerships = 0;
    let totalPartnerships = 0;
    
    for (const partners of partnerCounts.values()) {
      for (const count of partners.values()) {
        totalPartnerships++;
        if (count > 1) {
          repeatedPartnerships++;
        }
      }
    }
    
    const repetitionRate = repeatedPartnerships / totalPartnerships;
    
    // Early in the rotation, most partnerships should be unique
    expect(repetitionRate).toBeLessThan(0.3);
  });
  
  it('should maximize unique partners in first N games (10 players)', () => {
    const players = createTestPlayers(10);
    const playerIds = players.map(p => p.id);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 50);
    
    // After 15 games, check how many unique partners each player has had
    const uniquePartners = getUniquePartnersAfterNGames(
      new Map(),
      playerIds,
      15,
      matches
    );
    
    // With 10 players, each player has 9 potential partners
    // After 15 games, most players should have partnered with at least 4-5 different people
    const avgUniquePartners = Array.from(uniquePartners.values())
      .map(partners => partners.size)
      .reduce((sum, count) => sum + count, 0) / uniquePartners.size;
    
    expect(avgUniquePartners).toBeGreaterThan(3);
  });
});

describe('Round Robin Algorithm - Singles', () => {
  it('should generate singles matches', () => {
    const players = createTestPlayers(4);
    const matches = generateRoundRobinQueue(players, 'singles', []);
    
    expect(matches.length).toBeGreaterThan(0);
    expect(matches[0].team1.length).toBe(1);
    expect(matches[0].team2.length).toBe(1);
  });
  
  it('should maximize opponent diversity (4 players)', () => {
    const players = createTestPlayers(4);
    const matches = generateRoundRobinQueue(players, 'singles', [], 20);
    
    const opponentCounts = analyzeOpponentDiversity(matches);
    
    // Each player should play each other player
    for (const opponents of opponentCounts.values()) {
      expect(opponents.size).toBe(3); // Should have played all 3 other players
    }
  });
  
  it('should avoid duplicate matchups in singles', () => {
    const players = createTestPlayers(6);
    const matches = generateRoundRobinQueue(players, 'singles', [], 30);
    
    const matchupKeys = new Set<string>();
    let duplicates = 0;
    
    for (const match of matches) {
      const key = [match.team1[0], match.team2[0]].sort().join('|');
      
      if (matchupKeys.has(key)) {
        duplicates++;
      }
      matchupKeys.add(key);
    }
    
    expect(duplicates).toBe(0);
  });
  
  it('should distribute singles games evenly', () => {
    const players = createTestPlayers(8);
    const matches = generateRoundRobinQueue(players, 'singles', [], 20);
    
    const gamesPerPlayer = new Map<string, number>();
    players.forEach(p => gamesPerPlayer.set(p.id, 0));
    
    for (const match of matches) {
      match.team1.forEach(id => gamesPerPlayer.set(id, (gamesPerPlayer.get(id) || 0) + 1));
      match.team2.forEach(id => gamesPerPlayer.set(id, (gamesPerPlayer.get(id) || 0) + 1));
    }
    
    const gameCounts = Array.from(gamesPerPlayer.values());
    const maxGames = Math.max(...gameCounts);
    const minGames = Math.min(...gameCounts);
    
    expect(maxGames - minGames).toBeLessThanOrEqual(2);
  });
});

describe('Round Robin Algorithm - Edge Cases', () => {
  it('should return empty array for insufficient players', () => {
    const players = createTestPlayers(3);
    const matches = generateRoundRobinQueue(players, 'doubles', []);
    
    expect(matches.length).toBe(0);
  });
  
  it('should handle maxMatches limit', () => {
    const players = createTestPlayers(8);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 5);
    
    expect(matches.length).toBeLessThanOrEqual(5);
  });
  
  it('should handle large player counts efficiently', () => {
    const players = createTestPlayers(18);
    const startTime = Date.now();
    const matches = generateRoundRobinQueue(players, 'doubles', [], 50);
    const endTime = Date.now();
    
    expect(matches.length).toBeGreaterThan(0);
    expect(endTime - startTime).toBeLessThan(5000); // Should complete in under 5 seconds
  });
  
  it('should avoid same 4 players meeting too soon (18 players)', () => {
    const players = createTestPlayers(18);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 20);
    
    // Track when the same 4 players meet again
    const fourPlayerGroups = new Map<string, number[]>();
    
    matches.forEach((match, index) => {
      const fourPlayers = [...match.team1, ...match.team2].sort().join(',');
      
      if (!fourPlayerGroups.has(fourPlayers)) {
        fourPlayerGroups.set(fourPlayers, []);
      }
      fourPlayerGroups.get(fourPlayers)!.push(index);
    });
    
    // Check that same 4 players don't meet within first 10 games
    for (const [group, gameIndices] of fourPlayerGroups.entries()) {
      if (gameIndices.length > 1) {
        const firstGame = gameIndices[0];
        const secondGame = gameIndices[1];
        
        // If first game is in first 10, second game should not be in first 10
        if (firstGame < 10) {
          expect(secondGame).toBeGreaterThanOrEqual(10);
        }
      }
    }
  });
  
  it('should maximize player diversity early (18 players)', () => {
    const players = createTestPlayers(18);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 30);
    
    // In first 10 games with 18 players, each player should play with many different people
    const first10Games = matches.slice(0, 10);
    const playerParticipation = new Map<string, Set<string>>();
    
    players.forEach(p => playerParticipation.set(p.id, new Set()));
    
    first10Games.forEach(match => {
      const allPlayers = [...match.team1, ...match.team2];
      allPlayers.forEach(p1 => {
        allPlayers.forEach(p2 => {
          if (p1 !== p2) {
            playerParticipation.get(p1)?.add(p2);
          }
        });
      });
    });
    
    // Each player should have interacted with many different players early
    const avgInteractions = Array.from(playerParticipation.values())
      .map(set => set.size)
      .reduce((sum, size) => sum + size, 0) / playerParticipation.size;
    
    // With 18 players and 10 games (40 player-slots), average should be reasonable
    // Each player appears roughly 2-3 times, interacting with 3 others each time
    expect(avgInteractions).toBeGreaterThan(4);
  });
  
  it('should ensure all players participate early (18 players, 2 courts)', () => {
    const players = createTestPlayers(18);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 25);
    
    // Track when each player first plays
    const firstGameForPlayer = new Map<string, number>();
    
    matches.forEach((match, index) => {
      [...match.team1, ...match.team2].forEach(playerId => {
        if (!firstGameForPlayer.has(playerId)) {
          firstGameForPlayer.set(playerId, index);
        }
      });
    });
    
    // With 18 players and 2 courts (4 players per game), 
    // all players should play within first 5 rounds (10 games)
    for (const [playerId, firstGame] of firstGameForPlayer.entries()) {
      expect(firstGame).toBeLessThan(10);
    }
    
    // Players 17 and 18 should definitely play early (within first 5 games)
    expect(firstGameForPlayer.get('player17')).toBeLessThan(5);
    expect(firstGameForPlayer.get('player18')).toBeLessThan(5);
  });
  
  it('should distribute games evenly in first 20 games (18 players)', () => {
    const players = createTestPlayers(18);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 50);
    
    // Count games for each player in first 20 games
    const gamesCount = new Map<string, number>();
    players.forEach(p => gamesCount.set(p.id, 0));
    
    matches.slice(0, 20).forEach(match => {
      [...match.team1, ...match.team2].forEach(playerId => {
        gamesCount.set(playerId, (gamesCount.get(playerId) || 0) + 1);
      });
    });
    
    const counts = Array.from(gamesCount.values());
    const maxGames = Math.max(...counts);
    const minGames = Math.min(...counts);
    
    // With 20 games and 18 players, each player should play ~4-5 games
    // Max difference should be at most 2 games
    expect(maxGames - minGames).toBeLessThanOrEqual(2);
    expect(minGames).toBeGreaterThanOrEqual(3); // Everyone plays at least 3 games in first 20
  });
  
  it('should not repeat partnerships too quickly (18 players)', () => {
    const players = createTestPlayers(18);
    const matches = generateRoundRobinQueue(players, 'doubles', [], 30);
    
    // Track when each partnership first occurs and when it repeats
    const partnershipFirstSeen = new Map<string, number>();
    const partnershipRepeats = new Map<string, number[]>();
    
    matches.forEach((match, index) => {
      // Check team1 partnerships
      for (let i = 0; i < match.team1.length; i++) {
        for (let j = i + 1; j < match.team1.length; j++) {
          const key = [match.team1[i], match.team1[j]].sort().join('|');
          
          if (!partnershipFirstSeen.has(key)) {
            partnershipFirstSeen.set(key, index);
          } else {
            if (!partnershipRepeats.has(key)) {
              partnershipRepeats.set(key, []);
            }
            partnershipRepeats.get(key)!.push(index);
          }
        }
      }
      
      // Check team2 partnerships
      for (let i = 0; i < match.team2.length; i++) {
        for (let j = i + 1; j < match.team2.length; j++) {
          const key = [match.team2[i], match.team2[j]].sort().join('|');
          
          if (!partnershipFirstSeen.has(key)) {
            partnershipFirstSeen.set(key, index);
          } else {
            if (!partnershipRepeats.has(key)) {
              partnershipRepeats.set(key, []);
            }
            partnershipRepeats.get(key)!.push(index);
          }
        }
      }
    });
    
    // Check that partnerships don't repeat too quickly
    for (const [partnership, repeats] of partnershipRepeats.entries()) {
      const firstSeen = partnershipFirstSeen.get(partnership)!;
      if (repeats.length > 0) {
        const firstRepeat = repeats[0];
        const gap = firstRepeat - firstSeen;
        
        // With 18 players, partnerships should not repeat within 8 games
        expect(gap).toBeGreaterThanOrEqual(8);
      }
    }
  });
});
