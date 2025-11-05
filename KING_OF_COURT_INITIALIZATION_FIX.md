# King of Court Initialization Fix

## Problem Description

When starting a King of Court session with 14 players and 4 courts (doubles), only 2 courts were being utilized initially, with 8 players playing and 6 players waiting. This is inefficient since there are clearly enough players to fill at least 3 courts (12 players with only 2 waiting).

### Example Scenario
- **Configuration**: 14 players, 4 courts, doubles mode
- **Expected**: 3-4 courts active (12-16 players playing)
- **Actual (before fix)**: Only 2 courts active (8 players playing, 6 waiting)

## Root Causes

### 1. Loop Breaking Instead of Continuing
In `generateRankingBasedMatches()` function:
- When `selectPlayersForRankMatch()` failed to find players for a court, the function would **BREAK** the entire loop
- When `assignTeams()` failed to create valid team assignments, the function would **BREAK** the entire loop
- This meant if court 3 failed to find players, court 4 would never even be attempted

**Location**: `src/kingofcourt.ts` lines 697-698, 710-711

### 2. Overly Strict Ranking at Session Start
In `selectPlayersForRankMatch()` function:
- At session start (0 completed matches), there is no ranking data yet
- However, the code was still trying to enforce strict rank-based matchmaking constraints
- This could cause the algorithm to fail to find "valid" player groups even though any grouping would be fine

**Location**: `src/kingofcourt.ts` lines 734-756

## Solution

### Change 1: Continue Instead of Break
Changed the court loop to **CONTINUE** to the next court when player selection or team assignment fails, instead of breaking out of the loop entirely.

```typescript
// Before:
if (!selectedPlayers || selectedPlayers.length < playersPerMatch) {
  break;  // ❌ Stops trying other courts
}

// After:
if (!selectedPlayers || selectedPlayers.length < playersPerMatch) {
  continue;  // ✅ Tries next court
}
```

### Change 2: Aggressive Court Filling at Session Start
Added a special case at the beginning of `selectPlayersForRankMatch()` to be very aggressive about filling courts when the session has just started:

```typescript
// CRITICAL: At session start (no completed matches), be very aggressive about filling courts
// Rankings don't exist yet, so just take first available players
const completedMatches = matches.filter(m => m.status === 'completed');
if (completedMatches.length === 0) {
  // Simply take the first playersPerMatch available players
  return availableRankings.slice(0, playersPerMatch).map(r => r.playerId);
}
```

This bypasses all ranking logic when starting a session, since rankings are meaningless without match history.

## Expected Behavior After Fix

| Players | Courts | Expected Matches | Expected Waiting |
|---------|--------|------------------|------------------|
| 8       | 4      | 2 courts         | 0 players        |
| 14      | 4      | 3+ courts        | ≤2 players       |
| 16      | 4      | 4 courts         | 0 players        |
| 20      | 4      | 4 courts         | 4 players        |

## Files Modified

- `src/kingofcourt.ts`
  - Line 698: Changed `break` to `continue` for player selection failure
  - Line 711: Changed `break` to `continue` for team assignment failure  
  - Lines 745-751: Added aggressive court filling at session start

## Testing

### Manual Test Steps
1. Open the Pickleball Sessions app
2. Add 14 players (named Player 1 through Player 14)
3. Set number of courts to 4
4. Select "King of the Court" mode
5. Select "Doubles" session type
6. Click "Start Session"

### Expected Results
- At least 3 courts should have active matches
- Approximately 12 players should be playing
- Approximately 2 players should be waiting
- Courts should be numbered 1, 2, 3 (and possibly 4)

### Automated Test
A test file has been created at `src/test-14-players.test.ts` that verifies:
- 14 players with 4 courts fills at least 3 courts
- 16 players with 4 courts fills all 4 courts
- 8 players with 4 courts fills 2 courts

## Impact

This fix ensures that King of Court mode utilizes available courts efficiently from the very start of a session, maximizing player engagement and minimizing wait times. The ranking-based matchmaking constraints are still respected after matches have been completed and rankings are established.

## Related Issues

This fix addresses the issue reported in the session export file `pickleball-session-11-04-2025-20-52.txt` where only 2 courts were being used with 14 players.
