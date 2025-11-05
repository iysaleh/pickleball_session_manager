import { describe, it, expect } from 'vitest';
import { createSession, evaluateAndCreateMatches } from './session';
import type { Player, SessionConfig } from './types';

describe('King of Court - 14 players 4 courts initialization', () => {
  it('should fill at least 3 courts when starting with 14 players and 4 courts', () => {
    // Create 14 players
    const players: Player[] = [];
    for (let i = 1; i <= 14; i++) {
      players.push({ id: `player${i}`, name: `Player ${i}` });
    }

    // Create session config
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: players,
      courts: 4,
      bannedPairs: [],
      randomizePlayerOrder: false,
    };

    // Create and evaluate session
    let session = createSession(config, 100);
    session = evaluateAndCreateMatches(session);

    // Check active matches
    const activeMatches = session.matches.filter(
      m => m.status === 'in-progress' || m.status === 'waiting'
    );

    // With 14 players and 4 courts (4 players per court), we should have at least 3 courts active
    // Ideally 3 courts = 12 players, leaving 2 waiting
    expect(activeMatches.length).toBeGreaterThanOrEqual(3);
    
    // Verify no duplicate court numbers
    const courtNumbers = activeMatches.map(m => m.courtNumber);
    const uniqueCourts = new Set(courtNumbers);
    expect(uniqueCourts.size).toBe(activeMatches.length);
    
    // Count players in matches
    const playersInMatches = activeMatches.reduce(
      (sum, m) => sum + m.team1.length + m.team2.length, 
      0
    );
    
    // Should have at least 12 players in matches (3 courts * 4 players)
    expect(playersInMatches).toBeGreaterThanOrEqual(12);
    
    // Waiting players should be 2 or fewer
    expect(session.waitingPlayers.length).toBeLessThanOrEqual(2);
  });

  it('should fill all 4 courts when possible', () => {
    // Create 16 players (exactly 4 courts worth)
    const players: Player[] = [];
    for (let i = 1; i <= 16; i++) {
      players.push({ id: `player${i}`, name: `Player ${i}` });
    }

    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: players,
      courts: 4,
      bannedPairs: [],
      randomizePlayerOrder: false,
    };

    let session = createSession(config, 100);
    session = evaluateAndCreateMatches(session);

    const activeMatches = session.matches.filter(
      m => m.status === 'in-progress' || m.status === 'waiting'
    );

    // With exactly 16 players, all 4 courts should be filled
    expect(activeMatches.length).toBe(4);
    expect(session.waitingPlayers.length).toBe(0);
  });

  it('should fill 2 courts with 8 players', () => {
    const players: Player[] = [];
    for (let i = 1; i <= 8; i++) {
      players.push({ id: `player${i}`, name: `Player ${i}` });
    }

    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: players,
      courts: 4,
      bannedPairs: [],
      randomizePlayerOrder: false,
    };

    let session = createSession(config, 100);
    session = evaluateAndCreateMatches(session);

    const activeMatches = session.matches.filter(
      m => m.status === 'in-progress' || m.status === 'waiting'
    );

    // With 8 players, should fill 2 courts
    expect(activeMatches.length).toBe(2);
    expect(session.waitingPlayers.length).toBe(0);
  });
});
