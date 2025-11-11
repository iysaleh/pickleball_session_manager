# Python Port Development Guide

## Project Overview

This is an **incremental migration** of the TypeScript Pickleball Session Manager to Python with a PyQt6 GUI. The migration is being done phase-by-phase to manage complexity and maintain quality.

## Phase 1: Round Robin (✅ COMPLETE)

### What's Implemented

1. **Core Data Types** (`python/types.py`)
   - Player, Session, Match, PlayerStats
   - Configuration classes for different modes
   - All TypeScript types converted to Python dataclasses

2. **Round Robin Matchmaking** (`python/roundrobin.py`)
   - Advanced diversity algorithm
   - Optimizes for different partners and opponents
   - Respects banned pairs
   - Works with both singles (1v1) and doubles (2v2)

3. **Session Management** (`python/session.py`)
   - Create, add players, remove players
   - Complete matches with scores
   - Forfeit matches
   - Track all player statistics

4. **Queue Management** (`python/queue_manager.py`)
   - Populate empty courts with matches from queue
   - Track waiting players
   - Manage session advancement

5. **PyQt6 GUI** (`python/gui.py`)
   - Setup dialog for new sessions
   - Main session window with court displays
   - Match controls (complete, forfeit)
   - Real-time updates via timer

6. **Comprehensive Tests** (`test_roundrobin.py`)
   - 8 tests covering all major functionality
   - Queue generation, session management, stats tracking
   - All tests passing ✅

### How Round Robin Works

Round Robin generates matches that maximize player diversity:

```
Input: 8 players (Alice, Bob, Charlie, Diana, Eve, Frank, Grace, Henry)
Mode: Doubles (2v2)

Algorithm:
1. Generate all possible 4-player combinations
2. For each combination, try 3 possible team pairings:
   - (A,B) vs (C,D)
   - (A,C) vs (B,D)
   - (A,D) vs (B,C)
3. Score each potential match on:
   - New partnerships (boost: +50 per new teammate)
   - Repeated partnerships (penalty: -30 per repeat)
   - New opponents (boost: +20 per new opponent)
   - Repeated opponents (penalty: -15 per repeat)
   - Same 4-player group recently (penalty: -200)
   - Fair play time (boost: +30 for underutilized players)
4. Pick highest-scoring match
5. Update tracking and repeat

Result: Diverse matches where players constantly play with and against new people
```

## Phase 2: King of the Court (🚧 SKELETON READY)

### What Needs Implementation

Files that are skeletons, ready for Phase 2:
- `python/kingofcourt.py` - Main KOC logic

### KOC Features Required

1. **ELO-style Rating System**
   - Starting rating: 1500
   - K-factor: 32
   - Min/max clamping
   - Logarithmic win-rate scaling

2. **Rank-Based Matchmaking**
   - Calculate player rankings (1 = best)
   - 50% rule: Top-half only plays top-half, etc.
   - Close-rank prioritization
   - Provisional player handling

3. **Strategic Waiting**
   - Don't rush to fill courts with bad matchups
   - Wait for better opponent quality
   - Fair waiting distribution

4. **Variety Optimization**
   - Track which players have played together recently
   - Avoid repetition even within rank brackets
   - Back-to-back overlap thresholds

### Implementation Roadmap for KOC

```python
# Basic implementation:
def calculate_player_rating(stats) -> float:
    """Convert wins/losses to 800-2200 rating range"""

def get_player_rank(player_id, all_stats) -> int:
    """Get player's rank among all players"""

def get_matchmaking_range(player_id, all_stats) -> List[str]:
    """Get list of players in matchable range"""

# Intermediate:
def score_koc_matchup(team1, team2, constraints) -> float:
    """Score match quality for KOC"""

def select_best_koc_match(available, constraints) -> Tuple:
    """Pick best match from available players"""

# Advanced:
def evaluate_koc_session(session) -> Session:
    """Main session loop - continuous match generation"""
```

## Phase 3: Advanced Features

Planned for Phase 3:
- Session persistence (save/load to files)
- Locked teams mode
- Enhanced statistics UI
- History viewer and score editing
- Player profiles
- Dark/light mode toggle

## Phase 4: UI/UX Polish

- Better court layout visualization
- Real-time statistics dashboard
- Better responsive design
- Export session data
- Statistics analytics

## Development Workflow

### Adding a New Feature

1. **Define types** in `python/types.py` if needed
2. **Implement logic** in appropriate module
3. **Write tests** in `test_roundrobin.py` (or new test file)
4. **Update GUI** in `python/gui.py` if user-facing
5. **Run tests** to verify

### Testing Strategy

```bash
# Run all tests
python test_roundrobin.py

# Run specific test
python test_roundrobin.py TestRoundRobinBasics.test_round_robin_queue_generation_doubles

# Check syntax
python -m py_compile python/*.py
```

### Code Organization

```
Types & Data: types.py
Utilities: utils.py
Algorithms: roundrobin.py, kingofcourt.py (Phase 2)
Session Logic: session.py
Queue Management: queue_manager.py
GUI: gui.py
Tests: test_*.py
```

## Key Design Decisions

### 1. Python Dataclasses Over Dicts
**Why:** Type safety, autocomplete, cleaner code
```python
# ❌ Bad
player = {"id": "p1", "name": "Alice"}
player.get("unknown")  # Returns None, hard to debug

# ✅ Good
player = Player(id="p1", name="Alice")
player.unknown  # TypeError immediately caught
```

### 2. Functional Session Management
**Why:** Easier to test, predict, and debug
```python
# ❌ Bad (mutation)
def add_player(session, player):
    session.players.append(player)  # Modifies in place

# ✅ Good (pure functions where possible)
def add_player_to_session(session, player) -> Session:
    # Returns new or modified session
```

### 3. Separate Queue Manager
**Why:** Clean separation of concerns, easier to test court filling logic
```
Session: Owns players, matches, stats
QueueManager: Handles match distribution logic
GUI: Handles rendering and user interaction
```

### 4. PyQt6 Over Tkinter
**Why:**
- Modern widgets
- Cross-platform polish
- Better layout system
- More professional appearance
- Active development

## File Reference

### `python/types.py` (160 lines)
Core data structures. Easy to understand the data model by reading this file.

**Key Classes:**
- `Player` - Individual player
- `Session` - Entire session state
- `Match` - Single game
- `PlayerStats` - Per-player statistics
- `SessionConfig` - Configuration for new sessions

### `python/utils.py` (100 lines)
Helper functions used throughout the app.

**Key Functions:**
- `generate_id()` - Create unique identifiers
- `shuffle_list()` - Randomize player order
- `is_pair_banned()` - Check if pair can play together
- `get_default_advanced_config()` - Get default settings

### `python/roundrobin.py` (300 lines)
Round Robin matchmaking algorithm.

**Key Functions:**
- `generate_round_robin_queue()` - Generate optimized matches
- Internal scoring function for quality

**Algorithm:**
1. Generate all possible 4-player combos
2. Try all valid pairings for each combo
3. Score on partnership/opponent diversity
4. Pick best, mark as used, repeat

### `python/session.py` (250 lines)
Session lifecycle and statistics management.

**Key Functions:**
- `create_session()` - Initialize new session
- `add_player_to_session()` - Add player dynamically
- `complete_match()` - Finish a match, update stats
- `forfeit_match()` - Mark match as forfeited
- Stat tracking for wins, losses, partners, opponents

### `python/queue_manager.py` (150 lines)
Match queue and court management.

**Key Functions:**
- `get_empty_courts()` - Find courts with no active match
- `populate_empty_courts()` - Fill empty courts from queue
- `get_waiting_players()` - Get players not in matches

### `python/gui.py` (500 lines)
PyQt6 graphical interface.

**Key Classes:**
- `MainWindow` - Entry point
- `SetupDialog` - Session configuration
- `SessionWindow` - Active session display
- `CourtDisplayWidget` - Single court display

### `python/kingofcourt.py` (150 lines)
King of the Court skeleton (Phase 2).

**To Implement:**
- `calculate_player_rating()` - ELO calculation
- `get_player_rank()` - Player's rank
- `get_players_in_matchmaking_range()` - Matchable opponents
- `select_best_koc_match()` - Pick best KOC match
- `evaluate_koc_session()` - Main KOC loop

### `test_roundrobin.py` (300 lines)
Comprehensive unit tests.

**Test Classes:**
- `TestRoundRobinBasics` - Queue generation
- `TestSessionManagement` - Session lifecycle
- `TestPlayerStats` - Statistics tracking

## Running the Application

### Installation

```bash
# Install Python 3.8+
# Install dependencies
python -m pip install -r requirements.txt
```

### Running

```bash
# Run GUI application
python main.py

# Run tests
python test_roundrobin.py

# Check syntax
python -m py_compile python/*.py
```

## Common Tasks

### Add a New Test

```python
def test_new_feature(self):
    """Test description"""
    # Arrange
    players = [Player(id="p1", name="Alice"), ...]
    
    # Act
    result = some_function(players)
    
    # Assert
    self.assertEqual(result, expected)
```

### Implement KOC Rating Calculation

```python
import math

def calculate_player_rating(stats, base_rating=1500):
    if stats.games_played == 0:
        return base_rating
    
    win_rate = stats.wins / stats.games_played
    adjustment = math.log(1 + win_rate * 9) * 200
    rating = base_rating + adjustment - 200
    
    return max(800, min(2200, rating))
```

### Add GUI Element

```python
# In SessionWindow.init_ui():
self.new_widget = QLabel("New Feature")
self.new_widget.setFont(QFont("Arial", 12))
layout.addWidget(self.new_widget)

# In update method:
self.new_widget.setText(f"Value: {calculated_value}")
```

## Debugging

### Enable Verbose Output

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Single Component

```bash
# Run one test class
python -m pytest test_roundrobin.py::TestRoundRobinBasics -v

# Run one test method
python -m pytest test_roundrobin.py::TestRoundRobinBasics::test_round_robin_queue_generation_doubles -v
```

### Inspect Objects

```python
# In tests or debugging
print(session.__dict__)
print(player.__dict__)

# Pretty print
import pprint
pprint.pprint(session.__dict__)
```

## Performance Considerations

- Round Robin queue generation: O(n^4) for n players (all 4-player combos)
- For 8 players: ~70 combinations × 3 pairings = ~210 matchups to score
- Generation happens once at session start, then served from queue
- Acceptable for 8-18 players (typical session size)

## Next Steps for Contributors

1. **Review Phase 1**: Understand Round Robin algorithm
2. **Run tests**: Verify everything works
3. **Study TypeScript version**: Reference `src/kingofcourt.ts` for KOC logic
4. **Implement Phase 2**: Port KOC algorithm to Python
5. **Add KOC GUI**: Add mode selection in SetupDialog
6. **Test thoroughly**: Add KOC tests before moving forward

## References

- **TypeScript Implementation**: `src/` directory
- **Original Requirements**: `notes/prompts_used.txt`
- **GUI Framework**: [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
