# Player Rankings Feature

## Overview
Added a comprehensive player rankings system that ranks all players from best to worst based on their performance during a session.

## Ranking Algorithm

### Primary Ranking Criterion: Total Wins
Players are ranked primarily by the total number of wins. The player with the most wins ranks highest.

### Tiebreaker: Average Point Differential
When two or more players have the same number of wins, the tiebreaker is the **average point differential** across all games played.

**Average Point Differential Calculation:**
```
avgPointDifferential = (totalPointsFor - totalPointsAgainst) / gamesPlayed
```

- `totalPointsFor`: Sum of all points the player scored across all games
- `totalPointsAgainst`: Sum of all points scored against the player across all games
- `gamesPlayed`: Total number of games the player participated in

### Tie Handling
If two players have identical wins AND identical average point differentials, they receive the same rank.

## Implementation Details

### New Data Tracked
Extended the `PlayerStats` type to track:
- `totalPointsFor`: Total points scored by the player
- `totalPointsAgainst`: Total points allowed by the player

### Functions Added

#### `calculatePlayerRankings(playerIds, statsMap)`
**Location:** `src/utils.ts`

Calculates and returns an array of player rankings sorted by:
1. Wins (descending)
2. Average point differential (descending)

**Returns:**
```typescript
Array<{
  playerId: string;
  rank: number;
  wins: number;
  losses: number;
  avgPointDifferential: number;
}>
```

### UI Components

#### Rankings Button
A "Show Rankings" button in the session controls that toggles the rankings display.

#### Rankings Display
- Shows all players ranked from best to worst
- Visual indicators for top 3 positions (🥇🥈🥉)
- Displays:
  - Player rank
  - Player name
  - Total wins
  - Total losses
  - Average point differential (color-coded: green for positive, red for negative)

### Auto-Update Behavior
Rankings automatically update when:
- A match is completed
- A match score is edited in history
- The rankings section is visible

## Testing

### Test Suite: `rankings.test.ts`
Comprehensive test coverage including:
- ✅ Ranking players by wins in descending order
- ✅ Using average point differential as tiebreaker
- ✅ Handling ties correctly (same rank for identical stats)
- ✅ Handling players with no games played
- ✅ Handling negative point differential
- ✅ Edge cases (empty list, single player)
- ✅ Complex multi-tier scenarios

All 8 test cases pass successfully.

## Usage

1. Start a session and play some games
2. Click the "Show Rankings" button in the session controls
3. View the current rankings based on all completed games
4. Rankings update automatically as you complete more games or edit scores

## Example Ranking Scenarios

### Scenario 1: Clear Winner
- Player A: 10 wins, 0 losses, +60 avg point diff → Rank 1 🥇
- Player B: 7 wins, 3 losses, +20 avg point diff → Rank 2 🥈
- Player C: 5 wins, 5 losses, 0 avg point diff → Rank 3 🥉

### Scenario 2: Tiebreaker Applied
- Player A: 5 wins, +8.5 avg point diff → Rank 1 🥇
- Player B: 5 wins, +6.2 avg point diff → Rank 2 🥈
- Player C: 5 wins, +3.1 avg point diff → Rank 3 🥉

### Scenario 3: Exact Tie
- Player A: 5 wins, +5.0 avg point diff → Rank 1 🥇
- Player B: 5 wins, +5.0 avg point diff → Rank 1 🥇 (tied)
- Player C: 3 wins, +2.0 avg point diff → Rank 3 🥉

## Future Enhancements
Potential improvements for future versions:
- Export rankings to CSV/PDF
- Historical ranking tracking across multiple sessions
- Elo-style rating system
- Head-to-head win percentage statistics
