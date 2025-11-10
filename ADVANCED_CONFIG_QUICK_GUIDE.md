# Advanced Configuration Quick Guide

## How to Update Configuration During a Session

All King of the Court algorithm parameters can now be changed during an active session using the `updateAdvancedConfig` function.

## Quick Examples

### Change Provisional Player Threshold
```typescript
import { updateAdvancedConfig } from './session';

// Change from 2 games to 5 games before players stop being provisional
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    provisionalGamesThreshold: 5
  }
});
```

### Adjust Ranking Range (50% default)
```typescript
// Tighter matching (40% range)
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    rankingRangePercentage: 0.4  // Only match with closest 40% of players
  }
});

// Looser matching (60% range)
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    rankingRangePercentage: 0.6  // Can match with 60% of players
  }
});
```

### Reduce Partnership Repetition
```typescript
// Increase penalties to avoid playing with same partners too often
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    partnershipRepeatPenalty: 150,      // Up from 80
    recentPartnershipPenalty: 600       // Up from 300
  }
});
```

### Adjust Court Synchronization
```typescript
// Wait for more courts to finish before creating matches (better variety)
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    courtSyncThreshold: 3  // Wait for 3 courts instead of 2
  }
});

// More aggressive court filling (less waiting)
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    courtSyncThreshold: 1  // Fill courts immediately as they free up
  }
});
```

## All King of the Court Settings

### ELO Rating
- `baseRating`: 1500 (starting rating)
- `kFactor`: 32 (rating change speed)
- `minRating`: 800 (minimum possible rating)
- `maxRating`: 2200 (maximum possible rating)

### Provisional Players
- `provisionalGamesThreshold`: 2 games (when players stop being "new")

### Ranking Constraints  
- `rankingRangePercentage`: 0.5 (50% - who can play with whom)
- `closeRankThreshold`: 4 ranks (prefer close matchups)
- `veryCloseRankThreshold`: 3 ranks (ideal matchup)

### Waiting & Court Strategy
- `maxConsecutiveWaits`: 1 (force match after this many waits)
- `minCompletedMatchesForWaiting`: 6 (need this many matches before strategic waiting)
- `minBusyCourtsForWaiting`: 2 (need this many busy courts to consider waiting)
- `courtSyncThreshold`: 2 (wait for this many courts to finish together)

### Repetition Control
- `backToBackOverlapThreshold`: 3 players (avoid same 3+ players back-to-back)
- `recentMatchCheckCount`: 3 matches (look back this far)
- `singleCourtLoopThreshold`: 2 times (detect when same group loops)

### Variety Optimization
- `softRepetitionFrequency`: 3 or totalPlayers/6 (target play frequency)
- `highRepetitionThreshold`: 0.6 (60% - when to avoid repetition)
- `partnershipVarietyWeight`: 100 (importance of partner variety)
- `opponentVarietyWeight`: 50 (importance of opponent variety)

### Team Assignment Penalties
- `partnershipRepeatPenalty`: 80 (cost of repeated partnerships)
- `recentPartnershipPenalty`: 300 (heavy cost of recent partnerships)
- `opponentRepeatPenalty`: 25 (cost of repeated opponents)
- `recentOverlapPenalty`: 200 (cost of recent player overlap)
- `teamBalancePenalty`: 20 (cost of unbalanced teams)

## Common Tuning Scenarios

### More Variety, Less Repetition
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    partnershipRepeatPenalty: 150,
    recentPartnershipPenalty: 600,
    opponentRepeatPenalty: 50,
    courtSyncThreshold: 2  // Wait for multiple courts
  }
});
```

### Stricter Rankings, Tighter Matches
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    rankingRangePercentage: 0.4,
    closeRankThreshold: 3,
    provisionalGamesThreshold: 4
  }
});
```

### More Court Utilization, Less Waiting
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    courtSyncThreshold: 1,
    maxConsecutiveWaits: 0,
    minCompletedMatchesForWaiting: 10
  }
});
```

### Longer Provisional Period for New Players
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    provisionalGamesThreshold: 5,  // 5 games instead of 2
    baseRating: 1400  // Start slightly lower if you have strong players
  }
});
```

## Tips

1. **Start with defaults** - They work well for most scenarios
2. **Make small changes** - Adjust one setting at a time to see the effect
3. **Test with your player count** - Settings that work for 8 players may not work for 20
4. **Balance trade-offs**:
   - More variety → possible unbalanced matches
   - Stricter rankings → possible empty courts
   - More court filling → possible repetition
5. **Monitor during session** - You can adjust mid-session if needed!

## Getting Current Config

To see the current configuration:
```typescript
console.log(session.advancedConfig.kingOfCourt);
```

This will show all current values so you know what to adjust.
