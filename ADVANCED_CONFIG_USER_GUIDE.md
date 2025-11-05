# Advanced Configuration - User Guide

## Overview
The Advanced Configuration feature allows you to fine-tune the King of the Court matchmaking algorithm to suit your specific needs. All settings can be adjusted before starting a session or even during an active session.

## Accessing Advanced Configuration

1. On the **Setup** page, look for the **⚙️ Advanced Configuration** button
2. Click to expand the advanced settings section
3. Scroll through the collapsible sections to find the settings you want to adjust

## Configuration Sections

### 1. General Settings
- **Randomize Initial Player Order**: Shuffles players randomly at session start
- **Max Queue Size**: Controls how many matches to pre-generate (for Round Robin)

### 2. King of the Court Settings

#### ELO Rating System
**What it does**: Controls how players are ranked based on their performance

- **Base Rating** (default: 1500): Starting rating for new players
  - Lower = easier to move up from new player status
  - Higher = new players start with more "established" rating
  
- **Minimum/Maximum Rating**: Bounds for ratings
  - Prevents ratings from going too low or too high
  - Default range: 800-2200

**When to adjust**: 
- If new players dominate, lower base rating
- If you want tighter rating compression, narrow the min/max range

#### Provisional Players
**What it does**: Determines when a player's ranking becomes stable

- **Games Before Stable Ranking** (default: 2): Number of games before rankings are trusted
  - Lower = rankings stabilize faster
  - Higher = more games needed before matchmaking constraints apply

**When to adjust**:
- Set to 1 for very small sessions (6-8 players)
- Set to 3-5 for large sessions where you want more data before ranking

#### Ranking Disparity Control
**What it does**: Controls how big the skill gap can be in matches

- **Matchmaking Range %** (default: 50%): Percentage of pool that can play together
  - 50% = Top half plays with top half, bottom half with bottom half
  - 100% = Anyone can play with anyone (no ranking constraints)
  - 25% = Very tight constraints (top quarter only plays top quarter)

- **Close Rank Threshold** (default: 4): Max rank difference for acceptable matches
- **Very Close Rank Threshold** (default: 3): Ideal rank difference for best matches

**When to adjust**:
- **For more variety**: Increase matchmaking range to 75-100%
- **For competitive balance**: Keep at 50% or lower to 25%
- **For social play**: Increase close rank threshold to 6-8

#### Strategic Waiting
**What it does**: Controls when players wait for better matchups vs playing immediately

- **Max Consecutive Waits** (default: 1): Times a player can wait before forced into match
  - 0 = Never wait, always play when court available
  - 2-3 = Allow more waiting for better matchups

- **Min Completed Matches** (default: 6): Matches needed before waiting begins
  - Lower = Start waiting strategy sooner
  - Higher = Fill courts aggressively at session start

- **Min Busy Courts** (default: 2): Courts that must be busy before waiting
  - Lower = More willing to wait
  - Higher = Keep all courts full

**When to adjust**:
- **More courts available**: Lower min busy courts
- **Fewer players**: Increase max consecutive waits to 0
- **Want faster rotation**: Set max consecutive waits to 0

#### Variety & Repetition Control
**What it does**: Prevents players from playing with/against same people repeatedly

- **Back-to-Back Overlap** (default: 3): Max same players in consecutive matches
  - 3 = Prevent same 3+ players in a row
  - 4 = Allow everyone to play again immediately
  - 2 = Very strict, maximum variety

- **Single Court Loop Threshold** (default: 2): Times same group can play in last 10 matches
  - Lower = More variety enforcement
  - Higher = Allow more repetition

- **High Repetition %** (default: 60%): When to consider matchup "too repetitive"
  - Lower = Stricter variety requirements
  - Higher = Allow more same-person matchups

**When to adjust**:
- **Small groups**: Increase thresholds (players will repeat regardless)
- **Large groups**: Decrease thresholds for maximum variety
- **Fast rotation desired**: Increase all thresholds

#### Team Assignment Penalties (Doubles Only)
**What it does**: Controls how teams are formed in doubles matches

These are "penalty points" - higher = more avoided, lower = more allowed

- **Partnership Repeat Penalty** (default: 80): For partners who've played together before
- **Recent Partnership Penalty** (default: 300): For partners who played together recently
- **Opponent Repeat Penalty** (default: 25): For opponents who've faced before
- **Recent Overlap Penalty** (default: 200): For 3+ same players in recent match
- **Team Balance Penalty** (default: 20): For unbalanced team win rates

**When to adjust**:
- **Want more partner variety**: Increase partnership penalties to 150-200
- **Prefer consistent partners**: Decrease partnership penalties to 20-40
- **More opponent variety**: Increase opponent penalty to 50-100
- **Balanced matches priority**: Increase team balance penalty to 50-80

## Quick Presets

### Competitive / Skill-Based
```
Matchmaking Range: 50% or 25%
Close Rank Threshold: 3
Max Consecutive Waits: 1-2
Team Balance Penalty: 40-50
```

### Social / Variety-Focused
```
Matchmaking Range: 75-100%
Close Rank Threshold: 6-8
Back-to-Back Overlap: 2
Partnership Penalties: 150-200
High Repetition: 40%
```

### Fast Rotation / High Throughput
```
Max Consecutive Waits: 0
Min Busy Courts: 1
All Thresholds: Higher (4, 3, 70%)
```

### Small Group (6-10 players)
```
Matchmaking Range: 100%
Provisional Games: 1
All Repetition Controls: Relaxed (4, 3, 80%)
```

## Tips

1. **Start with defaults** - They work well for most scenarios
2. **Adjust one thing at a time** - See the effect before changing more
3. **Watch the waiting area** - If players wait too much, relax constraints
4. **Check match history** - Look for patterns to identify what to tune
5. **Settings persist** - Your changes save with the session
6. **Changes apply immediately** - Adjust during active sessions!

## Common Issues and Solutions

### "Players keep waiting"
- Increase matchmaking range percentage
- Decrease max consecutive waits to 0
- Increase close rank threshold

### "Same people playing together"
- Decrease high repetition threshold
- Increase partnership/opponent penalties
- Decrease back-to-back overlap threshold

### "Unbalanced matches"
- Decrease matchmaking range to 50% or 25%
- Increase team balance penalty
- Decrease close rank threshold

### "Courts sitting empty"
- Set max consecutive waits to 0
- Set min busy courts to 1
- Increase all thresholds

## Notes

- Round Robin mode doesn't use most of these settings (uses simple rotation)
- Settings only affect **future** matches, not past ones
- Changes auto-save with your session
- Restoring a session restores its configuration
