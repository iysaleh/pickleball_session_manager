# Advanced Configuration Quick Reference

## How to Update Config During Active Session

```typescript
import { updateAdvancedConfig } from './session';

// Only specify the fields you want to change
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    recentPartnershipPenalty: 500,  // Your new value
  }
});
```

## Most Common Adjustments

### Problem: Players playing together TOO OFTEN
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    recentPartnershipPenalty: 500,      // ↑ from 300
    partnershipRepeatPenalty: 120,      // ↑ from 80
    partnershipVarietyWeight: 150,      // ↑ from 100
  }
});
```

### Problem: New players ranked TOO QUICKLY
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    provisionalGamesThreshold: 3,  // ↑ from 2 (or 4, 5...)
  }
});
```

### Problem: Too much WAITING between games
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    maxConsecutiveWaits: 0,  // ↓ from 1 (never wait strategically)
  }
});
```

### Problem: Mismatched skill levels playing together
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    rankingRangePercentage: 0.4,  // ↓ from 0.5 (stricter matching)
  }
});
```

### Problem: Same group playing repeatedly on ONE court
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    courtSyncThreshold: 3,  // ↑ from 2 (wait for more courts)
  }
});
```

## All Available King of Court Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `baseRating` | 1500 | Starting ELO rating for new players |
| `kFactor` | 32 | ELO adjustment factor |
| `minRating` | 800 | Minimum rating clamp |
| `maxRating` | 2200 | Maximum rating clamp |
| `provisionalGamesThreshold` | 2 | Games before ranking stabilizes |
| `rankingRangePercentage` | 0.5 | Matchmaking range (50% = can play within your half) |
| `closeRankThreshold` | 4 | Max rank diff for "close" matchup |
| `veryCloseRankThreshold` | 3 | Ideal rank difference |
| `maxConsecutiveWaits` | 1 | Max waits before forcing match |
| `minCompletedMatchesForWaiting` | 6 | Min matches before strategic waiting |
| `minBusyCourtsForWaiting` | 2 | Min busy courts before waiting |
| `courtSyncThreshold` | 2 | Courts to wait for simultaneously |
| `backToBackOverlapThreshold` | 3 | Max overlapping players in consecutive matches |
| `recentMatchCheckCount` | 3 | Recent matches to check for repetition |
| `singleCourtLoopThreshold` | 2 | Max times same group plays recently |
| `softRepetitionFrequency` | 3 | Target games between playing same person |
| `highRepetitionThreshold` | 0.6 | 60% threshold for high repetition |
| `partnershipVarietyWeight` | 100 | Weight for partnership diversity |
| `opponentVarietyWeight` | 50 | Weight for opponent diversity |
| `partnershipRepeatPenalty` | 80 | Penalty for repeated partnerships |
| `recentPartnershipPenalty` | 300 | Heavy penalty for recent partners |
| `opponentRepeatPenalty` | 25 | Penalty for repeated opponents |
| `recentOverlapPenalty` | 200 | Penalty for recent player overlap |
| `teamBalancePenalty` | 20 | Penalty for unbalanced teams |

## Preset Configurations

### High Variety (minimize repetition)
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    recentPartnershipPenalty: 600,
    partnershipRepeatPenalty: 150,
    partnershipVarietyWeight: 200,
    opponentVarietyWeight: 100,
    highRepetitionThreshold: 0.4,  // More strict
  }
});
```

### Fast Play (minimize waiting)
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    maxConsecutiveWaits: 0,
    minCompletedMatchesForWaiting: 100,  // Effectively disable
    courtSyncThreshold: 1,  // Don't wait for synchronization
  }
});
```

### Strict Skill Matching
```typescript
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    rankingRangePercentage: 0.3,  // Only 30% range
    closeRankThreshold: 2,
    veryCloseRankThreshold: 1,
    provisionalGamesThreshold: 4,  // More games before ranking
  }
});
```

### Balanced (default)
```typescript
// Just use the defaults - no need to call updateAdvancedConfig
// Or reset to defaults:
import { getDefaultAdvancedConfig } from './utils';
session.advancedConfig = getDefaultAdvancedConfig();
```

## Tips

1. **Make small adjustments**: Change one setting at a time and observe
2. **Test with exports**: Use "Export Session" to see partnership patterns
3. **Monitor repetition**: Check if same pairs appear frequently in match history  
4. **Adjust penalties**: Higher penalties = stronger enforcement
5. **Balance tradeoffs**: More variety may mean longer waits or less balanced matches

## Examples from Real Sessions

### "Ibraheem and Jeremy playing together too much"
```typescript
// Increase recent partnership penalty dramatically
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    recentPartnershipPenalty: 800,  // Very heavy penalty
  }
});
```

### "7 players, only 2 of 3 waiters played"
This is now fixed in the core algorithm. If it still occurs:
```typescript
// Force more aggressive court filling
session = updateAdvancedConfig(session, {
  kingOfCourt: {
    maxConsecutiveWaits: 0,
  }
});
```

### "Added 8th player but 2nd court didn't fill"
This is now fixed in the core algorithm. The 2nd court should fill immediately when a player brings the total to 8.

## Browser Console

You can also update config via browser console during active session:

```javascript
// Access the session (assuming it's exposed)
const newConfig = {
  kingOfCourt: {
    recentPartnershipPenalty: 500
  }
};

// This would require exposing updateAdvancedConfig to window
// Or manually updating: currentSession.advancedConfig.kingOfCourt.recentPartnershipPenalty = 500
```

---

**Pro Tip**: Save successful configurations and apply them at session start for consistent behavior!
