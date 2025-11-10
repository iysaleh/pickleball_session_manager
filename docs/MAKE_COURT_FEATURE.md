# Make Court Feature

## Overview
The "Make Court" feature allows session organizers to manually create a court with their selected players during an active session. This provides flexibility when the automatic matchmaking algorithm needs to be overridden for special circumstances.

## Feature Description

### How to Use

1. **Open Active Session**: Start a pickleball session and navigate to the "Active Session" tab
2. **Click "Make Court" Button**: In the courts section, click the green "🎾 Make Court" button
3. **Select Players**: A modal dialog will appear with:
   - Two team sections (Team 1 and Team 2)
   - Four dropdown menus (one for each player)
   - An automatic suggestion for the most balanced team composition
4. **Review Win Probability**: The modal displays estimated win percentages based on player rankings
5. **Customize (Optional)**: Override the suggested lineup by selecting different players from the dropdowns
6. **Create Court**: Click "Create Court" to add the match

### Key Features

#### 1. **Smart Auto-Suggestion**
- Algorithm automatically suggests the most balanced team composition
- Calculates all possible 4-player combinations to find the matchup closest to 50-50
- Users can click "Apply Suggestion" to use the recommended lineup or manually override

#### 2. **Win Probability Display**
- Shows estimated win likelihood for each team (e.g., "70% vs 30%")
- Updates in real-time as players are selected
- Based on player rankings from their historical performance
- Calculation method:
  ```
  Team Win Rate = Average of both players' individual win rates
  Team Probability = Team Win Rate / (Team1 Win Rate + Team2 Win Rate) * 100
  ```

#### 3. **Input Validation**
- Prevents selecting the same player twice
- Prevents selecting a player for both teams
- Requires all 4 players to be selected before creating the court
- Shows clear error messages for validation issues

#### 4. **Ranking-Based Calculations**
- Uses player rankings based on wins, losses, and point differentials
- For King of the Court mode: Uses ELO-style ratings
- For Round Robin mode: Uses win rate calculations
- Considers player history for more accurate probability estimates

### Technical Implementation

#### Modal HTML Structure
```html
<aside id="make-court-modal" class="modal">
  <div class="modal-content">
    <!-- Team dropdowns -->
    <select id="make-court-team1-player1" class="make-court-select"></select>
    <select id="make-court-team1-player2" class="make-court-select"></select>
    <select id="make-court-team2-player1" class="make-court-select"></select>
    <select id="make-court-team2-player2" class="make-court-select"></select>
    
    <!-- Probability display -->
    <div id="make-court-team1-prob">50%</div>
    <div id="make-court-team2-prob">50%</div>
    
    <!-- Buttons -->
    <button id="make-court-create-btn">Create Court</button>
    <button id="make-court-apply-suggested">Apply Suggestion</button>
  </div>
</aside>
```

#### Main Functions

**openMakeCourtModal()**
- Validates that an active session exists
- Checks for at least 4 available (waiting) players
- Populates dropdown menus with waiting players
- Calculates and displays balanced team suggestion
- Opens the modal dialog

**suggestBalancedTeamComposition(availablePlayers)**
- Tests all possible 4-player combinations
- For each combination, tries 3 different team pairings:
  - Pairing 1: [0,1] vs [2,3]
  - Pairing 2: [0,2] vs [1,3]
  - Pairing 3: [0,3] vs [1,2]
- Calculates win probability for each arrangement
- Selects the pairing closest to 50-50 split
- Stores suggestion for later application

**updateMakeCourtProbabilities()**
- Triggered whenever a player dropdown changes
- Validates that no player is selected twice
- Shows error message if validation fails
- Calculates win probability for selected teams
- Updates probability display in real-time

**calculateWinProbability(team1Ids, team2Ids)**
- Gets strength rating for each team
- Team Strength = Average of two players' individual win rates
- Calculates probability: team1Strength / (team1Strength + team2Strength)
- Returns { team1: number, team2: number } with percentages

**handleCreateCustomCourt()**
- Final validation of all 4 selections
- Creates new Match object with:
  - Unique ID
  - Next available court number
  - Team compositions
  - Status: "waiting"
- Removes selected players from waiting list
- Adds match to session's match list
- Saves state to localStorage
- Re-renders courts and player list

#### Player Selection Logic
```typescript
// Get waiting players only
const waitingPlayerIds = currentSession.waitingPlayers;
const waitingPlayers = waitingPlayerIds
  .map(id => playerMap.get(id))
  .filter(p => p !== undefined);

// Populate dropdowns only with available players
waitingPlayers.forEach(player => {
  const option = document.createElement('option');
  option.value = player.id;
  option.textContent = player.name;
  select.appendChild(option);
});
```

#### Validation Rules
1. **Player Uniqueness**: Each of 4 players must be different
   ```typescript
   const uniqueSelected = new Set(selectedPlayers);
   if (uniqueSelected.size !== 4) {
     // Show error
   }
   ```

2. **All Players Required**: All 4 dropdowns must have selections
   ```typescript
   if (selectedPlayers.includes('')) {
     // Show error
   }
   ```

3. **Availability Check**: Players must be in the waiting list
   - Modal only shows players from `currentSession.waitingPlayers`

### UI/UX Features

#### Visual Hierarchy
- Modal displays teams side-by-side for easy comparison
- Team 1: Blue border (#667eea)
- Team 2: Purple border (#764ba2)
- Probability display prominent at top of modal

#### Real-Time Feedback
- Error messages appear immediately with red background
- Probabilities update as players are selected
- Suggested button only appears when suggestion is available

#### Accessibility
- All dropdowns labeled clearly
- Error messages descriptive and helpful
- Modal can be closed via close button or by clicking outside
- Keyboard navigation supported

### Example Scenario

**Scenario**: During a King of the Court session with 8 players:
1. After first few matches, 4 players become available
2. Organizer clicks "Make Court" button
3. Modal opens and suggests: 
   - Player A + Player B vs Player C + Player D
   - Estimated 48% vs 52% (fairly balanced)
4. Organizer is satisfied with suggestion
5. Clicks "Apply Suggestion" then "Create Court"
6. New court is created with selected players
7. Players are removed from waiting area

### Future Enhancements

1. **Partner History Integration**
   - Warn if selected team has played together recently
   - Suggest alternative pairings for more variety

2. **Opponent History Integration**
   - Show how often each team configuration has faced each other
   - Suggest alternatives to avoid repeated matchups

3. **Advanced Filtering**
   - Filter available players by skill level
   - Show only players who haven't played recently
   - Exclude specific players from selection

4. **Analytics**
   - Track manual court creation vs automatic
   - Show success rate of manually selected courts
   - Compare win rates for manually vs auto-generated courts

5. **Export/History**
   - Save favorite team compositions
   - Export manually created courts as templates
   - Review past manual selections

## Implementation Notes

- Uses real-time probability calculations (no pre-computed tables)
- Handles edge cases:
  - Players with 0 games (defaults to 50-50)
  - New sessions with no historical data
  - Different session types (doubles/singles)
- Works with both Round Robin and King of the Court modes
- Automatically saves to localStorage after court creation
- Re-renders all affected UI elements to maintain consistency

## Testing

The feature includes:
- Input validation tests
- Probability calculation tests
- UI state management tests
- Modal open/close behavior tests
- Player selection persistence tests

All tests verify:
1. Cannot create invalid courts
2. Probabilities calculate correctly
3. UI updates properly
4. Session state remains consistent
5. Local storage saves correctly
