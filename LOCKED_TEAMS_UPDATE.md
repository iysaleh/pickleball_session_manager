# Locked Teams UI Update

## Summary
Reworked the locked teams functionality to provide a cleaner, more intuitive user experience when creating team-based sessions.

## Changes Made

### Before
- Users had to:
  1. Add individual players first
  2. Then manually pair them into locked teams from dropdown menus
  3. The UI showed both a players list AND a teams list, which was confusing

### After
- When "Locked Teams" is checked:
  1. Users directly add players **as teams** (two name inputs side-by-side)
  2. The individual player input section is hidden
  3. Only the teams list is displayed
  4. Players are automatically created and added when a team is created
  5. Removing a team also removes those players

### UI Changes

#### Session Setup Page
- When "Locked Teams" checkbox is enabled:
  - Individual player input section is hidden
  - Team input section shows two text inputs: "Player 1 name" and "Player 2 name"
  - Enter key navigation: pressing Enter in Player 1 input moves to Player 2 input
  - Pressing Enter in Player 2 input submits the team
  - Teams are displayed in a numbered, multi-column list (similar to players list)
  - Remove button (×) next to each team removes both the team and the players

#### Validation
- When locked teams is enabled, session requires at least 2 teams to start
- When locked teams is disabled, session requires at least 2 players to start
- Start Session button is automatically disabled/enabled based on the requirement

#### Edit Session
- When editing a session, the UI properly maintains the locked teams state
- Teams and players are preserved when switching between setup and active session

### Technical Implementation

#### Modified Files
1. **src/main.ts**
   - Removed dependency on player dropdown selects for team creation
   - `handleAddLockedTeam()` now creates players directly from text inputs
   - `handleRemoveLockedTeam()` now removes both team and associated players
   - `handleLockedTeamsToggle()` manages UI visibility between player/team modes
   - Added Enter key event listeners for team name inputs
   - Updated validation logic in `handleStartSession()`

2. **index.html**
   - Replaced team player dropdown selects with text inputs (`team-player1-name`, `team-player2-name`)
   - Wrapped individual player input in `player-input-section` div for easier show/hide
   - Updated locked teams section with clearer labels and instructions

### Algorithm Reuse
The existing Round Robin and King of the Court algorithms already support locked teams through the `SessionConfig.lockedTeams` property. No changes to the scheduling algorithms were needed.

### Testing
- All existing tests pass (96 tests)
- Manual testing workflow:
  1. Select "Doubles" session type
  2. Check "Locked Teams" checkbox
  3. Individual player section hides, team input appears
  4. Add multiple teams using the text inputs
  5. Teams appear in numbered list with remove buttons
  6. Start session works with team validation
  7. Uncheck "Locked Teams" - individual player section reappears

## Benefits
1. **Simpler workflow**: Fewer steps to create a team session
2. **Less confusion**: UI only shows relevant inputs (teams OR players, not both)
3. **Faster data entry**: Direct text input instead of dropdown selection
4. **Better UX**: Clear visual separation between team mode and individual mode
5. **Consistent with existing patterns**: Team list uses same styling as player list

## Backward Compatibility
- Existing sessions with locked teams continue to work
- All existing tests pass without modification
- Algorithm behavior unchanged
