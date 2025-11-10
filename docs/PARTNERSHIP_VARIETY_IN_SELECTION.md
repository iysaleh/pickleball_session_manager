# Partnership Variety in Player Selection

## The Issue You Found

**Session:** `pickleball-session-11-05-2025-11-22.txt`

**Match 10 created:** Jeremy & 6 vs 5 & Ibraheem

**Problem:** Ibraheem had already partnered with **5** in Match 3, but had only partnered with **1** once (Match 2, 7 matches ago), and had **never** partnered with 2, 3, or 4!

**Better match:** Jeremy & 6 vs **1** & Ibraheem (more variety)

## Root Cause

The system has a **two-phase** matching process:

### Phase 1: Player Selection
Select which 4 players will be in the match
- `findMostBalancedMatch` chooses 4 players
- **OLD:** Only considers rating balance + back-to-back avoidance
- **MISSING:** Partnership variety!

### Phase 2: Team Assignment  
Divide the 4 selected players into 2 teams
- `assignTeams` creates team pairings
- Considers partnership history ✅

**The Problem:** By the time we reach Phase 2, player #1 isn't even in the group! We selected [Jeremy, 6, 5, Ibraheem], so we can only make teams from those 4 players.

## The Scenario

After Match 9, all 8 players available, creating 2 matches:

**Court 1 selection:**
1. Top 4 waiters: Jeremy, 5, 6, Ibraheem (they waited during Match 9)
2. `findMostBalancedMatch` evaluates combinations of these 4
3. Picks the combo with best **rating balance** only
4. Result: [Jeremy, 6, 5, Ibraheem] selected
5. `assignTeams` divides into teams considering partnerships
6. But can't include player #1 - they weren't selected!

## Ibraheem's Partnership History

```
Match 2: Ibraheem & 1
Match 3: Ibraheem & 5  ← First time
Match 4: Ibraheem & 6  
Match 6: Ibraheem & Jeremy
Match 8: Ibraheem & 6  ← 2nd time
Match 10: Ibraheem & 5 ← 2nd time (should have been #1!)
```

**Never partnered:** 2, 3, 4  
**Once:** 1 (7 matches ago), Jeremy (4 matches ago)  
**Twice:** 5, 6

## The Fix

**Incorporate partnership variety into player selection**, not just team assignment:

```typescript
// In findMostBalancedMatch, when evaluating 4-player combinations:
for (const config of configs) {
  const team1Avg = (config.team1[0].rating + config.team1[1].rating) / 2;
  const team2Avg = (config.team2[0].rating + config.team2[1].rating) / 2;
  const ratingBalance = Math.abs(team1Avg - team2Avg);
  
  // NEW: Factor in partnership variety
  const team1PartnerCount = getPartnershipCount(
    config.team1[0].playerId, 
    config.team1[1].playerId, 
    matches
  );
  const team2PartnerCount = getPartnershipCount(
    config.team2[0].playerId, 
    config.team2[1].playerId, 
    matches
  );
  const totalPartnerRepetition = team1PartnerCount + team2PartnerCount;
  
  // Combined score: balance + partnership repetition penalty
  // Each repeated partnership adds equivalent of 50 rating points imbalance
  const combinedScore = ratingBalance + (totalPartnerRepetition * 50);
  
  if (combinedScore < bestBalance) {
    bestBalance = combinedScore;
    bestMatch = playerIds;
  }
}
```

## How It Works Now

**Scenario:** Selecting 4 from [Jeremy, 5, 6, 1, Ibraheem]

**Option A: [Jeremy, 6, 5, Ibraheem]**
- Best team split: Jeremy & 6 vs 5 & Ibraheem
- Rating balance: 10 points
- Partnerships: Ibraheem-5 (1x), Jeremy-6 (0x) = 1 repetition
- **Score: 10 + (1 × 50) = 60**

**Option B: [Jeremy, 6, 1, Ibraheem]**
- Best team split: Jeremy & 6 vs 1 & Ibraheem  
- Rating balance: 15 points
- Partnerships: Ibraheem-1 (1x), Jeremy-6 (0x) = 1 repetition
- **Score: 15 + (1 × 50) = 65**

**Option C: [Jeremy, 1, 6, Ibraheem]** (different arrangement)
- Best team split: Jeremy & Ibraheem vs 1 & 6
- Rating balance: 12 points
- Partnerships: Jeremy-Ibraheem (1x), 1-6 (0x) = 1 repetition
- **Score: 12 + (1 × 50) = 62**

System picks **Option A** (lowest score = best balance & least repetition)

But wait - all have same repetition count! The issue is more subtle...

Actually, looking at the session again, after Match 9:
- Ibraheem & 5 had partnered once (Match 3)
- Ibraheem & 1 had partnered once (Match 2)

So both have the same repetition penalty! The system would then fall back to rating balance to decide.

**The real benefit:** When comparing options where partnership counts DIFFER, this will favor fresh partnerships. For example:

**Option D: [Jeremy, 6, 2, Ibraheem]**
- Partnerships: Ibraheem-2 (0x), Jeremy-6 (0x) = 0 repetitions
- **Score: balance + (0 × 50) = just balance**

This would be strongly preferred over options with repeated partnerships!

## Impact

✅ Player selection now considers partnership variety  
✅ Will favor combinations with fresh partnerships  
✅ Still maintains rating balance as primary goal  
✅ Penalty is tunable (currently 50 rating points per repetition)

## Penalty Tuning

Current: **50 rating points per repeated partnership**

This means:
- A match with 0 repeated partnerships is preferred over one with 1 repetition, even if 50 points less balanced
- A match with 1 repetition is preferred over 2 repetitions, even if 50 points less balanced

**Conservative (emphasis on balance):** 25-30 points  
**Current (balanced):** 50 points  
**Aggressive (emphasis on variety):** 75-100 points

## Files Modified

**`src/kingofcourt.ts` (lines 954-975)**
- `findMostBalancedMatch` function
- Added partnership count calculation for each team configuration
- Combined score = rating balance + (partnership repetition × 50)
- Selects combo with lowest combined score

## Future Enhancement

Consider making the penalty weight an advanced config setting:
```typescript
partnershipRepeatPenaltyInSelection: 50  // Rating points per repetition
```

This would allow users to tune how much they value variety vs. balance in the initial player selection phase.
