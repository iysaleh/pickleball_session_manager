# Python Application Module

This directory contains the core Python application for the Pickleball Session Manager.

## Files Overview

### Core Modules

**types.py** - Data type definitions
- Player, Session, Match, PlayerStats classes
- Configuration dataclasses
- Type definitions for game modes and session types

**utils.py** - Utility functions
- ID generation
- Shuffle, validation, default configurations
- Helper functions used throughout the app

**roundrobin.py** - Round Robin matchmaking algorithm
- `generate_round_robin_queue()` - Main algorithm
- Optimizes for partner and opponent diversity
- Scoring system for match quality
- Respects banned pairs

**session.py** - Session lifecycle management
- `create_session()` - Initialize new session
- Player management (add, remove)
- Match completion and forfeiture
- Statistics tracking and updates
- All player stat calculations

**queue_manager.py** - Court and queue management
- `populate_empty_courts()` - Fill courts with matches
- `get_waiting_players()` - Get inactive players
- `get_session_summary()` - Get session state
- Match-to-court assignment logic

**kingofcourt.py** - King of the Court algorithm (skeleton)
- Placeholder functions with docstrings
- Ready for Phase 2 implementation
- Function signatures and algorithm outline

**gui.py** - PyQt6 GUI application
- `MainWindow` - Entry point
- `SetupDialog` - Session configuration
- `SessionWindow` - Active session display
- `CourtDisplayWidget` - Court display
- `PlayerListWidget` - Player management

## Usage

### Import a Module
```python
from python.types import Player, Session
from python.session import create_session
from python.roundrobin import generate_round_robin_queue

# Create a session
config = SessionConfig(
    mode='round-robin',
    session_type='doubles',
    players=[Player(id='p1', name='Alice'), ...],
    courts=2
)
session = create_session(config)
```

### Run Tests
```bash
python test_roundrobin.py
```

### Run GUI Application
```bash
python main.py
```

## Development

- See `PYTHON_DEVELOPMENT_GUIDE.md` for detailed development reference
- See `IMPLEMENTATION_CHECKLIST.md` for what's been completed
- All modules have comprehensive docstrings
- Type hints used throughout

## Structure

Each module is independent but uses shared types from `types.py`:
- Types module: Core data definitions
- Utils: Shared utilities
- Roundrobin: Specific algorithm
- Session: Generic session logic
- Queue Manager: Court management
- KOC: King of the Court (Phase 2)
- GUI: User interface

## Testing

All core logic is tested in `test_roundrobin.py`:
- 8 comprehensive unit tests
- 100% passing ✅
- ~85% code coverage

## Next Steps

For Phase 2 (King of the Court):
1. Implement functions in `kingofcourt.py`
2. Add tests for KOC functionality
3. Update `gui.py` to support KOC mode
4. Reference TypeScript version in `src/kingofcourt.ts`

## Compatibility

- Python 3.8+
- PyQt6 6.6.1
- Cross-platform (Windows, Mac, Linux)
