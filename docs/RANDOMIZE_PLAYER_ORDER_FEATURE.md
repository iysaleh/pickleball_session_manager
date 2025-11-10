# Randomize Initial Player Order Feature

## Overview

Added an optional advanced configuration setting that randomizes the order of players when starting a session, ensuring that initial matches don't always feature the same players.

## Problem Addressed

**Before this feature:**
- Players were always processed in the order they were added to the session
- First matches always featured the first 4, 8, 12, or 16 players added
- If you always add your best players first, they always play in the first round together
- Predictable initial matchups reduced variety

**Example with 4 courts, 18 players:**
- Court 1: Always players 1 & 2 vs 3 & 4
- Court 2: Always players 5 & 6 vs 7 & 8
- Court 3: Always players 9 & 10 vs 11 & 12
- Court 4: Always players 13 & 14 vs 15 & 16
- Players 17 & 18 always wait first

## Solution Implemented

### New Configuration Option

Added `randomizePlayerOrder?: boolean` to `SessionConfig`:
- **Default**: `false` (disabled) - maintains existing behavior
- **When enabled**: Shuffles player order using Fisher-Yates algorithm before creating initial matches
- **Location**: Advanced Configuration section (collapsed by default)

### User Interface

**Checkbox Label:** "Randomize Initial Player Order"

**Description:** 
> Shuffle players randomly when starting the session instead of using the order they were added. This ensures first matches are not always the same players.

**Location:** Setup page → Advanced Configuration section

### Technical Implementation

#### 1. Type Definition (`types.ts`)
```typescript
export type SessionConfig = {
  // ... existing fields ...
  randomizePlayerOrder?: boolean; // New optional field
};
```

#### 2. Session Creation Logic (`session.ts`)
```typescript
export function createSession(config: SessionConfig, maxQueueSize: number = 100): Session {
  // Randomize player order if requested
  const playersToUse = config.randomizePlayerOrder 
    ? shuffleArray(config.players)
    : config.players;
  
  // Use shuffled players for stats and queue generation
  playersToUse.forEach((player) => {
    playerStats.set(player.id, createPlayerStats(player.id));
    activePlayers.add(player.id);
  });
  
  // Update config with potentially shuffled players
  const finalConfig = config.randomizePlayerOrder
    ? { ...config, players: playersToUse }
    : config;
  
  // ... rest of session creation
}
```

#### 3. UI Integration (`main.ts` and `index.html`)
- Added checkbox in advanced config section
- Checkbox state is read when "Start Session" is clicked
- Value is passed to `createSession()` via `SessionConfig`
- Setting is automatically saved/restored with session via localStorage

### Shuffle Algorithm

Uses existing `shuffleArray()` utility (Fisher-Yates shuffle):
```typescript
export function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}
```

**Properties:**
- **Unbiased**: Every permutation has equal probability
- **Time complexity**: O(n)
- **Space complexity**: O(n) (creates new array, preserves original)
- **In-place variant**: Could be optimized but clarity preferred

## Use Cases

### 1. **Social Play Sessions**
- Enable randomization to ensure variety in first-round matchups
- Prevents "usual suspects" always playing first matches
- Creates more social mixing from the start

### 2. **Fair Tournament Start**
- Randomize to avoid seeding bias in initial round
- Ensures no advantage from being added first/last
- Good for blind draw tournaments

### 3. **Testing & Development**
- Enable to test algorithm with different starting conditions
- Verify system handles various player orderings correctly
- Useful for finding edge cases

### 4. **King of the Court Mode**
- Initial matches set early rankings
- Randomization ensures ranking system starts fresh each session
- Prevents "camping" at top rankings across sessions

## Behavior Details

### What Gets Randomized
✅ **Player order** in config.players array  
✅ **Initial match assignments** (who plays first)  
✅ **Queue generation order** (for Round Robin mode)  
✅ **Statistical tracking order** (internal processing)  

### What Stays the Same
❌ **Player names/IDs** (identity preserved)  
❌ **Banned pairs** (restrictions still apply)  
❌ **Locked teams** (partnerships maintained)  
❌ **Court assignments** (courts still numbered 1-N)  
❌ **Algorithm logic** (matchmaking rules unchanged)  

### Timing
- Randomization happens **once** at session start
- Order is **fixed** for duration of session
- Subsequent rounds use algorithm-determined ordering
- Adding players mid-session: new players appended (not re-shuffled)

## Examples

### Example 1: Round Robin with 8 Players, 2 Courts

**Without randomization:**
```
Initial Order: [A, B, C, D, E, F, G, H]
Court 1: A & B vs C & D
Court 2: E & F vs G & H
```

**With randomization (example outcome):**
```
Shuffled Order: [F, C, A, H, B, G, D, E]
Court 1: F & C vs A & H
Court 2: B & G vs D & E
```

### Example 2: King of Court with 19 Players, 4 Courts

**Without randomization:**
```
Initial Order: [1, 2, 3, 4, 5, ..., 19]
Court 1: 1 & 2 vs 3 & 4
Court 2: 5 & 6 vs 7 & 8
Court 3: 9 & 10 vs 11 & 12
Court 4: 13 & 14 vs 15 & 16
Waiting: [17, 18, 19]
```

**With randomization (example outcome):**
```
Shuffled Order: [12, 5, 18, 3, 9, 1, 15, 7, 19, 2, 11, 6, 4, 14, 8, 17, 10, 13, 16]
Court 1: 12 & 5 vs 18 & 3
Court 2: 9 & 1 vs 15 & 7
Court 3: 19 & 2 vs 11 & 6
Court 4: 4 & 14 vs 8 & 17
Waiting: [10, 13, 16]
```

## Configuration Persistence

### Auto-Save Behavior
- Checkbox state is **NOT** persisted between browser sessions
- Always defaults to **unchecked** (disabled) on page load
- **Rationale**: Randomization is typically a per-session choice

### Session Save/Load
- Setting **IS** saved with active session in localStorage
- If session is loaded after page refresh, randomization setting is preserved
- Players remain in shuffled order from when session was created

### Export/Import
- Setting is included in session exports
- Imported sessions preserve the randomization flag
- **Note**: Players are already shuffled in export, re-import uses shuffled order

## Advanced Use Cases

### Custom Player Ordering
Users can still control order by:
1. **Without randomization**: Add players in desired order
2. **With randomization**: Add players in any order, let system shuffle
3. **Hybrid approach**: Strategically order some players, randomize rest (not currently supported)

### Seeded Randomization (Future Enhancement)
Could add seed input for reproducible shuffles:
```typescript
randomizePlayerOrder?: boolean;
randomSeed?: number; // Optional seed for reproducible randomization
```

Benefits:
- Reproducible sessions for testing
- Share "interesting" matchup patterns
- Replay exact session configurations

### Weighted Randomization (Future Enhancement)
Could add skill-based weighting:
```typescript
randomizePlayerOrder?: boolean;
randomizationStrategy?: 'pure' | 'skill-balanced' | 'mixed';
```

## Testing Recommendations

### Manual Testing
1. **Basic functionality:**
   - Create session with 8 players
   - Observe player order in first matches
   - Enable randomization
   - Start new session
   - Verify different order

2. **Edge cases:**
   - Test with 4 players (minimum for doubles)
   - Test with odd number (e.g., 19 players)
   - Test with locked teams enabled
   - Test with banned pairs

3. **Persistence:**
   - Start randomized session
   - Refresh page
   - Verify session loads with same order
   - End session, start new session
   - Verify checkbox resets to unchecked

### Automated Testing (Future)
```typescript
describe('Randomize Player Order', () => {
  it('should shuffle players when enabled', () => {
    const config = {
      randomizePlayerOrder: true,
      players: [/* 10 players */]
    };
    const session = createSession(config);
    // Verify order is different (statistically)
  });
  
  it('should maintain player order when disabled', () => {
    const config = {
      randomizePlayerOrder: false,
      players: [/* 10 players */]
    };
    const session = createSession(config);
    // Verify order is same as input
  });
});
```

## User Documentation

### How to Use

1. **Navigate to Setup page**
2. **Click "Advanced Configuration"** button to expand section
3. **Check "Randomize Initial Player Order"** checkbox
4. **Add your players** in any order
5. **Click "Start Session"**

Initial matches will use randomized player order!

### When to Use

**Enable randomization when:**
- ✅ You want variety in initial matchups
- ✅ Running social sessions where fairness matters
- ✅ Starting a new King of Court session
- ✅ Testing the system with different configurations

**Keep disabled when:**
- ❌ You've carefully ordered players by skill/preference
- ❌ You want consistent initial matchups for comparison
- ❌ Running a seeded tournament with specific bracket order
- ❌ You prefer traditional "first come, first serve" ordering

## Performance Impact

**Computational Cost:** Negligible
- O(n) shuffle operation where n = number of players
- Typical sessions: 10-30 players = <1ms to shuffle
- Runs once at session start only

**Memory Impact:** Minimal
- Creates one shallow copy of player array
- No additional data structures
- Same memory usage as non-randomized sessions

**User Experience:** Seamless
- No perceivable delay when starting session
- Checkbox interaction is instant
- Session starts same speed with or without randomization

## Backward Compatibility

**Existing Sessions:** ✅ Fully compatible
- Sessions created without this feature work unchanged
- `randomizePlayerOrder` is optional field (undefined = false)
- No migration needed for existing saved sessions

**Future Sessions:** ✅ Forward compatible
- Old code can load new sessions (field is ignored if not understood)
- Setting degrades gracefully to default behavior

## Summary

**Feature:** Optional randomization of initial player order at session start

**Default:** Disabled (maintains existing behavior)

**Location:** Advanced Configuration section (collapsed by default)

**Impact:** 
- ✅ Adds variety to initial matchups
- ✅ Prevents "usual suspects" always playing first
- ✅ Useful for social play and fair tournament starts
- ✅ Zero performance impact
- ✅ Fully backward compatible

**Trade-offs:**
- Players lose control over exact initial order
- May need to explain feature to confused users
- Randomization cannot be "undone" once session starts (must end and restart)

**Files Modified:**
1. `src/types.ts` - Added `randomizePlayerOrder` field to `SessionConfig`
2. `src/session.ts` - Implemented shuffle logic in `createSession()`
3. `src/main.ts` - Added checkbox reference and updated `handleStartSession()`
4. `index.html` - Added checkbox UI in advanced config section
