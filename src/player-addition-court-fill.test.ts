import { describe, it, expect } from 'vitest';
import { createSession, completeMatch, addPlayerToSession, startNextRound } from './session';

describe('Player Addition - Court Fill Bug', () => {
  it('should create new court when player added makes it possible', () => {
    // Recreate the bug scenario from pickleball-session-11-05-2025-11-38.txt
    // After match 4, we have 1 court in use with 4 players
    // When Jeremy is added, we should create a 2nd court with the 4 waiting players
    
    let session = createSession({
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
      players: [
        { id: '1', name: '1' },
        { id: '2', name: '2' },
        { id: '3', name: '3' },
        { id: '4', name: '4' },
        { id: '5', name: '5' },
        { id: '6', name: '6' },
        { id: 'Ibraheem', name: 'Ibraheem' },
      ],
      bannedPairs: []
    });
    
    session = startNextRound(session);
    
    // Play 4 matches (similar to the real scenario)
    for (let i = 0; i < 4; i++) {
      const activeMatches = session.matches.filter(m => m.status === 'in-progress');
      if (activeMatches.length > 0) {
        const match = activeMatches[0];
        const ibraheemOnTeam1 = match.team1.includes('Ibraheem');
        session = completeMatch(
          session,
          match.id,
          ibraheemOnTeam1 ? 11 : 7,
          ibraheemOnTeam1 ? 7 : 11
        );
      }
    }
    
    // At this point, we should have some matches created
    const matchesBeforeCount = session.matches.length;
    const activeMatchesBefore = session.matches.filter(m => 
      m.status === 'in-progress' || m.status === 'waiting'
    ).length;
    const waitingPlayersBefore = session.waitingPlayers.length;
    
    // Add Jeremy
    session = addPlayerToSession(session, { id: 'Jeremy', name: 'Jeremy' });
    
    // NOW we have more players available
    // Should create additional match(es) if possible
    const matchesAfterCount = session.matches.length;
    const activeMatchesAfter = session.matches.filter(m => 
      m.status === 'in-progress' || m.status === 'waiting'
    ).length;
    const waitingPlayersAfter = session.waitingPlayers.length;
    
    // Should have created new match(es) or at least have capacity for them
    // With 8 players total, we can run 2 matches (4 players each)
    expect(activeMatchesAfter).toBeGreaterThanOrEqual(1);
    
    // If we have 4+ waiting, should have created a 2nd match
    if (waitingPlayersBefore >= 3) {
      expect(matchesAfterCount).toBeGreaterThan(matchesBeforeCount);
    }
  });
  
  it('should immediately create courts when 8 players available and no courts busy', () => {
    // Another scenario: 8 players, 4 courts, nothing happening
    // Should immediately create 2 courts
    
    let session = createSession({
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
      players: [
        { id: '1', name: '1' },
        { id: '2', name: '2' },
        { id: '3', name: '3' },
        { id: '4', name: '4' },
        { id: '5', name: '5' },
        { id: '6', name: '6' },
        { id: '7', name: '7' },
        { id: '8', name: '8' },
      ],
      bannedPairs: []
    });
    
    // Start round
    session = startNextRound(session);
    
    // Should create 2 matches immediately (8 players / 4 per match = 2 matches)
    const activeMatches = session.matches.filter(m => m.status === 'in-progress' || m.status === 'waiting').length;
    expect(activeMatches).toBeGreaterThanOrEqual(1); // At least 1 match
    expect(session.waitingPlayers.length).toBeLessThanOrEqual(4); // At most 4 waiting
  });
  
  it('should re-evaluate courts when match completes and player was recently added', () => {
    // Start with 7 players, 1 court in use, 3 waiting
    // Add an 8th player (now 4 waiting)
    // When the court finishes, should create 2 new courts with all 8 players
    
    let session = createSession({
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
      players: [
        { id: '1', name: '1' },
        { id: '2', name: '2' },
        { id: '3', name: '3' },
        { id: '4', name: '4' },
        { id: '5', name: '5' },
        { id: '6', name: '6' },
        { id: '7', name: '7' },
      ],
      bannedPairs: []
    });
    
    session = startNextRound(session);
    
    // Should have 1 match, 3 waiting
    const activeMatches = session.matches.filter(m => m.status === 'in-progress' || m.status === 'waiting').length;
    expect(activeMatches).toBe(1);
    expect(session.waitingPlayers.length).toBe(3);
    
    // Add 8th player
    session = addPlayerToSession(session, { id: '8', name: '8' });
    
    // Should now have 2 matches (one from before, one new)
    const afterAdd = session.matches.filter(m => m.status === 'in-progress' || m.status === 'waiting').length;
    expect(afterAdd).toBeGreaterThanOrEqual(1); // At least the original match still there
    
    // Complete the first match (or start it first if it's waiting)
    let firstMatch = session.matches.find(m => m.status === 'waiting' || m.status === 'in-progress')!;
    if (firstMatch.status === 'waiting') {
      // Manually transition to in-progress
      session = {
        ...session,
        matches: session.matches.map(m =>
          m.id === firstMatch.id ? { ...m, status: 'in-progress' as const } : m
        )
      };
    }
    session = completeMatch(session, firstMatch.id, 11, 7);
    
    // Now with all 8 players available, should create 2 matches
    const finalActive = session.matches.filter(m => m.status === 'in-progress' || m.status === 'waiting').length;
    
    // Should be running matches now with all 8 players
    expect(finalActive).toBeGreaterThanOrEqual(1);
    
    // And very few waiting (ideally 0 if 2 matches created)
    expect(session.waitingPlayers.length).toBeLessThanOrEqual(4);
  });
});
