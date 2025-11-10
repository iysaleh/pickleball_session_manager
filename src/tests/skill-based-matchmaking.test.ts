import { describe, it, expect } from 'vitest';
import { createSession, completeMatch, evaluateAndCreateMatches } from '../session';
import type { SessionConfig } from '../types';

describe('Skill-Based Matchmaking Improvement', () => {
  it('should create balanced matches by pairing strong and weak players to balance teams', () => {
    // Setup: 8 players with 4 courts
    // We'll artificially create a scenario where one player is much stronger
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      courts: 4,
      players: [
        { id: 'Ibraheem', name: 'Ibraheem' },     // Will be the strongest
        { id: 'Jeremy', name: 'Jeremy' },         // Strong
        { id: '1', name: '1' },                   // Medium-strong
        { id: '2', name: '2' },                   // Medium
        { id: '3', name: '3' },                   // Medium-weak
        { id: '4', name: '4' },                   // Medium-weak
        { id: '5', name: '5' },                   // Weak
        { id: '6', name: '6' },                   // Weak
      ],
      bannedPairs: [],
    };

    let session = createSession(config);

    // Simulate several rounds to let skill differences emerge
    for (let round = 0; round < 8; round++) {
      session = evaluateAndCreateMatches(session);

      // Start all waiting matches
      const waitingMatches = session.matches.filter(m => m.status === 'waiting');
      waitingMatches.forEach(match => {
        match.status = 'in-progress';
      });

      // Complete all in-progress matches with skill-based outcomes
      const inProgressMatches = session.matches.filter(m => m.status === 'in-progress');
      inProgressMatches.forEach(match => {
        // Simulate match results based on player strength
        const getPlayerStrength = (id: string): number => {
          const statsMap = new Map([
            ['Ibraheem', 0.95],
            ['Jeremy', 0.85],
            ['1', 0.70],
            ['2', 0.60],
            ['3', 0.50],
            ['4', 0.50],
            ['5', 0.40],
            ['6', 0.40],
          ]);
          return statsMap.get(id) || 0.5;
        };

        const team1Strength = (match.team1[0] ? getPlayerStrength(match.team1[0]) : 0.5) +
                            (match.team1[1] ? getPlayerStrength(match.team1[1]) : 0.5);
        const team2Strength = (match.team2[0] ? getPlayerStrength(match.team2[0]) : 0.5) +
                            (match.team2[1] ? getPlayerStrength(match.team2[1]) : 0.5);

        const team1Score = team1Strength > team2Strength ? 11 : Math.floor(Math.random() * 8) + 3;
        const team2Score = team2Strength > team1Strength ? 11 : Math.floor(Math.random() * 8) + 3;
        
        session = completeMatch(session, match.id, Math.max(team1Score, team2Score) + 1, Math.min(team1Score, team2Score));
      });
    }

    // After 8 rounds, check that matches are reasonably balanced
    // With improved skill-based matchmaking, we should see:
    // - Strong players NOT always paired together
    // - Weak players NOT always paired together
    // - More often: strong + weak vs strong + weak (balanced matches)

    const stats = Array.from(session.playerStats.values());
    const completedMatches = session.matches.filter(m => m.status === 'completed');

    // Calculate match balance for each match
    let balancedMatchCount = 0;
    let totalMatches = 0;

    completedMatches.forEach(match => {
      totalMatches++;
      
      const getTeamStrength = (team: string[]): number => {
        const strengthMap = new Map([
          ['Ibraheem', 0.95],
          ['Jeremy', 0.85],
          ['1', 0.70],
          ['2', 0.60],
          ['3', 0.50],
          ['4', 0.50],
          ['5', 0.40],
          ['6', 0.40],
        ]);
        return team.reduce((sum, id) => sum + (strengthMap.get(id) || 0.5), 0) / team.length;
      };

      const team1Strength = getTeamStrength(match.team1);
      const team2Strength = getTeamStrength(match.team2);
      const diff = Math.abs(team1Strength - team2Strength);

      // Consider "balanced" if strength difference is < 0.2 (on a 0-1 scale)
      if (diff < 0.2) {
        balancedMatchCount++;
      }
    });

    const balanceRatio = balancedMatchCount / totalMatches;
    console.log(`\nSkill-Based Matchmaking Results:`);
    console.log(`Total matches: ${totalMatches}`);
    console.log(`Balanced matches (difference < 0.2): ${balancedMatchCount}`);
    console.log(`Balance ratio: ${(balanceRatio * 100).toFixed(1)}%`);
    console.log(`\nPlayer Statistics:`);
    stats.sort((a, b) => (b.wins / (b.gamesPlayed || 1)) - (a.wins / (a.gamesPlayed || 1)));
    stats.forEach(stat => {
      const winRate = stat.gamesPlayed > 0 ? (stat.wins / stat.gamesPlayed * 100).toFixed(1) : 'N/A';
      console.log(`  ${stat.playerId}: ${stat.wins}W-${stat.losses}L (${winRate}%)`);
    });

    // With improved skill-based matchmaking, we expect:
    // - At least 50% of matches to be reasonably balanced
    expect(balanceRatio).toBeGreaterThanOrEqual(0.5);
    
    // Win rates should be more compressed
    // Check that at most 1 player has extreme records (everyone else should have mixed results)
    const extremePlayers = stats.filter(s => s.gamesPlayed > 2 && (s.wins === 0 || s.wins === s.gamesPlayed));
    // Allow up to 1 extreme player (skill differences still matter)
    expect(extremePlayers.length).toBeLessThanOrEqual(1);
  });
});

