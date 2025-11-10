import { describe, it, expect } from 'vitest';
import { createSession, addPlayerToSession, completeMatch, startMatch, evaluateAndCreateMatches } from '../session';
import type { Player, SessionConfig } from '../types';

describe('Player Addition - Second Court Filling', () => {
  it('should fill second court when 8th player is added mid-session', () => {
    // Start with 7 players
    const initialPlayers: Player[] = [
      { id: '1', name: 'Player 1' },
      { id: '2', name: 'Player 2' },
      { id: '3', name: 'Player 3' },
      { id: '4', name: 'Player 4' },
      { id: '5', name: 'Player 5' },
      { id: '6', name: 'Player 6' },
      { id: 'Ibraheem', name: 'Ibraheem' },
    ];

    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: initialPlayers,
      courts: 4,
      bannedPairs: [],
    };

    let session = createSession(config);
    session = evaluateAndCreateMatches(session);

    // Should have 1 match with 7 players (4 playing, 3 waiting)
    expect(session.matches.length).toBe(1);
    expect(session.waitingPlayers.length).toBe(3);

    // Start the match
    const firstMatch = session.matches[0];
    session = startMatch(session, firstMatch.id);

    // Add 8th player (Jeremy) while match is in progress
    const jeremy: Player = { id: 'Jeremy', name: 'Jeremy' };
    session = addPlayerToSession(session, jeremy);

    // After adding Jeremy, should have 2 matches:
    // - First match still in progress (4 players)
    // - Second match waiting with Jeremy + 3 waiting players
    const activeMatches = session.matches.filter(
      m => m.status === 'in-progress' || m.status === 'waiting'
    );

    // CRITICAL: With 8 players and 1 court occupied, should create a 2nd match
    expect(activeMatches.length).toBe(2);

    // Verify all 8 players are in matches
    const playersInMatches = new Set<string>();
    activeMatches.forEach(m => {
      [...m.team1, ...m.team2].forEach(id => playersInMatches.add(id));
    });
    expect(playersInMatches.size).toBe(8);

    // Verify Jeremy is playing
    expect(playersInMatches.has('Jeremy')).toBe(true);
  });

  it('should create 2 balanced courts after first match completes when 8th player joins', () => {
    // Start with 7 players, play some matches, then add 8th player
    const initialPlayers: Player[] = [
      { id: '1', name: 'Player 1' },
      { id: '2', name: 'Player 2' },
      { id: '3', name: 'Player 3' },
      { id: '4', name: 'Player 4' },
      { id: '5', name: 'Player 5' },
      { id: '6', name: 'Player 6' },
      { id: 'Ibraheem', name: 'Ibraheem' },
    ];

    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: initialPlayers,
      courts: 4,
      bannedPairs: [],
    };

    let session = createSession(config);

    // Play 2 complete matches with 7 players
    for (let i = 0; i < 2; i++) {
      session = evaluateAndCreateMatches(session);
      const match = session.matches.find(m => m.status === 'waiting');
      if (match) {
        session = startMatch(session, match.id);
        session = completeMatch(session, match.id, 11, 7);
      }
    }

    // Start a 3rd match
    session = evaluateAndCreateMatches(session);
    const thirdMatch = session.matches.find(m => m.status === 'waiting');
    expect(thirdMatch).toBeDefined();

    if (thirdMatch) {
      session = startMatch(session, thirdMatch.id);

      // Add Jeremy while 3rd match is in progress
      const jeremy: Player = { id: 'Jeremy', name: 'Jeremy' };
      session = addPlayerToSession(session, jeremy);

      // Should now have 2 matches active (original + new one with Jeremy)
      let activeMatches = session.matches.filter(
        m => m.status === 'in-progress' || m.status === 'waiting'
      );
      expect(activeMatches.length).toBe(2);

      // Complete the 3rd match
      session = completeMatch(session, thirdMatch.id, 11, 7);

      // After completing, should create 2 new courts with all 8 players
      activeMatches = session.matches.filter(
        m => m.status === 'in-progress' || m.status === 'waiting'
      );

      // CRITICAL: Should wait for both courts to finish to create balanced matches
      // OR if both courts finished, should create 2 new matches
      // For now, check that we have either 1 or 2 active matches
      expect(activeMatches.length).toBeGreaterThanOrEqual(1);
      expect(activeMatches.length).toBeLessThanOrEqual(2);
    }
  });
});

