import { describe, it, expect } from 'vitest';
import { createSession, completeMatch, startMatch } from './session';
import type { Player, SessionConfig } from './types';
import { generateKingOfCourtRound } from './kingofcourt';

/**
 * CRITICAL TEST: Prevent rank #1 from playing rank #15+
 * 
 * This test replicates the bug found on 2025-11-03 where Ibraheem (rank #1, 100% win rate)
 * was matched against Leslie (rank #15, 0% win rate) in King of the Court mode.
 * 
 * The bug was caused by provisional players (< 3 games) being allowed to play with ANYONE,
 * completely ignoring the half-pool rank constraints.
 */
describe('King of Court - Critical Ranking Bug Prevention', () => {
  
  it('should NEVER match top-ranked player with bottom-ranked player', () => {
    // Create 18 players
    const players: Player[] = Array.from({ length: 18 }, (_, i) => ({
      id: `player${i + 1}`,
      name: `Player ${i + 1}`,
    }));
    
    // Special players
    const ibraheem = players[0]; // Will become rank #1
    const leslie = players[17];   // Will become rank #15+
    ibraheem.name = 'Ibraheem';
    leslie.name = 'Leslie';
    
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 4,
      bannedPairs: [],
    };
    
    let session = createSession(config, 100);
    
    // Simulate the scenario from the bug report:
    // 1. Ibraheem wins 2 games (becomes rank #1)
    // 2. Leslie loses 1 game (becomes rank #15)
    // 3. Most players have 0 games (provisional)
    
    // Match 1: Ibraheem + player2 vs player3 + player4
    let matches = generateKingOfCourtRound(session);
    expect(matches.length).toBeGreaterThan(0);
    
    let match1 = matches.find(m => 
      m.team1.includes(ibraheem.id) || m.team2.includes(ibraheem.id)
    );
    expect(match1).toBeDefined();
    
    // Start and complete match 1 - Ibraheem wins
    session = startMatch(session, match1!.id);
    session = completeMatch(session, match1!.id, 11, 5);
    
    // Match 2: Leslie + player15 vs player13 + player14 (Leslie loses)
    matches = generateKingOfCourtRound(session);
    let leslieMatch = matches.find(m => 
      m.team1.includes(leslie.id) || m.team2.includes(leslie.id)
    );
    
    if (leslieMatch) {
      session = startMatch(session, leslieMatch.id);
      // Make Leslie lose
      const leslieOnTeam1 = leslieMatch.team1.includes(leslie.id);
      session = completeMatch(session, leslieMatch.id, leslieOnTeam1 ? 7 : 11, leslieOnTeam1 ? 11 : 7);
    }
    
    // Match 3: Ibraheem + another player vs two others (Ibraheem wins again)
    matches = generateKingOfCourtRound(session);
    match1 = matches.find(m => 
      m.team1.includes(ibraheem.id) || m.team2.includes(ibraheem.id)
    );
    
    if (match1) {
      session = startMatch(session, match1.id);
      const ibraheemOnTeam1 = match1.team1.includes(ibraheem.id);
      session = completeMatch(session, match1.id, ibraheemOnTeam1 ? 11 : 2, ibraheemOnTeam1 ? 2 : 11);
    }
    
    // Now check rankings
    const ibraheemStats = session.playerStats.get(ibraheem.id)!;
    const leslieStats = session.playerStats.get(leslie.id)!;
    
    // Ibraheem should have 2 wins, 0 losses
    expect(ibraheemStats.wins).toBeGreaterThanOrEqual(2);
    expect(ibraheemStats.losses).toBe(0);
    
    // Leslie should have losses
    expect(leslieStats.losses).toBeGreaterThanOrEqual(1);
    
    // CRITICAL TEST: Generate next matches and ensure Ibraheem never plays Leslie
    for (let i = 0; i < 10; i++) {
      const newMatches = generateKingOfCourtRound(session);
      
      newMatches.forEach(match => {
        const hasIbraheem = match.team1.includes(ibraheem.id) || match.team2.includes(ibraheem.id);
        const hasLeslie = match.team1.includes(leslie.id) || match.team2.includes(leslie.id);
        
        // CRITICAL ASSERTION: Ibraheem and Leslie should NEVER be in the same match
        if (hasIbraheem && hasLeslie) {
          const allPlayers = [...match.team1, ...match.team2].map(id => 
            session.config.players.find(p => p.id === id)?.name || id
          );
          
          throw new Error(
            `CRITICAL BUG: Top-ranked player Ibraheem (${ibraheemStats.wins}-${ibraheemStats.losses}) ` +
            `was matched with bottom-ranked player Leslie (${leslieStats.wins}-${leslieStats.losses})! ` +
            `Match players: ${allPlayers.join(', ')}`
          );
        }
      });
      
      // Complete some matches to continue
      if (newMatches.length > 0) {
        newMatches.forEach(m => {
          session = startMatch(session, m.id);
          session = completeMatch(session, m.id, 11, 9);
        });
      }
    }
  });
  
  it('should enforce half-pool boundaries for all players', () => {
    // Create 18 players
    const players: Player[] = Array.from({ length: 18 }, (_, i) => ({
      id: `player${i + 1}`,
      name: `Player ${i + 1}`,
    }));
    
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 4,
      bannedPairs: [],
    };
    
    let session = createSession(config, 100);
    
    // Play several rounds
    for (let round = 0; round < 5; round++) {
      const matches = generateKingOfCourtRound(session);
      
      matches.forEach(match => {
        const allPlayerIds = [...match.team1, ...match.team2];
        
        // Get all player stats to determine their effective ranks
        const playerRatings = allPlayerIds.map(id => {
          const stats = session.playerStats.get(id)!;
          const winRate = stats.gamesPlayed > 0 ? stats.wins / stats.gamesPlayed : 0.5;
          return { id, winRate, gamesPlayed: stats.gamesPlayed };
        });
        
        // Sort by win rate to approximate ranking
        playerRatings.sort((a, b) => b.winRate - a.winRate);
        
        // Check if we have a clear top performer and clear bottom performer
        const hasTopPerformer = playerRatings.some(p => p.gamesPlayed >= 3 && p.winRate >= 0.8);
        const hasBottomPerformer = playerRatings.some(p => p.gamesPlayed >= 3 && p.winRate <= 0.2);
        
        if (hasTopPerformer && hasBottomPerformer) {
          // This should never happen - throw descriptive error
          const topPlayer = playerRatings.find(p => p.gamesPlayed >= 3 && p.winRate >= 0.8)!;
          const bottomPlayer = playerRatings.find(p => p.gamesPlayed >= 3 && p.winRate <= 0.2)!;
          
          const topName = session.config.players.find(p => p.id === topPlayer.id)?.name;
          const bottomName = session.config.players.find(p => p.id === bottomPlayer.id)?.name;
          
          throw new Error(
            `Half-pool boundary violated: Top performer ${topName} (${(topPlayer.winRate * 100).toFixed(0)}% win rate) ` +
            `matched with bottom performer ${bottomName} (${(bottomPlayer.winRate * 100).toFixed(0)}% win rate)`
          );
        }
        
        // Start and complete match
        session = startMatch(session, match.id);
        // Random score
        session = completeMatch(session, match.id, Math.random() > 0.5 ? 11 : 9, Math.random() > 0.5 ? 11 : 9);
      });
    }
  });
  
  it('should respect rank constraints even with provisional players', () => {
    // Create 12 players for simpler math (halfPool = 6)
    const players: Player[] = Array.from({ length: 12 }, (_, i) => ({
      id: `player${i + 1}`,
      name: `Player ${i + 1}`,
    }));
    
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 3,
      bannedPairs: [],
    };
    
    let session = createSession(config, 100);
    
    // Create a scenario with clear top/bottom players
    // Player 1: High performer (will be rank 1-3)
    // Player 12: Low performer (will be rank 10-12)
    
    const topPlayer = players[0];
    const bottomPlayer = players[11];
    
    // Simulate games to establish rankings
    for (let i = 0; i < 3; i++) {
      const matches = generateKingOfCourtRound(session);
      
      matches.forEach(match => {
        session = startMatch(session, match.id);
        
        // If top player is in match, they win
        const hasTopPlayer = match.team1.includes(topPlayer.id) || match.team2.includes(topPlayer.id);
        const topOnTeam1 = match.team1.includes(topPlayer.id);
        
        // If bottom player is in match, they lose
        const hasBottomPlayer = match.team1.includes(bottomPlayer.id) || match.team2.includes(bottomPlayer.id);
        const bottomOnTeam1 = match.team1.includes(bottomPlayer.id);
        
        let score1: number, score2: number;
        
        if (hasTopPlayer && !hasBottomPlayer) {
          // Top player wins
          score1 = topOnTeam1 ? 11 : 5;
          score2 = topOnTeam1 ? 5 : 11;
        } else if (hasBottomPlayer && !hasTopPlayer) {
          // Bottom player loses
          score1 = bottomOnTeam1 ? 5 : 11;
          score2 = bottomOnTeam1 ? 11 : 5;
        } else if (hasTopPlayer && hasBottomPlayer) {
          // They should never be in the same match!
          throw new Error('Top and bottom players should never be matched together!');
        } else {
          // Random outcome
          score1 = 11;
          score2 = 9;
        }
        
        session = completeMatch(session, match.id, score1, score2);
      });
    }
    
    // Verify top and bottom players have divergent records
    const topStats = session.playerStats.get(topPlayer.id)!;
    const bottomStats = session.playerStats.get(bottomPlayer.id)!;
    
    expect(topStats.wins).toBeGreaterThan(bottomStats.wins);
  });
});
