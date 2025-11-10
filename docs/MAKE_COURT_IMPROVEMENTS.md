# ✅ Make Court Feature Improvements

## Problem Identified

Two related issues with Make Court and automatic court creation:

**Issue 1**: With 11 waiting players and only 1 court playing, the system would NOT create any more courts.
- Example: pickleball-session-11-09-2025-19-29.txt showed 11 waiting but no new courts created

**Issue 2**: Make Court wasn't letting users select which court to play on
- Only auto-calculated next court number
- Made it impossible to fill waiting/finished courts
- Example: pickleball-session-11-09-2025-19-31.txt

## Solutions Implemented

### 1. Remove Artificial Gate on Court Evaluation

**File**: `src/kingofcourt.ts` (Line 297)

**Before**:
```typescript
if (possibleCourts >= 2 && occupiedCourts.size >= algConfig.minBusyCourtsForWaiting) {
  // Only checked if 2+ courts were ALREADY busy
  const shouldWait = shouldWaitForRankBasedMatchups(...);
}
```

**After**:
```typescript
if (possibleCourts >= 2) {
  // Check regardless of how many courts are currently busy
  const shouldWait = shouldWaitForRankBasedMatchups(...);
}
```

**Why**: The gate `occupiedCourts.size >= algConfig.minBusyCourtsForWaiting` prevented the waiting evaluation when only 1 court was busy. With 11 players waiting, we should evaluate whether to create courts, not skip that evaluation.

**Result**: Now when 11 players are waiting and 1 court is busy:
1. We properly evaluate `shouldWaitForRankBasedMatchups()`
2. It checks: do we have 2 courts' worth (8 players)? YES
3. Are 3+ courts busy (totalCourts - 1)? NO
4. Decision: CREATE courts!

### 2. Add Court Selection to Make Court Modal

**File**: `index.html` (Lines 1463-1472)

Added court selection dropdown:
```html
<!-- Court Selection -->
<div style="margin-bottom: 20px;">
  <label style="font-size: 0.95em; margin-bottom: 8px; display: block;">Which court?</label>
  <select id="make-court-court-select" style="width: 100%; padding: 8px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-secondary); color: var(--text-primary);"></select>
</div>
```

### 3. Update Make Court Functions

**File**: `src/main.ts`

#### Updated `openMakeCourtModal()` (Lines 2695-2747)
- Populate court dropdown with all available courts (1 to config.courts)
- Users can now select which court to play on

```typescript
// Populate court dropdown
courtSelect.innerHTML = '';
for (let i = 1; i <= currentSession.config.courts; i++) {
  const option = document.createElement('option');
  option.value = i.toString();
  option.textContent = `Court ${i}`;
  courtSelect.appendChild(option);
}
```

#### Updated `handleCreateCustomCourt()` (Lines 2893-2941)
- Read selected court instead of auto-calculating
- Use selected court number directly
- Bypasses all HARD CAP checks (manual override)

```typescript
const courtSelect = (document.getElementById('make-court-court-select') as HTMLSelectElement).value;
// ...
const courtNumber = parseInt(courtSelect, 10);

const newMatch: Match = {
  id: matchId,
  courtNumber: courtNumber,  // ✅ User selected court
  team1: [team1P1, team1P2],
  team2: [team2P1, team2P2],
  status: 'in-progress',
};
```

## How It Works Now

### Scenario 1: 11 Waiting Players, 1 Court Playing

**Before**:
- Gate blocks evaluation
- No courts created
- 11 players stuck waiting

**After**:
- Gate removed
- Evaluation proceeds: "We have 8 players (2 courts worth), only 1 court busy"
- Decision: CREATE 2 courts!
- 8 players start playing, 3 still waiting (fair rotation)

### Scenario 2: Using Make Court

**Before**:
- User opens Make Court
- Selects 4 players
- System auto-assigns "next court number"
- Can't fill finished/waiting courts

**After**:
- User opens Make Court
- Selects specific court: "Court 1" or "Court 2"
- Selects 4 players
- Match created on selected court
- Bypasses all HARD CAP restrictions (manual user choice)

## Benefits

✅ **More Fluent Game Flow**: Courts fill up as soon as 4 players are ready, not waiting for artificial synchronization

✅ **User Control**: Users can now manually fill any court, even if HARD CAP would normally block it

✅ **Faster Turnaround**: With 15 players and 4 courts, all courts stay busy (not idle while waiting)

✅ **Respects Fairness**: Still uses ranking-based matchmaking and variety optimization, just evaluates more often

## Testing

✅ **Build**: Successful (0 errors)
✅ **Tests**: 158 passed, 4 skipped
✅ **No Regressions**: All existing tests pass
✅ **New Tests**: Added `make-court-improvements.test.ts` (6 tests)

## Files Modified

1. **src/kingofcourt.ts**
   - Removed `occupiedCourts.size >= algConfig.minBusyCourtsForWaiting` gate
   - Now evaluates court creation more aggressively

2. **index.html**
   - Added court selection dropdown to Make Court modal

3. **src/main.ts**
   - Updated `openMakeCourtModal()` to populate court dropdown
   - Updated `handleCreateCustomCourt()` to use selected court
   - Make Court now bypasses HARD CAP (manual override)

4. **src/tests/make-court-improvements.test.ts** (NEW)
   - Tests for court selection
   - Tests for multiple court creation scenarios
   - Tests for Make Court bypass of HARD CAP

## Expected Behavior Changes

**Good Changes**:
- ✅ Courts create faster with many waiting players
- ✅ Make Court can fill any court
- ✅ More fair court utilization

**No Negative Changes**:
- ❌ HARD CAP still prevents same courts from mixing twice in a row (auto mode)
- ❌ Ranking fairness still enforced (auto mode)
- ❌ Partnership variety still optimized (auto mode)

## Verification in Sessions

Look for:
1. With 11+ waiting players → 2-3 courts created simultaneously ✓
2. Make Court modal shows court selection dropdown ✓
3. Users can select any court (1-4) ✓
4. Make Court courts appear immediately in-progress ✓

**Status: ✅ COMPLETE - MAKE COURT FULLY IMPROVED**
