import { describe, it, expect } from 'vitest';
import { createSession, completeMatch, evaluateAndCreateMatches } from '../session';
import type { Player, SessionConfig } from '../types';

describe('Seven Player Waiting Bug', () => {
  it('should ensure all 3 waiting players get to play after first match in 7-player KOC session', () => {
    // Create 7 players
    const players: Player[] = [
      { id: '1', name: 'Player 1' },
      { id: '2', name: 'Player 2' },
      { id: '3', name: 'Player 3' },
      { id: '4', name: 'Player 4' },
      { id: '5', name: 'Player 5' },
      { id: '6', name: 'Player 6' },
      { id: '7', name: 'Player 7' },
    ];

    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 4,
      bannedPairs: [],
    };

    // Create session and evaluate to create first match
    let session = createSession(config);
    session = evaluateAndCreateMatches(session);
    
    // First match should be created with 4 players
    expect(session.matches.length).toBe(1);
    const firstMatch = session.matches[0];
    expect(firstMatch.status).toBe('waiting');
    
    // 3 players should be waiting
    expect(session.waitingPlayers.length).toBe(3);
    const waitingPlayerIds = new Set(session.waitingPlayers);
    
    // Complete the first match
    session = completeMatch(session, firstMatch.id, 11, 5);
    
    // After first match completes, a second match should be created
    const activeMatches = session.matches.filter(m => m.status === 'in-progress' || m.status === 'waiting');
    expect(activeMatches.length).toBe(1);
    
    const secondMatch = activeMatches[0];
    const secondMatchPlayers = new Set([...secondMatch.team1, ...secondMatch.team2]);
    
    // CRITICAL: All 3 players who were waiting should be in the second match
    // (or at least the top 2-3 by wait priority should be selected)
    // The 4 players from the first match should NOT all be selected again
    const firstMatchPlayers = new Set([...firstMatch.team1, ...firstMatch.team2]);
    
    // Count how many players from first match are in second match
    let playersFromFirstMatch = 0;
    firstMatchPlayers.forEach(id => {
      if (secondMatchPlayers.has(id)) {
        playersFromFirstMatch++;
      }
    });
    
    // CRITICAL CHECK: At most 1 player from first match should be in second match
    // (ideally 0, but with ranking constraints maybe 1)
    // We should NOT see 2+ players from first match in second match
    expect(playersFromFirstMatch).toBeLessThanOrEqual(1);
    
    // Count how many waiting players are in second match
    let waitingPlayersInSecondMatch = 0;
    waitingPlayerIds.forEach(id => {
      if (secondMatchPlayers.has(id)) {
        waitingPlayersInSecondMatch++;
      }
    });
    
    // CRITICAL CHECK: At least 3 of the waiting players should be in second match
    // (or all 3 if we only have 3 waiting)
    if (waitingPlayerIds.size === 3) {
      expect(waitingPlayersInSecondMatch).toBe(3);
    } else {
      expect(waitingPlayersInSecondMatch).toBeGreaterThanOrEqual(3);
    }
  });

  it('should prioritize waiting players over players who just finished a match', () => {
    // Create 7 players
    const players: Player[] = [
      { id: 'A', name: 'Alice' },
      { id: 'B', name: 'Bob' },
      { id: 'C', name: 'Charlie' },
      { id: 'D', name: 'David' },
      { id: 'E', name: 'Eve' },
      { id: 'F', name: 'Frank' },
      { id: 'G', name: 'Grace' },
    ];

    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 2,
      bannedPairs: [],
    };

    // Create session and evaluate to create first match
    let session = createSession(config);
    session = evaluateAndCreateMatches(session);
    
    // First match should be created
    expect(session.matches.length).toBe(1);
    const firstMatch = session.matches[0];
    
    // Track who played in first match
    const firstMatchPlayerSet = new Set([...firstMatch.team1, ...firstMatch.team2]);
    
    // Track who waited
    const waitingPlayers = new Set(session.waitingPlayers);
    expect(waitingPlayers.size).toBe(3);
    
    // Complete first match
    session = completeMatch(session, firstMatch.id, 11, 7);
    
    // Second match should now exist
    const activeMatches = session.matches.filter(m => m.status === 'in-progress' || m.status === 'waiting');
    expect(activeMatches.length).toBe(1);
    
    const secondMatch = activeMatches[0];
    const secondMatchPlayerSet = new Set([...secondMatch.team1, ...secondMatch.team2]);
    
    // Count overlaps
    let playersFromBothMatches = 0;
    firstMatchPlayerSet.forEach(id => {
      if (secondMatchPlayerSet.has(id)) {
        playersFromBothMatches++;
      }
    });
    
    // Waiting players should get priority
    let waitersInSecondMatch = 0;
    waitingPlayers.forEach(id => {
      if (secondMatchPlayerSet.has(id)) {
        waitersInSecondMatch++;
      }
    });
    
    // CRITICAL: At least 3 waiting players should be selected for second match
    expect(waitersInSecondMatch).toBe(3);
    
    // CRITICAL: At most 1 player from first match should play again immediately
    expect(playersFromBothMatches).toBeLessThanOrEqual(1);
  });
});

