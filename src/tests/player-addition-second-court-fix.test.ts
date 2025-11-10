import { describe, it, expect } from 'vitest';
import { createSession, addPlayerToSession, completeMatch, evaluateAndCreateMatches } from '../session';
import type { SessionConfig, Player } from '../types';

describe('Player Addition - Second Court Creation', () => {
  it('should create a second court when an 8th player is added to a 7-player game', () => {
    // Setup: Start with 7 players
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

    // Create first match (4 play, 3 wait)
    session = evaluateAndCreateMatches(session);
    expect(session.matches.filter(m => m.status === 'waiting').length).toBe(1);

    // Start the match
    session.matches[0].status = 'in-progress';

    // Now add an 8th player (Jeremy)
    const newPlayer: Player = { id: 'Jeremy', name: 'Jeremy' };
    session = addPlayerToSession(session, newPlayer);

    // After adding the player, we should now have enough for 2 courts
    // Check if a second court was created
    const waitingMatches = session.matches.filter(m => m.status === 'waiting');
    const inProgressMatches = session.matches.filter(m => m.status === 'in-progress');

    // Should have 1 in-progress match and 1 waiting match (second court just created)
    expect(inProgressMatches.length).toBe(1);
    expect(waitingMatches.length).toBe(1);

    // Verify the second court uses the 3 waiting players + the new player
    const secondCourtMatch = waitingMatches[0];
    const playersInSecondCourt = [...secondCourtMatch.team1, ...secondCourtMatch.team2];

    // Jeremy (the new player) should be in the second court
    expect(playersInSecondCourt).toContain('Jeremy');

    // The 3 players who were waiting should also be in the second court
    const firstCourtPlayers = [
      ...inProgressMatches[0].team1,
      ...inProgressMatches[0].team2,
    ];
    const waitingPlayersBefore = config.players
      .map(p => p.id)
      .filter(id => !firstCourtPlayers.includes(id));

    // At least 3 of the waiting players should be in the second court
    const waitersInSecondCourt = playersInSecondCourt.filter(id => waitingPlayersBefore.includes(id));
    expect(waitersInSecondCourt.length).toBe(3);
  });

  it('should fill both courts when first court finishes after adding 8th player', () => {
    // This tests the scenario from the session files where after adding Jeremy,
    // Court 1 finishes but then only 1 court gets filled instead of creating 2 balanced courts
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

    // Play a few rounds to establish some stats
    for (let i = 0; i < 2; i++) {
      session = evaluateAndCreateMatches(session);
      session.matches
        .filter(m => m.status === 'waiting')
        .forEach(m => { m.status = 'in-progress'; });
      const toComplete = session.matches.filter(m => m.status === 'in-progress');
      toComplete.forEach(m => {
        session = completeMatch(session, m.id, 11, 5);
      });
    }

    // Start a new match
    session = evaluateAndCreateMatches(session);
    const beforeAddingPlayer = session.matches.filter(m => m.status === 'waiting');
    expect(beforeAddingPlayer.length).toBe(1);
    beforeAddingPlayer[0].status = 'in-progress';

    // Add Jeremy (8th player)
    session = addPlayerToSession(session, { id: 'Jeremy', name: 'Jeremy' });

    // Should now have 2 courts running (or 1 in-progress and 1 waiting)
    const allActive = session.matches.filter(m => 
      m.status === 'in-progress' || m.status === 'waiting'
    );
    expect(allActive.length).toBe(2);

    // Complete both courts
    const toComplete = session.matches.filter(m => 
      m.status === 'in-progress' || m.status === 'waiting'
    );
    toComplete.forEach(match => {
      if (match.status === 'waiting') match.status = 'in-progress';
    });
    toComplete.forEach(match => {
      session = completeMatch(session, match.id, 11, Math.floor(Math.random() * 11));
    });

    // Now create new matches - should create 2 courts with balanced teams
    session = evaluateAndCreateMatches(session);
    const newMatches = session.matches.filter(m => m.status === 'waiting');

    // Should create 2 new courts
    expect(newMatches.length).toBe(2);

    // All 8 players should be playing
    const playersInNewMatches = new Set<string>();
    newMatches.forEach(match => {
      [...match.team1, ...match.team2].forEach(id => playersInNewMatches.add(id));
    });
    expect(playersInNewMatches.size).toBe(8);
  });

  it('should handle player addition during active session without disrupting fairness', () => {
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

    // Play 3 rounds
    for (let round = 0; round < 3; round++) {
      session = evaluateAndCreateMatches(session);
      session.matches
        .filter(m => m.status === 'waiting')
        .forEach(m => { m.status = 'in-progress'; });
      const toComplete = session.matches.filter(m => m.status === 'in-progress');
      toComplete.forEach(m => {
        session = completeMatch(session, m.id, 11, Math.floor(Math.random() * 11));
      });
    }

    // Check wait fairness before adding player
    const waitsBefore: number[] = [];
    session.playerStats.forEach(stats => waitsBefore.push(stats.gamesWaited));
    const maxWaitBefore = Math.max(...waitsBefore);

    // Add 8th player
    session = addPlayerToSession(session, { id: '8', name: 'Player 8' });

    // New player should have high wait priority
    const newPlayerStats = session.playerStats.get('8');
    expect(newPlayerStats?.gamesWaited).toBeGreaterThanOrEqual(maxWaitBefore);

    // Continue playing - verify fairness is maintained
    for (let round = 0; round < 2; round++) {
      session = evaluateAndCreateMatches(session);
      session.matches
        .filter(m => m.status === 'waiting')
        .forEach(m => { m.status = 'in-progress'; });
      const toComplete = session.matches.filter(m => m.status === 'in-progress');
      toComplete.forEach(m => {
        session = completeMatch(session, m.id, 11, Math.floor(Math.random() * 11));
      });
    }

    // Check that wait times are still fair
    const waitsAfter: number[] = [];
    session.playerStats.forEach(stats => waitsAfter.push(stats.gamesWaited));
    const maxWaitAfter = Math.max(...waitsAfter);
    const minWaitAfter = Math.min(...waitsAfter);

    // No one should have waited excessively more than others
    expect(maxWaitAfter - minWaitAfter).toBeLessThanOrEqual(2);
  });
});

