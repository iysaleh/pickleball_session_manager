# Advanced Configuration System - Implementation Summary

## Overview
All tuning variables for the King of the Court and Round Robin algorithms have been extracted into a comprehensive Advanced Configuration system. These settings can now be changed during an active session and will take effect immediately for future matches.

## Changes Made

### 1. Type Definitions (`src/types.ts`)

#### New Types Added:
- **`KingOfCourtConfig`**: Contains all King of the Court algorithm tuning parameters
- **`RoundRobinConfig`**: Placeholder for future Round Robin settings
- **`AdvancedConfig`**: Combined config for all game modes

#### Added to `SessionConfig`:
- `advancedConfig?: AdvancedConfig` - Optional advanced algorithm tuning

#### Added to `Session`:
- `advancedConfig: AdvancedConfig` - Always present with defaults

### 2. King of the Court Configuration Parameters

#### ELO Rating System
- **`baseRating`** (default: 1500): Starting ELO rating for new players
- **`kFactor`** (default: 32): ELO K-factor for rating adjustments (not exposed in UI)
- **`minRating`** (default: 800): Minimum rating clamp
- **`maxRating`** (default: 2200): Maximum rating clamp

#### Provisional Player Settings
- **`provisionalGamesThreshold`** (default: 2): Number of games before player stops being provisional

#### Ranking Disparity
- **`rankingRangePercentage`** (default: 0.5 = 50%): Percentage of player pool for matchmaking range
- **`closeRankThreshold`** (default: 4): Max rank difference for "close" matchups
- **`veryCloseRankThreshold`** (default: 3): Ideal rank difference for best matchups

#### Waiting Strategy
- **`maxConsecutiveWaits`** (default: 1): Max waits before forcing a match
- **`minCompletedMatchesForWaiting`** (default: 6): Min completed matches before strategic waiting
- **`minBusyCourtsForWaiting`** (default: 2): Min busy courts before considering waiting

#### Repetition Control
- **`backToBackOverlapThreshold`** (default: 3): Max overlapping players for back-to-back matches
- **`recentMatchCheckCount`** (default: 3): Number of recent matches to check (not exposed in UI)
- **`singleCourtLoopThreshold`** (default: 2): Times same group can play in recent history

#### Variety Optimization
- **`softRepetitionFrequency`** (default: 3): Target frequency for playing with same person (calculated as Math.max(3, Math.floor(totalPlayers/6)))
- **`highRepetitionThreshold`** (default: 0.6 = 60%): Percentage threshold for high repetition

#### Team Assignment Penalties (for Doubles)
- **`partnershipRepeatPenalty`** (default: 80): Penalty for repeated partnerships (all-time)
- **`recentPartnershipPenalty`** (default: 300): Heavy penalty for recent partnerships (within last 2 rounds)
- **`opponentRepeatPenalty`** (default: 25): Penalty for repeated opponents (all-time)
- **`recentOverlapPenalty`** (default: 200): Penalty for recent player overlap (3+ same players)
- **`teamBalancePenalty`** (default: 20): Penalty for unbalanced teams (win rate difference)

### 3. Code Changes

#### `src/utils.ts`
- Added `getDefaultAdvancedConfig()` function to return default configuration
- Exports default config for all game modes

#### `src/kingofcourt.ts`
- Updated `calculatePlayerRating()` to accept rating parameters
- Updated `calculatePlayerRankings()` to use session config
- Updated all matchmaking functions to accept and use `Session` parameter
- Replaced all hardcoded constants with config values:
  - `BASE_RATING`, `K_FACTOR`, `minRating`, `maxRating` → from config
  - `provisionalGamesThreshold` → from config
  - `maxConsecutiveWaits` → from config
  - `minCompletedMatchesForWaiting` → from config
  - `minBusyCourtsForWaiting` → from config
  - `backToBackOverlapThreshold` → from config
  - `singleCourtLoopThreshold` → from config
  - `highRepetitionThreshold` → from config
  - `closeRankThreshold`, `veryCloseRankThreshold` → from config
  - All penalty values → from config

#### `src/session.ts`
- Updated `createSession()` to initialize `advancedConfig` with defaults or provided config

#### `src/main.ts`
- Added `getAdvancedConfigFromInputs()` function to read UI inputs
- Added `updateSessionAdvancedConfig()` function to update active session config
- Added `setupAdvancedConfigListeners()` to listen for config changes
- Updated `handleStartSession()` to include advanced config
- Updated `restoreSessionFromLocalStorage()` to restore or default advanced config
- Updated `calculatePlayerRating()` call to use session config

### 4. User Interface (`index.html`)

#### New Advanced Configuration Section
Added comprehensive UI in the Advanced Settings section with collapsible details sections:

1. **ELO Rating System**
   - Base Rating, Min Rating, Max Rating inputs

2. **Provisional Players**
   - Games before stable ranking input

3. **Ranking Disparity Control**
   - Matchmaking range %, close rank threshold, very close rank threshold

4. **Strategic Waiting**
   - Max consecutive waits, min completed matches, min busy courts

5. **Variety & Repetition Control**
   - Back-to-back overlap, single court loop threshold, high repetition %

6. **Team Assignment Penalties (Advanced)**
   - Partnership penalty, recent partnership penalty
   - Opponent penalty, recent overlap penalty
   - Team balance penalty

All inputs have:
- Clear labels with default values shown
- Descriptive help text
- Appropriate min/max/step values
- Real-time updates to active session

## How It Works

### At Session Start
1. User opens Advanced Configuration section
2. Adjusts any desired settings (or uses defaults)
3. Starts session with those settings applied

### During Active Session
1. User can change any advanced config setting at any time
2. Changes are immediately saved to the session
3. Next match generation uses the new settings
4. Session auto-saves to localStorage with new config

### Session Restore
1. When restoring from localStorage, advanced config is restored if present
2. Falls back to default config if not found (for backward compatibility)

## Benefits

1. **Full Control**: All algorithm behavior is now tunable
2. **Live Updates**: Settings can be changed during active sessions
3. **Experimentation**: Easy to test different parameter combinations
4. **Persistence**: Settings are saved with sessions
5. **Backward Compatible**: Old sessions without config use defaults
6. **Documentation**: Each setting has clear description in UI
7. **Safety**: Appropriate min/max bounds prevent invalid values

## King of the Court Settings Organized by Section

### Settings Only Apply to King of the Court:
- All ELO Rating System settings
- Provisional player settings
- Ranking disparity settings (50% pool, close rank thresholds)
- Strategic waiting settings
- Repetition control (back-to-back, loop detection)
- Variety optimization (high repetition threshold)
- Team assignment penalties (partnership, opponent, balance)

### Settings for Round Robin:
- Currently uses default random selection
- Future expansion possible in `RoundRobinConfig` type

## Testing Recommendations

1. **ELO System**: Try different base ratings to see ranking effects
2. **Provisional Threshold**: Test with 1-5 games to see when rankings stabilize
3. **Ranking Range**: Try 25%, 50%, 75% to control matchmaking tightness
4. **Waiting Strategy**: Adjust consecutive waits to control court utilization vs quality
5. **Repetition Control**: Fine-tune overlap thresholds for variety preferences
6. **Penalties**: Adjust team assignment penalties to control partnership/opponent rotation

## Notes

- K-factor (32) and recentMatchCheckCount (3) are not exposed in UI as they are rarely changed
- softRepetitionFrequency is calculated dynamically but has a minimum floor value
- All percentage values in UI are converted to decimals (60% → 0.6) in code
- Settings changes during session apply to future matches only, not retroactively
