/**
 * Manual test script for the ranking-based King of the Court algorithm
 * Tests the new ELO-style ranking system and rank-based matchmaking
 */

import { createSession, evaluateAndCreateMatches, completeMatch } from './src/session.js';
import { calculatePlayerRankings } from './src/utils.js';

// Helper to create test players
function createPlayers(count) {
  const players = [];
  for (let i = 1; i <= count; i++) {
    players.push({
      id: `player-${i}`,
      name: `Player ${i}`
    });
  }
  return players;
}

// Helper to print rankings
function printRankings(session) {
  const rankings = calculatePlayerRankings(
    Array.from(session.activePlayers),
    session.playerStats
  );
  
  console.log('\n=== CURRENT RANKINGS ===');
  rankings.forEach(r => {
    const stats = session.playerStats.get(r.playerId);
    console.log(`#${r.rank} ${r.playerId}: ${stats.wins}W-${stats.losses}L (${stats.gamesPlayed} games)`);
  });
  console.log('========================\n');
}

// Helper to print active matches
function printMatches(session) {
  const activeMatches = session.matches.filter(m => 
    m.status === 'waiting' || m.status === 'in-progress'
  );
  
  if (activeMatches.length === 0) {
    console.log('No active matches scheduled.');
    return;
  }
  
  console.log('\n=== ACTIVE MATCHES ===');
  activeMatches.forEach(match => {
    const team1Names = match.team1.map(id => id).join(', ');
    const team2Names = match.team2.map(id => id).join(', ');
    console.log(`Court ${match.courtNumber}: [${team1Names}] vs [${team2Names}]`);
  });
  console.log('======================\n');
}

// Test 1: Basic ranking system with 18 players
console.log('TEST 1: 18 Players - Ranking-Based Matchmaking');
console.log('================================================\n');

const players = createPlayers(18);
const config = {
  mode: 'king-of-court',
  sessionType: 'doubles',
  players,
  courts: 4,
  bannedPairs: [],
  lockedTeams: []
};

let session = createSession(config, 100);

console.log('Initial session created with 18 players');
console.log('Starting first round...\n');

// Start first round
session = evaluateAndCreateMatches(session);
printMatches(session);

// Simulate first round of matches - make Player 1-8 winners
console.log('Completing first round - making Courts 1-2 winners (top players)...');
const firstRoundMatches = session.matches.filter(m => m.status === 'waiting');

// Complete matches - team1 wins on courts 1-2, team2 wins on courts 3-4
firstRoundMatches.slice(0, 2).forEach(match => {
  const updated = {
    ...match,
    status: 'completed',
    score: { team1Score: 11, team2Score: 5 },
    endTime: Date.now()
  };
  session.matches = session.matches.map(m => m.id === match.id ? updated : m);
  
  // Update player stats
  [...match.team1].forEach(playerId => {
    const stats = session.playerStats.get(playerId);
    stats.wins++;
    stats.totalPointsFor += 11;
    stats.totalPointsAgainst += 5;
  });
  [...match.team2].forEach(playerId => {
    const stats = session.playerStats.get(playerId);
    stats.losses++;
    stats.totalPointsFor += 5;
    stats.totalPointsAgainst += 11;
  });
});

firstRoundMatches.slice(2, 4).forEach(match => {
  const updated = {
    ...match,
    status: 'completed',
    score: { team1Score: 5, team2Score: 11 },
    endTime: Date.now()
  };
  session.matches = session.matches.map(m => m.id === match.id ? updated : m);
  
  // Update player stats
  [...match.team1].forEach(playerId => {
    const stats = session.playerStats.get(playerId);
    stats.losses++;
    stats.totalPointsFor += 5;
    stats.totalPointsAgainst += 11;
  });
  [...match.team2].forEach(playerId => {
    const stats = session.playerStats.get(playerId);
    stats.wins++;
    stats.totalPointsFor += 11;
    stats.totalPointsAgainst += 5;
  });
});

printRankings(session);

// Start second round
console.log('Starting second round...');
session = evaluateAndCreateMatches(session);
printMatches(session);

// Check if winners are playing winners
const secondRoundMatches = session.matches.filter(m => 
  m.status === 'waiting' || m.status === 'in-progress'
);

console.log('Verification: Checking if winners are playing together...');
const winnerIds = [];
const loserIds = [];

session.playerStats.forEach((stats, playerId) => {
  if (stats.wins > 0 && stats.losses === 0) {
    winnerIds.push(playerId);
  } else if (stats.losses > 0 && stats.wins === 0) {
    loserIds.push(playerId);
  }
});

console.log(`Winners (1W-0L): ${winnerIds.join(', ')}`);
console.log(`Losers (0W-1L): ${loserIds.join(', ')}\n`);

// Check if any match has all winners vs all losers (should not happen)
let hasInvalidMatch = false;
secondRoundMatches.forEach(match => {
  const team1IsAllWinners = match.team1.every(id => winnerIds.includes(id));
  const team2IsAllLosers = match.team2.every(id => loserIds.includes(id));
  const team1IsAllLosers = match.team1.every(id => loserIds.includes(id));
  const team2IsAllWinners = match.team2.every(id => winnerIds.includes(id));
  
  if ((team1IsAllWinners && team2IsAllLosers) || (team1IsAllLosers && team2IsAllWinners)) {
    console.log(`❌ INVALID: Court ${match.courtNumber} has all winners vs all losers!`);
    hasInvalidMatch = true;
  }
});

if (!hasInvalidMatch) {
  console.log('✅ VALID: No matches with all winners vs all losers (rank-based matching works!)');
}

console.log('\n================================================');
console.log('Test completed. Check above for ranking-based matchmaking behavior.');
