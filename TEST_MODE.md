# Test Mode Documentation

## Overview

Test Mode is a special development feature that makes testing the Pickleball Session Manager much easier by providing a one-click way to populate the player list with realistic test data.

## How to Enable

Add the `test=true` query parameter to the URL:

```
http://localhost:5173/?test=true
```

## What It Does

When test mode is enabled:

1. **Yellow banner appears** at the top of the setup section
2. **"Add 18 Test Players" button** is displayed
3. Click the button to instantly add 18 players

## Test Players Added

The following 18 players are added (realistic first + last names):

1. James Anderson
2. Sarah Mitchell
3. Michael Chen
4. Emily Rodriguez
5. David Thompson
6. Jessica Williams
7. Christopher Lee
8. Amanda Martinez
9. Daniel Brown
10. Lauren Davis
11. Matthew Wilson
12. Ashley Garcia
13. Joshua Taylor
14. Rachel Johnson
15. Andrew Miller
16. Nicole White
17. Brandon Moore
18. Stephanie Harris

## Behavior

- **Clears existing players**: Any manually added players will be replaced
- **Clears banned pairs**: All banned pairs are removed
- **Updates UI**: Player list and dropdowns refresh automatically
- **Confirmation**: Shows alert "✅ Added 18 test players!"

## Use Cases

### Quick Testing
```
1. Open http://localhost:5173/?test=true
2. Click "Add 18 Test Players"
3. Set game mode and courts
4. Click "Start Session"
5. Immediately start testing features
```

### Testing Different Scenarios

**Doubles with 2 Courts:**
- 18 players = 8 playing, 10 waiting
- Perfect for testing waiting queue

**Doubles with 4 Courts:**
- 18 players = 16 playing, 2 waiting
- Tests nearly full court utilization

**Singles with 8 Courts:**
- 18 players = 16 playing, 2 waiting
- Tests many simultaneous matches

### Development Workflow
```
1. Make code changes
2. Refresh browser with ?test=true
3. Click test button
4. Immediately test new features
5. Repeat
```

## Visual Indicator

When test mode is active, you'll see:

```
┌──────────────────────────────────────────────┐
│ 🧪 Test Mode Active                          │
│                                              │
│ Quick setup for testing - adds 18 players   │
│ automatically                                │
│                                              │
│ [⚡ Add 18 Test Players]                     │
└──────────────────────────────────────────────┘
```

- **Background**: Light yellow (#fff3cd)
- **Border**: Gold (#ffc107)
- **Button**: Gold background with black text

## Implementation Details

### URL Parsing
```typescript
const urlParams = new URLSearchParams(window.location.search);
const isTestMode = urlParams.get('test') === 'true';
```

### Conditional Display
```typescript
if (isTestMode && testModeContainer) {
  testModeContainer.style.display = 'block';
  addTestPlayersBtn.addEventListener('click', handleAddTestPlayers);
}
```

### Player Generation
```typescript
function handleAddTestPlayers() {
  const testNames = [/* 18 names */];
  
  // Clear existing
  players = [];
  bannedPairs = [];
  
  // Add test players
  testNames.forEach(name => {
    const player: Player = {
      id: generateId(),
      name,
    };
    players.push(player);
  });
  
  // Update UI
  renderPlayerList();
  updateBannedPairSelects();
  renderBannedPairs();
  
  alert('✅ Added 18 test players!');
}
```

## Tips

### Combine with Other Testing

**Test banned pairs:**
1. Add 18 test players
2. Ban a few pairs manually
3. Start session and verify they never play together

**Test player removal:**
1. Add 18 test players
2. Start session
3. Remove players mid-session
4. Verify forfeits and re-evaluation work

**Test score editing:**
1. Add 18 test players
2. Complete several matches
3. Edit historical scores
4. Verify stats recalculate correctly

### Keyboard Shortcut

For even faster testing:
1. Bookmark `http://localhost:5173/?test=true`
2. Click bookmark → Click test button → Start session
3. Under 5 seconds to start testing!

## Production Notes

- ⚠️ **Not visible in production**: Only shows with `?test=true`
- ✅ **No security risk**: Client-side only, no data exposure
- ✅ **No performance impact**: Code only runs if parameter present
- ✅ **Easy to disable**: Remove query parameter to hide

## Future Enhancements

Potential improvements:
- [ ] Different player count options (8, 12, 18, 24)
- [ ] Pre-configured banned pairs for testing
- [ ] Pre-fill court numbers based on player count
- [ ] Auto-start session after adding players
- [ ] Remember test mode preference in localStorage
- [ ] Quick session templates (preset configurations)

## Comparison: Before vs After

### Before (Manual Entry)
```
1. Type "Alice" → Click Add
2. Type "Bob" → Click Add
3. Type "Carol" → Click Add
... (15 more times) ...
18. Type "Stephanie" → Click Add
Time: ~2-3 minutes
```

### After (Test Mode)
```
1. Open /?test=true
2. Click "Add 18 Test Players"
Time: ~2 seconds
```

**Time Saved**: ~120-180 seconds per test session!

## Troubleshooting

### Button Not Showing
- **Check URL**: Must include `?test=true` exactly
- **Case sensitive**: `test=True` or `TEST=true` won't work
- **Reload**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

### Players Not Added
- **Check console**: Open browser DevTools → Console
- **JavaScript errors**: Fix any errors that appear
- **Try again**: Click button again if no alert shows

### Wrong Number of Players
- Should always add exactly 18
- If different, check code for modifications
- Restart browser if issues persist

## Examples

### Quick 5-Minute Test Session
```bash
# Start server
npx -y vite@latest

# Open test mode
# Navigate to: http://localhost:5173/?test=true

# In browser:
1. Click "Add 18 Test Players" (✓)
2. Select "Round Robin" mode
3. Set 3 courts
4. Click "Start Session"
5. Complete a few matches
6. Check stats
7. Edit a score
8. Check history

Total time: Under 5 minutes including match completion!
```

### Testing Specific Feature
```
Testing match history with score editing:

1. /?test=true → Add players
2. Start session with 4 courts
3. Complete 8-10 matches quickly
4. Click "Show History"
5. Edit several scores
6. Verify stats update
7. Check winner/loser highlighting changes

Feature fully tested in ~3 minutes!
```

## FAQ

**Q: Does this affect production?**
A: No, only shows when `?test=true` is in the URL.

**Q: Can I customize the test players?**
A: Yes, edit the `testNames` array in `main.ts`.

**Q: Why 18 players specifically?**
A: Good for testing various scenarios:
- 2 courts doubles = 10 waiting
- 3 courts doubles = 6 waiting  
- 4 courts doubles = 2 waiting
- Enough variety without being overwhelming

**Q: Will this be in the final version?**
A: Yes, harmless development aid that doesn't affect normal use.

**Q: Can I add test players to an existing list?**
A: Currently no - it replaces existing players. This is by design to ensure clean test state.

---

**Pro Tip**: Bookmark `http://localhost:5173/?test=true` as "Pickleball Test" for instant access!
