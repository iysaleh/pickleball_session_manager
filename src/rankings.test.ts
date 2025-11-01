import { describe, it, expect } from 'vitest';
import { calculatePlayerRankings } from './utils';
import { createPlayerStats } from './utils';
import type { PlayerStats } from './types';

describe('Player Rankings', () => {
  it('should rank players by wins in descending order', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    const player1Stats = createPlayerStats('p1');
    player1Stats.wins = 5;
    player1Stats.losses = 0;
    player1Stats.gamesPlayed = 5;
    player1Stats.totalPointsFor = 55;
    player1Stats.totalPointsAgainst = 25;
    
    const player2Stats = createPlayerStats('p2');
    player2Stats.wins = 3;
    player2Stats.losses = 2;
    player2Stats.gamesPlayed = 5;
    player2Stats.totalPointsFor = 45;
    player2Stats.totalPointsAgainst = 35;
    
    const player3Stats = createPlayerStats('p3');
    player3Stats.wins = 1;
    player3Stats.losses = 4;
    player3Stats.gamesPlayed = 5;
    player3Stats.totalPointsFor = 30;
    player3Stats.totalPointsAgainst = 50;
    
    statsMap.set('p1', player1Stats);
    statsMap.set('p2', player2Stats);
    statsMap.set('p3', player3Stats);
    
    const rankings = calculatePlayerRankings(['p1', 'p2', 'p3'], statsMap);
    
    expect(rankings).toHaveLength(3);
    expect(rankings[0].playerId).toBe('p1');
    expect(rankings[0].rank).toBe(1);
    expect(rankings[0].wins).toBe(5);
    
    expect(rankings[1].playerId).toBe('p2');
    expect(rankings[1].rank).toBe(2);
    expect(rankings[1].wins).toBe(3);
    
    expect(rankings[2].playerId).toBe('p3');
    expect(rankings[2].rank).toBe(3);
    expect(rankings[2].wins).toBe(1);
  });
  
  it('should use average point differential as tiebreaker for same wins', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    const player1Stats = createPlayerStats('p1');
    player1Stats.wins = 3;
    player1Stats.losses = 2;
    player1Stats.gamesPlayed = 5;
    player1Stats.totalPointsFor = 60; // +10 per game avg differential
    player1Stats.totalPointsAgainst = 10;
    
    const player2Stats = createPlayerStats('p2');
    player2Stats.wins = 3;
    player2Stats.losses = 2;
    player2Stats.gamesPlayed = 5;
    player2Stats.totalPointsFor = 50; // +5 per game avg differential
    player2Stats.totalPointsAgainst = 25;
    
    const player3Stats = createPlayerStats('p3');
    player3Stats.wins = 3;
    player3Stats.losses = 2;
    player3Stats.gamesPlayed = 5;
    player3Stats.totalPointsFor = 45; // +1 per game avg differential
    player3Stats.totalPointsAgainst = 40;
    
    statsMap.set('p1', player1Stats);
    statsMap.set('p2', player2Stats);
    statsMap.set('p3', player3Stats);
    
    const rankings = calculatePlayerRankings(['p1', 'p2', 'p3'], statsMap);
    
    expect(rankings).toHaveLength(3);
    expect(rankings[0].playerId).toBe('p1');
    expect(rankings[0].rank).toBe(1);
    expect(rankings[0].avgPointDifferential).toBe(10);
    
    expect(rankings[1].playerId).toBe('p2');
    expect(rankings[1].rank).toBe(2);
    expect(rankings[1].avgPointDifferential).toBe(5);
    
    expect(rankings[2].playerId).toBe('p3');
    expect(rankings[2].rank).toBe(3);
    expect(rankings[2].avgPointDifferential).toBe(1);
  });
  
  it('should handle ties correctly (same rank for same wins and point differential)', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    const player1Stats = createPlayerStats('p1');
    player1Stats.wins = 5;
    player1Stats.losses = 0;
    player1Stats.gamesPlayed = 5;
    player1Stats.totalPointsFor = 55;
    player1Stats.totalPointsAgainst = 30;
    
    const player2Stats = createPlayerStats('p2');
    player2Stats.wins = 5;
    player2Stats.losses = 0;
    player2Stats.gamesPlayed = 5;
    player2Stats.totalPointsFor = 60;
    player2Stats.totalPointsAgainst = 35; // Same +5 differential
    
    const player3Stats = createPlayerStats('p3');
    player3Stats.wins = 3;
    player3Stats.losses = 2;
    player3Stats.gamesPlayed = 5;
    player3Stats.totalPointsFor = 40;
    player3Stats.totalPointsAgainst = 35;
    
    statsMap.set('p1', player1Stats);
    statsMap.set('p2', player2Stats);
    statsMap.set('p3', player3Stats);
    
    const rankings = calculatePlayerRankings(['p1', 'p2', 'p3'], statsMap);
    
    expect(rankings).toHaveLength(3);
    expect(rankings[0].rank).toBe(1);
    expect(rankings[1].rank).toBe(1); // Tied
    expect(rankings[2].rank).toBe(3);
  });
  
  it('should handle players with no games played', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    const player1Stats = createPlayerStats('p1');
    player1Stats.wins = 3;
    player1Stats.losses = 2;
    player1Stats.gamesPlayed = 5;
    player1Stats.totalPointsFor = 50;
    player1Stats.totalPointsAgainst = 40;
    
    const player2Stats = createPlayerStats('p2');
    // No games played, all zeros
    
    statsMap.set('p1', player1Stats);
    statsMap.set('p2', player2Stats);
    
    const rankings = calculatePlayerRankings(['p1', 'p2'], statsMap);
    
    expect(rankings).toHaveLength(2);
    expect(rankings[0].playerId).toBe('p1');
    expect(rankings[0].rank).toBe(1);
    
    expect(rankings[1].playerId).toBe('p2');
    expect(rankings[1].rank).toBe(2);
    expect(rankings[1].avgPointDifferential).toBe(0);
  });
  
  it('should handle negative point differential correctly', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    const player1Stats = createPlayerStats('p1');
    player1Stats.wins = 2;
    player1Stats.losses = 3;
    player1Stats.gamesPlayed = 5;
    player1Stats.totalPointsFor = 40; // -2 avg differential
    player1Stats.totalPointsAgainst = 50;
    
    const player2Stats = createPlayerStats('p2');
    player2Stats.wins = 2;
    player2Stats.losses = 3;
    player2Stats.gamesPlayed = 5;
    player2Stats.totalPointsFor = 30; // -6 avg differential
    player2Stats.totalPointsAgainst = 60;
    
    statsMap.set('p1', player1Stats);
    statsMap.set('p2', player2Stats);
    
    const rankings = calculatePlayerRankings(['p1', 'p2'], statsMap);
    
    expect(rankings).toHaveLength(2);
    expect(rankings[0].playerId).toBe('p1');
    expect(rankings[0].rank).toBe(1);
    expect(rankings[0].avgPointDifferential).toBe(-2);
    
    expect(rankings[1].playerId).toBe('p2');
    expect(rankings[1].rank).toBe(2);
    expect(rankings[1].avgPointDifferential).toBe(-6);
  });
  
  it('should handle empty player list', () => {
    const statsMap = new Map<string, PlayerStats>();
    const rankings = calculatePlayerRankings([], statsMap);
    
    expect(rankings).toHaveLength(0);
  });
  
  it('should handle single player', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    const player1Stats = createPlayerStats('p1');
    player1Stats.wins = 5;
    player1Stats.losses = 0;
    player1Stats.gamesPlayed = 5;
    player1Stats.totalPointsFor = 55;
    player1Stats.totalPointsAgainst = 25;
    
    statsMap.set('p1', player1Stats);
    
    const rankings = calculatePlayerRankings(['p1'], statsMap);
    
    expect(rankings).toHaveLength(1);
    expect(rankings[0].playerId).toBe('p1');
    expect(rankings[0].rank).toBe(1);
  });
  
  it('should rank complex scenario with multiple tiers', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    // Tier 1: 10 wins
    const p1 = createPlayerStats('p1');
    p1.wins = 10; p1.losses = 0; p1.gamesPlayed = 10;
    p1.totalPointsFor = 110; p1.totalPointsAgainst = 50; // +6 avg
    
    // Tier 2: 7 wins
    const p2 = createPlayerStats('p2');
    p2.wins = 7; p2.losses = 3; p2.gamesPlayed = 10;
    p2.totalPointsFor = 95; p2.totalPointsAgainst = 65; // +3 avg
    
    const p3 = createPlayerStats('p3');
    p3.wins = 7; p3.losses = 3; p3.gamesPlayed = 10;
    p3.totalPointsFor = 90; p3.totalPointsAgainst = 70; // +2 avg
    
    // Tier 3: 5 wins
    const p4 = createPlayerStats('p4');
    p4.wins = 5; p4.losses = 5; p4.gamesPlayed = 10;
    p4.totalPointsFor = 80; p4.totalPointsAgainst = 80; // 0 avg
    
    // Tier 4: 2 wins
    const p5 = createPlayerStats('p5');
    p5.wins = 2; p5.losses = 8; p5.gamesPlayed = 10;
    p5.totalPointsFor = 60; p5.totalPointsAgainst = 100; // -4 avg
    
    statsMap.set('p1', p1);
    statsMap.set('p2', p2);
    statsMap.set('p3', p3);
    statsMap.set('p4', p4);
    statsMap.set('p5', p5);
    
    const rankings = calculatePlayerRankings(['p1', 'p2', 'p3', 'p4', 'p5'], statsMap);
    
    expect(rankings).toHaveLength(5);
    expect(rankings[0].playerId).toBe('p1');
    expect(rankings[0].rank).toBe(1);
    
    expect(rankings[1].playerId).toBe('p2');
    expect(rankings[1].rank).toBe(2);
    
    expect(rankings[2].playerId).toBe('p3');
    expect(rankings[2].rank).toBe(3);
    
    expect(rankings[3].playerId).toBe('p4');
    expect(rankings[3].rank).toBe(4);
    
    expect(rankings[4].playerId).toBe('p5');
    expect(rankings[4].rank).toBe(5);
  });
});
