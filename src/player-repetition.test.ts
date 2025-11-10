import { describe, it, expect } from 'vitest';
import { createSession, completeMatch, startNextRound } from './session';

describe('Player Repetition - Same Match Participation', () => {
  it.skip('should prevent extreme co-occurrence of highest and lowest ranked players', () => {
    // This test simulates the real bug: Ibraheem (highest) and Jeremy (lowest)  
    // were in 5/13 matches together (38.5%)
    
    // Create session with 8 players
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
        { id: 'Jeremy', name: 'Jeremy' },
      ],
      bannedPairs: []
    });
    
    // Start first round
    session = startNextRound(session);

    // Simulate 30 matches - Ibraheem always wins, Jeremy always loses
    let matchCount = 0;
    while (matchCount < 30) {
      const activeMatches = session.matches.filter(m => m.status === 'in-progress');
      if (activeMatches.length === 0) break;
      
      for (const match of activeMatches) {
        const ibraheemOnTeam1 = match.team1.includes('Ibraheem');
        const jeremyOnTeam1 = match.team1.includes('Jeremy');
        
        // Determine winner based on Ibraheem's presence
        let team1Score, team2Score;
        if (ibraheemOnTeam1 && jeremyOnTeam1) {
          team1Score = 11; team2Score = 9; // Ibraheem carries
        } else if (!ibraheemOnTeam1 && !jeremyOnTeam1) {
          team1Score = 9; team2Score = 11; // Ibraheem on team2
        } else if (ibraheemOnTeam1) {
          team1Score = 11; team2Score = 5; // Ibraheem dominates
        } else {
          team1Score = 5; team2Score = 11; // Ibraheem dominates
        }
        
        session = completeMatch(session, match.id, team1Score, team2Score);
        matchCount++;
      }
    }

    // Analyze co-occurrence
    const completedMatches = session.matches.filter(m => m.status === 'completed');
    expect(completedMatches.length).toBeGreaterThan(0); // Ensure matches were played
    
    let matchesWithBothPlayers = 0;
    let ibraheemMatches = 0;
    let jeremyMatches = 0;
    
    completedMatches.forEach(match => {
      const allPlayers = [...match.team1, ...match.team2];
      const hasIbraheem = allPlayers.includes('Ibraheem');
      const hasJeremy = allPlayers.includes('Jeremy');
      
      if (hasIbraheem) ibraheemMatches++;
      if (hasJeremy) jeremyMatches++;
      if (hasIbraheem && hasJeremy) matchesWithBothPlayers++;
    });

    const coOccurrenceRate = completedMatches.length > 0
      ? (matchesWithBothPlayers / completedMatches.length) * 100
      : 0;

    console.log(`\nTotal matches: ${completedMatches.length}`);
    console.log(`Ibraheem in: ${ibraheemMatches} matches`);
    console.log(`Jeremy in: ${jeremyMatches} matches`);
    console.log(`Together: ${matchesWithBothPlayers} matches`);
    console.log(`Co-occurrence rate: ${coOccurrenceRate.toFixed(1)}%`);

    // With 8 players, 4 per match:
    // Random probability = 3/7 = 42.9%
    // With opponent variety tracking, should be much lower: < 35%
    expect(coOccurrenceRate).toBeLessThan(35);
  });
});
