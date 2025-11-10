# Technical Implementation Guide - Court Variety System

## Architecture Overview

The court variety system is built as a modular subsystem integrated into the session management:

```
Session Creation
    ↓
initializeCourtVarietyState()
    ↓
[Session Running]
    ↓
completeMatch()
    ├─ recordCourtFinish()
    ├─ updateVarietyThresholds()
    └─ calculateWaitlistCourtCount()
    ↓
evaluateAndCreateMatches()
    ├─ getBestCourtMixCombination() [to be integrated]
    ├─ shouldWaitForMoreCourts() [to be integrated]
    └─ recordCourtMix() [to be integrated]
    ↓
[Session Continues]
```

## Type System Integration

### New Types Added to types.ts

```typescript
export type CourtMixHistory = {
  courtNumber: number;
  lastMixedWith: Set<number>;
  finishCount: number;
  varietyThreshold: number;
};

export type CourtVarietyState = {
  courtMixes: Map<number, CourtMixHistory>;
  waitlistCourtCount: number;
  lastMixRound: number;
  totalCourtFinishes: Map<number, number>;
};
```

### Session Type Enhancement

```typescript
export type Session = {
  // ... existing fields ...
  courtVarietyState: CourtVarietyState; // NEW
};
```

## Initialization Flow

### When Session Starts

```typescript
export function createSession(config: SessionConfig, maxQueueSize: number = 100): Session {
  // ... existing initialization ...
  
  // NEW: Initialize court variety tracking
  const courtVarietyState = initializeCourtVarietyState(config.courts);
  
  return {
    // ... existing fields ...
    courtVarietyState, // NEW
  };
}
```

### Initialization Details

```typescript
export function initializeCourtVarietyState(totalCourts: number): CourtVarietyState {
  const courtMixes = new Map<number, CourtMixHistory>();
  
  // Create entry for each court (1-indexed)
  for (let i = 1; i <= totalCourts; i++) {
    courtMixes.set(i, {
      courtNumber: i,
      lastMixedWith: new Set(),      // No previous mixes
      finishCount: 0,                // No finishes yet
      varietyThreshold: 50,          // Neutral/balanced
    });
  }
  
  return {
    courtMixes,
    waitlistCourtCount: 0,
    lastMixRound: 0,
    totalCourtFinishes: new Map(
      Array.from({ length: totalCourts }, (_, i) => [i + 1, 0])
    ),
  };
}
```

## Match Completion Integration

### When Match Completes

```typescript
export function completeMatch(
  session: Session,
  matchId: string,
  team1Score: number,
  team2Score: number
): Session {
  // ... existing match completion logic ...
  
  const updated = { ...session, matches: updatedMatches, playerStats: newPlayerStats };
  
  // NEW: Track court variety (only on first completion, not edits)
  if (!isEdit) {
    recordCourtFinish(updated, match.courtNumber);
    updateVarietyThresholds(updated);
    updated.courtVarietyState.waitlistCourtCount = 
      calculateWaitlistCourtCount(updated.waitingPlayers.length);
  }
  
  return isEdit ? updated : evaluateAndCreateMatches(updated);
}
```

## Variety Threshold Algorithm

### updateVarietyThresholds Implementation

```typescript
export function updateVarietyThresholds(session: Session): void {
  const state = session.courtVarietyState;
  const finishCounts = Array.from(state.totalCourtFinishes.values());
  
  if (finishCounts.length === 0) return;
  
  // Calculate distribution statistics
  const avgFinishes = finishCounts.reduce((a, b) => a + b, 0) / finishCounts.length;
  const maxFinishes = Math.max(...finishCounts);
  const minFinishes = Math.min(...finishCounts);
  
  // Adjust thresholds based on imbalance
  state.courtMixes.forEach((court, courtNum) => {
    const courtFinishes = state.totalCourtFinishes.get(courtNum) || 0;
    
    if (courtFinishes < avgFinishes) {
      // Court behind - increase threshold (encourage mixing)
      court.varietyThreshold = Math.min(100, court.varietyThreshold + 5);
    } else if (courtFinishes > avgFinishes + 1) {
      // Court ahead - decrease threshold (be more flexible)
      court.varietyThreshold = Math.max(0, court.varietyThreshold - 5);
    } else {
      // Court balanced - drift toward 50
      if (court.varietyThreshold > 50) {
        court.varietyThreshold = Math.max(50, court.varietyThreshold - 2);
      } else if (court.varietyThreshold < 50) {
        court.varietyThreshold = Math.min(50, court.varietyThreshold + 2);
      }
    }
  });
}
```

### Threshold Semantics

```
Threshold 0-30:   "FLEXIBLE"    - Court finished more, allow repetition
Threshold 30-70:  "NORMAL"      - Standard variety rules apply
Threshold 70-100: "STRICT"      - Court behind, enforce strict variety
```

## Mix History Tracking

### Recording Court Mixes

```typescript
export function recordCourtMix(
  session: Session,
  courtsInvolved: number[]
): void {
  const state = session.courtVarietyState;
  
  // Clear previous mixes (one round lookback)
  state.courtMixes.forEach(court => {
    court.lastMixedWith.clear();
  });
  
  // Record current mix
  courtsInvolved.forEach(courtNum => {
    const courtData = state.courtMixes.get(courtNum);
    if (courtData) {
      // Add all other courts in this mix
      courtsInvolved.forEach(otherCourtNum => {
        if (otherCourtNum !== courtNum) {
          courtData.lastMixedWith.add(otherCourtNum);
        }
      });
    }
  });
  
  state.lastMixRound++;
}
```

### Example Mix Recording

```
recordCourtMix(session, [1, 2]);  // Courts 1 and 2 mixed

Court 1: lastMixedWith = {2}
Court 2: lastMixedWith = {1}
Court 3: lastMixedWith = {}  (not involved)
Court 4: lastMixedWith = {}  (not involved)
```

## Smart Court Selection

### Finding Best Mix Combination

```typescript
export function getBestCourtMixCombination(
  session: Session,
  availableCourts: number[],
  numCourtsToMix: number = 2
): number[] | null {
  const state = session.courtVarietyState;
  
  if (availableCourts.length < numCourtsToMix) {
    return null;
  }
  
  // Score each court
  const scoredCourts = availableCourts.map(courtNum => {
    const courtData = state.courtMixes.get(courtNum);
    if (!courtData) return { court: courtNum, score: 0 };
    
    const finishCount = state.totalCourtFinishes.get(courtNum) || 0;
    const avgFinishes = Array.from(state.totalCourtFinishes.values())
      .reduce((a, b) => a + b, 0) / state.totalCourtFinishes.size;
    
    // PRIMARY: Penalize courts that finished more
    let score = -(finishCount - avgFinishes) * 100;
    
    // SECONDARY: Reward higher variety threshold
    score += courtData.varietyThreshold;
    
    // TERTIARY: Bonus for courts not mixed recently
    score += courtData.lastMixedWith.size === 0 ? 50 : 0;
    
    return { court: courtNum, score };
  });
  
  // Sort by score (highest first)
  scoredCourts.sort((a, b) => b.score - a.score);
  
  // Return top N courts
  const selectedCourts = scoredCourts
    .slice(0, numCourtsToMix)
    .map(s => s.court)
    .sort();
  
  return selectedCourts;
}
```

### Scoring Example

```
Available: [1, 2, 3, 4]
Finish counts: [5, 3, 2, 2]
Avg: 3
Thresholds: [30, 50, 70, 75]
Last mixed: [{2}, {1}, {}, {}]

Court 1: score = -(5-3)*100 + 30 + 0 = -170 + 30 = -140
Court 2: score = -(3-3)*100 + 50 + 0 = 0 + 50 = 50
Court 3: score = -(2-3)*100 + 70 + 50 = 100 + 70 + 50 = 220
Court 4: score = -(2-3)*100 + 75 + 50 = 100 + 75 + 50 = 225

Sorted: [4 (225), 3 (220), 2 (50), 1 (-140)]
Selection: Courts 4 & 3
```

## Waiting Logic

### Should Court Wait for Diversity

```typescript
export function shouldCourtWaitForDiversity(
  session: Session,
  courtNumber: number,
  candidateCourts: number[]
): boolean {
  const state = session.courtVarietyState;
  const courtData = state.courtMixes.get(courtNumber);
  
  if (!courtData) return false;
  
  // Check if ALL candidates were mixed with this court
  const allWerePrevious = candidateCourts.every(c => 
    courtData.lastMixedWith.has(c)
  );
  
  if (!allWerePrevious) {
    return false;  // Safe, there's diversity
  }
  
  // High threshold forces waiting to prevent repetition
  return courtData.varietyThreshold > 70;
}
```

### Should Wait for More Courts

```typescript
export function shouldWaitForMoreCourts(
  session: Session,
  finishedCourts: number[]
): boolean {
  const state = session.courtVarietyState;
  
  if (finishedCourts.length === 0) return true;
  
  // Check finish count imbalance
  const finishCounts = Array.from(state.totalCourtFinishes.values());
  if (finishCounts.length > 0) {
    const maxFinishes = Math.max(...finishCounts);
    const minFinishes = Math.min(...finishCounts);
    
    // Significant imbalance - wait to balance
    if (maxFinishes - minFinishes > 2) {
      return true;
    }
  }
  
  // Single court with high threshold - wait
  if (finishedCourts.length === 1) {
    const courtNum = finishedCourts[0];
    const courtData = state.courtMixes.get(courtNum);
    if (courtData && courtData.varietyThreshold > 75) {
      return true;
    }
  }
  
  return false;
}
```

## Serialization for Persistence

### Serialize to JSON

```typescript
function serializeSession(session: Session): any {
  return {
    // ... existing fields ...
    courtVarietyState: {
      // Convert Map to Array for JSON
      courtMixes: Array.from(session.courtVarietyState.courtMixes.entries())
        .map(([num, data]) => ({
          courtNumber: data.courtNumber,
          lastMixedWith: Array.from(data.lastMixedWith),
          finishCount: data.finishCount,
          varietyThreshold: data.varietyThreshold,
        })),
      waitlistCourtCount: session.courtVarietyState.waitlistCourtCount,
      lastMixRound: session.courtVarietyState.lastMixRound,
      totalCourtFinishes: Array.from(session.courtVarietyState.totalCourtFinishes.entries()),
    },
  };
}
```

### Deserialize from JSON

```typescript
function deserializeSession(data: any): Session {
  // ... existing fields ...
  
  // Reconstruct court mixes Map
  const courtMixes = new Map();
  if (data.courtVarietyState?.courtMixes) {
    data.courtVarietyState.courtMixes.forEach((mData: any) => {
      courtMixes.set(mData.courtNumber, {
        courtNumber: mData.courtNumber,
        lastMixedWith: new Set(mData.lastMixedWith),
        finishCount: mData.finishCount,
        varietyThreshold: mData.varietyThreshold,
      });
    });
  }
  
  // Reconstruct totalCourtFinishes Map
  const totalCourtFinishes = new Map();
  if (data.courtVarietyState?.totalCourtFinishes) {
    data.courtVarietyState.totalCourtFinishes.forEach((entry: any) => {
      totalCourtFinishes.set(entry[0], entry[1]);
    });
  }
  
  return {
    // ... existing fields ...
    courtVarietyState: {
      courtMixes,
      waitlistCourtCount: data.courtVarietyState?.waitlistCourtCount || 0,
      lastMixRound: data.courtVarietyState?.lastMixRound || 0,
      totalCourtFinishes,
    },
  };
}
```

## Integration Checklist

For complete integration with matchmaking:

- [ ] Update `evaluateAndCreateMatches()` to use `getBestCourtMixCombination()`
- [ ] Update `evaluateAndCreateMatches()` to use `shouldWaitForMoreCourts()`
- [ ] Add `recordCourtMix()` call after matches are assigned
- [ ] Test with Round Robin mode
- [ ] Test with King of the Court mode
- [ ] Verify localStorage persistence
- [ ] Monitor variety thresholds during gameplay
- [ ] Validate court finish balancing
- [ ] Test edge cases (1 court, many courts, etc.)

## Performance Characteristics

```
Operation            | Time Complexity | Space Complexity | Typical Time
recordCourtFinish    | O(1)           | O(1)            | <1ms
recordCourtMix       | O(n)           | O(n)            | <1ms
updateVarietyThresholds | O(n)        | O(1)            | <1ms
getBestCourtMixCombination | O(n²)    | O(n)            | <5ms
shouldCourtWaitForDiversity | O(1)    | O(1)            | <1ms
shouldWaitForMoreCourts | O(n)        | O(1)            | <1ms
getCourtVarietySummary | O(n)         | O(n)            | <1ms
```

## Testing Strategy

```typescript
// Test 1: Initialization
const state = initializeCourtVarietyState(4);
assert(state.courtMixes.size === 4);
assert(state.courtMixes.get(1)?.varietyThreshold === 50);

// Test 2: Finish tracking
recordCourtFinish(session, 1);
assert(session.courtVarietyState.totalCourtFinishes.get(1) === 1);

// Test 3: Threshold adjustment
recordCourtFinish(session, 1);
recordCourtFinish(session, 1);
recordCourtFinish(session, 2);
updateVarietyThresholds(session);
// Court 1 finished more, threshold should decrease
assert(session.courtVarietyState.courtMixes.get(1)!.varietyThreshold < 50);

// Test 4: Mix history
recordCourtMix(session, [1, 2]);
assert(session.courtVarietyState.courtMixes.get(1)!.lastMixedWith.has(2));

// Test 5: Wait logic
assert(shouldCourtWaitForDiversity(session, 1, [2]) === true);
```

## Debugging Tips

Enable logging to trace execution:

```typescript
function debugCourtVariety(session: Session) {
  const summary = getCourtVarietySummary(session);
  console.table(summary.courts);
  console.log('Waitlist courts:', summary.waitlistCourtCount);
  console.log('Mix round:', summary.lastMixRound);
}
```

This provides a complete technical implementation guide for understanding and maintaining the court variety system.
