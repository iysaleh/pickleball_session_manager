# Python Source Modules

Core source code for the Pickleball Session Manager desktop application.

> **Note:** This directory is replaced by the auto-updater when new versions are installed. User data (`exports/`, `logs/`, player files) is preserved separately.

## Module Overview

### GUI & Application
| Module | Description |
|--------|-------------|
| `gui.py` | PyQt6 GUI — session setup, active session display, match management |
| `update_ui.py` | Update notification and download UI components |
| `time_manager.py` | Match and session timer management |
| `sleep_inhibitor.py` | Prevents system sleep during active sessions |

### Matchmaking Algorithms
| Module | Description |
|--------|-------------|
| `competitive_variety.py` | ELO-based matchmaking with skill brackets, variety constraints, and adaptive balance |
| `kingofcourt.py` | Rounds-based King of the Court with court movement and fair waitlist rotation |
| `competitive_round_robin.py` | Pre-scheduled tournament with continuous flow and human approval |
| `roundrobin.py` | Basic round robin partner diversity optimization |

### Session Management
| Module | Description |
|--------|-------------|
| `session.py` | Session lifecycle — creation, player management, match completion |
| `session_manager.py` | Event-driven session management service layer |
| `session_persistence.py` | Auto-save and session resume logic |
| `session_logger.py` | Session event logging |
| `queue_manager.py` | Court assignment and waiting queue management |

### Supporting Modules
| Module | Description |
|--------|-------------|
| `pickleball_types.py` | Data types — Player, Session, Match, Config dataclasses |
| `utils.py` | Utility functions — ID generation, shuffling, validation |
| `wait_priority.py` | Time-based wait priority with tier system (extreme/significant/normal) |
| `updater.py` | Auto-update system — checks GitHub releases and installs updates |
| `version.py` | Version tracking (single source of truth) |

### Round Robin Variants
| Module | Description |
|--------|-------------|
| `continuous_wave_flow.py` | Continuous wave-based scheduling for round robin |
| `pooled_continuous_rr.py` | Pooled continuous round robin variant |
| `strict_continuous_rr.py` | Strict continuous round robin variant |
| `inter_court_matching.py` | Cross-court player matching logic |
| `inter_court_mixing.py` | Cross-court player mixing optimization |
| `deterministic_waitlist.py` | Deterministic waitlist ordering |
| `deterministic_waitlist_v2.py` | Improved deterministic waitlist |

## Compatibility

- Python 3.8+
- PyQt6 6.6.1
- Cross-platform (Windows, macOS, Linux)
