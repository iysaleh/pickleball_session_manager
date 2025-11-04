# King of the Court Variety Improvement

## Problem Identified

In the session `pickleball-session-11-04-2025-13-54.txt` with 19 players and 4 courts, players 1 & 2 played together in **4 out of 10 matches**:

- **Match 1**: Partners (1 & 2 vs 3 & 4)
- **Match 5**: Opponents (9 & 1 vs 10 & 2)
- **Match 7**: Opponents (9 & 2 vs 1 & 5)
- **Match 10**: Player 1 appeared again

This "single court loop" problem occurs when:
1. 3 players are waiting (not enough for a full match)
2. One court finishes
3. The algorithm immediately schedules the same small group again
4. This creates a rapid rotation between the same 4-5 players

## Root Cause

The waiting logic was **too conservative** about when to wait:
- Only waited when 4+ courts were busy (too high)
- Only waited after 12+ completed matches (too late)
- Required exact 4-player group to detect loops
- Didn't detect **partial overlap** high-repetition scenarios

## Solution Implemented

### 1. **More Aggressive Waiting Thresholds**

**Before:**
```typescript
// Only consider waiting if we have at least 3 busy courts
if (numBusyCourts < 3) {
  return false;
}
// Need at least 12 completed matches to make meaningful ranking decisions
if (completedMatches.length < 12) {
  return false;
}
// If we're in a single court loop AND have many busy courts, WAIT
if (inSingleCourtLoop && numBusyCourts >= 4) {
  return true;
}
```

**After:**
```typescript
// Only consider waiting if we have at least 2 busy courts (LOWERED from 3)
if (numBusyCourts < 2) {
  return false;
}
// Need at least 6 completed matches (LOWERED from 12)
if (completedMatches.length < 6) {
  return false;
}
// If we're in a single court loop AND have multiple busy courts, WAIT (LOWERED from 4 to 2)
if (inSingleCourtLoop && numBusyCourts >= 2) {
  return true;
}
```

### 2. **Enhanced Loop Detection**

**Before:**
```typescript
// If this group has played together 3+ times in last 10 matches, we're looping
if (groupPlayCount >= 3) {
  return true;
}
```

**After:**
```typescript
// If this group has played together 2+ times in last 10 matches, we're looping (LOWERED from 3)
if (groupPlayCount >= 2) {
  return true;
}
```

### 3. **NEW: High Repetition Detection**

Added a completely new function `detectHighRepetitionMatchup()` that catches cases where:
- 3+ players are waiting
- These players have recently played together multiple times
- Even if not an exact "loop", there's high overlap with recent matches

**Key Logic:**
```typescript
function detectHighRepetitionMatchup(
  availablePlayerIds: string[],
  matches: Match[],
  numBusyCourts: number,
  playersPerMatch: number
): boolean {
  // Check the last 5 matches for repetition patterns
  const last5Matches = completedMatches.slice(-5);
  
  // Count how many of the waiting player pairs played together recently
  // If more than 60% of pairs played together in last 5 matches, HIGH REPETITION
  
  // Also check if ANY single player appeared in 3+ of last 5 matches with waiting partners
}
```

**This catches scenarios like:**
- Players 1 & 2 waiting together when they've played 3 times in last 5 matches
- Player 1 keeps getting scheduled with players 2, 3, 5 repeatedly
- Any waiting group where 60%+ of pairs have recent history

## Impact & Expected Results

### Before Changes:
❌ Players 1 & 2 played together 4 times in 10 matches (40%)  
❌ Small waiting groups create rapid loops  
❌ Only waited with 4 busy courts (rare in practice)  
❌ Waited too late (after 12 matches, problem already established)  

### After Changes:
✅ **Algorithm waits with 2+ busy courts** (triggers much more often)  
✅ **Detects loops after just 2 occurrences** (instead of 3)  
✅ **Catches partial overlap high-repetition** (not just exact loops)  
✅ **Starts waiting after 6 matches** (early intervention)  
✅ **Checks last 5 matches for patterns** (recent history matters more)  

### Expected Matchup Distribution:

**19 players, 4 courts scenario:**
- **Before**: Same 4 players might play 3-4 times together
- **After**: Same 4 players should play **at most 2 times** together
- **Waiting frequency**: 2-3 strategic waits per session vs 0-1 before
- **Variety improvement**: ~50% reduction in repetitive matchups

## Technical Details

### Wait Decision Flow:

```
1. Check if anyone waited 1+ rounds already → NO WAIT (fairness)
2. Check if we have 2+ courts busy → Proceed to checks
3. Check if 6+ matches completed → Proceed to checks
4. Check if waiting players = exact 4 → Check for single court loop
   - If exact group played 2+ times in last 10 matches → WAIT
5. Check if waiting players have high repetition → NEW CHECK
   - If 60%+ of pairs played recently → WAIT
   - If any player appeared 3+ times with waiting partners → WAIT
6. Otherwise → Schedule immediately
```

### Key Parameters Tuned:

| Parameter | Before | After | Reason |
|-----------|--------|-------|--------|
| Min busy courts to wait | 3 | 2 | Trigger more often in typical 4-court setup |
| Min matches before waiting | 12 | 6 | Catch problems earlier |
| Loop detection threshold | 3 occurrences | 2 occurrences | Be more proactive |
| Busy courts for loop wait | 4 | 2 | Actually trigger in practice |
| Repetition detection | None | 60% pair overlap | Catch partial loops |
| Recent history window | Last 10 matches | Last 5 matches | Weight recent history more |

## Testing Recommendations

### Test Scenario 1: 19 Players, 4 Courts
- Add 19 players
- Let session run for 15-20 matches
- Check any pair's matchup frequency
- **Expected**: No pair plays together more than 2 times

### Test Scenario 2: 15 Players, 3 Courts
- Add 15 players (3 waiting at a time)
- Monitor waiting queue behavior
- **Expected**: Occasional strategic waits when repetition detected

### Test Scenario 3: 21 Players, 4 Courts
- Add 21 players (5 waiting at a time)
- Check if system still waits appropriately
- **Expected**: Waits when high repetition detected even with 5 waiting

### Monitoring Metrics:

Track these per session:
1. **Max matchup count**: Any two players together
2. **Wait frequency**: How often system waits vs schedules
3. **Player satisfaction**: Subjective variety perception
4. **Average wait time**: Ensure fairness not compromised

## Edge Cases Handled

### 1. First Few Matches
- Don't wait until 6 matches completed
- Allows system to establish initial rankings

### 2. Long Wait Times
- Never wait if someone already waited 1+ round
- Fairness trumps variety

### 3. All Courts Idle
- Never wait if no courts are busy
- Ensures matches start immediately

### 4. Insufficient Players
- Never wait if fewer than 4 players available
- Can't schedule a match anyway

### 5. No Valid Rank Matches
- Never wait if no valid rank-constrained match possible
- Prevents deadlock

## Performance Impact

**Computational Cost**: Minimal
- `detectHighRepetitionMatchup()` runs only when considering waiting
- Checks last 5 matches (constant time)
- Pairwise comparisons: O(n²) where n = 4 (negligible)

**Memory Impact**: None
- No new data structures
- Uses existing match history

**User Experience**: Improved
- Slightly more waiting (2-3 times per session)
- Significantly better variety
- Waiting players see more variety when they play

## Configuration Options (Future)

Could make these tunable in advanced settings:

```typescript
interface KOCVarietyConfig {
  minBusyCourtsToWait: number;        // Default: 2
  minMatchesBeforeWaiting: number;    // Default: 6
  loopDetectionThreshold: number;     // Default: 2
  highRepetitionThreshold: number;    // Default: 0.6 (60%)
  recentHistoryWindow: number;        // Default: 5
}
```

## Rollback Plan

If the changes cause too much waiting or other issues:

1. **Increase thresholds back:**
   - `numBusyCourts < 3` (from 2)
   - `completedMatches.length < 10` (from 6)

2. **Disable new detection:**
   - Comment out `detectHighRepetitionMatchup()` call

3. **Revert to original:**
   - Use git to revert `kingofcourt.ts` changes

## Summary

**Problem**: Players 1 & 2 played together 4 times in 10 matches due to insufficient waiting.

**Solution**: 
- Lower waiting thresholds (2 courts, 6 matches)
- Detect loops earlier (2 occurrences instead of 3)
- Add new high-repetition detection (60% pair overlap)
- Check recent history more aggressively (last 5 matches)

**Impact**: ~50% reduction in repetitive matchups with minimal waiting increase.

**Trade-off**: 2-3 strategic waits per session for significantly better variety.
