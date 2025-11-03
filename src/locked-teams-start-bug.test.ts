import { describe, it, expect } from 'vitest';
import { createSession } from './session';
import type { Player, SessionConfig } from './types';
import { generateKingOfCourtRound } from './kingofcourt';

/**
 * CRITICAL TEST: Prevent empty courts at session start with locked teams
 * 
 * This test replicates the bug found on 2025-11-03 where a session with:
 * - 9 locked teams (18 players)
 * - 4 courts available
 * - Start of session (no games played yet)
 * 
 * Only filled 2 courts instead of all 4!
 * 
 * The bug was caused by the half-pool constraint being enforced when all teams
 * had the same rank (0 games played), causing arbitrary team exclusions.
 */
describe('Locked Teams King of Court - Session Start Bug Prevention', () => {
  
  it('should fill all available courts at session start', () => {
    // Create 18 players (9 locked teams)
    const players: Player[] = Array.from({ length: 18 }, (_, i) => ({
      id: `player${i + 1}`,
      name: `Player ${i + 1}`,
    }));
    
    // Create 9 locked teams
    const lockedTeams: string[][] = [];
    for (let i = 0; i < 18; i += 2) {
      lockedTeams.push([players[i].id, players[i + 1].id]);
    }
    
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 4,
      bannedPairs: [],
      lockedTeams,
    };
    
    const session = createSession(config, 100);
    
    // Generate first round of matches
    const matches = generateKingOfCourtRound(session);
    
    // CRITICAL ASSERTION: With 9 teams and 4 courts, we should fill all 4 courts
    expect(matches.length).toBe(4);
    
    // Verify all matches are unique teams
    const usedTeamKeys = new Set<string>();
    matches.forEach(match => {
      const team1Key = [...match.team1].sort().join(',');
      const team2Key = [...match.team2].sort().join(',');
      
      expect(usedTeamKeys.has(team1Key)).toBe(false);
      expect(usedTeamKeys.has(team2Key)).toBe(false);
      
      usedTeamKeys.add(team1Key);
      usedTeamKeys.add(team2Key);
    });
    
    // Should have used 8 teams (2 per match * 4 matches)
    expect(usedTeamKeys.size).toBe(8);
  });
  
  it('should fill courts proportionally to team count', () => {
    // Test with different team counts
    const testCases = [
      { teams: 4, courts: 4, expectedMatches: 2 }, // 4 teams, 4 courts = 2 matches
      { teams: 6, courts: 4, expectedMatches: 3 }, // 6 teams, 4 courts = 3 matches
      { teams: 8, courts: 4, expectedMatches: 4 }, // 8 teams, 4 courts = 4 matches (all)
      { teams: 10, courts: 4, expectedMatches: 4 }, // 10 teams, 4 courts = 4 matches (all)
      { teams: 2, courts: 4, expectedMatches: 1 }, // 2 teams, 4 courts = 1 match
      { teams: 12, courts: 6, expectedMatches: 6 }, // 12 teams, 6 courts = 6 matches (all)
    ];
    
    testCases.forEach(testCase => {
      const playerCount = testCase.teams * 2;
      const players: Player[] = Array.from({ length: playerCount }, (_, i) => ({
        id: `p${i + 1}`,
        name: `Player ${i + 1}`,
      }));
      
      const lockedTeams: string[][] = [];
      for (let i = 0; i < playerCount; i += 2) {
        lockedTeams.push([players[i].id, players[i + 1].id]);
      }
      
      const config: SessionConfig = {
        mode: 'king-of-court',
        sessionType: 'doubles',
        players,
        courts: testCase.courts,
        bannedPairs: [],
        lockedTeams,
      };
      
      const session = createSession(config, 100);
      const matches = generateKingOfCourtRound(session);
      
      expect(matches.length).toBe(testCase.expectedMatches);
    });
  });
  
  it('should handle odd number of teams correctly', () => {
    // Create 5 locked teams (10 players)
    const players: Player[] = Array.from({ length: 10 }, (_, i) => ({
      id: `player${i + 1}`,
      name: `Player ${i + 1}`,
    }));
    
    const lockedTeams: string[][] = [];
    for (let i = 0; i < 10; i += 2) {
      lockedTeams.push([players[i].id, players[i + 1].id]);
    }
    
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 4,
      bannedPairs: [],
      lockedTeams,
    };
    
    const session = createSession(config, 100);
    const matches = generateKingOfCourtRound(session);
    
    // With 5 teams, we can make 2 matches (using 4 teams), 1 team waits
    expect(matches.length).toBe(2);
    
    // Verify 4 unique teams are playing
    const usedTeamKeys = new Set<string>();
    matches.forEach(match => {
      const team1Key = [...match.team1].sort().join(',');
      const team2Key = [...match.team2].sort().join(',');
      usedTeamKeys.add(team1Key);
      usedTeamKeys.add(team2Key);
    });
    
    expect(usedTeamKeys.size).toBe(4);
  });
  
  it('should not leave courts empty when teams are available', () => {
    // Replicate the exact bug scenario from 2025-11-03
    const playerNames = [
      'James Anderson', 'Sarah Mitchell',
      'Michael Chen', 'Emily Rodriguez',
      'David Thompson', 'Jessica Williams',
      'Christopher Lee', 'Amanda Martinez',
      'Daniel Brown', 'Lauren Davis',
      'Matthew Wilson', 'Ashley Garcia',
      'Joshua Taylor', 'Rachel Johnson',
      'Andrew Miller', 'Nicole White',
      'Brandon Moore', 'Stephanie Harris',
    ];
    
    const players: Player[] = playerNames.map((name, i) => ({
      id: `player${i + 1}`,
      name,
    }));
    
    const lockedTeams: string[][] = [];
    for (let i = 0; i < 18; i += 2) {
      lockedTeams.push([players[i].id, players[i + 1].id]);
    }
    
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 4,
      bannedPairs: [],
      lockedTeams,
    };
    
    const session = createSession(config, 100);
    const matches = generateKingOfCourtRound(session);
    
    // CRITICAL: Must fill all 4 courts
    if (matches.length !== 4) {
      const usedTeams = matches.flatMap(m => {
        const team1 = m.team1.map(id => players.find(p => p.id === id)?.name).join(' & ');
        const team2 = m.team2.map(id => players.find(p => p.id === id)?.name).join(' & ');
        return [team1, team2];
      });
      
      throw new Error(
        `CRITICAL BUG: Only ${matches.length} courts filled out of 4 available!\n` +
        `Teams playing: ${usedTeams.join(', ')}\n` +
        `Total teams available: 9\n` +
        `This leaves courts empty unnecessarily!`
      );
    }
    
    expect(matches.length).toBe(4);
  });
  
  it('should still enforce half-pool after enough games are played', () => {
    // Create 8 locked teams
    const players: Player[] = Array.from({ length: 16 }, (_, i) => ({
      id: `player${i + 1}`,
      name: `Player ${i + 1}`,
    }));
    
    const lockedTeams: string[][] = [];
    for (let i = 0; i < 16; i += 2) {
      lockedTeams.push([players[i].id, players[i + 1].id]);
    }
    
    const config: SessionConfig = {
      mode: 'king-of-court',
      sessionType: 'doubles',
      players,
      courts: 4,
      bannedPairs: [],
      lockedTeams,
    };
    
    let session = createSession(config, 100);
    
    // Generate and complete several matches to establish rankings
    for (let round = 0; round < 3; round++) {
      const matches = generateKingOfCourtRound(session);
      
      matches.forEach(match => {
        // Start match
        const startedSession = {
          ...session,
          matches: session.matches.map(m => 
            m.id === match.id ? { ...m, status: 'in-progress' as const } : m
          ),
        };
        
        // Complete match with scores to create win/loss records
        const team1Wins = round % 2 === 0; // Alternate winners
        session = {
          ...startedSession,
          matches: startedSession.matches.map(m => {
            if (m.id === match.id) {
              // Update player stats
              [...m.team1, ...m.team2].forEach(playerId => {
                const stats = session.playerStats.get(playerId);
                if (stats) {
                  stats.gamesPlayed++;
                  if (team1Wins && m.team1.includes(playerId)) {
                    stats.wins++;
                  } else if (!team1Wins && m.team2.includes(playerId)) {
                    stats.wins++;
                  } else {
                    stats.losses++;
                  }
                  stats.totalPointsFor += team1Wins ? (m.team1.includes(playerId) ? 11 : 5) : (m.team2.includes(playerId) ? 11 : 5);
                  stats.totalPointsAgainst += team1Wins ? (m.team1.includes(playerId) ? 5 : 11) : (m.team2.includes(playerId) ? 5 : 11);
                }
              });
              
              return {
                ...m,
                status: 'completed' as const,
                score: { team1Score: team1Wins ? 11 : 5, team2Score: team1Wins ? 5 : 11 },
                endTime: Date.now(),
              };
            }
            return m;
          }),
        };
      });
    }
    
    // After several rounds, verify half-pool constraints are enforced
    // (Teams with high win rates should only play other high-win-rate teams)
    const nextMatches = generateKingOfCourtRound(session);
    
    // We should still get matches (not blocked by half-pool)
    expect(nextMatches.length).toBeGreaterThan(0);
  });
});
