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
Implements a rounds-based King of the Court system where players move between courts based on match results. Winners advance up the court hierarchy while losers move down, creating a natural skill-based tournament structure.

### Key Features

**Rounds-Based Progression**
- Courts populate only after ALL current matches complete (no partial round starts)
- Winners move up one court level (unless already at kings court)
- Losers move down one court level (unless already at bottom court)  
- Kings court winners stay and split, bottom court losers stay and split
- New matches formed by mixing winners/losers from adjacent court levels

**Court Hierarchy System**
- Configurable court ordering: which court is "kings court" vs "bottom court"
- Default: Court 1 = Kings Court, Court N = Bottom Court
- Drag-and-drop court ordering management via GUI dialog
- Court ordering persists between sessions

**Initial Seeding Options**
- **Random**: Players randomly distributed across courts
- **Highest to Lowest**: Top-rated players start on kings court, lowest on bottom court
- **Lowest to Highest**: Lowest-rated players start on kings court (skill development mode)
- **Pre-seeded Ratings Required**: Highest/Lowest seeding modes auto-enable skill rating input

**Waitlist Management (Smart Priority)**
- Waitlist selection prioritizes middle courts first, then bottom court
- Kings court players only wait after everyone else has waited once
- Fair rotation: no player waits twice until all players have waited once
- Returning players placed back in similar court position when possible

**Team Formation (True King of Court Rules)**
- **Winners Always Split**: Winning teams are automatically split and individual winners move up
- **Losers Always Split**: Losing teams are automatically split and individual losers move down  
- **Random Team Formation**: New teams formed by randomly pairing players at each court level
- **No Partnership Preservation**: Unlike other modes, King of Court always breaks up winning teams
- **Integrates with existing ban/lock systems**: Still respects banned pairs and locked teams

### Core Functions

**Session Management**
- `initialize_king_of_court_session()`: Initial player seeding and match creation
- `evaluate_king_of_court_session()`: Main evaluation loop (called after match completion)
- `advance_round()`: Processes completed matches and creates next round

**Court Movement Logic**  
- `create_next_round_matches()`: Handles winner/loser movement between courts
- `handle_waitlist_for_round()`: Smart waitlist management with court priority
- `create_matches_from_assignments()`: Forms teams avoiding recent partnerships

**Configuration Management**
- `get_court_ordering()`: Returns current court hierarchy
- `set_court_ordering()`: Updates court ordering configuration  
- `seed_players_across_courts()`: Distributes players based on seeding option

**Match Analysis**
- `get_matches_from_current_round()`: Identifies matches from same round
- `can_form_teams_avoiding_repetition()`: Smart team formation with variety

### Integration Points

**Session Creation**
- Automatic initialization when `mode = 'king-of-court'`
- Integrates with first bye players (automatically go to waitlist)
- Compatible with singles/doubles, locked teams, banned pairs

**GUI Integration**
- Setup dialog: Seeding option dropdown (appears for King of Court mode)
- Active session: "⚖️ Court Order" button for court hierarchy management
- Court ordering dialog: drag-and-drop reordering with visual instructions

**Match Completion**
- Auto-triggers round advancement via `evaluate_and_create_matches()`
- Disables court sliding (court positions are meaningful in King of Court)
- Maintains proper court number tracking throughout match lifecycle

### Critical Design Decisions

**Court Sliding Disabled**
- Court sliding logic disabled for King of Court mode (`session.py` line 451)
- Prevents court number corruption during match completion
- Court positions have specific meaning (hierarchy) unlike other game modes

**Round Synchronization** 
- All courts must finish before next round starts
- Prevents partial rounds and maintains fair progression
- Round number tracking via `session.king_of_court_round_number`

**Skill-Based Seeding Integration**
- Highest/Lowest seeding options automatically enable pre-seeded skill ratings
- Uses same ELO calculation as Competitive Variety mode
- GUI automatically shows/hides skill rating inputs based on seeding choice

**Waitlist Priority Algorithm**
- Middle courts preferred for waitlist (balanced skill mixing)
- Bottom court next priority (keeps beginners playing)  
- Kings court last resort (preserves competitive play)
- Prevents double-waiting until global fairness achieved

### Testing & Validation

**Comprehensive Test Suite**
- `test_king_of_court_rounds.py`: Core functionality (seeding, court ordering, byes)
- `test_king_of_court_advancement.py`: Round progression and winner/loser movement
- All seeding options tested (random, highest-to-lowest, lowest-to-highest)
- Singles and doubles mode validation
- Court ordering management verification

**Run King of Court Tests**
```bash
make test_king_of_court_rounds
make test_king_of_court_advancement  
```

**Critical Bug Fix Applied**
- Fixed court sliding interference causing match tracking corruption
- Court numbers now properly maintained throughout match completion
- Round advancement correctly identifies winners/losers by court position

### Architecture Benefits

**Clean Separation**
- Pure business logic in `kingofcourt.py`  
- Session integration in `session.py`
- GUI components in `gui.py`
- Reusable configuration types in `pickleball_types.py`

**Extensible Design**
- Easy to add new seeding algorithms
- Configurable court hierarchies (any number of courts)
- Compatible with all existing session features
- Maintains backward compatibility

**Production Ready**
- Comprehensive error handling and validation
- Proper persistence and session restoration
- Integration with wait time priority system
- Full GUI support with intuitive controls
- **Clean Architecture**: Business logic separated from GUI via Session Manager Service

### Session Manager Service Architecture

**Clean Separation of Concerns**
- **SessionEventHandler**: Centralized business logic service that handles all session state changes
- **GUI Layer**: Thin presentation layer that delegates to SessionEventHandler via events
- **Testable Design**: All session logic is testable in isolation without GUI dependencies
- **Event-Driven**: GUI listens to session events and updates accordingly

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
