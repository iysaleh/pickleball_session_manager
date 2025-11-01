# Edit Session Feature

## Overview

The Edit Session feature allows users to reconfigure a session (game mode, courts, banned pairs) without losing their player list.

## Problem Solved

**Before:** 
- User starts session with 18 players
- Realizes they want different mode or court count
- Clicks "End Session"
- ❌ All 18 players lost
- Must re-enter all players manually

**After:**
- User starts session with 18 players
- Realizes they want different configuration
- Clicks "Edit Session"
- ✅ All 18 players preserved
- Returns to setup screen
- Changes settings
- Starts new session with same players

## User Interface

### Button Placement

Located in Session Controls alongside:
- Show Statistics
- Show History
- **Edit Session** (new - yellow/warning)
- End Session (red/danger)

### Button Styling

```css
.btn-warning {
  background: #ffc107;  /* Gold/yellow */
  color: #000;          /* Black text */
  font-weight: 600;
}
```

Visual distinction from "End Session" (red) to indicate different behavior.

## Behavior

### Edit Session Flow

```
1. User clicks "Edit Session"
2. Confirmation prompt:
   "This will end the current session but keep all players. 
    You can then reconfigure and start a new session. Continue?"
3. If confirmed:
   - Current session cleared
   - Players preserved
   - Banned pairs preserved
   - Returns to setup section
   - Success message: "✅ Session ended. Players saved..."
4. User can now:
   - Change game mode
   - Adjust court count
   - Modify banned pairs
   - Add/remove players
   - Start new session
```

### End Session Flow (Updated)

```
1. User clicks "End Session"
2. Confirmation prompt:
   "Are you sure you want to end the session? 
    All data (including players) will be lost."
3. If confirmed:
   - Current session cleared
   - Players cleared
   - Banned pairs cleared
   - Returns to setup section
```

## What's Preserved

### Edit Session Preserves:
- ✅ All players (active and inactive)
- ✅ All banned pairs
- ❌ Match history
- ❌ Statistics
- ❌ Current matches

### End Session Clears:
- ❌ All players
- ❌ All banned pairs
- ❌ Match history
- ❌ Statistics
- ❌ Current matches

## Use Cases

### 1. Wrong Mode Selected
```
Scenario: Started Round Robin, wanted King of Court
Solution: Edit Session → Change mode → Start Session
Result: Same 18 players, different mode
```

### 2. Court Count Mismatch
```
Scenario: Set 2 courts, actually have 4 courts
Solution: Edit Session → Change courts to 4 → Start Session
Result: Same players, more courts available
```

### 3. Add Banned Pairs Mid-Session
```
Scenario: Players don't want to partner together
Solution: Edit Session → Add banned pairs → Start Session
Result: Same players, new restrictions
```

### 4. Complete Reset
```
Scenario: Done for the day, new group coming
Solution: End Session (not Edit)
Result: Clean slate, ready for new players
```

## Technical Implementation

### State Management

```typescript
function handleEditSession() {
  // Confirm action
  if (!confirm('...keep all players...')) return;
  
  // Clear session only
  currentSession = null;
  
  // players and bannedPairs arrays remain intact
  
  // Show setup, hide others
  setupSection.classList.remove('hidden');
  controlSection.classList.add('hidden');
  courtsSection.classList.add('hidden');
  statsSection.classList.add('hidden');
  matchHistorySection.classList.add('hidden');
  
  // Re-render preserved data
  renderPlayerList();
  updateBannedPairSelects();
  renderBannedPairs();
  
  // Confirmation
  alert('✅ Session ended. Players saved...');
}
```

### Data Preservation

```typescript
// These remain populated after Edit Session:
let players: Player[] = [...];        // ✅ Preserved
let bannedPairs: [string, string][] = [...]; // ✅ Preserved

// This is cleared:
let currentSession: Session | null = null;  // ❌ Cleared
```

## User Experience Improvements

### Before (Only End Session)
1. Start session with many players
2. Realize settings wrong
3. End session
4. **Pain:** Re-enter all players
5. Start new session
**Time:** 2-3 minutes to re-enter players

### After (Edit Session Available)
1. Start session with many players
2. Realize settings wrong
3. Edit session
4. **Quick:** Players already there
5. Change settings
6. Start new session
**Time:** 10 seconds

**Time Saved:** ~2-3 minutes per reconfiguration!

## Visual Design

### Button Layout
```
┌────────────────────────────────────────┐
│ Session Controls                       │
├────────────────────────────────────────┤
│ [Show Statistics]  [Show History]      │
│ [Edit Session]  [End Session]          │
│    (yellow)        (red)               │
└────────────────────────────────────────┘
```

### Color Coding
- **Edit Session**: Yellow (#ffc107)
  - Indicates caution but not danger
  - Suggests modification/change
  - Distinct from destructive action
  
- **End Session**: Red (#dc3545)
  - Indicates danger/destructive action
  - Clear visual warning
  - Matches convention for "delete/clear"

## Edge Cases

### 1. Edit Session with Active Matches
- Current matches cleared
- Players return to available pool
- No scores saved

### 2. Edit Session Then Cancel
- Can click "Start Session" to return to play
- Or continue modifying settings

### 3. Multiple Edit Sessions
- Can edit multiple times
- Players persist across all edits
- No limit on edits

### 4. Edit After Match Completion
- All match history lost
- Stats reset
- Fresh start with same players

## Safety Features

### Confirmation Dialogs
Both buttons require confirmation to prevent accidents:

**Edit Session:**
```
"This will end the current session but keep all players. 
 You can then reconfigure and start a new session. Continue?"
```

**End Session:**
```
"Are you sure you want to end the session? 
 All data (including players) will be lost."
```

### Clear Messaging
- Different colors (yellow vs red)
- Different text (Edit vs End)
- Different confirmation messages
- Success alert after Edit

## Testing Checklist

- [x] Edit Session preserves players
- [x] Edit Session preserves banned pairs
- [x] Edit Session clears match history
- [x] Edit Session returns to setup
- [x] Can change mode after Edit
- [x] Can change courts after Edit
- [x] Can add/remove players after Edit
- [x] End Session still clears everything
- [x] Confirmation dialogs work
- [x] Button styling correct
- [x] Success message appears

## Comparison Table

| Action | Players | Banned Pairs | Matches | Stats | Back to Setup |
|--------|---------|--------------|---------|-------|---------------|
| **Edit Session** | ✅ Keep | ✅ Keep | ❌ Clear | ❌ Clear | ✅ Yes |
| **End Session** | ❌ Clear | ❌ Clear | ❌ Clear | ❌ Clear | ✅ Yes |

## Future Enhancements

Potential improvements:
- [ ] "Save Configuration" - save mode/court settings
- [ ] "Load Configuration" - restore previous settings
- [ ] "Pause Session" - pause and resume later
- [ ] Edit session settings without stopping
- [ ] Undo last session clear

## Documentation Updates

Files updated:
- ✅ `README.md` - Usage instructions
- ✅ `CHANGELOG.md` - Feature announcement
- ✅ `src/main.ts` - Implementation
- ✅ `index.html` - Button and styling

## Related Features

- **Dynamic Player Management**: Add/remove during session
- **Test Mode**: Quick player population
- **Session Configuration**: Mode, courts, banned pairs

## User Feedback

Expected positive feedback:
- "Finally! Don't have to re-enter everyone"
- "Makes testing different modes so easy"
- "Saved so much time when we got more courts"

---

**Version:** 2.2  
**Status:** ✅ Implemented and tested  
**Impact:** High - significantly improves workflow
