# King of the Court: Ranking-Based Matchmaking Algorithm

## Overview

The King of the Court mode has been completely redesigned with a sophisticated ELO-style ranking system and strict rank-based matchmaking rules. This ensures fair, competitive matches where players only face opponents within their appropriate skill bracket.

## Core Principles

### 1. ELO-Style Rating System

Instead of simple win/loss ratios, the algorithm uses a logarithmic rating system where:
- Base rating: 1500 (for new players)
- Win value depends on opponent strength
- Point differential matters (quality of wins/losses)
- Ratings range from 800-2200

**Rating Calculation Formula:**
```
rating = BASE_RATING + 
         log(1 + winRate * 9) * 200 - 200 +              // Win rate adjustment (logarithmic)
         log(1 + |avgPointDiff|) * 50 * sign(avgPointDiff) +  // Point differential
         log(gamesPlayed) * 30 (if winRate >= 0.6)        // Consistency bonus
```

This means:
- A player with 10 wins is not simply "better" than a player with 5 wins
- A player who beats strong opponents gains more rating than beating weak ones
- Close games (e.g., 11-9) are valued differently than blowouts (e.g., 11-2)

### 2. Strict Rank-Based Matchmaking (50% Rule)

Players can ONLY play with others in their half of the player pool:

**18-Player Example:**
- Rank #1 (top player) can play with: Ranks #2-#9 (top half)
- Rank #9 (middle-top) can play with: Ranks #1-#9 (top half)
- Rank #10 (middle-bottom) can play with: Ranks #10-#18 (bottom half)
- Rank #18 (bottom player) can play with: Ranks #10-#17 (bottom half)

**Why this matters:**
- Prevents mismatches (top players won't play bottom players)
- Ensures appropriate competition levels for everyone
- Top players face challenging matches
- Bottom players get fair, winnable games

### 3. Provisional Rankings

Players with fewer than 3 games played have "provisional" rankings:
- Can play with anyone (not restricted by rank brackets)
- Allows new players to be integrated into the session
- After 3 games, their true skill level emerges and restrictions apply

### 4. Close-Rank Prioritization

The algorithm actively seeks out close-rank matchups:
- Prefers players within 4 ranks of each other
- Ideal scenario: #16, #17, #18 play together (if within same bracket)
- Maximizes competitive balance within matches

### 5. Strategic Waiting

Unlike the old algorithm, this one will WAIT for better matchups:
- Won't schedule games just to keep courts busy
- Waits for other courts to finish if current players would create poor matchups
- Will schedule immediately if:
  - Someone has waited 2+ consecutive rounds (fairness override)
  - We have enough players for multiple good matches (3+ matches worth)
  - No courts are busy (first round or all idle)

### 6. Variety Within Brackets

Within rank constraints, the algorithm maximizes opponent variety:
- Prioritizes opponents you haven't faced yet
- Scores groups based on how many new pairings exist
- Balances variety with rank-based constraints

## Algorithm Flow

### Match Generation Process

1. **Calculate Rankings**
   - Compute ELO-style rating for all active players
   - Sort by rating (descending)
   - Assign ranks (#1, #2, #3, etc.)
   - Mark provisional players (< 3 games)

2. **Determine Valid Matchmaking Ranges**
   - For each player, calculate which ranks they can play with
   - Top half can only play top half
   - Bottom half can only play bottom half
   - Provisional players can play with anyone

3. **Strategic Wait Check**
   - Check if we should wait for better matchups
   - Consider: busy courts, consecutive waits, available players
   - Consider: can we make valid rank-based matches?
   - Consider: do we have close-rank matchup opportunities?

4. **Player Selection (if not waiting)**
   - Sort available players by wait priority (who needs to play most)
   - For each court, try to find compatible group:
     - **Strategy A:** Find group of closely-ranked players (within 4 ranks)
     - **Strategy B:** Find any valid group that meets rank constraints
   - Score groups based on variety and closeness

5. **Team Assignment**
   - For singles: simple 1v1
   - For doubles: optimize for partner diversity and team balance
   - Avoid recent partnerships
   - Balance teams by skill level

## Key Differences from Old Algorithm

| Aspect | Old Algorithm | New Algorithm |
|--------|---------------|---------------|
| **Ranking** | Simple win/loss ratio | ELO-style with logarithmic scaling |
| **Matchmaking** | Flexible tier system (winners/middle/losers) | Strict 50% rule - hard bracket locks |
| **Win Value** | All wins equal | Depends on opponent strength |
| **Waiting** | Avoids waiting if possible | Strategically waits for quality matchups |
| **Court Priority** | Fill all courts | Will leave courts empty for better matches |
| **Variety** | Global variety focus | Variety within rank brackets |

## Example Scenarios

### Scenario 1: New Player Joins Mid-Session

- Player #19 joins after 15 matches have been played
- Gets provisional ranking (< 3 games)
- Can play with anyone initially
- After 3 games, rating stabilizes and rank restrictions apply
- Will likely land in bottom half (new players typically lose first games)

### Scenario 2: Top Player Dominance

- Player #1 has 15W-0L record
- Rating: ~1850
- Can only play with ranks #2-#9 (top half)
- Will primarily face ranks #2-#5 (close-rank prioritization)
- This ensures continued challenging competition

### Scenario 3: Bottom Player Improvement

- Player #18 starts 0W-5L
- Rating: ~1200
- Can only play with ranks #10-#17
- Wins a few games against similar skill level
- Rating improves to ~1400
- Moves up to rank #15
- Still in bottom half, but now faces slightly better competition

### Scenario 4: Strategic Waiting

- 4 courts, 18 players
- Courts 1-3 have matches in progress
- 6 players waiting:
  - 3 from top bracket (#2, #4, #6)
  - 3 from bottom bracket (#14, #16, #18)
- Algorithm recognizes: Can only make 1 match (either top or bottom group)
- Decision: **WAIT** for more courts to finish
- Why: Better to wait and make 2 good matches (one top, one bottom) than rush 1 match

## Configuration Constants

```typescript
BASE_RATING = 1500         // Starting ELO for new players
K_FACTOR = 32             // ELO adjustment factor (not currently used but available)
PROVISIONAL_GAMES = 3     // Games needed before rank restrictions apply
CLOSE_RANK_THRESHOLD = 4  // Ranks within this are "close"
MAX_CONSECUTIVE_WAITS = 2 // Override rank rules after this many waits
```

## Testing

All existing King of the Court unit tests pass with the new algorithm:
- ✅ Equal play time distribution
- ✅ Avoid long idle times
- ✅ Maximize opponent variety (within brackets)
- ✅ Partner diversity (doubles)
- ✅ Handle player joining/leaving
- ✅ Handle odd number of players
- ✅ Singles mode support
- ✅ Banned pairs respect

## Benefits

### For Top Players
- Always face challenging competition
- No "easy" matches against bottom players
- True skill development through appropriate challenge

### For Middle Players
- Balanced competition
- Can work their way up or down based on performance
- Not overwhelmed by top players or bored by bottom players

### For Bottom Players
- Fair, winnable games
- Not humiliated by facing top players
- Can improve at appropriate pace

### For Session Organizers
- Professional-quality matchmaking
- Fair competition for all skill levels
- Reduced complaints about unfair matches
- True competitive structure

## Limitations & Trade-offs

1. **May have more idle time**: Algorithm prioritizes quality over quantity
2. **Requires critical mass**: Works best with 12+ players
3. **Initial volatility**: First few rounds may have more variation as ratings stabilize
4. **Strict boundaries**: Some players may feel restricted in who they can play

## Future Enhancements

Potential improvements for future versions:
- Configurable bracket size (currently 50%, could be 40% or 60%)
- K-factor adjustments based on rating confidence
- Team-based ELO for locked teams mode
- Rating decay over time (favor recent performance)
- Separate ratings for singles vs doubles
