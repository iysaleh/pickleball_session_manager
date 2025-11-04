# Randomize Player Order - Quick Guide

## What It Does
Shuffles the order of players when starting a session, so initial matches aren't always the same people.

## How to Enable

1. Go to **Setup** page
2. Click **"⚙️ Advanced Configuration"** button
3. Check **"Randomize Initial Player Order"** checkbox
4. Add your players (order doesn't matter now!)
5. Click **"Start Session"**

## Before vs After

### WITHOUT Randomization (Default)
```
Players added: Alice, Bob, Carol, Dave, Eve, Frank, Grace, Henry

First matches:
Court 1: Alice & Bob vs Carol & Dave
Court 2: Eve & Frank vs Grace & Henry

➜ Same players in first matches every time
```

### WITH Randomization (Enabled)
```
Players added: Alice, Bob, Carol, Dave, Eve, Frank, Grace, Henry
Shuffled to: Frank, Carol, Eve, Alice, Henry, Dave, Grace, Bob

First matches:
Court 1: Frank & Carol vs Eve & Alice
Court 2: Henry & Dave vs Grace & Bob

➜ Different players in first matches each session!
```

## When to Use

✅ **Enable When:**
- Running social sessions
- Want variety in opening matches
- Starting King of the Court fresh
- Fair tournament starts

❌ **Keep Disabled When:**
- You ordered players by skill intentionally
- Want consistent testing conditions
- Running seeded tournaments
- Prefer first-come-first-serve

## Key Facts

- **Default:** Disabled (off)
- **Location:** Setup → Advanced Configuration
- **Timing:** Shuffles once at session start
- **Persists:** Order stays same for whole session
- **Performance:** Instant, no delay
- **Compatible:** Works with all modes and settings

## Important Notes

⚠️ **Randomization happens at session start only**
- Players stay in shuffled order for entire session
- Can't be undone without ending session

⚠️ **Checkbox doesn't stay checked**
- Resets to unchecked when page reloads
- Intentional: randomization is per-session choice

⚠️ **Works with other features**
- ✅ Compatible with locked teams
- ✅ Compatible with banned pairs
- ✅ Works in both Round Robin and King of Court
- ✅ Preserves all player settings

## Example Session Flow

1. **Add 19 players in order**: 1, 2, 3, ..., 19
2. **Enable randomization**
3. **Start session**
4. **Result:** Players shuffled (e.g., 12, 5, 18, 3, 9, ...)
5. **First matches use shuffled order**
6. **Rest of session proceeds normally**

## Tips

💡 **For Best Variety:**
- Enable randomization for social sessions
- Different first matches each time you play

💡 **For Consistent Testing:**
- Disable randomization
- Same initial conditions each session

💡 **For Fair Tournaments:**
- Enable to avoid add-order bias
- All players have equal chance to start

## Troubleshooting

**Q: Checkbox keeps unchecking after page reload**  
A: This is intentional! Randomization is a per-session choice, not a global setting.

**Q: Can I control which players randomize?**  
A: Not currently. It's all or nothing. Add players in desired order if you want some control.

**Q: Does this affect rankings in King of Court?**  
A: Only indirectly. Different starting matchups may lead to different early rankings, but the algorithm self-corrects over time.

**Q: Can I see the shuffled order before starting?**  
A: Not in the UI, but you'll see it immediately in the first matches once session starts.

## Technical Details

- **Algorithm:** Fisher-Yates shuffle (unbiased)
- **Complexity:** O(n) time, O(n) space
- **Random:** Uses Math.random() (sufficient for this use case)
- **Persistence:** Order saved with session in localStorage
