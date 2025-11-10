const { createSession, evaluateAndCreateMatches, startMatch, completeMatch } = require('./dist/session.js');

const config = {
  mode: 'king-of-court',
  sessionType: 'doubles',
  players: [
    { id: '1', name: 'Player 1' },
    { id: '2', name: 'Player 2' },
    { id: '3', name: 'Player 3' },
    { id: '4', name: 'Player 4' },
    { id: '5', name: 'Player 5' },
    { id: '6', name: 'Player 6' },
    { id: '7', name: 'Player 7' },
    { id: '8', name: 'Player 8' },
  ],
  courts: 1,
  bannedPairs: [],
};

let session = createSession(config);
session = evaluateAndCreateMatches(session);

console.log('=== After initial evaluation ===');
console.log('Match 1:', session.matches[0].team1, 'vs', session.matches[0].team2);

// Complete 2 matches
for (let i = 0; i < 2; i++) {
  const match = session.matches.find(m => m.status === 'waiting');
  session = startMatch(session, match.id);
  session = completeMatch(session, match.id, 11, 5);
  console.log(`\nAfter Match ${i+1} completes:`);
  for (const [id, stats] of session.playerStats.entries()) {
    console.log(`  ${id}: games=${stats.gamesPlayed}, waits=${stats.gamesWaited}`);
  }
}

console.log('\n=== After 2 matches ===');
const playerWaits = Array.from(session.playerStats.entries())
  .map(([playerId, stats]) => ({ playerId, waits: stats.gamesWaited }))
  .sort((a, b) => b.waits - a.waits);

console.log('Players by wait count:');
playerWaits.forEach(p => console.log(`  ${p.playerId}: ${p.waits} waits`));

const maxWaits = playerWaits[0].waits;
const topWaiters = playerWaits
  .filter(p => p.waits >= maxWaits - 1)
  .map(p => p.playerId);

console.log(`\nTop waiters (waits >= ${maxWaits - 1}): `, topWaiters);

const newMatch = session.matches.find(m => m.status === 'waiting');
if (newMatch) {
  const matchPlayers = [...newMatch.team1, ...newMatch.team2];
  console.log('New match players:', matchPlayers);
  console.log('All from top waiters?', matchPlayers.every(id => topWaiters.includes(id)));
}
