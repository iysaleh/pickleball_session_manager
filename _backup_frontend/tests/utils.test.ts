import { describe, it, expect } from 'vitest';
import {
  generateId,
  shuffleArray,
  isPairBanned,
  createPlayerStats,
  getPlayersWithFewestGames,
  getPlayersWhoWaitedMost,
  calculatePartnerDiversity,
} from '../utils';

describe('Utils', () => {
  describe('generateId', () => {
    it('should generate unique IDs', () => {
      const id1 = generateId();
      const id2 = generateId();
      expect(id1).not.toBe(id2);
    });
    
    it('should generate non-empty strings', () => {
      const id = generateId();
      expect(id).toBeTruthy();
      expect(typeof id).toBe('string');
    });
  });
  
  describe('shuffleArray', () => {
    it('should return array with same length', () => {
      const arr = [1, 2, 3, 4, 5];
      const shuffled = shuffleArray(arr);
      expect(shuffled.length).toBe(arr.length);
    });
    
    it('should contain all original elements', () => {
      const arr = [1, 2, 3, 4, 5];
      const shuffled = shuffleArray(arr);
      arr.forEach((item) => {
        expect(shuffled).toContain(item);
      });
    });
    
    it('should not modify original array', () => {
      const arr = [1, 2, 3, 4, 5];
      const original = [...arr];
      shuffleArray(arr);
      expect(arr).toEqual(original);
    });
  });
  
  describe('isPairBanned', () => {
    it('should return true for banned pair in order', () => {
      const bannedPairs: [string, string][] = [['p1', 'p2']];
      expect(isPairBanned('p1', 'p2', bannedPairs)).toBe(true);
    });
    
    it('should return true for banned pair in reverse order', () => {
      const bannedPairs: [string, string][] = [['p1', 'p2']];
      expect(isPairBanned('p2', 'p1', bannedPairs)).toBe(true);
    });
    
    it('should return false for non-banned pair', () => {
      const bannedPairs: [string, string][] = [['p1', 'p2']];
      expect(isPairBanned('p1', 'p3', bannedPairs)).toBe(false);
    });
    
    it('should handle empty banned pairs list', () => {
      expect(isPairBanned('p1', 'p2', [])).toBe(false);
    });
  });
  
  describe('createPlayerStats', () => {
    it('should create stats with correct initial values', () => {
      const stats = createPlayerStats('player1');
      expect(stats.playerId).toBe('player1');
      expect(stats.gamesPlayed).toBe(0);
      expect(stats.gamesWaited).toBe(0);
      expect(stats.wins).toBe(0);
      expect(stats.losses).toBe(0);
      expect(stats.partnersPlayed.size).toBe(0);
      expect(stats.opponentsPlayed.size).toBe(0);
    });
  });
  
  describe('getPlayersWithFewestGames', () => {
    it('should return players with minimum games played', () => {
      const statsMap = new Map();
      statsMap.set('p1', createPlayerStats('p1'));
      statsMap.set('p2', createPlayerStats('p2'));
      statsMap.set('p3', createPlayerStats('p3'));
      
      statsMap.get('p1')!.gamesPlayed = 2;
      statsMap.get('p2')!.gamesPlayed = 1;
      statsMap.get('p3')!.gamesPlayed = 1;
      
      const result = getPlayersWithFewestGames(['p1', 'p2', 'p3'], statsMap);
      expect(result).toEqual(['p2', 'p3']);
    });
    
    it('should return empty array for empty input', () => {
      const statsMap = new Map();
      const result = getPlayersWithFewestGames([], statsMap);
      expect(result).toEqual([]);
    });
    
    it('should handle players with no stats', () => {
      const statsMap = new Map();
      const result = getPlayersWithFewestGames(['p1', 'p2'], statsMap);
      expect(result).toEqual(['p1', 'p2']);
    });
  });
  
  describe('getPlayersWhoWaitedMost', () => {
    it('should return players with maximum waits', () => {
      const statsMap = new Map();
      statsMap.set('p1', createPlayerStats('p1'));
      statsMap.set('p2', createPlayerStats('p2'));
      statsMap.set('p3', createPlayerStats('p3'));
      
      statsMap.get('p1')!.gamesWaited = 3;
      statsMap.get('p2')!.gamesWaited = 1;
      statsMap.get('p3')!.gamesWaited = 3;
      
      const result = getPlayersWhoWaitedMost(['p1', 'p2', 'p3'], statsMap);
      expect(result).toEqual(['p1', 'p3']);
    });
    
    it('should return empty array for empty input', () => {
      const statsMap = new Map();
      const result = getPlayersWhoWaitedMost([], statsMap);
      expect(result).toEqual([]);
    });
  });
  
  describe('calculatePartnerDiversity', () => {
    it('should return 1 for players who have not played together', () => {
      const statsMap = new Map();
      statsMap.set('p1', createPlayerStats('p1'));
      statsMap.set('p2', createPlayerStats('p2'));
      
      const result = calculatePartnerDiversity('p1', 'p2', statsMap);
      expect(result).toBe(1);
    });
    
    it('should return -1 for players who have played together', () => {
      const statsMap = new Map();
      const stats1 = createPlayerStats('p1');
      const stats2 = createPlayerStats('p2');
      stats1.partnersPlayed.add('p2');
      statsMap.set('p1', stats1);
      statsMap.set('p2', stats2);
      
      const result = calculatePartnerDiversity('p1', 'p2', statsMap);
      expect(result).toBe(-1);
    });
    
    it('should return 0 for missing stats', () => {
      const statsMap = new Map();
      const result = calculatePartnerDiversity('p1', 'p2', statsMap);
      expect(result).toBe(0);
    });
  });
});

