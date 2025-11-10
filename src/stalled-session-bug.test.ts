import { describe, it, expect } from 'vitest';
import { createSession, evaluateAndCreateMatches, startMatch, completeMatch } from './session';
import type { SessionConfig } from './types';

describe('Stalled Session Bug - Fairness and Balance', () => {
  it('should create matches initially', () => {
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: [
        { id: '1', name: 'Player 1' },
        { id: '2', name: 'Player 2' },
        { id: '3', name: 'Player 3' },
        { id: '4', name: 'Player 4' },
        { id: '5', name: 'Player 5' },
        { id: '6', name: 'Player 6' },
        { id: '7', name: 'Player 7' },
      ],
      courts: 1,
      bannedPairs: [],
    };

    let session = createSession(config);
    session = evaluateAndCreateMatches(session);

    expect(session.matches.length).toBeGreaterThan(0);
  });
  
  it('should create new match after completing one when courts are idle', () => {
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: [
        { id: '1', name: 'Player 1' },
        { id: '2', name: 'Player 2' },
        { id: '3', name: 'Player 3' },
        { id: '4', name: 'Player 4' },
        { id: '5', name: 'Player 5' },
        { id: '6', name: 'Player 6' },
        { id: '7', name: 'Player 7' },
      ],
      courts: 1,
      bannedPairs: [],
    };

    let session = createSession(config);
    session = evaluateAndCreateMatches(session);
    
    // Start and complete the first match
    const waitingMatch = session.matches.find(m => m.status === 'waiting');
    expect(waitingMatch).toBeDefined();
    
    if (waitingMatch) {
      session = startMatch(session, waitingMatch.id);
      session = completeMatch(session, waitingMatch.id, 11, 5);
      
      // Check that a new match was created
      const newWaitingMatches = session.matches.filter(m => m.status === 'waiting');
      expect(newWaitingMatches.length).toBeGreaterThan(0);
    }
  });

  it('should include ALL top waiters even when less than 4', () => {
    // Reproduce scenario from pickleball-session-11-05-2025-10-44.txt
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: [
        { id: '1', name: '1' },
        { id: '2', name: '2' },
        { id: '3', name: '3' },
        { id: '4', name: '4' },
        { id: '5', name: '5' },
        { id: '6', name: '6' },
        { id: 'Ibraheem', name: 'Ibraheem' },
      ],
      courts: 4,
      bannedPairs: [],
    };

    let session = createSession(config);
    session = evaluateAndCreateMatches(session);
    
    // Start and complete first match: 1,2 vs 3,4 (1,2 win)
    const match1 = session.matches.find(m => m.status === 'waiting');
    expect(match1).toBeDefined();
    
    if (match1) {
      session = startMatch(session, match1.id);
      session = completeMatch(session, match1.id, 11, 7);
      
      // After match 1:
      // - Players 1,2,3,4 have played (1 game each)
      // - Players 5,6,Ibraheem have waited (never played)
      
      // Verify wait counts
      const stats5 = session.playerStats.get('5')!;
      const stats6 = session.playerStats.get('6')!;
      const statsIbraheem = session.playerStats.get('Ibraheem')!;
      const stats1 = session.playerStats.get('1')!;
      
      expect(stats5.gamesPlayed).toBe(0);
      expect(stats6.gamesPlayed).toBe(0);
      expect(statsIbraheem.gamesPlayed).toBe(0);
      expect(stats1.gamesPlayed).toBe(1);
      
      // Check wait counts
      expect(stats5.gamesWaited).toBeGreaterThan(0);
      expect(stats6.gamesWaited).toBeGreaterThan(0);
      expect(statsIbraheem.gamesWaited).toBeGreaterThan(0);
      
      // Get the new match that was created
      const match2 = session.matches.find(m => m.status === 'waiting' || m.status === 'in-progress');
      expect(match2).toBeDefined();
      
      if (match2) {
        const match2Players = [...match2.team1, ...match2.team2];
        
        // CRITICAL: Match 2 must include ALL 3 top waiters (5, 6, Ibraheem)
        expect(match2Players).toContain('5');
        expect(match2Players).toContain('6');
        expect(match2Players).toContain('Ibraheem');
        
        // And exactly 1 player from match 1
        const playersFromMatch1 = match2Players.filter(id => ['1', '2', '3', '4'].includes(id));
        expect(playersFromMatch1.length).toBe(1);
      }
    }
  });

  it('should use multiple courts when enough players available', () => {
    // Reproduce scenario from pickleball-session-11-05-2025-10-54.txt
    // 8 players, 4 courts -> should use 2 courts simultaneously
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: [
        { id: '1', name: '1' },
        { id: '2', name: '2' },
        { id: '3', name: '3' },
        { id: '4', name: '4' },
        { id: '5', name: '5' },
        { id: '6', name: '6' },
        { id: 'Ibraheem', name: 'Ibraheem' },
        { id: 'Jeremy', name: 'Jeremy' },
      ],
      courts: 4,
      bannedPairs: [],
    };

    let session = createSession(config);
    session = evaluateAndCreateMatches(session);
    
    // With 8 players and 4 courts, should create 2 matches initially
    const initialMatches = session.matches.filter(m => 
      m.status === 'waiting' || m.status === 'in-progress'
    );
    
    // CRITICAL: With 8 players and 4 courts available, should use 2 courts
    expect(initialMatches.length).toBe(2);
    
    // All 8 players should be in matches
    const playingPlayerIds = new Set<string>();
    initialMatches.forEach(m => {
      [...m.team1, ...m.team2].forEach(id => playingPlayerIds.add(id));
    });
    expect(playingPlayerIds.size).toBe(8);
  });

  it('should create 2 courts after 8th player joins and match completes', () => {
    // Reproduce scenario from pickleball-session-11-05-2025-11-05.txt
    // Start with 7 players, add 8th mid-session, complete match → should create 2 courts
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: [
        { id: '1', name: '1' },
        { id: '2', name: '2' },
        { id: '3', name: '3' },
        { id: '4', name: '4' },
        { id: '5', name: '5' },
        { id: '6', name: '6' },
        { id: 'Ibraheem', name: 'Ibraheem' },
      ],
      courts: 4,
      bannedPairs: [],
    };

    let session = createSession(config);
    
    // Play 4 matches completely with 7 players
    for (let i = 0; i < 4; i++) {
      session = evaluateAndCreateMatches(session);
      const match = session.matches.find(m => m.status === 'waiting');
      if (match) {
        session = startMatch(session, match.id);
        session = completeMatch(session, match.id, 11, 7);
      }
    }
    
    // Start match 5 with 7 players
    session = evaluateAndCreateMatches(session);
    const match5 = session.matches.find(m => m.status === 'waiting');
    if (match5) {
      session = startMatch(session, match5.id);
    }
    
    // Add 8th player (Jeremy) mid-session while match 5 is in progress
    const newConfig: SessionConfig = {
      ...config,
      players: [...config.players, { id: 'Jeremy', name: 'Jeremy' }],
    };
    
    session = {
      ...session,
      config: newConfig,
      activePlayers: new Set([...session.activePlayers, 'Jeremy']),
      playerStats: new Map([
        ...session.playerStats,
        ['Jeremy', {
          gamesPlayed: 0,
          gamesWon: 0,
          gamesLost: 0,
          gamesWaited: 0,
          pointsFor: 0,
          pointsAgainst: 0,
          partnersPlayed: new Set(),
          opponentsPlayed: new Set(),
        }]
      ])
    };
    
    // Now complete match 5 with Jeremy waiting
    if (match5) {
      session = completeMatch(session, match5.id, 11, 7);
    }
    
    // Now with 8 players and all courts empty, should create 2 matches
    const newMatches = session.matches.filter(m => 
      m.status === 'waiting' || m.status === 'in-progress'
    );
    
    // CRITICAL: After 8th player joins and match completes, should use 2 courts
    expect(newMatches.length).toBeGreaterThanOrEqual(2);
    
    // All 8 players should be in matches
    const playingPlayerIds = new Set<string>();
    newMatches.forEach(m => {
      [...m.team1, ...m.team2].forEach(id => playingPlayerIds.add(id));
    });
    
    expect(playingPlayerIds.size).toBe(8);
  });

  it('should prioritize players who have waited most when all courts are idle', () => {
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: [
        { id: '1', name: 'Player 1' },
        { id: '2', name: 'Player 2' },
        { id: '3', name: 'Player 3' },
        { id: '4', name: 'Player 4' },
        { id: '5', name: 'Player 5' },
        { id: '6', name: 'Player 6' },
        { id: '7', name: 'Player 7' },
        { id: '8', name: 'Player 8' },
      ],
      courts: 1,
      bannedPairs: [],
    };

    let session = createSession(config);
    session = evaluateAndCreateMatches(session);
    
    // Complete 2 matches to build up different wait counts
    for (let i = 0; i < 2; i++) {
      const match = session.matches.find(m => m.status === 'waiting');
      if (match) {
        session = startMatch(session, match.id);
        session = completeMatch(session, match.id, 11, 5);
      }
    }
    
    // Get players sorted by wait count
    const playerWaits = Array.from(session.playerStats.entries())
      .map(([playerId, stats]) => ({ playerId, waits: stats.gamesWaited }))
      .sort((a, b) => b.waits - a.waits);
    
    const maxWaits = playerWaits[0].waits;
    const topWaiters = playerWaits
      .filter(p => p.waits >= maxWaits - 1)
      .map(p => p.playerId);
    
    // Get the new match that was created
    const newMatch = session.matches.find(m => m.status === 'waiting');
    expect(newMatch).toBeDefined();
    
    if (newMatch) {
      const matchPlayers = [...newMatch.team1, ...newMatch.team2];
      
      // At least 3 out of 4 players should be from the top waiters
      // (allowing for edge cases with ranking constraints)
      const numFromTopWaiters = matchPlayers.filter(id => topWaiters.includes(id)).length;
      expect(numFromTopWaiters).toBeGreaterThanOrEqual(3);
    }
  });
});
