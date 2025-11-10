# King of the Court Algorithm Improvements

## Problem Statement

The previous King of the Court algorithm used a **pure continuous flow** approach - it would schedule games immediately whenever any court became available and there were enough waiting players. While this minimized court idle time, it led to several issues:

1. **Repetitive Matchups**: The same players would constantly play each other
2. **Poor Variety**: Limited diversity in opponents and partners
3. **Skill Imbalance**: Winners would sometimes face losers due to availability timing

## Solution: Strategic Continuous Flow

The improved algorithm balances **continuous flow** with **strategic waiting** for better matchups.

### Key Changes

#### 1. Categorize Players by Win Rate
Players are categorized into three tiers based on performance:
- **Winners**: Win rate ≥ 60%
- **Middle**: Win rate between 40-60% (or new players)
- **Losers**: Win rate ≤ 40%

#### 2. Strategic Waiting Logic
The algorithm decides whether to schedule immediately or wait based on:

**Wait if:**
- Multiple courts are available (2+)
- Some courts are still busy (not first round)
- No player has waited 3+ consecutive rounds
- Available players are too homogeneous (e.g., only winners OR only losers)

**Schedule immediately if:**
- No courts are busy (first round or all courts idle)
- Only 1 court available
- Someone has waited 3+ consecutive rounds
- Good mix of skill levels available

#### 3. Balanced Player Selection
When scheduling, the algorithm tries to select players from different skill tiers:
- Mix winners with middle/losers
- Avoid all-winner vs all-loser matchups
- Ensure variety while maintaining competitiveness

### Algorithm Flow

```
1. Check available courts and players
2. Categorize players by win rate (winners/middle/losers)
3. Determine if we should wait for better matchups:
   - If yes: Return empty array (no new matches)
   - If no: Continue to step 4
4. Select players strategically (mix of skill levels)
5. Assign teams to maximize partner variety
6. Create balanced matchups
7. Schedule matches on available courts
```

### Benefits

✅ **Better Variety**: Players face more diverse opponents
✅ **Balanced Competition**: Winners play winners, but not exclusively
✅ **Fair Waiting**: Strategic waiting applies to everyone equally
✅ **Skill-Based Matching**: Similar skill levels compete while maintaining variety
✅ **Continuous Flow**: Still generates matches dynamically (not strict rounds)

### Example Scenario

**Setup**: 12 players, 3 courts

**Old Behavior**:
- Court 1 finishes → Immediately schedule next 4 available players
- Court 2 finishes → Immediately schedule next 4 available players
- Court 3 finishes → Immediately schedule next 4 available players
- Result: Same 4 players might play together multiple times in a row

**New Behavior**:
- Court 1 finishes → Wait to see who else becomes available
- Court 2 finishes → Now we have 8 players waiting
- Algorithm: Mix 4 winners + 4 middle-tier players → Schedule 2 balanced games
- Court 3 finishes → Mix remaining players + newly available
- Result: More variety, better matchups, winners play winners appropriately

### Test Results

All 21 King of the Court tests pass, including:
- ✅ Equal play time distribution
- ✅ No excessive consecutive waits
- ✅ Partner diversity maximization
- ✅ Opponent variety
- ✅ Balanced team creation
- ✅ Skill-based matchmaking
- ✅ Deterministic scheduling

### Court Numbers Are Arbitrary

Unlike traditional "King of the Court" where court 1 is the "top" court and winning promotes you up:
- **This algorithm**: Court numbers don't matter for ranking
- **What matters**: Matching players with similar win rates
- **Philosophy**: Winners play winners regardless of which physical court

This design choice allows for:
- Better variety (players don't get stuck on one court)
- More flexible scheduling
- Focus on competitive balance over positional hierarchy

## Configuration

The strategic waiting thresholds can be tuned:
- Max consecutive waits before forcing scheduling: **3 rounds**
- Minimum available courts to consider waiting: **2 courts**
- Win rate thresholds: Winners (≥60%), Middle (40-60%), Losers (≤40%)

These values are optimized for typical pickleball session sizes (8-16 players, 2-4 courts).
