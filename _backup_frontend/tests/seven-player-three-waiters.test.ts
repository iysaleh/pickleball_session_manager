import { describe, it, expect } from 'vitest';
import { createSession, completeMatch, evaluateAndCreateMatches } from '../session';
import type { SessionConfig } from '../types';

describe('Seven Player - Three Waiters Bug', () => {
  it('should ensure all 3 waiting players get to play after waiting one round', () => {
    // Setup: 7 players in King of the Court mode
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
      ],
      bannedPairs: [],
    };

    let session = createSession(config);

    // Round 1: Create first match (4 players play, 3 wait)
    session = evaluateAndCreateMatches(session);
    
    // Should have 1 match with 4 players
    const activeMatches = session.matches.filter(m => m.status === 'waiting');
    expect(activeMatches.length).toBe(1);
    
    // Get the 4 players who are playing
    const playingPlayers = new Set([
      ...activeMatches[0].team1,
      ...activeMatches[0].team2,
    ]);
    
    // 3 players should be waiting
    const waitingPlayers = config.players
      .map(p => p.id)
      .filter(id => !playingPlayers.has(id));
    expect(waitingPlayers.length).toBe(3);
    
    // Check that waiting players all have gamesWaited = 1
    waitingPlayers.forEach(id => {
      const stats = session.playerStats.get(id);
      expect(stats?.gamesWaited).toBe(1);
    });

    // Start the match
    session.matches[0].status = 'in-progress';
    
    // Complete the match
    session = completeMatch(session, session.matches[0].id, 11, 5);
    
    // Round 2: Create next match - ALL 3 waiting players should play now
    session = evaluateAndCreateMatches(session);
    
    // Find the new match (should be the 2nd match)
    const newMatches = session.matches.filter(m => m.status === 'waiting');
    expect(newMatches.length).toBeGreaterThan(0);
    
    // Get all players in new matches
    const playersInNewMatches = new Set<string>();
    newMatches.forEach(match => {
      match.team1.forEach(id => playersInNewMatches.add(id));
      match.team2.forEach(id => playersInNewMatches.add(id));
    });
    
    // CRITICAL: ALL 3 waiting players MUST be in the new match(es)
    // This was the bug - only 2 were getting selected
    const waitingPlayersInNewMatch = waitingPlayers.filter(id => playersInNewMatches.has(id));
    expect(waitingPlayersInNewMatch.length).toBe(3);
    
    // Verify: The 3 waiting players should now have gamesWaited = 0 (they're playing)
    // Actually, gamesWaited only resets after they've been selected, and they shouldn't increment
    // again since they were just selected. Let's just verify they're all playing.
  });

  it('should handle 7 players with 3 waiters across multiple rounds', () => {
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
      ],
      bannedPairs: [],
    };

    let session = createSession(config);

    // Simulate multiple rounds
    for (let round = 0; round < 3; round++) {
      // Create matches
      session = evaluateAndCreateMatches(session);
      
      // Start all matches
      session.matches
        .filter(m => m.status === 'waiting')
        .forEach(match => {
          match.status = 'in-progress';
        });
      
      // Complete all matches
      const matchesToComplete = session.matches.filter(m => m.status === 'in-progress');
      matchesToComplete.forEach(match => {
        session = completeMatch(session, match.id, 11, 5);
      });
    }

    // After 3 rounds, check that no one has been unfairly left waiting
    // Calculate max wait difference
    const waitCounts: number[] = [];
    session.playerStats.forEach(stats => {
      waitCounts.push(stats.gamesWaited);
    });
    
    const maxWaits = Math.max(...waitCounts);
    const minWaits = Math.min(...waitCounts);
    
    // No one should have waited more than 2 times more than someone else
    // (some variation is OK, but not excessive)
    expect(maxWaits - minWaits).toBeLessThanOrEqual(2);
  });
});

