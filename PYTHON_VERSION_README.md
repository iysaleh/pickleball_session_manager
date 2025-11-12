# Pickleball Session Manager - Python GUI Version

A professional-grade pickleball session management tool written in Python with a PyQt6 GUI.

**Status: Incremental Migration in Progress**
- ✅ Round Robin matchmaking engine
- ✅ Session management
- ✅ Player statistics tracking
- ✅ Basic PyQt6 GUI
- ✅ Test suite (8 tests passing)
- ⏳ King of the Court mode (next phase)
- ⏳ Advanced features (coming in next revisions)

## Requirements

- Python 3.8+
- PyQt6 6.6.1

## Installation

```bash
# Install dependencies
python -m pip install -r requirements.txt
```

## Running the Application

```bash
# Run the GUI application
python main.py
```

## Features Implemented (Phase 1: Round Robin)

### 1. Session Setup
- Create new pickleball sessions
- Choose game mode (Round Robin or King of the Court - KOC placeholder)
- Select session type (Doubles or Singles)
- Configure number of courts
- Add players individually or with test data

### 2. Round Robin Matchmaking
- Advanced algorithm that maximizes player diversity
- Optimizes for:
  - Different partners each game
  - Different opponents each game
  - Fair play time distribution
  - Respects banned pairs (players who won't play together)
- Supports both singles (1v1) and doubles (2v2)

### 3. Session Management
- View active matches on each court
- Input scores for completed matches
- Forfeit matches without recording results
- Add/remove players dynamically during session
- Track player statistics in real-time

### 4. Player Statistics
- Games played and waited
- Wins and losses
- Total points for/against
- Partnership history
- Opponent history
- Win rate calculation

### 5. Match History
- Complete game history with scores
- Edit scores if mistakes occurred (coming soon)
- View by court or chronologically

## Architecture

### Core Modules

**python/types.py**
- Data types and configuration classes
- Player, Session, Match, PlayerStats

**python/utils.py**
- Utility functions
- ID generation, shuffling, pair validation
- Default configuration

**python/roundrobin.py**
- Round Robin matchmaking algorithm
- Generates optimized match queues
- Tracks diversity metrics

**python/session.py**
- Session creation and management
- Match completion and forfeiture
- Player addition/removal
- Statistics tracking

**python/gui.py**
- PyQt6 GUI implementation
- Setup dialog
- Court displays
- Match controls

## Testing

Run the test suite:

```bash
python test_roundrobin.py
```

Tests cover:
- Round Robin queue generation (doubles/singles)
- Banned pairs handling
- Session creation
- Player addition/removal
- Match completion with score validation
- Forfeit handling
- Player statistics tracking

## Future Phases

### Phase 2: King of the Court Mode
- ELO-style ranking system
- Rank-based matchmaking
- Provisional player rankings
- Strategic waiting for better matchups
- Close-rank prioritization

### Phase 3: Advanced Features
- Locked teams mode
- Match history editing
- Session persistence (save/load)
- Rankings display
- Statistics analytics
- Dark mode / Light mode toggle
- Player profiles

### Phase 4: UI/UX Improvements
- Real-time match queue display
- Better court layout visualization
- Statistics dashboard
- Responsive design improvements
- Export session data

## Design Decisions

1. **PyQt6 for GUI**: Cross-platform, native look, feature-rich
2. **Phase-based approach**: Incremental migration reduces risk and testing overhead
3. **Dataclass-based types**: Clean, maintainable data structures
4. **Functional session management**: Pure functions where possible for testability
5. **Comprehensive testing**: Unit tests for all major functionality

## Development Progress

**Completed:**
- Core data types and structures
- Round Robin matchmaking algorithm with diversity optimization
- Session creation and player management
- Match completion and forfeiture with stats tracking
- Player statistics tracking (wins, losses, partnerships, opponents)
- Basic PyQt6 GUI with court displays
- Comprehensive test suite

**In Progress:**
- GUI refinements (better layouts, real-time updates)
- Court display improvements

**Planned:**
- King of the Court mode implementation
- Advanced configuration UI
- Match history viewer/editor
- Session persistence
- Statistics and analytics display

## File Structure

```
pickleball_rework_python/
├── python/
│   ├── __init__.py
│   ├── types.py           # Core data types
│   ├── utils.py           # Utility functions
│   ├── roundrobin.py      # Round Robin matchmaking
│   ├── kingofcourt.py     # KOC mode (coming)
│   ├── session.py         # Session management
│   └── gui.py             # PyQt6 GUI
├── main.py                # Entry point
├── test_roundrobin.py     # Unit tests
├── requirements.txt       # Dependencies
└── README.md             # This file
```

## Notes

This is an incremental migration from the TypeScript web application to a Python desktop application. The goal is to maintain feature parity while providing a more robust, local-machine experience.

The original TypeScript implementation can be found in the `src/` directory for reference during development.

## License

Same as original project
