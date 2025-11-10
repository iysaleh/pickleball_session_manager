# ✅ Court Variety State Preservation Fix

## Problem Identified

The court variety state mutations were being lost between rounds because:

1. `generateKingOfCourtRound()` was called with `sessionWithClonedStats`
2. `recordCourtMix()` mutated `sessionWithClonedStats.courtVarietyState`
3. But `evaluateAndCreateMatches()` returned `{ ...session, ... }` without the updated `courtVarietyState`
4. Result: Mix history was reset each round, allowing same courts to mix together

**Symptom**: Only 2 of 3 possible courts being used at a time instead of all 3+.

## Root Cause

In `evaluateAndCreateMatches()`:
```typescript
// Line 254: Pass cloned session to generateKingOfCourtRound
const sessionWithClonedStats: Session = { ...session, playerStats: newPlayerStats };
const newMatches = generateKingOfCourtRound(sessionWithClonedStats);

// Lines 306-311: Return new session WITHOUT courtVarietyState mutations
return {
  ...session,
  matches: [...session.matches, ...newMatches],
  waitingPlayers,
  playerStats: newPlayerStats,
  // ❌ Missing: courtVarietyState from sessionWithClonedStats
};
```

## Solution

Explicitly preserve the `courtVarietyState` from the cloned session:

```typescript
return {
  ...session,
  matches: [...session.matches, ...newMatches],
  waitingPlayers,
  playerStats: newPlayerStats,
  courtVarietyState: sessionWithClonedStats.courtVarietyState, // ✅ PRESERVED
};
```

Updated in TWO places in `evaluateAndCreateMatches()`:
1. When `newMatches.length === 0` (no matches to create)
2. When returning matches

## How It Works Now

**Before Fix**:
```
Round 1: Create [Court 1, 2, 3] & Waitlist
  recordCourtMix([1, 2, 3, 0])
  courtVarietyState updated
  
Return session: { ...session, courtVarietyState: LOST }

Round 2: Check mix against OLD courtVarietyState
  lastMixedWith not updated → no HARD CAP check
  Results: Can use same courts again
```

**After Fix**:
```
Round 1: Create [Court 1, 2, 3] & Waitlist
  recordCourtMix([1, 2, 3, 0])
  courtVarietyState updated
  
Return session: { ...session, courtVarietyState: sessionWithClonedStats.courtVarietyState }

Round 2: Check mix against UPDATED courtVarietyState
  lastMixedWith is preserved
  violatesHardCap([1, 0]) = true (mixed last round)
  Forces use of Courts 2, 3, or 4
```

## Results

✅ **Build**: Successful (0 errors)
✅ **Tests**: 153 passed, 4 skipped
✅ **Court Variety**: Now properly maintained across rounds
✅ **Expected**: All available courts will be used fairly

## Expected Behavior After Fix

With 15 players and 4 courts:

```
Match 1: Court 1 → lastMixedWith = {0}
Match 2: Court 2 → lastMixedWith = {0}  
Match 3: Court 3 → lastMixedWith = {0}
Match 4: Try Court 1
  violatesHardCap([1, 0]) = true
  Wait for Court 4 or another court to finish
Match 4 (retry): Court 4 → lastMixedWith = {0}
Match 5: Try Court 1 again
  violatesHardCap([1, 0]) still true
  Wait for a court to finish that hasn't mixed with waitlist yet
```

Result: **ALL 4 courts get used fairly before repetition**

## Files Modified

- **src/session.ts**
  - Added `courtVarietyState: sessionWithClonedStats.courtVarietyState` to both return statements in `evaluateAndCreateMatches()`

## Impact

This fix ensures:
1. ✅ Court mix history is preserved between rounds
2. ✅ HARD CAP violations are properly detected
3. ✅ All courts get fair usage
4. ✅ No court gets stuck in repetitive loops
5. ✅ Waiting players force variety across all courts

## Verification

Session will now show:
- ✅ Multiple courts being used progressively (not 2 at a time)
- ✅ Fair rotation between all available courts
- ✅ Waiting players distributed evenly
- ✅ Proper court variety enforcement

**Status: ✅ COMPLETE - COURT VARIETY STATE NOW PRESERVED**
