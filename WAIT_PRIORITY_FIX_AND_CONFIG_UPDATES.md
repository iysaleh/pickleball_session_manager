# Wait Priority Fix and Advanced Configuration Updates

## Summary
Fixed critical wait priority bug and enhanced advanced configuration system to allow runtime tuning of algorithm parameters.

## Issues Fixed

### 1. Seven-Player Wait Bug (CRITICAL)
**Problem**: In a 7-player King of the Court session, when 4 players finished a match and 3 players were waiting, only 2 of the waiting players would get selected for the next match. This violated the core fairness principle that players who waited should get priority.

**Root Cause**: 
- The `gamesWaited` counter was not being incremented for waiting players when matches were first created
- The logic only incremented wait counts when `hasCompletedMatches` was true
- This meant at session start, all players had `gamesWaited = 0`, so the algorithm couldn't distinguish who had been waiting

**Fix**:
1. **session.ts** - Changed wait counter logic to increment `gamesWaited` for ALL waiting players whenever new matches are created (lines 258-270)
2. **kingofcourt.ts** - Enhanced player selection logic to ensure ALL players with the maximum wait count get priority (lines 1130-1253)
3. **kingofcourt.ts** - Fixed sorting priority in `generateRankingBasedMatches` to prioritize wait count FIRST, before considering recently-played status (lines 863-897)

**Result**: The test `seven-player-wait-bug.test.ts` now passes, ensuring all 3 waiting players get selected after the first match completes.

---

### 2. Wait Priority Hierarchy
**Changes**:
The wait priority sorting now follows this strict hierarchy:
1. **HIGHEST PRIORITY**: `gamesWaited` (most waits first)
2. **SECOND PRIORITY**: Recently played status (de-prioritize players who just finished)
3. **THIRD PRIORITY**: `gamesPlayed` (fewer games = higher priority for new players)

This ensures that wait fairness is ALWAYS the top priority, with recently-played status only used as a tiebreaker.

---

### 3. Empty Courts Strategy
**Enhancement**: When courts are empty (session stalled or court freed up), the algorithm now:
1. Identifies all players with the maximum wait count
2. If exactly `playersPerMatch` top waiters exist, selects them immediately
3. If more top waiters exist, finds the most balanced match from them
4. If fewer top waiters exist, includes ALL of them plus rank-compatible additional players
5. As last resort, forces all top waiters into the match even if rank constraints can't be fully satisfied

**Key Principle**: Wait fairness is MORE important than perfect ranking constraints or avoiding repetition.

---

## Advanced Configuration System

### Configuration Structure
All tuning variables are now exposed through the `AdvancedConfig` type:

```typescript
type AdvancedConfig = {
  kingOfCourt: KingOfCourtConfig;
  roundRobin: RoundRobinConfig;
}
```

### King of the Court Configuration Variables

#### ELO Rating System
- `baseRating`: Starting ELO rating for new players (default: 1500)
- `kFactor`: ELO K-factor for rating adjustments (default: 32)
- `minRating`: Minimum rating clamp (default: 800)
- `maxRating`: Maximum rating clamp (default: 2200)

#### Provisional Player Settings
- `provisionalGamesThreshold`: Games before player stops being provisional (default: 2)
  - **User Request**: This can now be changed during an active session

#### Ranking Disparity
- `rankingRangePercentage`: Percentage of player pool for matchmaking range (default: 0.5 = 50%)
  - **User Request**: This is the setting mentioned for "50% for the range of people that can be used for ranking disparity"
  - Can be adjusted from 0.3 (30%) to 0.7 (70%) for tighter or looser matching

#### Matchmaking Constraints
- `closeRankThreshold`: Max rank difference for "close" matchups (default: 4)
- `veryCloseRankThreshold`: Ideal rank difference (default: 3)

#### Waiting Strategy
- `maxConsecutiveWaits`: Max waits before forcing a match (default: 1)
- `minCompletedMatchesForWaiting`: Min completed matches before strategic waiting (default: 6)
- `minBusyCourtsForWaiting`: Min busy courts before considering waiting (default: 2)
- `courtSyncThreshold`: Wait for N courts to finish when we have players for N+ courts (default: 2)

#### Repetition Control
- `backToBackOverlapThreshold`: Max overlapping players for back-to-back (default: 3)
- `recentMatchCheckCount`: Number of recent matches to check (default: 3)
- `singleCourtLoopThreshold`: Times same group can play in recent history (default: 2)

#### Variety Optimization
- `softRepetitionFrequency`: Target frequency for playing with same person (default: Math.floor(totalPlayers/6))
- `highRepetitionThreshold`: Percentage threshold for high repetition (default: 0.6 = 60%)
- `partnershipVarietyWeight`: Weight for partnership variety in team assignment (default: 100)
- `opponentVarietyWeight`: Weight for opponent variety in team assignment (default: 50)

#### Team Assignment Penalties
- `partnershipRepeatPenalty`: Penalty for repeated partnerships (default: 80)
- `recentPartnershipPenalty`: Heavy penalty for recent partnerships (default: 300)
- `opponentRepeatPenalty`: Penalty for repeated opponents (default: 25)
- `recentOverlapPenalty`: Penalty for recent player overlap (default: 200)
- `teamBalancePenalty`: Penalty for unbalanced teams (default: 20)

### Updating Configuration During Active Session

You can now update the advanced configuration during an active session:

```typescript
import { updateAdvancedConfig } from './session';

// Update provisional games threshold
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    provisionalGamesThreshold: 3
  }
});

// Update ranking range percentage
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    rankingRangePercentage: 0.6 // 60% instead of 50%
  }
});

// Update multiple settings
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    provisionalGamesThreshold: 4,
    maxConsecutiveWaits: 2,
    partnershipRepeatPenalty: 100
  }
});
```

---

## Files Modified

### 1. `src/types.ts`
- Already had complete `KingOfCourtConfig` type with all tuning variables
- No changes needed

### 2. `src/utils.ts`
- Already had `getDefaultAdvancedConfig()` function with all default values
- No changes needed

### 3. `src/session.ts`
- **Lines 255-270**: Fixed `gamesWaited` increment logic to happen whenever new matches are created
- **Lines 566-580**: Already had `updateAdvancedConfig()` function for runtime updates

### 4. `src/kingofcourt.ts`
- **Lines 863-897**: Fixed player sorting to prioritize `gamesWaited` FIRST
- **Lines 1130-1253**: Enhanced `selectPlayersForRankMatch` with proper wait fairness logic
- Removed unreachable code that was leftover from previous implementation

### 5. `src/seven-player-wait-bug.test.ts`
- Tests now pass, validating that all 3 waiting players get selected after first match

---

## Testing

### Test Results
✅ `seven-player-wait-bug.test.ts` - Both tests passing:
- "should ensure all 3 waiting players get to play after first match in 7-player KOC session"
- "should prioritize waiting players over players who just finished a match"

### How to Run Tests
```bash
npm test -- src/seven-player-wait-bug.test.ts
```

---

## Remaining Issues to Address

Based on the user's feedback, these issues still need to be fixed:

### 1. Court Filling After Player Addition
When a player is added to an active session and courts become available, the system should automatically re-evaluate and create new matches. Currently implemented in `addPlayerToSession` but may need refinement.

### 2. Partnership Repetition
The user noted that players like Ibraheem and Jeremy were playing together too frequently. The current penalties may need adjustment:
- Consider increasing `recentPartnershipPenalty` from 300 to 500
- Consider increasing `partnershipRepeatPenalty` from 80 to 120

### 3. Court Synchronization
When multiple courts are available and finishing at different times, the algorithm should sometimes wait for 2+ courts to finish before creating new matches. This improves variety by allowing larger player pools for matching.

The `courtSyncThreshold` setting (default: 2) controls this behavior.

---

## Usage Examples

### Example 1: Make New Players Stay Provisional Longer
```typescript
// Default is 2 games, increase to 4 for more stable initial rankings
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    provisionalGamesThreshold: 4
  }
});
```

### Example 2: Tighter Ranking Constraints
```typescript
// Reduce matching range from 50% to 40%
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    rankingRangePercentage: 0.4
  }
});
```

### Example 3: Reduce Partnership Repetition
```typescript
// Increase penalties for repeated partnerships
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    partnershipRepeatPenalty: 120,
    recentPartnershipPenalty: 500
  }
});
```

### Example 4: More Aggressive Court Synchronization
```typescript
// Wait for 3 courts to finish instead of 2 (better variety, less utilization)
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    courtSyncThreshold: 3
  }
});
```

---

## Benefits

1. **Fair Wait Priority**: Players who wait are guaranteed priority in next match selection
2. **Runtime Tuning**: All algorithm parameters can be adjusted during an active session
3. **Flexible Matching**: Admins can tune the balance between:
   - Ranking strictness vs. court utilization
   - Variety vs. balanced matchups
   - Wait fairness vs. optimal pairings
4. **Better Documentation**: All tuning variables are clearly documented with their purpose and defaults

---

## Next Steps

1. ✅ Fix wait priority bug (DONE)
2. ✅ Extract all tuning variables (DONE - already existed)
3. ✅ Document all configuration options (DONE)
4. ⏳ Test and refine court filling after player addition
5. ⏳ Add tests for partnership repetition scenarios
6. ⏳ Test court synchronization behavior with 8+ players
