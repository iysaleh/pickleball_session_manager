// Simple test to verify round-robin uniqueness
import { generateRoundRobinQueue } from './src/queue.ts';

const players = [];
for (let i = 1; i <= 8; i++) {
  players.push({ id: `player${i}`, name: `Player ${i}` });
}

const queue = generateRoundRobinQueue(players, 'doubles', []);

console.log(`Generated ${queue.length} matches`);
console.log('\nFirst 20 matches:');

const matchupsSeen = new Set();
let duplicateFound = false;

queue.slice(0, 20).forEach((match, index) => {
  const team1Str = match.team1.sort().join(',');
  const team2Str = match.team2.sort().join(',');
  const matchupKey = [team1Str, team2Str].sort().join('|');
  
  const isDuplicate = matchupsSeen.has(matchupKey);
  if (isDuplicate) {
    duplicateFound = true;
    console.log(`Match ${index + 1}: [${team1Str}] vs [${team2Str}] *** DUPLICATE ***`);
  } else {
    console.log(`Match ${index + 1}: [${team1Str}] vs [${team2Str}]`);
  }
  
  matchupsSeen.add(matchupKey);
});

if (duplicateFound) {
  console.log('\n❌ DUPLICATES FOUND!');
} else {
  console.log('\n✅ No duplicates in first 20 matches');
}

// Count unique matchups in entire queue
const allMatchups = new Set();
queue.forEach(match => {
  const team1Str = match.team1.sort().join(',');
  const team2Str = match.team2.sort().join(',');
  const matchupKey = [team1Str, team2Str].sort().join('|');
  allMatchups.add(matchupKey);
});

console.log(`\nTotal matches: ${queue.length}`);
console.log(`Unique matchups: ${allMatchups.size}`);
console.log(`Duplicates in full queue: ${queue.length - allMatchups.size}`);
