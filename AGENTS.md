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

**Candidate Pool Optimization (Smart Performance Scaling)**
- Balances wait time fairness, ELO quality, and computational performance
- **Small sessions (≤16 players)**: Uses ALL available players as candidates (no limitation)
- **Large sessions (17+ players)**: Limits to top 12-16 candidates using priority system
- Prevents combinatorial explosion: C(24,4)=10,626 → C(16,4)=1,820 (83% reduction)
- Prioritizes candidates by wait time tiers: Extreme (20+ min) → Significant (12+ min) → Normal
- **First round exception**: Uses all players to ensure court filling when everyone has equal priority
- Automatic scaling: `max_candidates = min(16, max(12, available_players // 2))`

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
- **First round detection**: Uses randomized player order + all available players as candidates
- **Later rounds**: Uses candidate pool optimization with wait time prioritization
- Prioritizes locked teams
- Integrates with sophisticated candidate pool system from wait_priority module
- **Adaptive constraints**: Automatically adjusts repetition constraints based on session progression

**get_adaptive_constraints(session) → (partner_constraint, opponent_constraint)**
- Calculates current repetition constraints based on player game progression
- Returns dynamically adjusted constraints (3→2→1 for partners, 2→1→1 for opponents)
- Uses average games played across all players to determine phase
- Ensures minimum constraint of 1 (never allows back-to-back repetition)

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

5. **CANDIDATE POOL OPTIMIZATION**: 
   - Small sessions (≤16 players): Uses ALL available players (no performance concerns)
   - Large sessions (17+ players): Uses top 12-16 candidates by wait priority
   - Automatic scaling prevents O(n^4) combinatorial explosion
   - First round bypass: Uses all players when everyone has equal priority
   - Ensures fairness (longest waiters first) while maintaining performance

6. **FIRST ROUND RANDOMIZATION**:
   - Player order is randomized in first round to ensure variety between sessions
   - Later rounds use deterministic order for consistency
   - Detection: `completed_matches = [m for m in session.matches if m.status == 'completed']`
   - When `len(completed_matches) == 0`, randomize available player order

7. **WAIT PRIORITY INTEGRATION**: 
   - Uses sophisticated wait time priority system (python/wait_priority.py)
   - Candidates selected via `get_priority_aware_candidates()` which prioritizes actual wait time
   - Integrates seamlessly with candidate pool optimization system
   - Maintains backward compatibility with legacy `games_waited` counter

8. **ADAPTIVE CONSTRAINT SYSTEM**:
   - Dynamically relaxes repetition constraints as sessions progress to improve match balance
   - Uses player-based progression instead of hardcoded match counts
   - Three phases: Early (full constraints), Mid (partner: 2→1, opponent: 2→1), Late (partner: 1→1, opponent: 1→1)
   - Thresholds based on average player game counts:
     - Mid phase: After players average 4+ games (2 provisional + 2 regular)
     - Late phase: After players average 6+ games (2 more games beyond mid)
   - GUI slider shows current phase and allows manual override
   - NEVER reduces constraints below 1 (back-to-back prevention always maintained)
   - Preserves skill-based roaming ranges (quality over quantity)

## WAIT TIME PRIORITY SYSTEM (python/wait_priority.py)

### Core Purpose
Implements sophisticated wait time priority logic that considers actual accumulated wait time rather than simple game counts. Ensures players who have waited significantly longer are prioritized for match placement while avoiding micro-optimization for small time differences.

### Key Features

**Time-Based Priority Calculation**
- Uses `total_wait_time` + `current_wait_seconds` for accurate priority
- Replaces legacy `games_waited` as primary priority metric
- Maintains `games_waited` as fallback/tiebreaker for backward compatibility

**Gap-Based Threshold System**
- MINIMUM_PRIORITY_GAP_SECONDS = 120 (2 minutes) - differences smaller than this are ignored
- SIGNIFICANT_GAP_SECONDS = 720 (12 minutes) - players who waited 12+ minutes longer than shortest waiter become "significant"
- EXTREME_GAP_SECONDS = 1200 (20 minutes) - players who waited 20+ minutes longer than shortest waiter become "extreme"
- Thresholds are calculated as fixed time gaps from the shortest waiter, not absolute times
- Only prioritizes wait differences when they exceed meaningful fixed gaps

**Priority Tiers**
- Tier 0 (Extreme): 20+ minutes longer than shortest waiter - highest priority (⚠️ indicator)
- Tier 1 (Significant): 12-20 minutes longer than shortest waiter - high priority (⏰ indicator)  
- Tier 2 (Normal): < 12 minutes longer than shortest waiter - standard priority

### Critical Functions

**calculate_wait_priority_info(session, player_id) → WaitPriorityInfo**
- Central calculation point for all wait priority data
- Returns comprehensive priority information including tier assignment
- Combines historical `total_wait_time` + current session wait time

**get_priority_aware_candidates(session, available_players, max_candidates=16) → List[str]**
- Intelligent candidate selection for match generation
- Prioritizes extreme waiters first, then significant, then normal
- Used by competitive variety algorithm for player selection

**sort_players_by_wait_priority(session, player_ids, reverse=True) → List[str]**
- Flexible sorting with time-based priority
- Primary key: Priority tier (0=extreme > 1=significant > 2=normal)
- Secondary key: Total wait time within tier
- Tertiary key: Legacy `games_waited` counter (backward compatibility)

**should_prioritize_wait_differences(wait_infos) → bool**
- Implements threshold logic to determine when wait differences matter
- Returns False if all players within 2-minute range (avoids micro-optimization)
- Returns True if any extreme/significant waiters or large gaps exist

### Integration Points

**Competitive Variety Algorithm**
- `populate_empty_courts_competitive_variety()` uses `get_priority_aware_candidates()`
- Maintains all existing constraints (ELO brackets, repetition rules, etc.)
- Preserves match quality while prioritizing wait time

**GUI System** 
- Waitlist display shows priority indicators (⚠️ extreme, ⏰ significant)
- Manual match creation uses `sort_players_by_wait_priority()`
- Time formatting via `format_wait_time_display()` (e.g., "15m 30s", "1h 20m")

**Session Management**
- Legacy `games_waited` counter still incremented for backward compatibility
- Wait timers (`start_player_wait_timer`, `stop_player_wait_timer`) accumulate to `total_wait_time`
- Seamless integration with existing persistence and serialization

## ADAPTIVE CONSTRAINTS SYSTEM (python/competitive_variety.py)

### Core Purpose
The adaptive constraints system intelligently relaxes variety constraints (partner/opponent repetition) as sessions progress to improve match balance quality. It dynamically adjusts based on player count and average games played, ensuring variety constraints are relaxed gradually and never completely eliminated.

### Key Features

**Dynamic Threshold Calculation**
- Early → Mid: Each player has played 4 games on average
- Mid → Late: Each player has played 6 games on average  
- Thresholds scale with player count: `threshold = (player_count * target_games_per_player) / 4`
- Example: 16 players → Early→Mid at 16 matches, Mid→Late at 24 matches

**Progressive Constraint Relaxation**
- **Early phase**: Standard constraints (partner: 3 games, opponent: 2 games), 1.0x balance weight
- **Mid phase**: Reduced constraints (partner: 2 games, opponent: 1 game), 3.0x balance weight
- **Late phase**: Minimal constraints (partner: 1 game, opponent: 1 game), 5.0x balance weight
- **NEVER goes to 0**: Maintains minimum 1-game gaps to prevent back-to-back repetition

**GUI Slider Control**
- Position 0: **NONE** - Disables adaptive constraints entirely (maintains standard Early phase settings)
- Position 1: **AUTO** - Automatic progression based on session progress (default behavior)
- Positions 2-5: **Manual Override** - Fixed balance weights (2.0x, 3.0x, 5.0x, 8.0x)
- Status display shows current phase and effective balance weight

### Critical Functions

**get_adaptive_constraints(session) → Dict**
- Returns current constraints based on session progression or manual override
- Handles disabled state when `session.adaptive_constraints_disabled = True`
- Never allows constraints to go to 0 (minimum partner: 1, opponent: 1)

**get_adaptive_phase_info(session) → Dict**
- Provides comprehensive information about current adaptive state
- Includes phase name, auto weight, effective weight, and progression thresholds
- Returns "Disabled" phase when adaptive constraints are turned off

**calculate_session_thresholds(session) → Dict**
- Computes dynamic thresholds based on player count
- Formula: `(player_count * games_per_player) / 4` matches per threshold
- Ensures thresholds scale appropriately with session size

### Slider Behavior Design

**User Experience Philosophy**
- Variety slider (user preference) **remains unchanged** when adaptive constraints activate
- Adaptive constraints slider shows **current state** and allows manual control
- Clear separation between user preferences and automatic system adjustments

**State Management**
- NONE (0): `adaptive_constraints_disabled = True` - System completely disabled
- AUTO (1): `adaptive_balance_weight = None` - Automatic progression active
- Manual (2-5): `adaptive_balance_weight = [2.0, 3.0, 5.0, 8.0]` - Fixed override

**Status Display Examples**
- AUTO mode: "Auto: Mid (3.0x)" - Shows automatic phase and weight
- Manual mode: "Manual: 5.0x" - Shows fixed override weight  
- Disabled: "Disabled" - Adaptive system completely off

### Integration with Balance Algorithm

The balance weight multiplier affects how strongly the matching algorithm prioritizes ELO balance versus variety constraints:
- 1.0x: Standard balance consideration
- 3.0x: 3× more weight given to skill balance in match selection
- 5.0x: 5× more weight - aggressively prioritizes balanced matches
- 8.0x: Maximum balance priority - will accept more repetition for better skill balance

### Testing & Validation
- `test_adaptive_slider.py`: Comprehensive slider functionality testing
- `test_disabled_adaptive.py`: Validates disabled state behavior
- Fuzzing tests: `make run_fuzz_tests` validates constraint enforcement

### Threshold Logic Examples

- **15 players all waited 2-4 minutes**: Algorithm treats equally, no micro-optimization (gaps < 12 min)
- **13 players waited 2-4 minutes + 2 players waited 16+ minutes**: Prioritizes the 2 long waiters (12+ min gap)
- **Players who waited 20+ minutes longer than shortest**: Get extreme priority with visual indicators
- **Context-aware gaps**: If shortest wait is 1 minute, 21+ minutes = extreme. If shortest is 10 minutes, 30+ minutes = extreme

### Testing & Validation
Run fuzzing tests with: `make run_fuzz_tests`
Wait priority specific tests: `make test_wait_priority test_wait_priority_integration`

Critical test files:
- test_competitive_variety_fuzzing.py: fuzz tests with random player counts/constraints
- test_enhanced_mixing.py: validates variety enforcement
- test_roaming_range_enforcement.py: roaming range specific tests
- test_wait_priority_system.py: comprehensive wait priority system validation
- test_wait_priority_integration.py: integration testing with existing systems
- test_adaptive_matchmaking.py: validates adaptive constraint system behavior
- test_adaptive_slider.py: tests GUI slider integration and manual override functionality
