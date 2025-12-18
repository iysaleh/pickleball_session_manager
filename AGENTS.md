# Custom Instructions for Claude

## Repository Rules

- We are only working on the python code right now, not the javascript version of the app. Do not write any implementation documentation or summary files in any format (text , markdown). Do not use EOF syntax to write temporary test files, instead just write the test file and run the test separately. Persist the tests.
- You don't need to cd to the "pickleball_python_rework" directory to run tests or any python code, that is the current working directory you are in. Commands like `cd "C:\Users\Ibraheem Saleh\Documents\ProjectDevelopment\pickleball_rework_python" && python test_court_dropdowns.py 2>&1` only need the 2nd part: `python test_court_dropdowns.py 2>&1`
- Whenever you change something related to the Competitive Variety Matchmaking algorithm, you always run the fuzzing tests for it: `make run_fuzz_tests`
- Tests built should have a make target added for them in the Makefile (Do not create new makefiles just for new tests, use the existing Makefile). Always run tests from their make targets, do not tail the output of tests that are run, just parse the entire output (or grep for what you care about!)
- Do not prompt me to run the tests, always run the tests without prompting me. Run the tests without the tail command.

## COMPETITIVE VARIETY ALGORITHM (python/competitive_variety.py)

### Core Purpose
This module implements an ELO-based skill-balanced matchmaking system with hard variety constraints. It ensures fair, diverse matches while preventing excessive partner/opponent repetition.

### Key Concepts

**ELO Rating System (calculate_elo_rating)**
- BASE_RATING: 1500
- MIN/MAX: 800-2200
- Formula combines:
  - Win rate (logarithmic scaling: log(1 + winRate * 9) * 200 - 200)
  - Point differential bonus (log(1 + |avgPointDiff|) * 50 * sign)
  - Consistency bonus for strong players (win_rate >= 0.6: log(games) * 30)
- Players with < 2 games are PROVISIONAL (no restrictions, can play anyone)

**Hard Repetition Constraints** (CRITICAL - never violate)
- PARTNER_REPETITION_GAMES_REQUIRED = 3 (must wait 3 games before re-partnering)
- OPPONENT_REPETITION_GAMES_REQUIRED = 2 (must wait 2 games before facing again)
- TWO-PHASE CHECK in can_play_with_player():
  1. Global Recency: Last X completed matches globally forbid the pairing
  2. Player-Specific History: Count INTERVENING games (gaps) in that player's personal history
  - For 8+ players: enforces the full constraints
  - For < 8 players: enforces minimum 1-game gap (back-to-back prevention)

**Roaming Range (50% Moving Window Rule)**
- Only applies with 12+ players
- Each player can match with others within ± 50% of total active players
- Example: 16 players, rank #1 → can play with ranks 1-9 (1 ± 8)
- Provisional players have NO roaming restrictions
- Used by: get_roaming_rank_range(), can_play_with_player()

**Locked Teams & Banned Pairs**
- Locked teams MUST be partners (override repetition constraints)
- Locked teams CANNOT be opponents
- Banned pairs cannot be partners
- Checked FIRST in can_play_with_player()

### Critical Functions

**get_roaming_rank_range(session, player_id) → (min_rank, max_rank)**
- Returns the skill-based roaming window for a player
- Enforces the 50% moving window rule
- Returns (1, total_players) for < 12 players (no restriction)

**can_play_with_player(session, player1, player2, role, allow_cross_bracket=False) → bool**
- THE GATEKEEPER: checks if two players can play together
- role = 'partner' or 'opponent'
- allow_cross_bracket: when True, relaxes roaming range checks (used in fallback matching)
- Order of checks:
  1. Locked teams (hard enforced)
  2. Banned pairs (hard enforced)
  3. Roaming range compatibility (if 12+ players & competitive-variety mode)
  4. Global recency check (last N games globally)
  5. Player-specific history check (intervening games in personal history)

**populate_empty_courts_competitive_variety(session)**
- Main court-filling function
- Two-stage process:
  1. Try queued matches first (respects waitlist)
  2. Generate new matches from available players
- Prioritizes locked teams
- Uses combination search with two passes: strict bracketing, then relaxed
- Takes top 12-16 candidates sorted by wait time/priority

**_can_form_valid_teams(session, players, allow_cross_bracket=False) → bool**
- Helper: checks if 4 players can form ANY valid team configuration
- Tries all 3 possible pairings: (0,1)v(2,3), (0,2)v(1,3), (0,3)v(1,2)
- Returns True if ANY configuration works

**can_players_form_match_together(session, player_ids) → bool**
- Public API: checks if 4 specific players can match
- First checks roaming range for all players together
- Then tries all team configurations

### Important Invariants & Gotchas

1. **INTERVENING GAMES CALCULATION**: 
   - Formula: `intervening = current_personal_count - last_index - 1`
   - Index 0, count 1 → gap = 0 (back-to-back)
   - Index 0, count 2 → gap = 1 (1 game between)

2. **PROVISIONAL PLAYERS**: 
   - Always pass roaming/bracket checks
   - Still blocked by repetition constraints with non-provisionals
   - Get full restrictions once they play 2 games

3. **ALLOW_CROSS_BRACKET FLAG**: 
   - Used only in populate_empty_courts() for fallback matching
   - When True, skips roaming range checks to find ANY valid match
   - Must still respect repetition constraints

4. **LOCKED TEAMS BYPASS PARTNER REPETITION**: 
   - Line 335-336: locked partners return True immediately, skipping repetition checks
   - This is intentional - locked teams are exempt

5. **COMBINATION SEARCH LIMITS**: 
   - Limited to 12-16 top-priority candidates to prevent O(n^4) slowness
   - Candidates sorted by wait time first, then ELO
   - Does NOT sort primary candidate list by ELO (preserves priority ordering)

### Testing & Validation
Run fuzzing tests with: `make run_fuzz_tests`
Critical test files:
- test_competitive_variety_fuzzing.py: fuzz tests with random player counts/constraints
- test_enhanced_mixing.py: validates variety enforcement
- test_roaming_range_enforcement.py: roaming range specific tests
