import { describe, it, expect } from 'vitest';
import { createSession, evaluateAndCreateMatches, completeMatch, addPlayerToSession } from '../session';
import type { Player, SessionConfig } from '../types';

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

  it('should never leave courts empty when enough players are waiting', () => {
    // Simulate the scenario from pickleball-session-11-04-2025-21-30.txt
    // 13 active players, 4 courts, but only 2 courts were being used
    const players: Player[] = [];
    for (let i = 1; i <= 13; i++) {
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

    // With 13 players and 4 courts, should fill 3 courts (12 players), leaving 1 waiting
    expect(activeMatches.length).toBeGreaterThanOrEqual(3);
    expect(session.waitingPlayers.length).toBeLessThanOrEqual(1);
  });

  it('should handle adding players mid-session with provisional logic', () => {
    // Simulate pickleball-session-11-04-2025-21-40.txt
    // Start with 10 players, then add 2 more
    const initialPlayers: Player[] = [];
    for (let i = 1; i <= 10; i++) {
      initialPlayers.push({ id: `player${i}`, name: `Player ${i}` });
    }

    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: initialPlayers,
      courts: 4,
      bannedPairs: [],
      randomizePlayerOrder: false,
    };

    // Create session and start some matches
    let session = createSession(config, 100);
    session = evaluateAndCreateMatches(session);

    // Simulate some completed matches to establish rankings
    const firstMatch = session.matches[0];
    if (firstMatch) {
      session = completeMatch(session, firstMatch.id, 11, 5);
      session = evaluateAndCreateMatches(session);
    }

    const secondMatch = session.matches.find(m => m.status === 'in-progress' || m.status === 'waiting');
    if (secondMatch) {
      session = completeMatch(session, secondMatch.id, 11, 3);
      session = evaluateAndCreateMatches(session);
    }

    // Now add 2 new players mid-session
    const newPlayer1: Player = { id: 'player11', name: 'Player 11' };
    const newPlayer2: Player = { id: 'player12', name: 'Player 12' };
    
    session = addPlayerToSession(session, newPlayer1);
    session = addPlayerToSession(session, newPlayer2);

    // After adding players, evaluate matches
    session = evaluateAndCreateMatches(session);

    const activeMatches = session.matches.filter(
      m => m.status === 'in-progress' || m.status === 'waiting'
    );

    // With 12 active players and 4 courts, should have at least 2 courts active
    // (ideally 3 courts, but at minimum we shouldn't be stuck with just 1 court)
    expect(activeMatches.length).toBeGreaterThanOrEqual(2);
    
    // Shouldn't have more than 4 players waiting when we have 12 total and 4 courts
    expect(session.waitingPlayers.length).toBeLessThanOrEqual(4);
  });

  it('should allow two provisional players to play together across rank boundaries', () => {
    // Create a session with established players
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

    // Complete several matches to establish clear top/bottom rankings
    for (let i = 0; i < 4; i++) {
      const match = session.matches.find(m => m.status === 'in-progress' || m.status === 'waiting');
      if (match) {
        // Make team1 win consistently to create ranking separation
        session = completeMatch(session, match.id, 11, 2);
        session = evaluateAndCreateMatches(session);
      }
    }

    // Add 4 new provisional players
    const newPlayers: Player[] = [
      { id: 'new1', name: 'New Player 1' },
      { id: 'new2', name: 'New Player 2' },
      { id: 'new3', name: 'New Player 3' },
      { id: 'new4', name: 'New Player 4' },
    ];

    newPlayers.forEach(player => {
      session = addPlayerToSession(session, player);
    });

    session = evaluateAndCreateMatches(session);

    // With 12 total players (8 established + 4 new), should be able to create matches
    // The 4 new provisional players should be able to form at least one match together
    const activeMatches = session.matches.filter(
      m => m.status === 'in-progress' || m.status === 'waiting'
    );

    // Should have at least 2 courts active with 12 players
    expect(activeMatches.length).toBeGreaterThanOrEqual(2);

    // Check if any match contains 2 or more new players
    const matchesWithNewPlayers = activeMatches.filter(match => {
      const allPlayers = [...match.team1, ...match.team2];
      const newPlayerCount = allPlayers.filter(id => id.startsWith('new')).length;
      return newPlayerCount >= 2;
    });

    // At least one match should have provisional players playing together
    expect(matchesWithNewPlayers.length).toBeGreaterThan(0);
  });

  it('should integrate provisional players with recent match players for variety', () => {
    // Test case from pickleball-session-11-04-2025-23-07.txt
    // 14 players total, 4 courts, Match 1 completes (1 & 2 vs 3 & 4)
    // Waiting: 1, 2, 3, 4, 13 (0 games), Ibraheem (0 games)
    // Should create a match mixing provisional players with winners/losers
    
    const players: Player[] = [];
    for (let i = 1; i <= 14; i++) {
      if (i === 13) {
        players.push({ id: 'player13', name: '13' });
      } else if (i === 14) {
        players.push({ id: 'ibraheem', name: 'Ibraheem' });
      } else {
        players.push({ id: `player${i}`, name: `${i}` });
      }
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

    // Complete first match: players 1 & 2 vs 3 & 4 (1 & 2 win)
    const firstMatch = session.matches.find(m => 
      m.team1.includes('player1') && m.team1.includes('player2') &&
      m.team2.includes('player3') && m.team2.includes('player4')
    );

    if (firstMatch) {
      session = completeMatch(session, firstMatch.id, 11, 4);
    }

    // Now we should have:
    // - 2 courts still in progress
    // - Players 1, 2, 3, 4 waiting
    // - Players 13 and Ibraheem also waiting (0 games)
    
    // Evaluate to create next matches
    session = evaluateAndCreateMatches(session);

    // Count active matches
    const activeMatches = session.matches.filter(
      m => m.status === 'in-progress' || m.status === 'waiting'
    );

    // With 6 waiting players (including 2 provisional), should create at least 1 new match
    // Don't wait just because players from last match are available - we have new players!
    const newMatches = activeMatches.filter(m => 
      m.id !== firstMatch?.id && // Not the original match
      (m.status === 'waiting' || m.status === 'in-progress')
    );

    expect(newMatches.length).toBeGreaterThan(0);

    // At least one new match should include a provisional player
    const matchesWithProvisional = newMatches.filter(match => {
      const allPlayers = [...match.team1, ...match.team2];
      return allPlayers.includes('player13') || allPlayers.includes('ibraheem');
    });

    expect(matchesWithProvisional.length).toBeGreaterThan(0);

    // Verify provisional players are actually playing (not waiting)
    const provisionalStats = [
      session.playerStats.get('player13'),
      session.playerStats.get('ibraheem')
    ].filter(s => s !== undefined);

    // At least one provisional player should be in a match or have played
    const inMatches = matchesWithProvisional.some(match => {
      const allPlayers = [...match.team1, ...match.team2];
      return allPlayers.includes('player13') || allPlayers.includes('ibraheem');
    });

    expect(inMatches).toBe(true);
  });
});

