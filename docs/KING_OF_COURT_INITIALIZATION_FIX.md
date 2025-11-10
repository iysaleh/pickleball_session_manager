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

### 3. Waiting for "Better" Matchups While Courts Sit Empty
In `shouldWaitForRankBasedMatchups()` function:
- The function would decide to "wait" for better matchups when detecting repetition or loops
- However, it didn't consider whether there were **empty courts available**
- This caused scenarios where 5 players were waiting while only 2 of 4 courts were being used
- The system was waiting for "perfect" matchups that would never come, leaving courts idle

**Location**: `src/kingofcourt.ts` lines 350-436

### 4. New Players Locked by Rank Constraints
In `canPlayTogether()` function:
- The HARD RULE prevented crossing the half-pool boundary (top half vs bottom half)
- When new players joined mid-session, they were immediately assigned to a rank
- But with 0 games played, we have no data about their actual skill level
- This could lock them out of matchmaking if their half didn't have enough waiting players
- Example: 8 players waiting, but 5 in top half and 3 in bottom half → can't make a second match

**Location**: `src/kingofcourt.ts` lines 120-158

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

### Change 3: Smart Waiting Logic for Empty Courts
Modified the waiting logic to balance quality matchups with court utilization:

**In `shouldWaitForRankBasedMatchups()`:**
```typescript
// CRITICAL: Only wait if ALL courts are busy
// If there are empty courts, we should fill them rather than wait indefinitely
const allCourtsBusy = numBusyCourts >= totalCourts;
if (!allCourtsBusy) {
  return false; // Don't wait, try to fill empty courts
}
```

**In `selectPlayersForRankMatch()`:**
When courts are empty, use more lenient matchmaking that prioritizes court utilization:
- Skip the strict variety and close-rank requirements
- Still enforce rank-based constraints (top half vs top half, bottom vs bottom)
- Only hard constraint: no back-to-back games with the exact same 4 players
- This allows some repetition if needed to keep courts filled

**Result**: The system still waits for better matchups when all courts are busy, but will fill empty courts even if the matchup isn't perfect.

### Change 4: Allow Provisional Players to Cross Rank Boundaries
Modified `canPlayTogether()` to allow very new players to play across half-pool boundaries:

```typescript
// Allow crossing if both players are truly new (very few games)
const bothVeryNew = player1Provisional && player2Provisional;

// Players must be in the same half (unless both are very new)
if (!bothVeryNew && player1TopHalf !== player2TopHalf) {
  return false; // Cannot cross the half-pool boundary
}
```

**Rationale**: When players have played fewer than 3 games, we don't have enough data to know their true skill level. Their initial BASE_RATING of 1500 is arbitrary. Allowing two provisional players to play together (even from different halves) prevents matchmaking gridlock when new players join mid-session.

**Example**: If 5 top-half players and 3 bottom-half players (including 2 new) are waiting, the new players can now form a match together, allowing courts to fill.

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
  - Lines 760-763: Added aggressive court filling at session start (0 completed matches)
  - Lines 208-224: Pass `hasEmptyCourts` flag through matchmaking pipeline
  - Lines 358-367: Only wait for better matchups if ALL courts are busy
  - Lines 769-818: When courts are empty, use lenient matchmaking (rank-constrained but allow repetition)
  - Lines 127-141: Allow two provisional players to cross half-pool boundary

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

This fix addresses two issues:

1. **Session Start Issue** (`pickleball-session-11-04-2025-20-52.txt`): Only 2 courts were being used at the start with 14 players and 4 courts available.

2. **Mid-Session Issue** (`pickleball-session-11-04-2025-21-30.txt`): Started with 10 players, then grew to 13 active players with 4 courts, but only 2 courts were ever used throughout the session. With 5 players waiting, a 3rd court should have been consistently filled.

3. **New Player Addition Issue** (`pickleball-session-11-04-2025-21-40.txt`): 12 active players (10 original + 2 new), 4 courts available, but only 1 court in use with 8 players waiting. When new players joined mid-session, they were immediately ranked but had no game data. The half-pool ranking constraints prevented them from forming matches with available players.

The root cause was the algorithm being too conservative:
- Enforcing ranking constraints when no data existed (session start)
- Waiting for "perfect" matchups while leaving courts empty (mid-session)  
- Applying strict rank boundaries to brand-new players with 0 games (new player addition)
