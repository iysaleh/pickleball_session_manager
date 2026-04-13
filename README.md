# 🎾 Pickleball Session Manager

A desktop application for managing pickleball play sessions with intelligent matchmaking, multiple game modes, and fair player rotation.

🌐 **Website:** [betterpickleballsessions.com](https://betterpickleballsessions.com/)

## ✨ Features

### Game Modes
- **Competitive Variety** — ELO-based matchmaking with skill brackets, partner/opponent variety constraints, and adaptive balance
- **King of the Court** — Rounds-based court hierarchy where winners move up and losers move down, with fair waitlist rotation
- **Round Robin** — Maximizes partner diversity across all players
- **Competitive Round Robin** — Pre-scheduled tournament with continuous court flow and human-in-the-loop approval
- **Locked Teams** — Fixed partnerships throughout the session

### Matchmaking
- **ELO Rating System** — Skill-based player ratings with provisional player handling
- **Roaming Range** — Skill bracket windows to keep matches competitive
- **Hard Variety Constraints** — Prevents excessive partner/opponent repetition
- **Adaptive Balance** — Progressively tightens balance requirements as sessions progress
- **Wait Time Priority** — Time-based priority system ensures fair court access

### Session Management
- **Multi-Court Support** — Manage 1–10+ courts simultaneously
- **Dynamic Player Management** — Add/remove players mid-session
- **Session Persistence** — Auto-save and resume sessions
- **Match History** — Full match history with score editing
- **Session Export** — Export session data for analysis
- **Built-in Auto-Updater** — Automatically checks for and installs new versions

### Statistics & Rankings
- Win/loss records and win rates
- ELO ratings and ranking progression
- Partner and opponent diversity tracking
- Wait time tracking per player

## Screenshots

<!-- SCREENSHOT: Replace the placeholder images below with actual screenshots -->
<!-- Create a screenshots/ directory and add your images there -->

| Session Setup | Active Session |
|:---:|:---:|
| ![Session Setup](screenshots/setup.png) | ![Active Session](screenshots/active.png) |

| Rankings & Stats | Match History |
|:---:|:---:|
| ![Rankings](screenshots/rankings.png) | ![History](screenshots/history.png) |

## Getting Started

### Requirements
- **Python 3.8+** (download from [python.org](https://www.python.org/downloads/))
- Works on **Windows**, **macOS**, and **Linux**

### Installation

```bash
# 1. Clone or download the repository
git clone https://github.com/iysaleh/pickleball_session_manager.git
cd pickleball_session_manager

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

#### Windows Users
If you encounter issues with PyQt6, use the Windows-specific requirements:
```bash
pip install -r requirements-windows.txt
```

### Create a Desktop Shortcut (Optional)
```bash
python create_shortcut.py
```
This creates a clickable shortcut on your desktop to launch the app.

## Project Structure

```
pickleball_session_manager/
├── main.py                  # Application entry point
├── create_shortcut.py       # Desktop shortcut utility
├── pickleball.ico           # App icon
├── requirements.txt         # Python dependencies
├── Makefile                 # Test targets
├── LICENSE                  # ISC License
├── python/                  # Source code
│   ├── gui.py               # PyQt6 GUI application
│   ├── competitive_variety.py  # Competitive Variety matchmaking
│   ├── kingofcourt.py       # King of the Court algorithm
│   ├── competitive_round_robin.py  # Round Robin tournament
│   ├── session.py           # Session lifecycle management
│   ├── wait_priority.py     # Wait time priority system
│   ├── updater.py           # Auto-update system
│   └── ...                  # Additional modules
├── tests/                   # Test suite (160+ test files)
├── scripts/                 # Debug and demo utilities
├── exports/                 # Session export files
└── logs/                    # Session logs
```

## Running Tests

```bash
# Run the fuzzing test suite
make run_fuzz_tests

# Run a specific test
make test_competitive_round_robin

# See all available test targets
make help
```

## License

ISC — see [LICENSE](LICENSE) for details.

## Contributing

Found a bug or have a feature request? [Open an issue](https://github.com/iysaleh/pickleball_session_manager/issues) on GitHub.
