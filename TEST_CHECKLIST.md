# Test Checklist

## Setup
1. Run `npm install` to ensure dependencies are installed
2. Run `npm run dev` to start the development server
3. Navigate to the URL shown (typically `http://localhost:5173/?test=true`)

## Test Cases

### Test 1: Player List Display
- [ ] Click "Add 18 Test Players" button
- [ ] **Expected**: Players appear as a numbered list (1-18)
- [ ] **Expected**: Each player has a red "×" button next to their name
- [ ] **Expected**: Text is readable in dark mode (light colored text on dark background)

### Test 2: Match Queue Display
- [ ] Start a session with Round-Robin mode, Doubles, 2 courts
- [ ] Look at the Match Queue section (should be visible by default)
- [ ] **Expected**: Queue shows 10 matches by default
- [ ] **Expected**: Match #1 and Match #6 have DIFFERENT players
- [ ] **Expected**: Match #2 and Match #7 have DIFFERENT players
- [ ] **Expected**: All matches in the queue are unique

### Test 3: Queue Toggle Button
- [ ] Click "Hide Queue" button
- [ ] **Expected**: Queue section disappears
- [ ] **Expected**: Button text changes to "Show Queue"
- [ ] Click "Show Queue" button
- [ ] **Expected**: Queue section reappears
- [ ] **Expected**: Button text changes back to "Hide Queue"

### Test 4: Section Ordering
- [ ] With an active session, observe the order of sections from top to bottom
- [ ] **Expected Order**:
  1. Session Controls
  2. Active Courts
  3. Match Queue
  4. Match History
  5. Player Statistics (when visible)

### Test 5: Score Input Spinners
- [ ] Look at the Active Courts section with a game in progress
- [ ] **Expected**: Score input boxes do NOT have up/down arrow buttons
- [ ] Look at Match History scores
- [ ] **Expected**: Score input boxes do NOT have up/down arrow buttons
- [ ] Look at "Courts per row" input
- [ ] **Expected**: Input box does NOT have up/down arrow buttons
- [ ] Look at "Matches per page" input  
- [ ] **Expected**: Input box does NOT have up/down arrow buttons

### Test 6: Auto-Update Statistics
- [ ] Click "Show Statistics" to make stats visible
- [ ] Complete a game by entering scores and clicking "Complete"
- [ ] **Expected**: Player statistics update immediately without needing to hide/show stats

### Test 7: Queue Persistence
- [ ] Complete a game (e.g., score 11-5)
- [ ] Observe the Match Queue
- [ ] **Expected**: Queue automatically updates and removes the completed match
- [ ] **Expected**: Next queued match moves up in the list
- [ ] Complete another game
- [ ] **Expected**: Queue continues to update correctly

### Test 8: Edit Session
- [ ] Click "Edit Session" button
- [ ] **Expected**: Returns to setup screen
- [ ] **Expected**: Match Queue section is HIDDEN
- [ ] **Expected**: Player list still shows all 18 players
- [ ] **Expected**: Can change mode/settings and start new session

### Test 9: End Session
- [ ] Start a new session
- [ ] Make sure Match Queue is visible
- [ ] Click "End Session" button
- [ ] **Expected**: Returns to setup screen  
- [ ] **Expected**: Match Queue section is HIDDEN
- [ ] **Expected**: Player list is EMPTY
- [ ] **Expected**: All match data is cleared

### Test 10: Round-Robin Queue Generation
- [ ] Start session with 18 players, Round-Robin, Doubles, 2 courts
- [ ] In Match Queue, scroll through pages to see all queued matches
- [ ] **Expected**: Each match should be unique (no exact duplicates)
- [ ] **Expected**: Players should be partnered with different people across matches
- [ ] **Expected**: Players should face different opponents across matches

### Test 11: Match History Display
- [ ] Start a session
- [ ] **Expected**: Match History section is visible by default
- [ ] Complete 2-3 games
- [ ] **Expected**: Match History updates immediately after each game completion
- [ ] **Expected**: Most recent game appears at the TOP of the history
- [ ] **Expected**: Scores are displayed correctly with winner highlighted

## Known Issues (If Any)
- npm install may have issues if run from certain terminals. Try running from a fresh PowerShell or Command Prompt window.
- If vite is not found, manually install: `npm install --save-dev vite typescript`

## Success Criteria
- All checkboxes above should be checked
- No console errors in browser developer tools
- Smooth user experience with proper visual feedback
