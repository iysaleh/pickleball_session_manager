import { describe, it, expect } from 'vitest';
import { createSession, evaluateAndCreateMatches } from './session';
import type { SessionConfig } from './types';

describe('Stalled Session Recovery', () => {
  it('should create matches immediately when all courts are empty and players are ready', () => {
    // Setup: 7 players, all courts empty, but players are available
    // This simulates the scenario from pickleball-session-11-05-2025-10-11.txt
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
      players: [
        { id: 'Ibraheem', name: 'Ibraheem' },
        { id: '1', name: '1' },
        { id: '2', name: '2' },
        { id: '3', name: '3' },
        { id: '4', name: '4' },
        { id: '5', name: '5' },
        { id: '6', name: '6' },
        { id: '7', name: '7' },
      ],
      bannedPairs: [],
    };

    const session = createSession(config);

    // Manually set some players to have waited (simulating they were waiting before)
    session.playerStats.get('Ibraheem')!.gamesWaited = 2;
    session.playerStats.get('1')!.gamesWaited = 2;
    session.playerStats.get('2')!.gamesWaited = 1;
    session.playerStats.get('3')!.gamesWaited = 1;
    session.playerStats.get('4')!.gamesWaited = 0;
    session.playerStats.get('5')!.gamesWaited = 0;
    session.playerStats.get('6')!.gamesWaited = 0;
    session.playerStats.get('7')!.gamesWaited = 0;

    // All courts are empty (no active matches)
    // Should create matches immediately using the most-waited players
    const updatedSession = evaluateAndCreateMatches(session);

    // Should have at least 1 match created
    expect(updatedSession.matches.length).toBeGreaterThan(0);

    // The match should prioritize the most-waited players
    const firstMatch = updatedSession.matches[0];
    const playersInMatch = [...firstMatch.team1, ...firstMatch.team2];

    // Ibraheem and '1' waited the most (2 times), so they should be included
    expect(playersInMatch).toContain('Ibraheem');
    expect(playersInMatch).toContain('1');

    // At least 2 of the players who waited 1 time should also be included
    const oneWaiters = ['2', '3'];
    const oneWaitersInMatch = playersInMatch.filter(id => oneWaiters.includes(id));
    expect(oneWaitersInMatch.length).toBeGreaterThanOrEqual(2);
  });

  it('should create fair matches when session is stalled with 4 or more players', () => {
    // Test with exactly 4 players (minimum for doubles)
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
      players: [
        { id: '1', name: 'Player 1' },
        { id: '2', name: 'Player 2' },
        { id: '3', name: 'Player 3' },
        { id: '4', name: 'Player 4' },
      ],
      bannedPairs: [],
    };

    const session = createSession(config);

    // All players have equal wait times
    session.playerStats.forEach(stats => {
      stats.gamesWaited = 1;
    });

    // Create matches (all courts empty, 4 players ready)
    const updatedSession = evaluateAndCreateMatches(session);

    // Should create exactly 1 match with all 4 players
    expect(updatedSession.matches.length).toBe(1);
    const match = updatedSession.matches[0];
    expect(match.team1.length).toBe(2);
    expect(match.team2.length).toBe(2);

    // All 4 players should be in the match
    const playersInMatch = [...match.team1, ...match.team2];
    expect(playersInMatch).toHaveLength(4);
    expect(new Set(playersInMatch).size).toBe(4); // All unique
  });

  it('should create balanced matches when session is stalled with 8 players', () => {
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
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
      bannedPairs: [],
    };

    const session = createSession(config);

    // Set different wait times to test fairness
    session.playerStats.get('1')!.gamesWaited = 3;
    session.playerStats.get('2')!.gamesWaited = 3;
    session.playerStats.get('3')!.gamesWaited = 2;
    session.playerStats.get('4')!.gamesWaited = 2;
    session.playerStats.get('5')!.gamesWaited = 1;
    session.playerStats.get('6')!.gamesWaited = 1;
    session.playerStats.get('7')!.gamesWaited = 0;
    session.playerStats.get('8')!.gamesWaited = 0;

    // All courts empty, 8 players available
    const updatedSession = evaluateAndCreateMatches(session);

    // Should create 2 matches (8 players / 4 per match = 2)
    expect(updatedSession.matches.length).toBe(2);

    // Get all players in matches
    const playersInMatches = new Set<string>();
    updatedSession.matches.forEach(match => {
      [...match.team1, ...match.team2].forEach(id => playersInMatches.add(id));
    });

    // All 8 players should be playing
    expect(playersInMatches.size).toBe(8);

    // The 4 most-waited players (1, 2, 3, 4) should all be included
    expect(playersInMatches.has('1')).toBe(true);
    expect(playersInMatches.has('2')).toBe(true);
    expect(playersInMatches.has('3')).toBe(true);
    expect(playersInMatches.has('4')).toBe(true);
  });
});
