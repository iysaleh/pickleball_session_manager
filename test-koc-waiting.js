// Test the King of Court waiting logic
import { createSession, startNextRound, completeMatch } from './src/session.js';

const config = {
  mode: 'king-of-court',
  sessionType: 'singles',
  players: [
    { id: 'p1', name: 'Player 1' },
    { id: 'p2', name: 'Player 2' },
    { id: 'p3', name: 'Player 3' },
    { id: 'p4', name: 'Player 4' },
    { id: 'p5', name: 'Player 5' },
    { id: 'p6', name: 'Player 6' },
    { id: 'p7', name: 'Player 7' },
    { id: 'p8', name: 'Player 8' },
  ],
  courts: 4,
  bannedPairs: [],
};

let session = createSession(config);

// Start initial round
session = startNextRound(session);
console.log('\n=== Round 1 Started ===');
session.matches.filter(m => m.status === 'waiting').forEach(m => {
  console.log(`Court ${m.courtNumber}: ${m.team1[0]} vs ${m.team2[0]}`);
});

// Finish only court 1, repeat 10 times
for (let i = 0; i < 10; i++) {
  const court1Match = session.matches.find(m => m.courtNumber === 1 && m.status !== 'completed');
  if (court1Match) {
    session = completeMatch(session, court1Match.id, 11, 9);
    console.log(`\n=== Court 1 finished (iteration ${i + 1}) ===`);
    
    // Try to start next round
    session = startNextRound(session);
    
    const newMatches = session.matches.filter(m => 
      m.courtNumber === 1 && m.status === 'waiting'
    );
    
    if (newMatches.length > 0) {
      console.log(`NEW MATCH on Court 1: ${newMatches[0].team1[0]} vs ${newMatches[0].team2[0]}`);
    } else {
      console.log('NO NEW MATCH scheduled on Court 1 (WAITING for variety)');
    }
    
    // Show who's waiting
    const inMatch = new Set();
    session.matches.filter(m => m.status !== 'completed').forEach(m => {
      m.team1.forEach(p => inMatch.add(p));
      m.team2.forEach(p => inMatch.add(p));
    });
    const waiting = config.players.filter(p => !inMatch.has(p.id));
    console.log(`Waiting players: ${waiting.map(p => p.id).join(', ')}`);
  }
}

// Show final matchup counts
console.log('\n=== Matchup Frequency ===');
const matchups = new Map();
session.matches.filter(m => m.status === 'completed').forEach(m => {
  const p1 = m.team1[0];
  const p2 = m.team2[0];
  const key = [p1, p2].sort().join('-');
  matchups.set(key, (matchups.get(key) || 0) + 1);
});

for (const [pair, count] of matchups.entries()) {
  console.log(`${pair}: ${count} times`);
}
