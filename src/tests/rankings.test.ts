import { describe, it, expect } from 'vitest';
import { calculatePlayerRankings, calculateTeamRankings } from '../utils';
import { createPlayerStats } from '../utils';
import type { PlayerStats } from '../types';

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

describe('Team Rankings', () => {
  it('should rank teams by combined wins in descending order', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    // Team 1: p1 + p2
    const p1Stats = createPlayerStats('p1');
    p1Stats.wins = 6;
    p1Stats.losses = 0;
    p1Stats.gamesPlayed = 6;
    p1Stats.totalPointsFor = 60;
    p1Stats.totalPointsAgainst = 30;
    
    const p2Stats = createPlayerStats('p2');
    p2Stats.wins = 4;
    p2Stats.losses = 2;
    p2Stats.gamesPlayed = 6;
    p2Stats.totalPointsFor = 50;
    p2Stats.totalPointsAgainst = 40;
    
    // Team 2: p3 + p4
    const p3Stats = createPlayerStats('p3');
    p3Stats.wins = 3;
    p3Stats.losses = 3;
    p3Stats.gamesPlayed = 6;
    p3Stats.totalPointsFor = 45;
    p3Stats.totalPointsAgainst = 45;
    
    const p4Stats = createPlayerStats('p4');
    p4Stats.wins = 3;
    p4Stats.losses = 3;
    p4Stats.gamesPlayed = 6;
    p4Stats.totalPointsFor = 42;
    p4Stats.totalPointsAgainst = 48;
    
    statsMap.set('p1', p1Stats);
    statsMap.set('p2', p2Stats);
    statsMap.set('p3', p3Stats);
    statsMap.set('p4', p4Stats);
    
    const teams = [['p1', 'p2'], ['p3', 'p4']];
    const rankings = calculateTeamRankings(teams, statsMap);
    
    expect(rankings).toHaveLength(2);
    expect(rankings[0].team).toEqual(['p1', 'p2']);
    expect(rankings[0].rank).toBe(1);
    expect(rankings[0].wins).toBe(5); // (6+4)/2 = 5
    
    expect(rankings[1].team).toEqual(['p3', 'p4']);
    expect(rankings[1].rank).toBe(2);
    expect(rankings[1].wins).toBe(3); // (3+3)/2 = 3
  });
  
  it('should use average point differential as tiebreaker for teams with same wins', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    // Team 1: p1 + p2 - high differential
    const p1Stats = createPlayerStats('p1');
    p1Stats.wins = 4;
    p1Stats.losses = 2;
    p1Stats.gamesPlayed = 6;
    p1Stats.totalPointsFor = 72; // +7 per game
    p1Stats.totalPointsAgainst = 30;
    
    const p2Stats = createPlayerStats('p2');
    p2Stats.wins = 4;
    p2Stats.losses = 2;
    p2Stats.gamesPlayed = 6;
    p2Stats.totalPointsFor = 60; // +5 per game
    p2Stats.totalPointsAgainst = 30;
    
    // Team 2: p3 + p4 - lower differential
    const p3Stats = createPlayerStats('p3');
    p3Stats.wins = 4;
    p3Stats.losses = 2;
    p3Stats.gamesPlayed = 6;
    p3Stats.totalPointsFor = 54; // +4 per game
    p3Stats.totalPointsAgainst = 30;
    
    const p4Stats = createPlayerStats('p4');
    p4Stats.wins = 4;
    p4Stats.losses = 2;
    p4Stats.gamesPlayed = 6;
    p4Stats.totalPointsFor = 48; // +3 per game
    p4Stats.totalPointsAgainst = 30;
    
    statsMap.set('p1', p1Stats);
    statsMap.set('p2', p2Stats);
    statsMap.set('p3', p3Stats);
    statsMap.set('p4', p4Stats);
    
    const teams = [['p1', 'p2'], ['p3', 'p4']];
    const rankings = calculateTeamRankings(teams, statsMap);
    
    expect(rankings).toHaveLength(2);
    expect(rankings[0].team).toEqual(['p1', 'p2']);
    expect(rankings[0].rank).toBe(1);
    expect(rankings[0].avgPointDifferential).toBe(6); // (7+5)/2 = 6
    
    expect(rankings[1].team).toEqual(['p3', 'p4']);
    expect(rankings[1].rank).toBe(2);
    expect(rankings[1].avgPointDifferential).toBe(3.5); // (4+3)/2 = 3.5
  });
  
  it('should handle teams with no games played', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    // Team 1: Has games
    const p1Stats = createPlayerStats('p1');
    p1Stats.wins = 3;
    p1Stats.losses = 2;
    p1Stats.gamesPlayed = 5;
    p1Stats.totalPointsFor = 50;
    p1Stats.totalPointsAgainst = 40;
    
    const p2Stats = createPlayerStats('p2');
    p2Stats.wins = 3;
    p2Stats.losses = 2;
    p2Stats.gamesPlayed = 5;
    p2Stats.totalPointsFor = 50;
    p2Stats.totalPointsAgainst = 40;
    
    // Team 2: No games
    const p3Stats = createPlayerStats('p3');
    const p4Stats = createPlayerStats('p4');
    
    statsMap.set('p1', p1Stats);
    statsMap.set('p2', p2Stats);
    statsMap.set('p3', p3Stats);
    statsMap.set('p4', p4Stats);
    
    const teams = [['p1', 'p2'], ['p3', 'p4']];
    const rankings = calculateTeamRankings(teams, statsMap);
    
    expect(rankings).toHaveLength(2);
    expect(rankings[0].team).toEqual(['p1', 'p2']);
    expect(rankings[0].rank).toBe(1);
    
    expect(rankings[1].team).toEqual(['p3', 'p4']);
    expect(rankings[1].rank).toBe(2);
    expect(rankings[1].avgPointDifferential).toBe(0);
  });
  
  it('should handle ties correctly for teams', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    // Team 1 and Team 2 have identical stats
    const p1Stats = createPlayerStats('p1');
    p1Stats.wins = 5;
    p1Stats.losses = 0;
    p1Stats.gamesPlayed = 5;
    p1Stats.totalPointsFor = 55;
    p1Stats.totalPointsAgainst = 30;
    
    const p2Stats = createPlayerStats('p2');
    p2Stats.wins = 5;
    p2Stats.losses = 0;
    p2Stats.gamesPlayed = 5;
    p2Stats.totalPointsFor = 55;
    p2Stats.totalPointsAgainst = 30;
    
    const p3Stats = createPlayerStats('p3');
    p3Stats.wins = 5;
    p3Stats.losses = 0;
    p3Stats.gamesPlayed = 5;
    p3Stats.totalPointsFor = 55;
    p3Stats.totalPointsAgainst = 30;
    
    const p4Stats = createPlayerStats('p4');
    p4Stats.wins = 5;
    p4Stats.losses = 0;
    p4Stats.gamesPlayed = 5;
    p4Stats.totalPointsFor = 55;
    p4Stats.totalPointsAgainst = 30;
    
    // Team 3 has lower stats
    const p5Stats = createPlayerStats('p5');
    p5Stats.wins = 3;
    p5Stats.losses = 2;
    p5Stats.gamesPlayed = 5;
    p5Stats.totalPointsFor = 40;
    p5Stats.totalPointsAgainst = 35;
    
    const p6Stats = createPlayerStats('p6');
    p6Stats.wins = 3;
    p6Stats.losses = 2;
    p6Stats.gamesPlayed = 5;
    p6Stats.totalPointsFor = 40;
    p6Stats.totalPointsAgainst = 35;
    
    statsMap.set('p1', p1Stats);
    statsMap.set('p2', p2Stats);
    statsMap.set('p3', p3Stats);
    statsMap.set('p4', p4Stats);
    statsMap.set('p5', p5Stats);
    statsMap.set('p6', p6Stats);
    
    const teams = [['p1', 'p2'], ['p3', 'p4'], ['p5', 'p6']];
    const rankings = calculateTeamRankings(teams, statsMap);
    
    expect(rankings).toHaveLength(3);
    expect(rankings[0].rank).toBe(1);
    expect(rankings[1].rank).toBe(1); // Tied with first team
    expect(rankings[2].rank).toBe(3);
  });
  
  it('should handle empty team list', () => {
    const statsMap = new Map<string, PlayerStats>();
    const rankings = calculateTeamRankings([], statsMap);
    
    expect(rankings).toHaveLength(0);
  });
  
  it('should handle single team', () => {
    const statsMap = new Map<string, PlayerStats>();
    
    const p1Stats = createPlayerStats('p1');
    p1Stats.wins = 5;
    p1Stats.losses = 0;
    p1Stats.gamesPlayed = 5;
    p1Stats.totalPointsFor = 55;
    p1Stats.totalPointsAgainst = 25;
    
    const p2Stats = createPlayerStats('p2');
    p2Stats.wins = 5;
    p2Stats.losses = 0;
    p2Stats.gamesPlayed = 5;
    p2Stats.totalPointsFor = 55;
    p2Stats.totalPointsAgainst = 25;
    
    statsMap.set('p1', p1Stats);
    statsMap.set('p2', p2Stats);
    
    const teams = [['p1', 'p2']];
    const rankings = calculateTeamRankings(teams, statsMap);
    
    expect(rankings).toHaveLength(1);
    expect(rankings[0].team).toEqual(['p1', 'p2']);
    expect(rankings[0].rank).toBe(1);
  });
});

