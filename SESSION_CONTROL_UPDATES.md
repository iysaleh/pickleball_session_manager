# Session Control Updates

## Summary
Updated the session control system to properly lock configuration during active sessions and provide two distinct end session options.

## Changes Made

### 1. Configuration Locking During Active Session

**Setup Page (index.html lines 1116-1119)**
- Changed single "End Session" button to two buttons:
  - "End Session and Clear Data" 
  - "End Session and Keep Players"

**Active Session Page (index.html lines 1142-1150)**
- Replaced single "End Session" button with:
  - "End Session and Clear Data"
  - "End Session and Keep Players"

**JavaScript (main.ts)**
- Updated button references to use new button IDs
- Modified `lockConfigurationInputs()` to:
  - Disable all setup inputs when session is active
  - Show two end session buttons instead of one
  - Re-render player/team lists to disable remove buttons
  
- Modified `unlockConfigurationInputs()` to:
  - Enable all setup inputs when no session is active
  - Show start session button
  - Hide end session buttons

### 2. Dynamic Button Disabling

**Player List Rendering**
- `renderPlayerList()` now checks if session is active and disables remove buttons accordingly
- Remove buttons have `disabled = currentSession !== null`

**Locked Teams Rendering**
- `renderLockedTeams()` now checks if session is active and disables remove buttons accordingly
- Remove buttons have `disabled = currentSession !== null`

**Banned Pairs Rendering**
- `renderBannedPairs()` now creates buttons dynamically instead of using innerHTML
- Remove buttons have `disabled = currentSession !== null`

### 3. End Session Functions

**handleEndSessionAndClearData()**
- Ends the session
- Clears all players, banned pairs, and locked teams
- Clears localStorage
- Unlocks all configuration inputs
- Switches to Setup page
- Shows confirmation message

**handleEndSessionAndKeepPlayers()**
- Ends the session
- Keeps all players, banned pairs, and locked teams for next session
- Saves state to localStorage
- Unlocks all configuration inputs
- Switches to Setup page
- Shows confirmation message

**handleEditSession()** (updated)
- Now uses `showPage('setup')` for consistency
- Closes any open modals before switching pages
- Keeps all existing functionality

### 4. Session Start Prevention

The `handleStartSession()` function already has a check at line 798-801:
```javascript
if (currentSession) {
  alert('A session is already active. Please end the current session before starting a new one.');
  return;
}
```

This prevents starting a new session while one is active.

## User Experience

### During Active Session (Setup Page)
- All configuration dropdowns are disabled
- Number of courts input is disabled
- Player name input is disabled
- Add player button is disabled
- Add team button is disabled (if in locked teams mode)
- Banned pairs controls are disabled
- All remove buttons (×) are disabled (grayed out)
- Start Session button is hidden
- Two End Session buttons are visible

### During Active Session (Active Session Page)
- Two End Session buttons are available:
  1. "End Session and Clear Data" - Removes everything
  2. "End Session and Keep Players" - Keeps players for next session

### After Ending Session
- All controls are re-enabled
- User can modify configuration
- User can add/remove players
- Start Session button is visible again

## Testing

To test the changes:
1. Start the dev server: `npx -y vite@latest`
2. Open the app in browser (http://localhost:5176 or similar)
3. Add some players on the Setup page
4. Click "Start Session"
5. Verify all setup controls are disabled
6. Try to remove a player - button should be disabled
7. Click one of the End Session buttons
8. Verify all controls are re-enabled
9. If you used "Keep Players", verify players are still there
10. If you used "Clear Data", verify everything is cleared

## Files Modified
- `index.html` - Updated button HTML
- `src/main.ts` - Updated button handling, locking logic, and rendering functions
