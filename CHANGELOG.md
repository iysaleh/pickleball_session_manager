# Changelog

## Version 2.2 - Court Stability & Improvements (Current)

### Bug Fixes & Improvements

#### ✅ Score Validation
- **FIXED**: Cannot submit tied scores (5-5, 11-11, etc.)
- **FIXED**: Cannot submit negative scores
- Validation alerts explain the issue
- Ensures valid match results

#### 🔢 Better Score Display
- **FIXED**: Score input font size reduced for readability
- Changed from 1.2em to 0.95em
- Numbers easier to see and input
- Better visual balance in controls

#### 🔄 New Player Priority
- **FIXED**: Players added mid-session now get priority
- New players automatically placed at front of queue
- Set to have "waited" longer than anyone else
- Ensures fair rotation for late arrivals

### Quality of Life Improvements

#### 🎛️ Court Layout Controls
- **NEW**: Manually control courts per row (1-6)
- Input field and "Apply" button in Active Courts header
- Defaults to 2 courts per row
- Dynamically adjusts grid layout
- Responsive: Auto-stacks on mobile
- Perfect for different screen sizes and preferences

#### 🔄 Edit Session Feature
- **NEW**: "Edit Session" button in session controls
- Keeps all players when ending session
- Returns to setup screen with players preserved
- Change game mode, courts, or banned pairs
- Start fresh session without re-entering players
- Separate from "End Session" which clears everything

## Version 2.2 - Court Stability & Improvements

### Major Improvements

#### 🎯 Static Court Positions
- **FIXED**: Courts now maintain their positions and numbers
- Courts render in ascending order (1, 2, 3...) always
- Empty courts displayed with "Available" status
- No more jumping around when matches complete
- Easy to map on-screen courts to physical courts

#### 📜 Per-Court Match History
- **NEW**: Each court shows its last 3 completed matches
- Displays right in the court card when empty
- Shows scores, team names, and match status
- Indicates if more matches exist ("+5 more...")
- Great for tracking court utilization

#### 🔧 Fixed Team Box Overflow
- **FIXED**: Long player names no longer break layout
- Added text truncation with ellipsis
- Proper overflow handling
- Centered text alignment
- Professional appearance maintained

### Technical Changes
- Modified `evaluateAndCreateMatches()` to assign courts in order
- Added `renderEmptyCourt()` function for empty court display
- Updated court rendering to show ALL courts (not just active)
- Enhanced CSS for overflow protection and empty court styling
- Added `updateCourtsGridLayout()` for dynamic grid adjustment
- Changed CSS from auto-fit to fixed column count

---

## Version 2.1 - Match History & UI Improvements

### New Features

#### 🧪 Test Mode
- **NEW**: Access with `?test=true` query parameter
- Displays special "Add 18 Test Players" button
- Instantly adds 18 players with realistic names
- Perfect for development and testing
- Clears existing players when used

#### 📜 Match History
- **NEW**: "Show History" button to view all completed/forfeited matches
- Shows most recent matches first
- Displays:
  - Court number
  - Match status (Completed/Forfeited)
  - Team names
  - Final scores (for completed matches)
  - Winner/loser highlighting

#### ✏️ Edit Match Scores
- **NEW**: Edit scores of any completed match
- Inline score editing in match history
- Stats automatically recalculated when scores change
- Use cases:
  - Score was entered incorrectly
  - Need to correct a mistake
  - Disputed score resolution

#### 🎨 Improved Court Layout
- **REDESIGNED**: Court display now uses horizontal layout
- Team 1 displayed on the LEFT (with blue border)
- Match controls and score in the MIDDLE
- Team 2 displayed on the RIGHT (with purple border)
- Much more intuitive visual flow
- Larger, clearer team boxes

### Technical Changes
- Modified `completeMatch()` to support editing completed matches
- Added `renderMatchHistory()` function
- Added `toggleHistory()` function
- Added history section to UI
- Enhanced CSS for horizontal court layout
- Added winner/loser styling in history

---

## Version 2.0 - Continuous Queue System

### Major Changes

#### 🎯 Continuous Queue System
- **REMOVED**: "Start Next Round" button - no more manual round management
- **NEW**: Automatic match creation whenever courts become available
- Matches are evaluated and created after:
  - Session starts
  - Match completes (with scores)
  - Match forfeited
  - Player added to session
  - Player removed from session

#### 👥 Dynamic Player Management
- **NEW**: Add players during active session
  - Input field in session controls
  - Automatically tries to create matches with new player
  - Player immediately enters queue system
  
- **NEW**: Remove players from active session
  - Players marked as "inactive" (not deleted from history)
  - Any active/waiting matches with that player are forfeited
  - Court freed immediately for new match
  
- **NEW**: Reactivate players
  - Can bring inactive players back into the session
  - Automatically triggers match evaluation

#### ⚠️ Match Forfeiting
- **NEW**: Forfeit button on each match
- Forfeited matches:
  - Do NOT count toward wins/losses
  - Do NOT record any statistics
  - Free up the court immediately
  - Trigger new match creation
- Use cases:
  - Player needs to leave mid-match
  - Injury or other issue
  - Match can't be completed

#### 📊 Player Status Display
- **NEW**: Active players list in session controls
- Shows all players with their status:
  - Active (can remove)
  - Inactive (can reactivate)
- Visual distinction with styling

### Technical Changes

#### Type Definitions
- Added `'forfeited'` status to `Match` type
- Added `activePlayers: Set<string>` to `Session` type
- Removed `currentRound` from `Session` type

#### Session Functions
- Renamed: `addPlayer` → `addPlayerToSession`
- Renamed: `removePlayer` → `removePlayerFromSession`
- Renamed: `startNextRound` → `evaluateAndCreateMatches`
- Added: `forfeitMatch()`
- Modified: `completeMatch()` now calls `evaluateAndCreateMatches()`
- Modified: `removePlayerFromSession()` forfeits matches and re-evaluates
- Modified: `addPlayerToSession()` triggers match evaluation

#### UI Changes
- Removed "Start Next Round" button
- Removed "Round X" display
- Added player management UI in session controls
- Added "Forfeit" button to each match
- Added inactive player styling
- Added reactivate functionality

### Behavior Changes

#### Before (v1.0)
1. User starts session
2. User clicks "Start Next Round" manually
3. Matches created for all available courts
4. User enters scores
5. User manually clicks "Start Next Round" again
6. Repeat...

#### After (v2.0)
1. User starts session → matches automatically created
2. User enters scores → new matches automatically created
3. Player leaves? Remove them → match forfeited, new match created
4. Player arrives late? Add them → new match created if possible
5. Continuous flow with no manual round management

### Migration Notes

If you have existing code using v1.0:

```typescript
// OLD v1.0
import { addPlayer, removePlayer, startNextRound } from './session';
session = startNextRound(session);

// NEW v2.0
import { addPlayerToSession, removePlayerFromSession, evaluateAndCreateMatches } from './session';
session = evaluateAndCreateMatches(session);
// Or more commonly, this happens automatically now
```

### Breaking Changes
- ❌ `currentRound` no longer exists in Session
- ❌ `addPlayer()` renamed to `addPlayerToSession()`
- ❌ `removePlayer()` renamed to `removePlayerFromSession()`
- ❌ `startNextRound()` renamed to `evaluateAndCreateMatches()`
- ❌ Removing a player no longer deletes them from history
- ✅ All removed players are now marked as inactive instead

### Bug Fixes
- Fixed issue where players couldn't be added during session
- Fixed issue where removing player from active match didn't free the court
- Improved match generation to handle edge cases better

---

## Version 1.0 - Initial Release

### Features
- Round-based session management
- Three game modes: Round Robin, King of the Court, Teams
- Singles and Doubles support
- Banned pairs
- Statistics tracking
- Manual round progression
- Static player list (set before session starts)

