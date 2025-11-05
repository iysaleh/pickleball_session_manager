# Provisional Player Threshold Update

## Change

**Updated provisional player threshold from 3 games to 2 games.**

Players are now considered "provisional" (having an unstable ranking) if they have played **fewer than 2 games** instead of fewer than 3 games.

## Rationale

- **Faster Integration**: Players establish a meaningful ranking after just 2 games instead of 3
- **Better User Experience**: Players are treated as "established" sooner, getting into more competitive matchups faster
- **Still Flexible**: 2 games is enough to determine if a player is a beginner, intermediate, or advanced
- **Reduced Waiting**: Provisional players have more flexibility in matchmaking, so reducing the threshold means less time in the "flexible matching" phase

## Changes Made

### 1. Core Algorithm (`src/kingofcourt.ts`)
```typescript
// Before: 
const isProvisional = stats.gamesPlayed < 3;

// After:
const isProvisional = stats.gamesPlayed < 2;
```

### 2. UI Display (`src/main.ts`)
```typescript
// Before:
const provisionalBadge = ranking.gamesPlayed < 3 ? '(Provisional)' : '';

// After:
const provisionalBadge = ranking.gamesPlayed < 2 ? '(Provisional)' : '';
```

### 3. Tests (`src/kingofcourt-ranking-bug.test.ts`)
```typescript
// Before:
const bothProvisional = topStats.gamesPlayed < 3 && bottomStats.gamesPlayed < 3;

// After:
const bothProvisional = topStats.gamesPlayed < 2 && bottomStats.gamesPlayed < 2;
```

## Impact on Gameplay

### Player Status Timeline

**Before** (3-game threshold):
- Game 1: Provisional (can play anyone)
- Game 2: Provisional (can play anyone)
- Game 3: Provisional (can play anyone)
- Game 4+: Established (rank-based matching)

**After** (2-game threshold):
- Game 1: Provisional (can play anyone)
- Game 2: Provisional (can play anyone)
- Game 3+: Established (rank-based matching)

### Benefits

1. **Faster Ranking Stabilization**: After 2 games, the system has enough data to create competitive matchups
2. **Reduced Gridlock**: Fewer provisional players means less boundary-crossing needed
3. **Better Balance**: Players get one fewer "wildcard" game before being slotted into their skill tier
4. **Still Fair**: 2 games is statistically significant for initial ranking

### Matchmaking Flexibility

**Provisional Players (< 2 games)**:
- Can cross half-pool rank boundaries
- Not restricted by rank constraints
- Helps fill courts when established players are in progress

**Established Players (2+ games)**:
- Must respect half-pool rank boundaries
- Matched with players of similar skill level
- Creates more competitive, balanced matches

## Testing

✅ **All tests passing**: 126/129 (3 skipped)
- All King of Court tests pass
- All Round Robin tests pass
- All provisional player integration tests pass

## Files Modified

1. `src/kingofcourt.ts` - Core algorithm threshold
2. `src/main.ts` - UI display threshold  
3. `src/kingofcourt-ranking-bug.test.ts` - Test assertions and comments

## Backward Compatibility

This change is backward compatible:
- Existing sessions continue to work
- Player stats are not affected
- Only the interpretation of "provisional" changes

## Conclusion

Changing the provisional threshold from 3 to 2 games provides a better balance between:
- **Flexibility** for new players to get into games quickly
- **Competitive matching** for established players
- **Court utilization** by reducing the provisional pool size

Players now graduate to established status one game earlier, creating more stable and competitive matchups while maintaining the flexibility needed for optimal court filling.
