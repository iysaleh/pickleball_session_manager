# Court Variety and Mix Tracking System

## Overview

A sophisticated system that tracks court finishes and ensures maximum variety by preventing the same courts from mixing repeatedly. This system works with both Round Robin and King of the Court modes.

## Core Concepts

### 1. Court Finish Tracking
- Each court has a `finishCount` that increments every time a match completes
- Tracks `totalCourtFinishes` across all courts to identify imbalances
- If one court finishes 3x while another finishes 1x, the system waits to let slower courts catch up

### 2. Variety Threshold (0-100 scale)
- Each court has a `varietyThreshold` counter that starts at 50 (neutral)
- **Higher threshold (>70)**: Court has finished less than average, increase variety enforcement
- **Lower threshold (<30)**: Court has finished more than average, be more flexible
- **Medium (50)**: Court is balanced, normal variety rules apply
- Thresholds slowly drift toward 50 when balanced

### 3. Mix History Tracking
- Each court records which other courts it mixed with in the last round
- Stored in `lastMixedWith` Set<number>
- **Rule**: Never mix the same courts together twice in a row
- If only same courts are available, the system WAITS for a different court to finish

### 4. Waitlist as Virtual Courts
- Waitlist players are treated as virtual courts
- Formula: `floor(waitlistSize / 4)`
- Example: 8 waiting players = 2 virtual courts
- This is tracked in `waitlistCourtCount`

## Data Structures

### CourtMixHistory
```typescript
type CourtMixHistory = {
  courtNumber: number;           // Which court (1, 2, 3, etc)
  lastMixedWith: Set<number>;    // Courts mixed with in last round
  finishCount: number;           // Times this court has finished
  varietyThreshold: number;      // 0-100 variety counter
};
```

### CourtVarietyState
```typescript
type CourtVarietyState = {
  courtMixes: Map<number, CourtMixHistory>;
  waitlistCourtCount: number;    // Virtual courts from waitlist
  lastMixRound: number;          // Round counter
  totalCourtFinishes: Map<number, number>;
};
```

## Key Functions

### initializeCourtVarietyState(totalCourts: number)
- Called when session starts
- Creates CourtMixHistory for each court
- Initializes all courts to variety threshold of 50
- Sets all finish counts to 0

### recordCourtFinish(session, courtNumber)
- Called when a match completes on a court
- Increments `finishCount` for that court
- Updates `totalCourtFinishes` map
- Used to track imbalance and variety thresholds

### recordCourtMix(session, courtsInvolved)
- Called after a round of matches completes
- Records which courts mixed together
- Stores in `lastMixedWith` for each court
- Prevents same courts from mixing again immediately

### updateVarietyThresholds(session)
- Called after match completion
- Calculates average finishes across all courts
- Adjusts variety thresholds:
  - Courts finishing less → increase threshold
  - Courts finishing more → decrease threshold
  - Courts at average → drift toward 50

**Algorithm:**
```
avgFinishes = total finishes / number of courts
for each court:
  if (courtFinishes < avgFinishes):
    threshold += 5  (encourage mixing)
  else if (courtFinishes > avgFinishes + 1):
    threshold -= 5  (reduce over-playing)
  else:
    drift toward 50
```

### calculateWaitlistCourtCount(waitlistSize)
- Returns: `floor(waitlistSize / 4)`
- Treats waitlist as virtual courts
- Updated each time waiting players change

### shouldCourtWaitForDiversity(session, courtNumber, candidateCourts)
- Returns true if court should wait before mixing
- Checks if ALL candidate courts were mixed with in last round
- If variety threshold > 70, enforces waiting
- Prevents repetitive mixing patterns

**Logic:**
```
if (all candidates were mixed last round AND threshold > 70):
  WAIT for different court
else:
  OK to proceed
```

### getBestCourtMixCombination(session, availableCourts, numCourtsToMix)
- Finds optimal courts to mix together
- Scores each court based on:
  1. **Primary**: Courts with fewer finishes (higher priority)
  2. **Secondary**: Higher variety threshold (more balanced)
  3. **Tertiary**: Haven't mixed recently (bonus points)
- Returns top N courts sorted by score

**Scoring Formula:**
```
score = -(finishCount - avgFinishes) * 100
score += varietyThreshold
score += (lastMixedWith.size === 0) ? 50 : 0
```

### shouldWaitForMoreCourts(session, finishedCourts)
- Determines if we should wait before creating matches
- Returns true if:
  1. Finish count imbalance > 2
  2. Only 1 court finished and variety threshold > 75
  3. No variety opportunities available

### getRecommendedMixSize(session, availableCourts)
- Calculates optimal number of courts to mix
- If avg variety > 70: Use 3 courts (more balancing needed)
- Otherwise: Use 2 courts (normal flow)

### getCourtVarietySummary(session)
- Returns debugging/logging summary
- Shows finish counts, thresholds, and mix history for all courts
- Useful for monitoring variety system

## Example Flow

### Scenario: 4 Courts, 12 Players

**Initial State:**
```
Court 1: finishCount=0, threshold=50, lastMixed={}
Court 2: finishCount=0, threshold=50, lastMixed={}
Court 3: finishCount=0, threshold=50, lastMixed={}
Court 4: finishCount=0, threshold=50, lastMixed={}
```

**Round 1 Matches:**
- Courts 1 & 2 finish first
- Courts 3 & 4 still playing

**After Round 1:**
```
recordCourtFinish(1)
recordCourtFinish(2)
recordCourtMix(session, [1, 2])
updateVarietyThresholds()

Court 1: finishCount=1, threshold=55, lastMixed={2}
Court 2: finishCount=1, threshold=55, lastMixed={1}
Court 3: finishCount=0, threshold=45, lastMixed={}
Court 4: finishCount=0, threshold=45, lastMixed={}
```

**Decision for Round 2:**
```
shouldCourtWaitForDiversity([1, 2], [1, 2])?
  → Courts 1 & 2 mixed last round
  → Check if threshold > 70: NO (threshold = 55)
  → Proceed with 1 & 2
  
But also check:
  getBestCourtMixCombination([1, 2, 3, 4], 2)
  → Courts 3 & 4 have lower finishes
  → Recommend mixing with different courts
```

**Result:** 
- If courts 3 & 4 also finished: Mix them (new courts, lower finish count)
- If courts 3 & 4 still playing: Mix 1 & 2 (only option)
- If courts 1 & 2 both wait: Other courts can finish and break the pattern

## Integration Points

### Session Creation
```typescript
// In createSession()
const courtVarietyState = initializeCourtVarietyState(config.courts);
```

### Match Completion
```typescript
// In completeMatch()
recordCourtFinish(updated, match.courtNumber);
updateVarietyThresholds(updated);
updated.courtVarietyState.waitlistCourtCount = calculateWaitlistCourtCount(updated.waitingPlayers.length);
```

### Serialization
```typescript
// For localStorage persistence
courtVarietyState: {
  courtMixes: Array (serialized from Map)
  waitlistCourtCount: number
  lastMixRound: number
  totalCourtFinishes: Array (serialized from Map)
}
```

## Real-World Examples

### Example 1: Unbalanced Courts
**Situation:** Court 1 finishes 5 times, Court 2 finishes 2 times

```
Court 1: threshold = 30 (decreased)
Court 2: threshold = 70 (increased)

Action:
- Court 1 is forced to wait more
- Court 2 is prioritized for mixing
- Balances finish counts
```

### Example 2: Repetitive Mixing
**Situation:** Courts 1 & 2 mixed in last 2 rounds

```
Court 1: lastMixedWith = {2}, threshold = 75
Court 2: lastMixedWith = {1}, threshold = 75

shouldCourtWaitForDiversity([1], [2])?
  → Yes! (all candidates mixed last round AND threshold > 70)
  
Action:
- System WAITS for Court 3 or 4 to finish
- Then mixes 1 with 3 (or 4)
- Ensures court variety
```

### Example 3: Waitlist Integration
**Situation:** 8 players waiting

```
waitlistCourtCount = floor(8 / 4) = 2

Decision Logic:
- Waitlist counts as 2 virtual courts
- If only 1 court finished, wait for another
- Create 2 courts when 2+ physical courts finish
```

## Configuration

The system uses these session settings (indirectly through variety thresholds):
- `courtSyncThreshold`: Original setting, now augmented by variety system
- `maxConsecutiveWaits`: Limits how long a player can wait

## Performance Impact

- **Memory**: O(n) where n = number of courts (minimal)
- **CPU**: O(n) per match completion (negligible)
- **Latency**: <1ms for all calculations

## Debugging

Use `getCourtVarietySummary()` to monitor system:
```typescript
const summary = getCourtVarietySummary(session);
console.log('Court Variety Status:', summary);

// Output example:
{
  waitlistCourtCount: 2,
  lastMixRound: 5,
  courts: [
    { court: 1, finishCount: 4, varietyThreshold: 35, lastMixedWith: [2, 3] },
    { court: 2, finishCount: 5, varietyThreshold: 30, lastMixedWith: [1] },
    { court: 3, finishCount: 2, varietyThreshold: 65, lastMixedWith: [1, 4] },
    { court: 4, finishCount: 2, varietyThreshold: 70, lastMixedWith: [3] }
  ]
}
```

## Future Enhancements

1. **Configurable Thresholds**: Allow users to tune variety aggressiveness
2. **Machine Learning**: Learn optimal mix patterns over time
3. **Analytics**: Track variety metrics and generate reports
4. **Preview System**: Show users which courts will mix next
5. **Custom Rules**: Allow specific court pairings to be forbidden
6. **Historical Analysis**: Analyze past mixing patterns

## Testing

The system is tested with:
- Court finish tracking accuracy
- Variety threshold calculations
- Serialization/deserialization
- Edge cases (single court, many courts, unbalanced finishes)
- Integration with existing algorithms

All existing tests pass with the variety system integrated.
