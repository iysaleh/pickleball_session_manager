# Court Sync Threshold - Quick Guide

## What is Court Sync Threshold?

The Court Sync Threshold determines how many courts must be busy before the algorithm waits for multiple courts to finish simultaneously. This creates variety by batching match creation.

## Default Value

**Default:** 2 courts

## How It Works

### Example with 8 Players, 2 Courts Running

**Scenario:** Court 1 finishes, Court 2 still playing

**With Court Sync Threshold = 2:**
- 4 players from Court 1 are now available
- Court 2 still has 4 players (busy court count = 1)
- Since busy courts (1) < threshold (2), create a new match immediately
- Result: Court 1 gets a new match right away

**With Court Sync Threshold = 1:**
- Same scenario
- Since busy courts (1) >= threshold (1), WAIT for Court 2 to finish
- When Court 2 finishes, all 8 players are available
- Create 2 balanced matches from all 8 players
- Result: Better variety, but players wait longer

## When to Adjust

### Increase to 3-4 (More Variety, Longer Waits)
**Best For:**
- Large sessions (16+ players)
- Groups that value variety over activity
- Sessions where players don't mind waiting

**Benefits:**
- Better variety in matchups
- More balanced court creation
- Reduces repetitive pairings

**Drawbacks:**
- Longer wait times
- Courts may sit idle temporarily
- Less activity

### Decrease to 1 (More Activity, Less Variety)
**Best For:**
- Small sessions (6-10 players)
- Groups that value constant activity
- Time-limited sessions

**Benefits:**
- Minimal wait times
- Courts always active
- Maximum games played

**Drawbacks:**
- More repetitive matchups
- Same players may play together frequently
- Less balanced court creation

## Interaction with Other Settings

### Works With
- **Min Busy Courts for Waiting** - Must have this many busy courts to consider waiting
- **Max Consecutive Waits** - Overrides sync waiting if someone waited too long
- **Min Completed Matches for Waiting** - Need this many matches before sync waiting activates

### Example Configuration for High Variety
```
Court Sync Threshold: 3
Min Busy Courts for Waiting: 2
Max Consecutive Waits: 2
```
This waits for 3 courts to finish, creating very balanced matches, but won't let anyone wait more than 2 times.

### Example Configuration for High Activity
```
Court Sync Threshold: 1
Min Busy Courts for Waiting: 1
Max Consecutive Waits: 1
```
This creates matches as soon as possible, keeping everyone active.

## Real-World Examples

### Example 1: 8 Players, 2 Courts, Threshold = 2
```
Initial: Court 1 & 2 playing (8 players)
Court 1 finishes → Creates new match immediately (4 players play again)
Court 2 finishes → Creates new match immediately (4 players play again)
Result: Same 4 players keep playing together on each court
```

### Example 2: 8 Players, 2 Courts, Threshold = 1
```
Initial: Court 1 & 2 playing (8 players)
Court 1 finishes → WAITS for Court 2
Court 2 finishes → Creates 2 new matches (all 8 players reshuffled)
Result: Better variety, all players mix together
```

### Example 3: 16 Players, 4 Courts, Threshold = 3
```
Initial: All 4 courts playing (16 players)
Court 1 finishes → WAITS (1 < 3)
Court 2 finishes → WAITS (2 < 3)
Court 3 finishes → Creates 3 new matches (12 players reshuffled)
Court 4 finishes → Creates 1 new match
Result: Good variety, reasonable wait times
```

## Mathematical Considerations

With limited player pools, perfect variety is impossible:

| Players | Courts | Rounds | Expected Max Pair Count |
|---------|--------|--------|-------------------------|
| 8       | 2      | 6      | 4-6 times              |
| 12      | 3      | 6      | 3-4 times              |
| 16      | 4      | 6      | 2-3 times              |

Higher Court Sync Threshold helps approach these theoretical minimums but can't eliminate all repetition.

## Troubleshooting

### "Same players keep playing together!"
- **Increase** Court Sync Threshold to 2 or 3
- **Increase** Min Busy Courts for Waiting to 2
- This forces the algorithm to wait for more courts to finish before creating new matches

### "Players complain about waiting too long!"
- **Decrease** Court Sync Threshold to 1
- **Decrease** Min Busy Courts for Waiting to 1
- This creates matches more aggressively, reducing wait times

### "Courts are sitting idle!"
- **Decrease** Court Sync Threshold
- Check if you have enough players for the number of courts
- Consider reducing the number of courts in use

## Advanced Tips

1. **Start Conservative:** Begin with threshold = 2 and adjust based on feedback
2. **Monitor Patterns:** Watch the first 3-4 rounds to see if variety is good
3. **Player Feedback:** Ask players if they prefer more variety or less waiting
4. **Session Size Matters:** Larger sessions benefit more from higher thresholds
5. **Time Constraints:** If session is time-limited, use lower threshold for more games

## Summary

| Setting | Variety | Wait Time | Activity | Best For |
|---------|---------|-----------|----------|----------|
| 1       | Low     | Minimal   | Maximum  | 6-10 players, time-limited |
| 2       | Medium  | Moderate  | High     | 8-16 players, balanced |
| 3       | High    | Longer    | Moderate | 16+ players, variety-focused |
| 4       | Maximum | Longest   | Lower    | 20+ players, maximum variety |

**Default of 2 is recommended for most sessions** - it provides a good balance between variety and activity.
