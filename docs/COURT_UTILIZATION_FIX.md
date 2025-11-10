# Court Utilization Fix

## Problem
With 8 players and 4 courts available, the system was only using 1 court instead of filling 2 courts simultaneously.

### Example (from pickleball-session-11-05-2025-10-54.txt)
- **8 active players**
- **4 courts available**  
- **Only 1 court in use** (Court 1)
- **4 players waiting** unnecessarily

**Expected**: 2 courts running simultaneously (8 players / 4 per match = 2 matches)  
**Actual**: Only 1 match created, 4 players waiting

## Root Causes

### Issue 1: Variety check too conservative
The `shouldWaitForRankBasedMatchups` function had logic to prevent repetition by waiting for better variety:

```typescript
// Check if 2+ of last 3 matches used only currently available players
if (matchesFromSamePool >= 2 && availablePlayerIds.length <= 8) {
  return true; // Wait for variety
}
```

This was TOO conservative when:
- We have enough players for multiple courts (8 players = 2 matches)
- Courts are empty and available
- **Court utilization should be priority #1**, not variety

### Issue 2: Multi-match creation timing bug (CRITICAL!)
When creating multiple matches in one batch (e.g., after a match completes with 8 available players), the system would:
1. Create match 1 successfully (4 players)
2. Try to create match 2 with remaining 4 players
3. **Check if "all courts empty"** → sees match 1 (status 'waiting') → says NO
4. **Rejects match 2** because it doesn't use ultra-lenient logic
5. **Result**: Only 1 match created instead of 2!

The problem was checking `allCourtsEmpty` DYNAMICALLY during the loop:
```typescript
// WRONG: Checks dynamically, sees newly created matches
const allCourtsEmpty = matches.filter(m => 
  m.status === 'in-progress' || m.status === 'waiting'
).length === 0;
```

**Order of operations matters!** The check should be made ONCE at the start, then applied consistently to ALL matches in the batch.

## Solutions

### Fix 1: Court utilization priority check
Added priority check: **If we can fill multiple courts, ALWAYS do so** regardless of repetition concerns:

```typescript
// PRIORITY: If we have enough players for multiple courts, ALWAYS fill them
// Court utilization > variety concerns when we can run 2+ matches simultaneously
const emptyCourtCount = totalCourts - numBusyCourts;
const possibleMatches = Math.floor(availableRankings.length / playersPerMatch);

if (possibleMatches >= 2 || possibleMatches >= emptyCourtCount) {
  // We have enough players for multiple courts OR enough to fill all empty courts
  // Fill them! Court utilization is priority #1
  return false;
}
```

### Fix 2: Consistent batch matching (THE KEY FIX!)
**Check `allCourtsEmpty` ONCE at the start**, then pass it to all matches in the batch:

```typescript
function generateRankingBasedMatches(...) {
  // CRITICAL: Check if ALL courts are empty at the START
  const allCourtsEmptyAtStart = occupiedCourts.size === 0;
  
  for (let courtNum = 1; courtNum <= totalCourts; courtNum++) {
    // Pass allCourtsEmptyAtStart to ensure consistent matching
    const selectedPlayers = selectPlayersForRankMatch(
      ...,
      allCourtsEmptyAtStart  // Same value for ALL matches in this batch
    );
  }
}
```

```typescript
function selectPlayersForRankMatch(..., allCourtsWereEmpty: boolean = false) {
  if (hasEmptyCourts) {
    // Use the value from the START, not a dynamic check
    const allCourtsEmpty = allCourtsWereEmpty;  // ← FIXED!
    
    if (allCourtsEmpty) {
      // Apply ultra-lenient matching for ALL matches in this batch
    }
  }
}
```

**Why this works:**
- When match completes with 8 available players and 0 courts busy
- `allCourtsEmptyAtStart = true`
- Creates match 1 (4 players) → uses lenient logic ✅
- Creates match 2 (4 players) → **STILL uses lenient logic** ✅
- Result: 2 matches created, all 8 players playing!

### Logic Flow
1. **Check empty courts**: Are there courts not in use?
2. **Calculate possible matches**: How many matches can we create with available players?
3. **Priority decision**:
   - If `possibleMatches >= 2`: Fill courts! (Can run multiple simultaneous matches)
   - OR if `possibleMatches >= emptyCourtCount`: Fill all empty courts!
   - Otherwise: Check repetition concerns

### Example Scenarios

#### Scenario 1: 8 players, 4 courts, 0 busy
- `emptyCourtCount = 4`
- `possibleMatches = 8 / 4 = 2`
- `possibleMatches (2) >= 2` ✅ → **Fill courts!**
- **Result**: Create 2 matches

#### Scenario 2: 12 players, 4 courts, 1 busy
- `emptyCourtCount = 3`
- `possibleMatches = 8 / 4 = 2` (8 available, 4 playing)
- `possibleMatches (2) >= emptyCourtCount (3)` ❌ (but 2 >= 2 ✅)
- **Result**: Create 2 matches

#### Scenario 3: 5 players, 4 courts, 1 busy
- `emptyCourtCount = 3`
- `possibleMatches = 5 / 4 = 1`
- `possibleMatches (1) >= 2` ❌
- `possibleMatches (1) >= emptyCourtCount (3)` ❌
- **Check repetition**: If would cause repetition, wait
- **Result**: Variety check applies (normal logic)

## Impact

### Before Fix
- 8 players → 1 court used, 4 waiting unnecessarily
- Poor court utilization
- Longer wait times

### After Fix
- 8 players → 2 courts used, 0 waiting ✅
- Optimal court utilization
- Minimal wait times
- Variety concerns secondary to utilization

## Test Coverage
Added test in `stalled-session-bug.test.ts`:

```typescript
it('should use multiple courts when enough players available', () => {
  // 8 players, 4 courts
  // Should create 2 matches initially (not just 1)
  
  session = evaluateAndCreateMatches(session);
  const initialMatches = session.matches.filter(m => 
    m.status === 'waiting' || m.status === 'in-progress'
  );
  
  expect(initialMatches.length).toBe(2); // 2 courts used ✅
  expect(playingPlayerIds.size).toBe(8); // All 8 players playing ✅
});
```

## All Tests Pass ✅
```
Test Files: 11 passed
Tests: 131 passed | 3 skipped (134 total) ← +1 NEW TEST
Build: Successful
```

## Files Modified

### 1. **`src/kingofcourt.ts`**

**Line 476-492:** Added court utilization priority check
- Bypasses repetition check when enough players for multiple courts

**Line 803-820:** Fixed batch matching timing (generateRankingBasedMatches)
- Check `allCourtsEmptyAtStart` ONCE at function start
- Pass to all `selectPlayersForRankMatch` calls in the loop

**Line 998-1038:** Updated function signature (selectPlayersForRankMatch)
- Added parameter: `allCourtsWereEmpty: boolean = false`
- Use passed value instead of dynamic check
- Ensures consistent lenient matching for all matches in batch

### 2. **`src/stalled-session-bug.test.ts`**
- Added test for 8 players / 4 courts scenario
- Verifies 2 matches created initially
- Tests mid-session player addition (Jeremy joins)

## Configuration Respect
All advanced config settings still apply when utilization priority doesn't override:
- Repetition checks ✅ (when only 1 match possible)
- Strategic waiting ✅ (when utilization isn't priority)
- Back-to-back prevention ✅ (within matches)

## Mid-Session Player Addition
The fix also handles the scenario where a player joins mid-session:

### Example: 7 players → 8 players
1. Session running with 7 players (only 1 court possible)
2. Match 5 is in progress (4 playing, 3 waiting)
3. **8th player (Jeremy) joins** while match is in progress
4. Match 5 completes
5. System evaluates: 8 players available, 0 courts busy
6. **Creates 2 matches immediately** ✅

```typescript
// Test case: Add player mid-session
// Start match 5 with 7 players
session = startMatch(session, match5.id);

// Add 8th player while match in progress
session.activePlayers.add('Jeremy');

// Complete match 5
session = completeMatch(session, match5.id, 11, 7);

// Result: 2 new matches created with all 8 players
expect(newMatches.length).toBe(2);
```

## Summary
**Before**: System prioritized variety over court utilization  
**After**: System prioritizes utilization when enough players for multiple courts  
**Result**: Optimal court usage with 8+ players, minimal wait times

### Priority Hierarchy
1. **Court Utilization** (NEW) - Fill multiple courts when possible
2. **Fairness** - Top waiters get priority  
3. **Balance** - Create competitive matches
4. **Variety** - Avoid repetition when constraints allow

## Edge Cases Handled
- ✅ Session starts with 8 players → 2 courts immediately
- ✅ Player joins mid-match to make 8 → 2 courts after match completes
- ✅ 12 players, 4 courts, 1 busy → Creates 2 more matches
- ✅ 7 players → Correctly uses 1 court only
