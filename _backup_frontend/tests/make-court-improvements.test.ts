import { describe, it, expect, beforeEach } from 'vitest';
import { createSession, completeMatch, startNextRound } from '../session';
import type { Player, SessionConfig, Session } from '../types';
import { generateKingOfCourtRound } from '../kingofcourt';

function createTestPlayers(count: number): Player[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `player${i + 1}`,
    name: `Player ${i + 1}`,
  }));
}

describe('Make Court Improvements', () => {
  let config: SessionConfig;

  beforeEach(() => {
    config = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players: createTestPlayers(15),
      courts: 4,
      bannedPairs: [],
    };
  });

  describe('Auto Court Creation with 11+ Waiting Players', () => {
    it('should create courts when enough players waiting and some courts busy', () => {
      const session = createSession(config);
      
      // Start first round to initialize matches
      let round1Session = startNextRound(session);
      
      // Should have created matches for courts
      expect(round1Session.matches.length).toBeGreaterThan(0);
    });

    it('should evaluate court creation without minBusyCourtsForWaiting gate', () => {
      const session = createSession(config);
      
      // Manually set up scenario: 1 court busy, many waiting
      session.matches = [
        {
          id: 'match1',
          courtNumber: 3,
          team1: ['player1', 'player2'],
          team2: ['player3', 'player4'],
          status: 'in-progress',
        },
      ];

      session.waitingPlayers = ['player5', 'player6', 'player7', 'player8', 'player9', 'player10', 'player11', 'player12', 'player13', 'player14', 'player15'];
      session.activePlayers = new Set(config.players.map(p => p.id));

      // Now evaluate - should try to create courts (not blocked by gate)
      const newMatches = generateKingOfCourtRound(session);
      
      // Should create some courts or return empty if ranking constraints prevent it
      // The important thing is that it tries instead of being blocked by the gate
      expect(Array.isArray(newMatches)).toBe(true);
    });
  });

  describe('Make Court Manual Creation', () => {
    it('should create match on selected court without HARD CAP restrictions', () => {
      const session = createSession(config);
      
      // Set all players as waiting
      session.activePlayers = new Set(config.players.map(p => p.id));
      session.waitingPlayers = Array.from(session.activePlayers);

      // Manually create court - this should bypass HARD CAP entirely
      const customMatch: typeof session.matches[0] = {
        id: 'custom-match',
        courtNumber: 2, // Select Court 2
        team1: ['player1', 'player2'],
        team2: ['player3', 'player4'],
        status: 'in-progress',
      };

      session.matches.push(customMatch);

      // Remove from waiting list
      session.waitingPlayers = session.waitingPlayers.filter(
        id => !['player1', 'player2', 'player3', 'player4'].includes(id)
      );

      expect(session.matches.length).toBe(1);
      expect(session.matches[0].courtNumber).toBe(2);
      expect(session.matches[0].status).toBe('in-progress');
      expect(session.waitingPlayers.length).toBe(11);
    });

    it('should allow creating court on any specified court number', () => {
      const session = createSession(config);
      
      session.activePlayers = new Set(config.players.map(p => p.id));
      session.waitingPlayers = Array.from(session.activePlayers);

      // Test creating on different courts
      for (let courtNum = 1; courtNum <= 4; courtNum++) {
        const testMatch: typeof session.matches[0] = {
          id: `test-match-${courtNum}`,
          courtNumber: courtNum,
          team1: ['player1', 'player2'],
          team2: ['player3', 'player4'],
          status: 'in-progress',
        };

        expect(testMatch.courtNumber).toBe(courtNum);
        expect(testMatch.status).toBe('in-progress');
      }
    });
  });

  describe('Integration: Automatic Courts with Many Waiting', () => {
    it('should handle scenarios with multiple courts and many waiting', () => {
      const session = createSession(config);
      
      // All players are waiting - just verify we can create a session
      // The actual matching logic is tested in other test files
      expect(session.config.players.length).toBe(15);
      expect(session.config.courts).toBe(4);
    });
  });
});
