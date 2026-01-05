# Custom Instructions for Claude

## Repository Rules

- We are only working on the python code right now, not the javascript version of the app. Do not write any implementation documentation or summary files in any format (text , markdown). Do not use EOF syntax to write temporary test files, instead just write the test file and run the test separately. Persist the tests.
- You don't need to cd to the "pickleball_python_rework" directory to run tests or any python code, that is the current working directory you are in. Commands like `cd "C:\Users\Ibraheem Saleh\Documents\ProjectDevelopment\pickleball_rework_python" && python test_court_dropdowns.py 2>&1` only need the 2nd part: `python test_court_dropdowns.py 2>&1`
- Whenever you change something related to the Competitive Variety Matchmaking algorithm, you always run the fuzzing tests for it: `make run_fuzz_tests`
- Tests built should have a make target added for them in the Makefile (Do not create new makefiles just for new tests, use the existing Makefile). Always run tests from their make targets, do not tail the output of tests that are run, just parse the entire output (or grep for what you care about!)
- Do not prompt me to run the tests, always run the tests without prompting me. Run the tests without the tail command.

## KING OF THE COURT ALGORITHM (python/kingofcourt.py)

### Core Purpose
Implements rounds-based King of the Court where all courts finish before the next round begins. Winners move up and split, losers move down and split. Includes sophisticated fair waitlist rotation system and automatic session advancement.

### Key Features

**Rounds-Based Architecture**
- All courts must complete before advancing to next round
- No immediate match generation after individual court completion
- Clear round boundaries with automatic advancement detection
- Round number tracking: `session.king_of_court_round_number`

**King of Court Movement Rules**
- **Winners**: Move up one court and SPLIT (unless already at kings court)
- **Losers**: Move down one court and SPLIT (unless already at bottom court)
- **Kings Court Winners**: Stay at kings court and SPLIT
- **Bottom Court Losers**: Stay at bottom court and SPLIT
- **Court Ordering**: Configurable via GUI, persists between sessions in user preferences
- **Team Splitting**: Previous teammates MUST be on opposite teams in next round

**Fair Waitlist Rotation System** 
- **Phase 1**: Nobody waits twice until everyone has waited once
- **Initial Priority**: Middle courts → Bottom courts → Kings court (only if all others waited)
- **Phase 2**: Fair rotation using immutable waitlist history order
- **Waitlist History**: `session.king_of_court_waitlist_history` - ordered list of first wait times
- **Rotation Index**: `session.king_of_court_waitlist_rotation_index` - cycles through history
- **Maximum Wait Gap**: Ensures longest time between repeated waits for each player
- **Wait Counts**: `session.king_of_court_wait_counts` - tracks total waits per player

**Initial Seeding Options** (Session Setup Page)
- **Random**: Players randomly distributed across courts (default)
- **Highest to Lowest**: Top ELO rated players start at kings court, lowest at bottom
- **Lowest to Highest**: Lowest ELO rated players start at kings court, highest at bottom  
- **Pre-seeded Ratings**: Required for ELO-based seeding options (like Competitive Variety)
- **First Bye Respect**: All seeding modes respect manually selected First Bye players

**Court Management & Persistence**
- **Court Ordering GUI**: Drag-and-drop reordering interface in Active Session
- **Persistent Settings**: Court names and ordering saved in user preferences
- **Direction Convention**: Court 1 (default kings) → Last court number (default bottom)
- **Export Integration**: Court ordering included in session export files

### Critical Functions

**apply_king_of_court_advancement(session, completed_matches) → bool**
- **Purpose**: Main advancement function called from GUI when matches finish
- **Logic**: Only advances if ALL current round matches are completed
- **Returns**: True if advancement occurred, False if waiting for more matches
- **Integration**: Called from GUI but contains NO GUI logic itself

**advance_round(session) → Session**
- **Core Algorithm**: Implements the 3-step King of Court advancement:
  1. **Movement**: Apply winner/loser court movement and team splitting
  2. **Waitlist**: Handle fair waitlist rotation while preserving court assignments
  3. **Matches**: Create new matches from final court assignments
- **Round Tracking**: Increments `king_of_court_round_number`
- **Match Detection**: Uses `get_matches_from_current_round()` to identify completed matches

**apply_king_of_court_movement(session, court_ordering, court_winners, court_losers) → Dict**
- **Step 1**: Pure King of Court movement logic
- **Winners**: Move up one court (or stay at kings), update player positions
- **Losers**: Move down one court (or stay at bottom), update player positions  
- **Returns**: `court_number → [individual_player_ids]` after movement
- **Position Tracking**: Updates `session.king_of_court_player_positions`

**apply_waitlist_rotation(session, court_assignments, court_ordering, players_per_court) → Dict**
- **Step 2**: Handle waitlist while preserving King of Court court assignments
- **Rule Enforcement**: Nobody waits twice until everyone waits once
- **Fair Rotation**: After Phase 1, uses `select_players_for_fair_rotation()`
- **Capacity Management**: Handles player overflow/underflow scenarios
- **History Updates**: Maintains `king_of_court_waitlist_history` and wait counts

**select_players_for_fair_rotation(session, all_active_players, excess_players) → List[str]**
- **Purpose**: Selects players for Phase 2 waitlist rotation (after everyone waited once)
- **Fairness**: Uses immutable waitlist history to ensure maximum time between waits
- **Cycle Logic**: Rotation index starts from beginning when transitioning to fair rotation
- **Reset Detection**: Automatically detects when everyone has waited once and resets rotation
- **Order Preservation**: Maintains chronological order from `king_of_court_waitlist_history`

**create_matches_from_final_assignments(session, court_assignments, players_per_court)**
- **Step 3**: Generate new matches from final court player assignments
- **Team Formation**: Uses `enforce_king_of_court_team_splitting()` for doubles
- **Anti-Partnership**: Ensures previous teammates are on opposite teams
- **Match Creation**: Creates Match objects with proper IDs and court assignments

**enforce_king_of_court_team_splitting(players, session) → Tuple[List[str], List[str]]**
- **Core Rule**: Previous teammates MUST be split onto opposite teams
- **Partnership Avoidance**: Uses recent match history to avoid repeated partnerships
- **Fallback Logic**: If no recent partnerships found, optimizes for lowest total partnerships
- **Integration**: Works with session match history to determine previous teams

### Important Invariants & Rules

1. **NO GUI LOGIC IN ALGORITHMS**: All session advancement logic moved out of GUI into testable functions
2. **ROUNDS-BASED ENFORCEMENT**: Courts never populate individually - only after all courts finish
3. **TEAM SPLITTING MANDATORY**: Winners and losers ALWAYS split - never stay as teams
4. **WAITLIST HISTORY IMMUTABLE**: Once established, waitlist history order never changes
5. **FAIR ROTATION RESET**: When everyone has waited once, rotation starts from history beginning
6. **COURT ORDERING RESPECT**: Movement always follows user-configured court ordering
7. **POSITION TRACKING**: `king_of_court_player_positions` maintains where each player last played
8. **WAIT COUNT ACCURACY**: `king_of_court_wait_counts` incremented for each wait instance
9. **EXPORT COMPLETENESS**: Session export includes all King of Court state for resumption

### Integration Points

**GUI System (python/gui.py)**
- **Session Setup**: Seeding option selection and pre-seeded ratings integration
- **Active Session**: Court ordering management UI with drag-and-drop
- **Match Completion**: Calls `apply_king_of_court_advancement()` when matches finish
- **Status Display**: Shows current round number and waitlist state
- **Export Integration**: Includes King of Court state in session export files

**Session Management (python/pickleball_types.py)**
- **King of Court Fields**: Round number, player positions, wait counts, waitlist history
- **Persistence**: All state fields included in session serialization
- **Court Ordering**: Stored in user preferences, loaded on session creation

**Testing Framework**
- **Comprehensive Tests**: `test_king_of_court_comprehensive.py` validates full 6-round scenarios
- **Waitlist Tests**: `test_waitlist_rotation_fix.py` and `test_waitlist_exact_rotation.py`
- **Movement Tests**: Validate winner/loser movement and team splitting rules
- **Integration Tests**: End-to-end testing of GUI + algorithm integration

### Fixed Issues & Improvements

**RESOLVED: Rounds-Based Implementation**
- ✅ Eliminated continuous match generation after individual court completion
- ✅ Implemented proper round boundaries with advancement detection
- ✅ All courts now wait for complete round before next matches start

**RESOLVED: Team Splitting Algorithm**
- ✅ Winners and losers now properly split in all scenarios  
- ✅ Previous teammates correctly placed on opposite teams
- ✅ Partnership history tracking prevents immediate re-partnering

**RESOLVED: Court Movement Logic**
- ✅ Winners move up one court (or stay at kings court)
- ✅ Losers move down one court (or stay at bottom court)
- ✅ Court ordering properly respected and configurable
- ✅ Player position tracking maintains accurate state

**RESOLVED: Fair Waitlist Rotation**
- ✅ Nobody waits twice until everyone waits once (Phase 1)
- ✅ Fair rotation using waitlist history after Phase 1 complete  
- ✅ Rotation index resets when transitioning to fair rotation
- ✅ Maximum time gaps between repeated waits for each player
- ✅ Waitlist history immutable and chronologically ordered

**RESOLVED: GUI Logic Separation**
- ✅ Moved all session advancement logic out of GUI into testable functions
- ✅ GUI only handles UI events and calls algorithm functions
- ✅ Comprehensive test coverage for all algorithm components
- ✅ Clean separation of concerns for maintainability

**RESOLVED: Session Export & Persistence**
- ✅ King of Court state fully included in export files
- ✅ Waitlist history exported in correct chronological order  
- ✅ Court ordering persistence implemented in user preferences
- ✅ Round number and player positions included in exports

### Testing & Validation

**Comprehensive Test Suite**
- `test_king_of_court_comprehensive.py`: End-to-end 6-round validation with 19 players
- `test_waitlist_rotation_fix.py`: Fair rotation algorithm validation
- `test_waitlist_exact_rotation.py`: Specific rotation scenario from session files
- `test_debug_waitlist_issue.py`: Waitlist stuck bug reproduction and fix

**Test Coverage Includes**
- ✅ Winner/loser movement validation across all courts
- ✅ Team splitting enforcement in every round
- ✅ Waitlist rotation fairness (nobody waits twice until all wait once)
- ✅ Fair rotation using waitlist history (Phase 2)
- ✅ Court ordering respect and persistence
- ✅ Session state export and import accuracy
- ✅ Edge cases: insufficient players, court overflow, etc.

**Run King of Court Tests**
```bash
make test_king_of_court_comprehensive  # Full 6-round validation
python test_waitlist_exact_rotation.py  # Specific rotation scenarios
python test_waitlist_rotation_fix.py    # Fair rotation algorithm
```
- Main advancement function - processes all completed matches
- STEP 1: Move winners up/losers down and split teams
- STEP 2: Apply waitlist rotation while preserving court assignments
- STEP 3: Create new matches from final assignments with proper splitting
- Returns True if advancement successful, False if not ready

**apply_court_movement_and_splitting(session, completed_matches, court_ordering) → Dict**
- Handles the core King of Court movement logic
- Winners move up and split, losers move down and split
- Maintains court position tracking in session.king_of_court_player_positions
- Returns court assignments after movement (before waitlist rotation)

**apply_waitlist_rotation(session, court_assignments, court_ordering, players_per_court) → Dict**
- Manages fair waitlist rotation while preserving court assignments from movement
- Phase 1 (initial): Priority-based selection (middle→bottom→kings)  
- Phase 2 (ongoing): Fair rotation using immutable waitlist history
- Updates wait counts and maintains rotation index for cyclical fairness
- Critical fix: Uses fair rotation when all players are in history OR everyone has waited

**select_players_for_fair_rotation(session, all_active_players, excess_players) → List**
- Core fair rotation algorithm using waitlist history
- Rotates through players cyclically to maximize time between waits
- Handles active player filtering and rotation index bounds checking
- Ensures rotation index is relative to active players, not full history

**create_matches_from_final_assignments(session, court_assignments, players_per_court)**
- Creates new matches after movement and waitlist rotation
- Handles team formation with King of Court splitting rules
- Uses partnership history minimization when possible (not strict constraint)
- Fills courts in court ordering sequence

**seed_initial_king_of_court_players(session, seeding_option)**
- Sets up initial court assignments based on seeding choice
- Integrates with ELO system for skill-based seeding
- Handles First Bye players correctly in all seeding modes

### Important Invariants & Design Principles

1. **Round-Based Operation**: 
   - All matches must complete before next round begins
   - No partial advancement or individual court repopulation
   - Session.can_advance_to_next_round() controls advancement timing

2. **Fair Waitlist Rotation**:
   - Phase detection: Initial (priority-based) vs Ongoing (fair rotation)
   - Waitlist history is immutable once established - never reordered
   - Rotation index tracks position in active players, handles dropouts
   - Nobody waits twice until everyone waits once (fundamental fairness rule)

3. **Court Movement Priority**:
   - King of Court movement rules ALWAYS take priority over partnership constraints
   - Partnership history used for tiebreaking, not hard constraints
   - Court assignments from movement are preserved through waitlist rotation

4. **Persistence & State Management**:
   - Court ordering persists between sessions
   - Waitlist history and rotation index maintained across rounds
   - Player position tracking handles movement and waitlist transitions

5. **GUI Integration**:
   - Session advancement logic moved from GUI to algorithm files
   - GUI only triggers advancement, doesn't manage logic
   - Court ordering UI reflects actual court names (not internal IDs)

### Testing & Validation

**Comprehensive Tests**:
- test_king_of_court_comprehensive.py: Full 19-player, 6-round validation
- test_king_of_court_rounds.py: Basic setup and seeding validation
- test_waitlist_rotation_fix.py: Fair rotation algorithm validation
- All tests validate movement rules, splitting, and waitlist fairness

**Key Test Scenarios**:
- Winners move up and split correctly
- Losers move down and split correctly  
- Court boundary conditions (kings/bottom courts)
- Fair waitlist rotation after everyone waits once
- Partnership history minimization when possible
- Court ordering and persistence

### Recent Fixes (Dec 30, 2024)

**Critical Waitlist Rotation Fix**:
- Fixed bug where same players kept waiting instead of fair rotation
- Root cause: Algorithm wasn't detecting when to switch to fair rotation mode
- Solution: Check if all players are in waitlist history OR everyone has waited
- Ensures fair rotation activates properly after initial phase
- Waitlist rotation now works correctly for long sessions

**GUI Logic Refactoring**:
- Moved session advancement logic from GUI to algorithm files
- Improved testability and maintainability
- GUI now only triggers advancement, doesn't manage complex logic

The King of Court algorithm now provides fair, predictable gameplay with proper team movement and balanced wait times for all participants.

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

**check_partner_opponent_partner_pattern(session, player1, player2) → bool**
- Detects the problematic Partner → Opponent → Partner relationship sequence
- **Requires both-sided gaps**: Both players must have played other games since being opponents
- Only active when adaptive balance system kicks in (mid-late session)
- BLOCKED: Partners → Opponents → Partners (immediate) or Partners → Opponents → [One plays] → Partners
- ALLOWED: Partners → Opponents → [Both players play other games] → Partners
- Prevents unfair "waiting out" on bench scenarios and ensures balanced constraint application

**can_play_with_player(session, player1, player2, role, allow_cross_bracket=False) → bool**
- THE GATEKEEPER: checks if two players can play together
- role = 'partner' or 'opponent'
- allow_cross_bracket: when True, relaxes roaming range checks (used in fallback matching)
- Enhanced with Partner-Opponent-Partner pattern prevention
- Order of checks:
  1. Partner-Opponent-Partner pattern (when adaptive system active)
  2. Locked teams (hard enforced)
  3. Banned pairs (hard enforced)
  4. Roaming range compatibility (if 12+ players & competitive-variety mode)
  5. Global recency check (last N games globally)
  6. Player-specific history check (intervening games in personal history)

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
- **Enhanced balance filtering**: Applies hard balance constraints in mid-late sessions

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

9. **ENHANCED BALANCE CONSTRAINTS**:
   - Only activate when adaptive system kicks in (balance_weight >= 3.0)
   - Progressive thresholds: Early (no limit) → Mid (300 pts) → Late (200 pts)
   - Homogeneous partnership bonuses and mismatch penalties scale with balance weight
   - Partner-Opponent-Partner prevention requires both-sided gaps
   - All constraints integrate seamlessly with existing variety and wait time systems

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
The adaptive constraints system intelligently relaxes variety constraints (partner/opponent repetition) as sessions progress to improve match balance quality. It dynamically adjusts based on player count and average games played, ensuring variety constraints are relaxed gradually while implementing **progressively stricter balance constraints**.

**CRITICAL**: The adaptive system **NEVER** changes the roaming range (competitiveness level). User's competitiveness choice is always preserved.

### Key Features

**Dynamic Threshold Calculation**
- Early → Mid: Each player has played 4 games on average
- Mid → Late: Each player has played 6 games on average  
- Thresholds scale with player count: `threshold = (player_count * target_games_per_player) / 4`
- Example: 16 players → Early→Mid at 16 matches, Mid→Late at 24 matches

**Progressive Constraint Relaxation + Balance Enforcement**
- **Early phase**: Standard constraints (partner: 3 games, opponent: 2 games), 1.0x balance weight, ≤400 rating threshold
- **Mid phase**: Reduced constraints (partner: 2 games, opponent: 1 game), 3.0x balance weight, ≤300 rating threshold
- **Late phase**: Minimal constraints (partner: 1 game, opponent: 1 game), 5.0x balance weight, ≤200 rating threshold
- **NEVER goes to 0**: Maintains minimum 1-game gaps to prevent back-to-back repetition

**Enhanced Balance Constraint System**
- **Hard Balance Thresholds**: Maximum acceptable team rating differences that activate when adaptive system kicks in (mid-late session)
- **Homogeneous Partnership Bonus**: Rewards pairing similar-skill players (Elite+Elite, Strong+Strong) once adaptive system activates
- **Mismatched Partnership Penalties**: Discourages Elite+Weak partnerships that create 'carry' dynamics (mid-late session only)
- **Partner-Opponent-Partner Prevention**: Blocks awkward Partner → Opponent → Partner sequences requiring both-sided gaps (mid-late session only)
- **Balance-First Filtering**: Severely imbalanced matches (>threshold) automatically rejected after Round 3-4
- **Progressive Balance Prioritization**: Variety weight decreases while balance weight increases over time
- **Skill Tier Matching Bonus**: Extra rewards for Elite vs Elite, Strong vs Strong matchups (mid-late session only)
- **Perfect Balance Bonus**: Extra scoring rewards for very close team rating matches (all phases)

**GUI Slider Control**
- Position 0: **NONE** - Disables adaptive constraints entirely (maintains standard Early phase settings)
- Position 1: **AUTO** - Automatic progression based on session progress (default behavior)
- Positions 2-5: **Manual Override** - Fixed balance weights (2.0x, 3.0x, 5.0x, 8.0x)
- Status display shows current phase and effective balance weight
- **State Toggle Button**: Cycles through Disabled → Auto → Manual modes

### Critical Functions

**get_balance_threshold(session) → float**
- Calculates maximum acceptable team rating difference based on session progression
- Only activates when adaptive system kicks in (balance_weight >= 3.0)
- Early: No threshold (inf), Mid: 300 points, Late: 200 points
- Ensures progressively stricter balance requirements

**meets_balance_constraints(session, team1, team2) → bool**
- Checks if potential match meets hard balance constraints
- Used to filter out severely imbalanced matches before scoring
- Returns False for matches exceeding the current balance threshold
- Only active when adaptive system kicks in

**check_partner_opponent_partner_pattern(session, player1, player2) → bool**
- Detects the problematic Partner → Opponent → Partner relationship sequence
- **Requires both-sided gaps**: Both players must have played other games since being opponents
- Only active when adaptive balance system kicks in (mid-late session)
- BLOCKED: Partners → Opponents → Partners (immediate) or Partners → Opponents → [One plays] → Partners
- ALLOWED: Partners → Opponents → [Both players play other games] → Partners
- Prevents unfair "waiting out" on bench scenarios and ensures balanced constraint application

**get_adaptive_constraints(session) → Dict**
- Returns current constraints based on session progression or manual override
- Handles disabled state when `session.adaptive_constraints_disabled = True`
- Never allows constraints to go to 0 (minimum partner: 1, opponent: 1)

**score_potential_match(session, team1, team2) → float**
- Enhanced scoring function with balance constraint integration
- Returns -10000 for matches that violate hard balance constraints
- Includes elite+weak partnership bonus (50+ points scaled by balance weight)
- Progressive variety weight reduction (3.0→1.0) as balance weight increases
- Perfect balance bonus for very close teams (50-100 points scaled by balance weight)

**get_adaptive_phase_info(session) → Dict**
- Provides comprehensive information about current adaptive state
- Includes phase name, auto weight, effective weight, and progression thresholds
- Returns "Disabled" phase when adaptive constraints are turned off

**calculate_session_thresholds(session) → Dict**
- Computes dynamic thresholds based on player count
- Formula: `(player_count * games_per_player) / 4` matches per threshold
- Ensures thresholds scale appropriately with session size

### Expert Balance Strategy Implementation

As a staff-level expert with years of observing sessions, this system implements these key insights:

**Problem Identification**
- Variety constraints become too restrictive in long sessions
- Algorithm forced to choose imbalanced matches when good options blocked
- Players get frustrated with 800+ rating point team differences
- Elite vs beginner matches create poor experiences
- **But early rounds need variety exploration to work properly**

**Smart Balance Solution**
1. **Delayed Activation**: Balance constraints only activate when adaptive system kicks in (Round 4+)
2. **Hard Thresholds**: Absolute limits on acceptable imbalance that get stricter over time (mid-late session)
3. **Homogeneous Partnerships**: Actively encourage similar-skill partnerships once adaptive system activates
4. **Mismatch Penalties**: Discourage Elite+Weak partnerships that create 'carry' dynamics (mid-late session)
5. **Social Pattern Prevention**: Block Partner→Opponent→Partner sequences with both-sided gap requirements
6. **Progressive Prioritization**: Gradually shift from variety-first to balance-first matching
7. **Threshold Enforcement**: Filter out bad matches before they're even considered (after Round 3-4)

**Session Progression Logic**
- **Early (Rounds 1-3)**: Variety exploration, no balance constraints, moderate imbalance allowed
- **Mid (Round 4+)**: Balance constraints activate (≤300 pts), homogeneous partnerships encouraged  
- **Late (Round 6+)**: Strict balance priority (≤200 pts), minimal imbalance tolerated

### Slider Behavior Design

**User Experience Philosophy**
- Variety slider (user preference) **remains unchanged** when adaptive constraints activate
- Adaptive constraints slider shows **current state** and allows manual control
- Clear separation between user preferences and automatic system adjustments

**State Management**
- NONE (0): `adaptive_constraints_disabled = True` - System completely disabled
- AUTO (1): `adaptive_balance_weight = None` - Automatic progression active (DEFAULT)
- Manual (2-5): `adaptive_balance_weight = [2.0, 3.0, 5.0, 8.0]` - Fixed override

**Status Display Examples**
- AUTO mode: "Auto: Mid (3.0x)" - Shows automatic phase and weight
- Manual mode: "Manual: 5.0x" - Shows fixed override weight  
- Disabled: "Disabled" - Adaptive system completely off

### Integration with Balance Algorithm

The enhanced system affects match generation at multiple levels:

**Match Filtering Level**
- `meets_balance_constraints()` pre-filters severely imbalanced combinations
- Prevents 800+ rating point differences from being considered
- Applied before scoring for computational efficiency
- Only active when adaptive system kicks in (mid-late session)

**Match Scoring Level**
- Balance weight multiplier affects scoring: 1.0x → 3.0x → 5.0x → 8.0x
- Homogeneous partnership bonus: 75+ points for similar-skill partnerships (Elite+Elite, Strong+Strong)
- Mismatched partnership penalties: 50-100+ points for Elite+Weak combinations that create 'carry' dynamics
- Variety weight reduction: 3.0x → 1.0x to deprioritize repetition concerns
- Perfect balance bonus: 50-250 points for very close team ratings
- Skill tier matching bonus: 40-75+ points for Elite vs Elite, Strong vs Strong matchups
- Partner-Opponent-Partner pattern prevention with both-sided gap requirements

**Match Generation Level** 
- Algorithm selects highest-scoring valid match that meets all constraints
- Balance constraints integrated into core `populate_empty_courts_competitive_variety()`
- Maintains all existing variety and roaming range constraints
- Wait time prioritization fully preserved throughout

### Testing & Validation
- `test_adaptive_slider.py`: Comprehensive slider functionality testing
- `test_disabled_adaptive.py`: Validates disabled state behavior  
- `test_enhanced_balance_constraints.py`: Tests all new balance constraint features
- `test_both_sided_gap.py`: Tests Partner-Opponent-Partner pattern prevention with both-sided gaps
- `test_partner_opponent_partner_prevention.py`: Social dynamic constraint testing
- `test_roaming_range_preservation.py`: Verifies roaming range is never changed by adaptive system
- `demo_enhanced_balance_system.py`: Realistic demonstration of balance improvements
- Fuzzing tests: `make run_fuzz_tests` validates constraint enforcement without violations

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
- test_enhanced_balance_constraints.py: tests enhanced balance constraint system
- test_both_sided_gap.py: tests both-sided gap requirements for pattern prevention
- test_partner_opponent_partner_prevention.py: social dynamic constraint testing
- test_roaming_range_preservation.py: verifies roaming range preservation across all adaptive phases

## COMPETITIVE ROUND ROBIN ALGORITHM (python/competitive_round_robin.py)

### Core Purpose
Implements a pre-scheduled tournament format where ALL matches are generated upfront with human-in-the-loop approval. The schedule is skill-balanced, respects variety constraints, and optimizes for **continuous flow** - ensuring courts never sit empty waiting for other matches to finish.

### Key Features

**Pre-Scheduled Tournament Format**
- All matches generated before session starts
- Human approval workflow: Review → Approve/Reject → Regenerate
- Schedule can be modified after approval via player swaps
- Matches executed in order with automatic court assignment

**Continuous Flow Scheduling (CRITICAL)**
- **Problem Solved**: Prevents courts from sitting empty waiting for multiple games to finish
- **Wave Structure**: Matches organized in waves of `num_courts` matches each
- **1:1 Flow**: When Match N finishes on Court C, Match N+4 can start immediately on Court C
- **Court Continuity**: Each follow-up match retains 3/4 players from the same court
- **Single Dependency**: Wave 1 matches each depend on exactly ONE Wave 0 match

**Skill-Balanced Matchmaking**
- Uses ELO ratings from `competitive_variety.py` for player skill assessment
- Team balance scoring prioritizes close team ratings
- Alternating round styles: SKILL rounds (tight spreads) vs VARIETY rounds (mixed levels)
- Balance score calculation: `500 - abs(team1_rating - team2_rating)`

**Variety Constraints**
- **No Repeated Partnerships**: Same two players never partner twice in schedule
- **Individual Opponent Limit**: Default max 3 times facing same individual opponent
- **No Repeated Groups**: Same 4 players never play together twice (as any configuration)
- Uses `partnership_used`, `individual_opponent_count`, `groups_played` tracking

**First Bye Integration**
- First bye players excluded from initial wave
- Introduced in later waves after initial matches complete
- Maintains fair games distribution across all players

### Critical Functions

**generate_initial_schedule(session, config) → List[ScheduledMatch]**
- **Main Entry Point**: Generates complete tournament schedule
- **Wave 0**: Initial matches filling all courts with top-rated players
- **Subsequent Waves**: Uses continuous flow optimization algorithm
- **Alternating Styles**: Odd waves = skill-focused, even waves = variety-focused
- **Returns**: List of `ScheduledMatch` objects with `pending` status

**find_best_match(pool, preferred_players, style) → Optional[Tuple[team1, team2]]**
- **Purpose**: Find best valid match from a pool of players
- **Constraints Checked**: Groups played, partnership constraints, opponent limits
- **Scoring**: Balance + style score + continuity bonus + games needed
- **Continuity Bonus**: Prefers players from same court position (+50 per player)

**_reorder_for_fair_distribution(matches, all_player_ids, first_bye_player_ids) → List[ScheduledMatch]**
- **Purpose**: Reorder matches for first-bye handling while preserving wave structure
- **CRITICAL**: Preserves wave structure for continuous flow (matches stay in wave groups)
- **First Bye Handling**: Delays first-bye player matches to later in schedule

**score_match_variety(team1, team2) → float**
- Scores matches for VARIETY rounds (mixed skill levels)
- Rewards skill diversity: high+low pairings over similar-skill pairings
- Penalty for repeated partnerships in match history

**score_match_skill_focused(team1, team2) → float**
- Scores matches for SKILL rounds (competitive balance)
- Rewards homogeneous teams: both teammates at similar skill levels
- Bonus for tight intra-team skill spreads (<70 ELO)

**validate_schedule(session, matches) → ScheduleValidationResult**
- Validates schedule against all constraints
- Returns violations list and games-per-player distribution
- Used before approval to ensure schedule integrity

**regenerate_match(session, schedule, rejected_idx, config) → Optional[ScheduledMatch]**
- Regenerates a single rejected match
- Respects all constraints from approved matches
- Maintains games-per-player balance

**swap_player_in_match(match, old_player, new_player) → bool**
- Swaps a player in an approved match
- Validates constraints after swap
- Used for manual adjustments after approval

### Algorithm Details

**Continuous Flow Wave Algorithm**
```
For each wave after Wave 0:
  1. Distribute waiters evenly across courts (1 per court with 4 waiters)
  2. For each court:
     a. PHASE 1 (Optimal): Try court's previous players + assigned waiter
     b. PHASE 2 (Adjacent): Expand to adjacent court if needed
     c. PHASE 3 (Full): Use all available players (worst case)
  3. Select best match from available pool
  4. Track used players to prevent double-booking within wave
```

**Scoring Formula**
```
total_score = balance_score + style_score + continuity_bonus + games_needed

where:
  balance_score = 500 - abs(team1_rating - team2_rating)
  style_score = score_match_variety() or score_match_skill_focused()
  continuity_bonus = 50 * (players from same court position)
  games_needed = 20 * sum(target_games - games_per_player[p] for p in match)
```

### Configuration

**CompetitiveRoundRobinConfig (python/pickleball_types.py)**
```python
@dataclass
class CompetitiveRoundRobinConfig:
    games_per_player: int = 8              # Target games per player
    max_partner_repeats: int = 0           # Never repeat partners
    max_opponent_pair_repeats: int = 0     # Never face same pair twice
    max_individual_opponent_repeats: int = 3  # Max times facing individual
    scheduled_matches: List[ScheduledMatch] = field(default_factory=list)
    schedule_finalized: bool = False       # True after user approval
```

### Session State

**ScheduledMatch Dataclass**
```python
@dataclass
class ScheduledMatch:
    id: str                    # Unique identifier
    team1: List[str]           # Player IDs for team 1
    team2: List[str]           # Player IDs for team 2
    status: str                # 'pending', 'approved', 'rejected', 'completed'
    match_number: int          # Order in schedule
    balance_score: float       # Quality score for UI display
```

### Testing & Validation

**Test Files**
- `test_competitive_round_robin.py`: Main test suite (15 tests)
- `test_continuous_flow.py`: Verifies 1:1 continuous flow and court continuity

**Make Targets**
```bash
make test_competitive_round_robin  # Main algorithm tests
make test_continuous_flow          # Continuous flow verification
```

**Key Test Assertions**
- Generated matches respect all constraints (partnerships, opponents, groups)
- Average games per player within ±1 of target
- 100% positive balance scores (teams reasonably matched)
- 3/4 court continuity between consecutive waves
- 1:1 continuous flow (each finish enables exactly one start)

### Integration with GUI

**Session Setup Page**
- Select "Competitive Round Robin" game mode
- Configure target games per player
- Review/approve generated schedule before starting

**Active Session**
- Matches execute in schedule order
- Courts auto-assigned based on availability
- Completed matches tracked via standard match completion flow
- Schedule progress shown in UI

### Important Invariants

1. **NO REPEATED PARTNERSHIPS**: Same two players never partner twice in entire schedule
2. **NO REPEATED GROUPS**: Same 4 players never play together twice
3. **WAVE STRUCTURE PRESERVED**: Reordering functions maintain wave boundaries
4. **CONTINUOUS FLOW**: Each court's next match uses 3/4 players from that court
5. **SINGLE DEPENDENCY**: Wave N+1 matches each depend on exactly one Wave N match
6. **BALANCE PRIORITY**: Team rating differences minimized within constraints
7. **FAIR DISTRIBUTION**: All players get approximately equal games (±1-2)

## KING OF THE COURT ALGORITHM (python/king_of_court.py)

### Core Purpose
Implements a rounds-based King of the Court system where teams move up/down courts based on wins/losses and split after each match. Courts are ranked from Kings Court (top) to Bottom Court, with structured movement and fair waitlist rotation.

### Key Features

**Round-Based System**
- All matches must complete before next round begins
- No individual court advancement - entire session moves as rounds
- Prevents immediate re-population and ensures proper court movement logic

**Court Movement Rules**
- **Winners**: Move up one court position and split (stay if already at Kings Court)
- **Losers**: Move down one court position and split (stay if already at Bottom Court)
- **Splitting**: Teams never stay together after a match - partners always separate
- **Court Ordering**: Configurable court hierarchy with persistent user customization

**Waitlist Management**
- **Priority Order**: Middle courts → Bottom court → Kings court (only if everyone else waited)
- **Fair Rotation**: Nobody waits twice until everyone has waited once
- **Waitlist History**: Tracks who waited when for proper rotation after everyone waits once
- **Position Restoration**: Players return to same court position after waiting when possible

**Initial Seeding Options** (Session Setup)
- **Random**: Players randomly distributed across courts
- **Highest to Lowest**: Elite players start on Kings Court, beginners on Bottom Court
- **Lowest to Highest**: Beginners start on Kings Court, elite players on Bottom Court
- **First Byes**: Respected in all seeding configurations

### Critical Functions

**advance_to_next_round_koc(session) → bool**
- Main round advancement function for King of Court mode
- Only executes when ALL current matches are completed
- Returns True if round advanced, False if matches still in progress
- Moves winners up/losers down according to court hierarchy
- Manages waitlist rotation with fair distribution

**get_king_of_court_seeding_order(session, seeding_preference) → List[str]**
- Generates initial player order based on seeding preference
- Handles Random/Highest-to-Lowest/Lowest-to-Highest configurations
- Integrates with pre-seeded skill ratings when available
- Respects First Byes selection for all seeding types

**move_players_after_round_koc(session, court_results)**
- Core movement logic for winners/losers between courts
- Ensures proper court hierarchy movement (up for win, down for loss)
- Handles edge cases (already at top/bottom courts)
- Enforces mandatory team splitting after each match

**manage_waitlist_rotation_koc(session, moved_players)**
- Sophisticated waitlist management ensuring fairness
- Implements "nobody waits twice until everyone waits once" rule
- Maintains waitlist history for proper rotation after initial cycle
- Prioritizes middle courts for waitlist selection

**get_koc_waitlist_candidates(session) → List[str]**
- Determines who should be placed on waitlist based on King of Court rules
- Priority: Middle courts → Bottom court → Kings court (last resort)
- Respects wait count constraints and fairness principles

### Court Ordering System

**User Customizable Hierarchy**
- **Manage Court Order** button allows drag-and-drop court reordering
- Uses actual court display names (not internal numbers)
- **Persistent Storage**: Court ordering saved between sessions
- Default: Court 1 (Kings) → Court 2 → ... → Court N (Bottom)

**Court Names Integration**
- Court ordering respects custom court names set by users
- Display shows actual court labels users see in Active Session GUI
- Ordering list updates dynamically when court names change
- Full integration with existing court name persistence system

### Session State Management

**King of Court Specific State**
- `king_of_court_round_number`: Current round counter
- `king_of_court_wait_counts`: Per-player wait tracking
- `king_of_court_waitlist_history`: Complete history of who waited when
- `court_ordering`: User-configured court hierarchy

**Export Integration**
- Session exports include complete King of Court state
- Waitlist history exported for analysis and debugging
- Court ordering and round numbers preserved
- Wait count distribution included in export

### Testing & Validation

**Comprehensive Test Coverage**
- `test_king_of_court_comprehensive.py`: Full 6-round simulation with 19 players
- Validates all movement rules, team splitting, and waitlist fairness
- Confirms nobody waits more than once until everyone has waited
- Tests court ordering compliance and round-based advancement

**Key Test Scenarios**
- Winner/loser movement between courts with proper splitting
- Waitlist rotation ensuring maximum fairness (18 different players wait exactly once in 6 rounds)
- Court hierarchy respect (Kings at top, bottom at bottom)
- Round-based advancement (no premature court population)
- Initial seeding with different preferences and skill ratings integration

### Algorithm Integration

**Session Management Integration**
- Refactored from GUI-based logic to core session management
- `advance_session_if_needed()` handles King of Court round detection
- Testable logic separated from GUI concerns for better maintainability
- Clean separation between algorithm logic and user interface

**Skill Rating Support**
- Supports pre-seeded skill ratings for Highest/Lowest configurations
- Integrates with existing ELO rating system from Competitive Variety
- Falls back gracefully when no skill ratings available
- Maintains compatibility with First Byes system

## ROUNDS-BASED KING OF THE COURT ALGORITHM (python/kingofcourt.py)

### Core Purpose
Implements a rounds-based King of the Court tournament system where courts populate simultaneously after all current matches complete. Winners move up courts and split, losers move down courts and split, with intelligent waitlist rotation.

### Key Features

**Rounds-Based Execution**
- Courts do not populate until ALL currently scheduled matches finish
- Prevents individual match advancement that breaks court hierarchy
- Ensures synchronized round progression across all courts

**Core King of Court Rules**
- **Winners**: Move up one court and split (or stay at Kings court if already there)
- **Losers**: Move down one court and split (or stay at bottom court if already there)
- **Team Splitting**: Previous teammates MUST be on opposite teams in new matches
- **Court Movement Priority**: Court assignments are determined by win/loss, not partnership constraints

**Court Ordering & Direction**
- Configurable court ordering with Court 1 as Kings court (top) by default
- Court ordering persists between sessions via `set_court_ordering()`
- Movement direction: Kings court ← Winners | Losers → Bottom court
- GUI interface for reordering courts by dragging court names up/down

**Waitlist Management (King of Court Rules)**
- **Priority**: Nobody waits twice until everyone has waited once
- **Selection Order**: Middle courts first → Bottom court → Kings court (only if everyone else waited)
- **Capacity Management**: Always maintain exactly 16 players on 4 courts, 3 waiting (19 players)
- **Return Placement**: Try to place returning waiters in middle courts when possible

**Initial Seeding Options**
- **Random**: Players randomly distributed across courts
- **Highest to Lowest**: Top skill players on Kings court, lowest on bottom court  
- **Lowest to Highest**: Lowest skill players on Kings court, highest on bottom court
- **First Byes Respected**: Selected first bye players always start on waitlist regardless of seeding
- **Pre-seeded Ratings**: Uses skill ratings when available for H→L and L→H seeding

### Critical Functions

**evaluate_king_of_court_session(session) → Session**
- Main entry point for King of Court sessions
- Handles initialization on first call
- Advances rounds when all matches completed

**advance_round(session) → Session**
- **STEP 1**: Apply King of Court movement (winners up & split, losers down & split)
- **STEP 2**: Handle waitlist rotation using KoC waitlist rules  
- **STEP 3**: Create matches with enforced team splitting
- Only advances when ALL active matches are completed

**apply_king_of_court_movement(session, court_ordering, court_winners, court_losers) → Dict**
- Pure King of Court movement logic - winners up, losers down
- Updates `session.king_of_court_player_positions` for court tracking
- Maintains court hierarchy determined by match results

**apply_waitlist_rotation(session, court_assignments, court_ordering, players_per_court) → Dict**
- Implements KoC waitlist rules while preserving court assignments from movement
- Selects waiters from middle courts first, respecting wait count fairness
- Fills gaps with returning waiters while maintaining exact court capacity
- **CRITICAL**: Removes waiters from `king_of_court_player_positions` to prevent display issues

**enforce_king_of_court_team_splitting(players, session) → Tuple[List[str], List[str]]**
- Ensures previous teammates are placed on OPPOSITE teams
- Uses recently completed matches to identify teammate relationships
- Finds optimal arrangement with minimum violations when perfect splitting impossible
- **King of Court Priority**: Team splitting enforced over partnership variety constraints

**initialize_king_of_court_session(session) → Session**
- Seeds players according to selected seeding option (Random/H→L/L→H)
- Handles first bye players and excess players via waitlist
- Creates initial matches with randomized teams for variety
- Sets `king_of_court_round_number = 1`

### Important Data Structures

**session.king_of_court_player_positions: Dict[str, int]**
- Maps player_id → current_court_number
- Updated by movement algorithm, cleared for waiters
- Used by GUI for court assignment display

**session.king_of_court_wait_counts: Dict[str, int]**
- Tracks how many times each player has waited
- Enforces "nobody waits twice until everyone waits once" rule
- Incremented when player goes to waitlist

**session.king_of_court_round_number: int**
- Current round number (0 = not initialized, 1+ = active rounds)
- Used to detect first-time initialization vs. round advancement

### Algorithm Invariants & Design Principles

1. **Rounds-Based Execution**: Never advance individual courts - wait for ALL matches to complete
2. **Movement Hierarchy**: Court assignments determined by wins/losses, not partnership constraints  
3. **Exact Capacity**: Always maintain exactly `courts × 4` players on courts, excess on waitlist
4. **Team Splitting**: Previous teammates MUST split - this overrides partnership variety preferences
5. **Waitlist Fairness**: Middle court players chosen for waitlist first to ensure fairness
6. **Wait Count Enforcement**: Algorithm guarantees nobody waits twice until everyone waits once
7. **Court Position Tracking**: Waiters have no court position - prevents GUI display inconsistencies

### Integration Points

**Session Management**
- Called from `populate_session()` when mode = 'king-of-court'  
- Returns updated session with new matches or advanced round state
- Works with existing session persistence and match management

**GUI Integration**
- Court reordering via dragging interface in active session
- Court assignments displayed via `king_of_court_player_positions` 
- Waitlist display shows current waiters with wait count indicators
- Initial seeding options integrated into Session Setup page

**Configuration**
- `KingOfCourtConfig` dataclass stores seeding option and court ordering
- Court ordering persists between sessions like court names
- Pre-seeded ratings option enables H→L and L→H seeding modes

### Testing & Validation

**test_king_of_court_comprehensive.py**
- Validates 6 rounds of 19-player King of Court
- Ensures winners move up & split, losers move down & split
- Validates waitlist rotation (nobody waits twice until all wait once)
- Confirms exact court capacity maintenance (16 on courts, 3 waiting)
- Tests team splitting with optimal violation minimization

**Key Test Scenarios**
- Court movement validation for each round
- Wait count distribution tracking 
- Team splitting effectiveness measurement
- Court capacity consistency verification
- Partnership constraint vs. movement priority resolution

## KING OF THE COURT ALGORITHM (python/kingofcourt.py)

### Core Purpose
This module implements a rounds-based King of the Court algorithm where courts do not populate until all currently scheduled games are finished. Teams move up/down courts based on wins/losses and always split after each game.

### Key Concepts

**Rounds-Based System**
- All matches in a round must complete before the next round begins
- Winners move up one court and split (unless already at top)
- Losers move down one court and split (unless already at bottom)
- Court hierarchy: Court 1 = Kings Court (top), Last Court = Bottom Court

**Court Ordering & Management**
- Courts have configurable ordering stored in `session.config.king_of_court_config.court_ordering`
- GUI provides "Manage Court" button to reorder courts via drag-and-drop interface
- Court ordering persists between sessions
- Default ordering: [1, 2, 3, 4] (Court 1 = Kings, Court 4 = Bottom)

**Team Splitting Rules**
- After every game, winning team splits and losing team splits
- Previous teammates MUST be placed on opposite teams in the next round
- Partnership avoidance is secondary to court movement rules
- Algorithm attempts to avoid recent partnerships when possible

**Waitlist Management**
- **Primary Rule**: Nobody waits twice until everyone has waited once
- **Waitlist Priority**: Choose waiters from middle courts first, then bottom court, then kings court (only if everyone else waited)
- **Waitlist History Tracking**: Maintains immutable ordered list of who has waited (oldest to newest)
- **Fair Rotation**: After everyone waits once, cycles through waitlist history using rotation index
- **Rotation Logic**: Uses `king_of_court_waitlist_rotation_index` to track current position in history
- **No Re-ordering**: Players are never moved within history - only added when waiting for first time
- **Guaranteed Fairness**: Ensures maximum time between waits for each player via cyclical selection
- **Capacity Management**: With C courts and 4 players per court, exactly max(0, total_players - C*4) players wait

**Initial Seeding Options**
- **Random**: Players randomly placed across courts
- **Highest to Lowest**: Top-rated players start in Kings Court, lowest in bottom court
- **Lowest to Highest**: Lowest-rated players start in Kings Court, highest in bottom court
- **First Byes**: Always respected regardless of seeding method

### Critical Functions

**advance_round(session: Session) → Session**
- Main advancement function that processes completed round
- STEP 1: Apply King of Court movement (winners up, losers down, both split)
- STEP 2: Apply waitlist rotation while preserving court assignments
- STEP 3: Create new matches with team splitting rules
- Only executes when ALL courts have completed matches

**apply_king_of_court_movement(session, court_ordering, players_per_court) → Dict[int, List[str]]**
- Implements core King of Court movement logic
- Winners from court N → move to court N-1 (unless already at court 1)
- Losers from court N → move to court N+1 (unless already at last court)
- All players split from their previous teammates
- Returns court assignments after movement

**apply_waitlist_rotation(session, court_assignments, court_ordering, players_per_court) → Dict[int, List[str]]**
- Handles waitlist rotation while preserving King of Court court assignments
- **Nobody waits twice rule**: Prioritizes players who have never waited
- **Waitlist priority order**: Middle courts → Bottom court → Kings court (only if others waited)
- **Fair rotation**: When everyone has waited once, chooses players who waited longest ago
- **Waitlist history tracking**: Updates `session.king_of_court_waitlist_history`

**select_players_for_fair_rotation(session, all_active_players, excess_players) → List[str]**
- Implements fair rotation after everyone has waited once
- Uses `king_of_court_waitlist_rotation_index` to cycle through waitlist history
- Selects consecutive players from current rotation position, wrapping around list
- Advances rotation index to ensure next selection starts from different position  
- **FIXED**: Never re-orders history - players maintain original waitlist position
- **FIXED**: Guarantees truly fair distribution with maximum time between individual waits

**enforce_king_of_court_team_splitting(players: List[str], session: Session) → Tuple[List[str], List[str]]**
- Enforces team splitting rule: previous teammates must be on opposite teams
- Analyzes recent match history to identify previous partnerships
- Creates team assignments that minimize recent partnerships
- Falls back to random assignment if no good split possible

**get_court_ordering(session: Session) → List[int]**
- Returns court ordering from session configuration
- Default ordering if not configured: [1, 2, 3, ..., num_courts]

### Session State Tracking

**King of Court Specific Fields**
- `session.king_of_court_round_number`: Current round number
- `session.king_of_court_player_positions`: Dict[player_id, court_number] tracking where players last played
- `session.king_of_court_wait_counts`: Dict[player_id, int] tracking how many times each player has waited
- `session.king_of_court_waitlist_history`: List[player_id] immutable ordered history of who has waited (oldest first)
- `session.king_of_court_waitlist_rotation_index`: int tracking current position for fair rotation through history

**Configuration**
- `session.config.king_of_court_config.court_ordering`: List[int] defining court hierarchy
- Court names stored in session configuration and used in GUI display

### Export Integration
The session export includes King of Court specific information:
- Current round number
- Court ordering (Kings to Bottom)
- Wait counts for all players (ordered by waitlist history)
- Waitlist history showing progression of who has waited
- Current rotation index for debugging waitlist fairness

### GUI Integration
- **Active Session**: Shows current matches, waitlist, and round number
- **Manage Court**: Allows reordering court hierarchy via drag-and-drop
- **Session Setup**: Provides initial seeding options for King of Court mode
- **Pre-seeded Ratings**: Supports skill-based initial seeding (Highest to Lowest / Lowest to Highest)

### Algorithm Validation
Comprehensive test suite validates:
- Winners move up and split correctly
- Losers move down and split correctly
- Waitlist rotation follows King of Court rules
- Nobody waits more than once until everyone has waited
- Court ordering is respected
- Team splitting occurs correctly
- Waitlist history tracking works properly
- Fair rotation cycles correctly through history without bias

Key tests: 
- `test_king_of_court_comprehensive.py` runs 6 rounds with 19 players, 4 courts and validates all rules
- `test_waitlist_rotation_fix.py` validates fair rotation logic and ensures proper cycling

### Recent Fixes & Improvements

**Waitlist Rotation Bug Fix (December 2025)**
- **Problem**: Players were getting stuck on waitlist after everyone waited once, leading to unfair distribution
- **Root Cause**: Waitlist history was being re-ordered when players waited again, causing rotation logic to malfunction
- **Solution**: Made waitlist history immutable - players never change position once added
- **Implementation**: Added `king_of_court_waitlist_rotation_index` to track cycling through fixed history
- **Result**: Guaranteed fair rotation with maximum time between waits for each player
- **Validation**: `test_waitlist_rotation_fix.py` confirms rotation index advances correctly and produces fair distribution

### Known Limitations & Design Decisions

1. **Court Movement Over Partnership Constraints**: King of Court prioritizes proper court movement over avoiding partnerships. Players may occasionally partner with recent teammates if necessary for correct court progression.

2. **Rounds-Based System**: Unlike Competitive Variety's continuous play, King of Court waits for ALL courts to finish before advancing. This ensures proper movement logic.

3. **Team Splitting Requirement**: Teams ALWAYS split after each game. There is no mechanism for teams to stay together across rounds.

4. **Waitlist Fairness**: The algorithm strongly enforces that nobody waits twice until everyone waits once, which may occasionally override other preferences.

5. **Court Capacity Management**: With fixed court capacity, the waitlist size is deterministic: max(0, total_players - courts*4).

### Testing
- **Unit Tests**: Individual function validation
- **Integration Tests**: Complete session workflows
- **Comprehensive Test**: 6-round validation with 19 players, 4 courts
- **Makefile Target**: `make test_king_of_court_comprehensive`

The algorithm ensures fair, balanced King of Court play while maintaining the competitive court hierarchy and proper team rotation.

**Session Manager API**
```python
# Create session manager
manager = create_session_manager(session)

# Handle business events
success, slides = manager.handle_match_completion(match_id, team1_score, team2_score)
success = manager.handle_match_forfeit(match_id)
manager.handle_player_addition(new_players)
manager.handle_player_removal(player_ids)
manager.handle_settings_change('variety', value=4.0)
manager.handle_manual_match_creation(court_number, team1, team2)
manager.force_session_evaluation()
```

**Event System**
- `session_updated`: Session state has changed
- `matches_changed`: Match assignments have changed  
- `match_completed`: A match was completed
- `match_forfeited`: A match was forfeited
- `player_added/removed`: Player roster changes
- `round_advanced`: King of Court round progression

**Architectural Benefits**
- **Maintainable**: Business logic centralized in testable services
- **Testable**: Complete test coverage without GUI dependencies
- **Extensible**: Easy to add new features via service methods
- **Reliable**: Consistent state management through single source of truth
- **Performance**: Efficient event-driven updates instead of polling

### Critical Bug Fixes Applied

**Court Sliding Interference (FIXED)**
- Disabled court sliding for King of Court mode in `session.py` line 451
- Court positions have specific hierarchical meaning in King of Court
- Prevents match tracking corruption during completion

**Round Number Initialization (FIXED)**  
- `initialize_king_of_court_session()` now sets `king_of_court_round_number = 1`
- Prevents system from re-initializing after first match completion
- Ensures proper rounds-based evaluation logic

**GUI Match Creation Bypass (FIXED)**
- Replaced all direct `populate_empty_courts()` calls with `evaluate_and_create_matches()`
- GUI events (sliders, buttons) now properly route through game mode logic
- Prevents immediate match creation that bypasses King of Court rules

**Rounds-Based Behavior Enforced**
- Matches only created when ALL current matches complete
- Individual match completion properly waits for round completion  
- Round advancement follows proper winner/loser movement logic

**King of Court Algorithm Fixed (CRITICAL)**
- **Individual Player Movement**: Winners and losers now split and move individually, not as intact teams
- **Correct Court Movement**: Winners move up one court level, losers move down one court level
- **Team Splitting Enforced**: All winning teams automatically split (core King of Court rule)
- **Random Team Formation**: New matches formed by randomly pairing players at each court level
- **Proper Court Hierarchy**: Court ordering correctly determines kings court vs bottom court progression
