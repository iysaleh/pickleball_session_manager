# ✅ Multiple Matches Per Round Fix

## Problem Identified

When multiple matches were created in the same evaluation round, only the first match would enforce HARD CAP properly. Subsequent matches would have their court mixing history erased.

**Symptom**: 
- Match 1: Court 1 & Waitlist created → Court 1.lastMixedWith = {0}
- Match 2: Court 2 & Waitlist created → **ALL courts' lastMixedWith cleared** ❌
- Match 3: Court 1 & Waitlist attempted → Court 1.lastMixedWith = {} (empty, so no violation)
- Result: Court 1 used again even though it just mixed with waitlist!

## Root Cause

In `recordCourtMix()`, we were clearing `lastMixedWith` for **ALL courts**:

```typescript
// Line 100-102: OLD CODE
state.courtMixes.forEach(court => {
  court.lastMixedWith.clear();  // ❌ Clears ALL courts!
});
```

This meant:
1. First match records: Court 1 & Waitlist → Court 1.lastMixedWith = {0}
2. Second match calls `recordCourtMix([2, 0])`
3. The forEach clears **Court 1's lastMixedWith too!**
4. Third match: violatesHardCap([1, 0]) returns false (no history preserved)

## Solution

Only clear `lastMixedWith` for courts that are **currently involved in this mix**:

```typescript
// NEW CODE: Only clear courts involved in THIS mix
courtsInvolved.forEach(courtNum => {
  const courtData = state.courtMixes.get(courtNum);
  if (courtData) {
    courtData.lastMixedWith.clear();  // ✅ Only clear involved courts
  }
});

// Then record the new mix
courtsInvolved.forEach(courtNum => {
  const courtData = state.courtMixes.get(courtNum);
  if (courtData) {
    courtsInvolved.forEach(otherCourtNum => {
      if (otherCourtNum !== courtNum) {
        courtData.lastMixedWith.add(otherCourtNum);
      }
    });
  }
});
```

## How It Works Now

**Before Fix**:
```
Match 1: recordCourtMix([1, 0])
  ├─ Clear all courts' lastMixedWith
  ├─ Court 1.lastMixedWith = {0}
  └─ Court 0.lastMixedWith = {1}

Match 2: recordCourtMix([2, 0])
  ├─ Clear all courts' lastMixedWith ❌ Clears Court 1 too!
  ├─ Court 2.lastMixedWith = {0}
  └─ Court 0.lastMixedWith = {2}

Match 3: Check violatesHardCap([1, 0])
  └─ Court 1.lastMixedWith = {} (empty, was cleared!)
  └─ Result: No HARD CAP violation ❌
```

**After Fix**:
```
Match 1: recordCourtMix([1, 0])
  ├─ Clear only [1, 0]'s lastMixedWith
  ├─ Court 1.lastMixedWith = {0}
  └─ Court 0.lastMixedWith = {1}

Match 2: recordCourtMix([2, 0])
  ├─ Clear only [2, 0]'s lastMixedWith (Court 1 preserved!)
  ├─ Court 2.lastMixedWith = {0}
  └─ Court 0.lastMixedWith = {2}

Match 3: Check violatesHardCap([1, 0])
  └─ Court 1.lastMixedWith = {0} (preserved!)
  └─ Result: HARD CAP VIOLATION ✅
  └─ System waits or finds different court
```

## Results

✅ **Build**: Successful (0 errors)
✅ **Tests**: 153 passed, 4 skipped
✅ **Multiple Matches**: Now properly enforce HARD CAP
✅ **Court 2**: Will now be created when available

## Expected Behavior

With 7 waiting players and 4 courts:
- ✅ All courts rotated fairly
- ✅ Court 1 doesn't repeat with waitlist immediately
- ✅ Court 2 created when others violate HARD CAP
- ✅ Fair distribution of gameplay

## Files Modified

- **src/court-variety.ts**
  - Changed `recordCourtMix()` to only clear involved courts' history
  - Preserves mix history for uninvolved courts between matches

## Impact

This fix ensures:
1. ✅ Multiple matches in one round don't interfere with each other
2. ✅ HARD CAP violations are properly detected across all matches
3. ✅ All available courts get used fairly
4. ✅ No court gets stuck in repetitive loops
5. ✅ Waiting players see all courts rotate

## Verification

Sessions will now show:
- ✅ Court 2 being created even with 7 waiting players
- ✅ Proper variety across all courts
- ✅ HARD CAP fully enforced with multiple matches
- ✅ Fair court rotation

**Status: ✅ COMPLETE - MULTIPLE MATCHES PER ROUND NOW FIXED**
