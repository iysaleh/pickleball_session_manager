import { describe, it, expect } from 'vitest';
import { selectPlayersForNextGame, createMatch } from './matchmaking';
import { createPlayerStats } from './utils';
import type { PlayerStats } from './types';

describe('Matchmaking', () => {
  describe('selectPlayersForNextGame', () => {
    it('should return null if not enough players', () => {
      const statsMap = new Map<string, PlayerStats>();
      const result = selectPlayersForNextGame(['p1'], 2, statsMap, []);
      expect(result).toBeNull();
    });
    
    it('should select correct number of players for doubles', () => {
      const players = ['p1', 'p2', 'p3', 'p4'];
      const statsMap = new Map<string, PlayerStats>();
      players.forEach((p) => statsMap.set(p, createPlayerStats(p)));
      
      const result = selectPlayersForNextGame(players, 2, statsMap, []);
      expect(result).not.toBeNull();
      expect(result?.length).toBe(4);
    });
    
    it('should select correct number of players for singles', () => {
      const players = ['p1', 'p2', 'p3', 'p4'];
      const statsMap = new Map<string, PlayerStats>();
      players.forEach((p) => statsMap.set(p, createPlayerStats(p)));
      
      const result = selectPlayersForNextGame(players, 1, statsMap, []);
      expect(result).not.toBeNull();
      expect(result?.length).toBe(2);
    });
    
    it('should prioritize players with fewest games', () => {
      const players = ['p1', 'p2', 'p3', 'p4'];
      const statsMap = new Map<string, PlayerStats>();
      players.forEach((p) => {
        const stats = createPlayerStats(p);
        statsMap.set(p, stats);
      });
      
      statsMap.get('p1')!.gamesPlayed = 5;
      statsMap.get('p2')!.gamesPlayed = 1;
      statsMap.get('p3')!.gamesPlayed = 1;
      statsMap.get('p4')!.gamesPlayed = 1;
      
      const result = selectPlayersForNextGame(players, 2, statsMap, []);
      expect(result).not.toBeNull();
      expect(result).not.toContain('p1');
    });
    
    it('should respect banned pairs', () => {
      const players = ['p1', 'p2', 'p3', 'p4'];
      const statsMap = new Map<string, PlayerStats>();
      players.forEach((p) => statsMap.set(p, createPlayerStats(p)));
      
      const bannedPairs: [string, string][] = [['p1', 'p2']];
      
      // Run multiple times to ensure banned pairs are never together
      for (let i = 0; i < 10; i++) {
        const result = selectPlayersForNextGame(players, 2, statsMap, bannedPairs);
        if (result) {
          const team1 = result.slice(0, 2);
          const team2 = result.slice(2);
          
          // Check team1 doesn't have banned pair
          if (team1.includes('p1') && team1.includes('p2')) {
            expect(false).toBe(true); // Should never happen
          }
          
          // Check team2 doesn't have banned pair
          if (team2.includes('p1') && team2.includes('p2')) {
            expect(false).toBe(true); // Should never happen
          }
        }
      }
      
      expect(true).toBe(true); // If we get here, banned pairs were respected
    });
  });
  
  describe('createMatch', () => {
    it('should create match with correct structure', () => {
      const statsMap = new Map<string, PlayerStats>();
      ['p1', 'p2', 'p3', 'p4'].forEach((p) =>
        statsMap.set(p, createPlayerStats(p))
      );
      
      const match = createMatch(1, ['p1', 'p2'], ['p3', 'p4'], statsMap);
      
      expect(match.courtNumber).toBe(1);
      expect(match.team1).toEqual(['p1', 'p2']);
      expect(match.team2).toEqual(['p3', 'p4']);
      expect(match.status).toBe('waiting');
      expect(match.id).toBeTruthy();
    });
    
    it('should update games played for all players', () => {
      const statsMap = new Map<string, PlayerStats>();
      ['p1', 'p2', 'p3', 'p4'].forEach((p) =>
        statsMap.set(p, createPlayerStats(p))
      );
      
      createMatch(1, ['p1', 'p2'], ['p3', 'p4'], statsMap);
      
      expect(statsMap.get('p1')?.gamesPlayed).toBe(1);
      expect(statsMap.get('p2')?.gamesPlayed).toBe(1);
      expect(statsMap.get('p3')?.gamesPlayed).toBe(1);
      expect(statsMap.get('p4')?.gamesPlayed).toBe(1);
    });
    
    it('should track partners correctly', () => {
      const statsMap = new Map<string, PlayerStats>();
      ['p1', 'p2', 'p3', 'p4'].forEach((p) =>
        statsMap.set(p, createPlayerStats(p))
      );
      
      createMatch(1, ['p1', 'p2'], ['p3', 'p4'], statsMap);
      
      expect(statsMap.get('p1')?.partnersPlayed.has('p2')).toBe(true);
      expect(statsMap.get('p2')?.partnersPlayed.has('p1')).toBe(true);
      expect(statsMap.get('p3')?.partnersPlayed.has('p4')).toBe(true);
      expect(statsMap.get('p4')?.partnersPlayed.has('p3')).toBe(true);
    });
    
    it('should track opponents correctly', () => {
      const statsMap = new Map<string, PlayerStats>();
      ['p1', 'p2', 'p3', 'p4'].forEach((p) =>
        statsMap.set(p, createPlayerStats(p))
      );
      
      createMatch(1, ['p1', 'p2'], ['p3', 'p4'], statsMap);
      
      expect(statsMap.get('p1')?.opponentsPlayed.has('p3')).toBe(true);
      expect(statsMap.get('p1')?.opponentsPlayed.has('p4')).toBe(true);
      expect(statsMap.get('p2')?.opponentsPlayed.has('p3')).toBe(true);
      expect(statsMap.get('p2')?.opponentsPlayed.has('p4')).toBe(true);
    });
    
    it('should work for singles matches', () => {
      const statsMap = new Map<string, PlayerStats>();
      ['p1', 'p2'].forEach((p) => statsMap.set(p, createPlayerStats(p)));
      
      const match = createMatch(1, ['p1'], ['p2'], statsMap);
      
      expect(match.team1).toEqual(['p1']);
      expect(match.team2).toEqual(['p2']);
      expect(statsMap.get('p1')?.gamesPlayed).toBe(1);
      expect(statsMap.get('p2')?.gamesPlayed).toBe(1);
    });
  });
});
