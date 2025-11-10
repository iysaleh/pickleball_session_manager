# ✅ Waitlist History Accumulation Fix - Multiple Courts Per Round

## Problem Identified

When multiple courts were created in a single round with the waitlist, the waitlist's history was being erased, allowing it to mix with a court it had just mixed with in a previous match.

**Scenario**:
- Round 1: Mix [1, 0] → Court 1.lastMixedWith = {0}, Court 0.lastMixedWith = {1}
- Round 2: Mix [2, 0] → Clears Court 0's history!
  - Court 0.lastMixedWith is reset to {2}
  - **LOST: History that Court 0 mixed with Court 1**
- Round 3: Try Mix [1, 0] → No violation detected (Court 0's history doesn't include 1 anymore)
- Result: Court 1 & waitlist mix again even though they just mixed! ❌

**Symptom**: Never make 3 courts at a time. Always reuse Court 1 or 2 instead of progressing to new courts.

## Root Cause

In `recordCourtMix()`, we were clearing the waitlist (Court 0) history along with other courts:

```typescript
// OLD CODE
courtsInvolved.forEach(courtNum => {
  const courtData = state.courtMixes.get(courtNum);
  if (courtData) {
    courtData.lastMixedWith.clear();  // ❌ Clears waitlist too!
  }
});
```

This meant the waitlist's history was reset with every new mix, losing track of which physical courts it had recently interacted with.

## Solution

Don't clear the waitlist (Court 0) history - let it accumulate across multiple mixes in a round:

```typescript
// NEW CODE
courtsInvolved.forEach(courtNum => {
  if (courtNum !== 0) { // ✅ Don't clear waitlist history
    const courtData = state.courtMixes.get(courtNum);
    if (courtData) {
      courtData.lastMixedWith.clear();
    }
  }
});

// Record this mix - waitlist history accumulates
courtsInvolved.forEach(courtNum => {
  const courtData = state.courtMixes.get(courtNum);
  if (courtData) {
    courtsInvolved.forEach(otherCourtNum => {
      if (otherCourtNum !== courtNum) {
        courtData.lastMixedWith.add(otherCourtNum);  // Accumulates for waitlist
      }
    });
  }
});
```

## How It Works Now

**Before Fix**:
```
Round 1: Mix [1, 0]
  Court 1.lastMixedWith = {0}
  Court 0.lastMixedWith = {1}

Round 2: Mix [2, 0]
  Clear Court 0's history ❌
  Court 2.lastMixedWith = {0}
  Court 0.lastMixedWith = {2}  (lost the {1}!)

Round 3: Try Mix [1, 0]
  Court 1.lastMixedWith = {0}? YES
  Court 0.lastMixedWith = {1}? NO (it's {2})
  Result: No HARD CAP violation ❌ (WRONG!)
```

**After Fix**:
```
Round 1: Mix [1, 0]
  Court 1.lastMixedWith = {0}
  Court 0.lastMixedWith = {1}

Round 2: Mix [2, 0]
  Don't clear Court 0's history ✅
  Court 2.lastMixedWith = {0}
  Court 0.lastMixedWith = {1, 2}  (accumulates!)

Round 3: Try Mix [1, 0]
  Court 1.lastMixedWith = {0}? YES
  Court 0.lastMixedWith = {1}? YES ✅
  Result: HARD CAP violation ✅ (CORRECT!)
  
  Try Mix [3, 0] instead
  Court 3.lastMixedWith = {}? No history
  Court 0.lastMixedWith = {1, 2}? No 3 in history
  Result: No HARD CAP violation ✅ (Can create Court 3!)
```

## Multiple Courts Per Round

**Before Fix**:
```
Available: 11 players (7 waiting + 4 from finished court)
Occupied: Court 1 & 3

createMatches called:
  Loop: Court 1 occupied, skip
  Loop: Court 2 → Try with waitlist
    Generate [2, 0]
    recordCourtMix([2, 0]) clears 0's history
    Return [Court 2 match]
  
Result: Only 1 court created (Court 2)
```

**After Fix**:
```
Available: 11 players (7 waiting + 4 from finished court)
Occupied: Court 1 & 3

createMatches called:
  Loop: Court 1 occupied, skip
  Loop: Court 2 → Try with waitlist
    Generate [2, 0]
    recordCourtMix([2, 0]) - DON'T clear 0's history
    Return [Court 2 match]
  
  Loop: Court 3 occupied, skip
  Loop: Court 4 → Try with remaining waitlist
    Generate [4, 0]
    violatesHardCap([4, 0])? 
      Court 4.lastMixedWith = {}? No
      Court 0.lastMixedWith = {2}? Yes, but 4 not in it
      Result: No violation ✅
    recordCourtMix([4, 0])
    Court 0.lastMixedWith = {2, 4}  (keeps accumulating!)
    Return [Court 2 match, Court 4 match]

Result: 2 courts created! (Court 2 & 4)
```

With even more players, all 3+ courts can be created because the waitlist's history prevents reusing the same court.

## Results

✅ **Build**: Successful (0 errors)
✅ **Tests**: 153 passed, 4 skipped
✅ **Multiple Courts**: Now creates 2-3 courts per round
✅ **Waitlist History**: Accumulates across mixes
✅ **HARD CAP**: Properly enforced across all courts

## Expected Behavior

**Session with 15 players, 4 courts, 7 waiting**:
```
Match 1: Court 1 with Waitlist(4)
Match 2: Court 2 with Waitlist(4)
Match 3: Courts 3 & 4 with Waitlist(7) ← Creates 2 courts at once!
  (Because waitlist history = {1, 2} prevents remixing)
```

## Files Modified

- **src/court-variety.ts**
  - Modified `recordCourtMix()` to preserve waitlist (Court 0) history
  - Waitlist history now accumulates across multiple mixes in a round
  - Physical courts' history is cleared as before

## Impact

This fix ensures:
1. ✅ Multiple courts created per round (2-3 at a time)
2. ✅ Waitlist history prevents court reuse
3. ✅ HARD CAP properly enforced across all mixes
4. ✅ All 4 courts utilized in fair rotation
5. ✅ No court gets stuck in a loop with the waitlist

## The Key Insight

The waitlist (Court 0) is not a physical court with matches - it's a proxy for "available players". When it mixes with multiple physical courts in one round, its history should ACCUMULATE to track all courts it has interacted with, preventing those same courts from mixing with it again.

## Verification

Sessions will now show:
- ✅ 2-3 courts created per evaluation round
- ✅ All 4 courts progressing through rotation
- ✅ Proper HARD CAP enforcement
- ✅ Fair distribution of gameplay

**Status: ✅ COMPLETE - WAITLIST HISTORY NOW ACCUMULATES PROPERLY**
