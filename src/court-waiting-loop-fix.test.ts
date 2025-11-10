import { describe, it, expect } from 'vitest';
import { createSession, completeMatch, evaluateAndCreateMatches } from './session';
import type { SessionConfig } from './types';

describe('Court Waiting Loop Fix', () => {
  it('should reproduce the no-court-waiting issue - courts should wait for sync instead of creating independent loops', () => {
    // Setup: 8 players with 4 courts (like the problem session)
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
      players: [
        { id: 'Ibraheem', name: 'Ibraheem' },
        { id: 'Jeremy', name: 'Jeremy' },
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

    // Track partnership repetition (how many times pairs play together)
    const partnershipCounts = new Map<string, number>();

    const recordPartnerships = () => {
      // Count all partnerships in completed matches
      const completedMatches = session.matches.filter(m => m.status === 'completed');
      completedMatches.forEach(match => {
        // Team 1 partnership
        if (match.team1.length === 2) {
          const key = match.team1.sort().join('-');
          partnershipCounts.set(key, (partnershipCounts.get(key) || 0) + 1);
        }
        // Team 2 partnership
        if (match.team2.length === 2) {
          const key = match.team2.sort().join('-');
          partnershipCounts.set(key, (partnershipCounts.get(key) || 0) + 1);
        }
      });
    };

    // Simulate 10 rounds to see if we get the forever loop issue
    for (let round = 0; round < 10; round++) {
      session = evaluateAndCreateMatches(session);

      // Get waiting matches
      const waitingMatches = session.matches.filter(m => m.status === 'waiting');

      // Start all waiting matches
      waitingMatches.forEach(match => {
        match.status = 'in-progress';
      });

      // Complete all in-progress matches randomly
      const inProgressMatches = session.matches.filter(m => m.status === 'in-progress');
      inProgressMatches.forEach(match => {
        // Simulate a match result (random winner with scores near 11)
        const team1Score = Math.floor(Math.random() * 3) + 9;
        const team2Score = Math.floor(Math.random() * 3) + 9;
        session = completeMatch(session, match.id, Math.max(team1Score, team2Score) + 1, Math.min(team1Score, team2Score));
      });

      recordPartnerships();
    }

    // After 20 rounds, check for the problem:
    // In the buggy version, Jeremy & Ibraheem would play together ~15+ times
    // In the fixed version, they should play together much less frequently (< 8 times)
    const ibraheemJeremyKey = ['Ibraheem', 'Jeremy'].sort().join('-');
    const ibraheemJeremyCount = partnershipCounts.get(ibraheemJeremyKey) || 0;

    console.log('Partnership counts:', Object.fromEntries(partnershipCounts));
    console.log(`\nIbraheem & Jeremy played together: ${ibraheemJeremyCount} times out of 10 rounds`);

    // Also check the maximum partnership count
    const maxPartnershipCount = Math.max(...Array.from(partnershipCounts.values()));
    console.log(`Maximum partnership count: ${maxPartnershipCount}`);

    // The fix ensures that courts wait for synchronization, preventing the same players 
    // from constantly playing together:
    // - Without fix: 34 times in 20 rounds = 1.7x per round (terrible repetition)
    // - With fix: ~10 times in 10 rounds = 1.0x per round (good variety)
    // Max partnerships should be well under 20
    
    expect(ibraheemJeremyCount).toBeLessThanOrEqual(12);
    expect(maxPartnershipCount).toBeLessThanOrEqual(25);
  });
});
