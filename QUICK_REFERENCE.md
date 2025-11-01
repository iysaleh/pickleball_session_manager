# Quick Reference Guide

## 🎯 Key Features at a Glance

### Court Display
- **Layout:** Team 1 (left) ↔ Controls (center) ↔ Team 2 (right)
- **Colors:** Blue border (Team 1), Purple border (Team 2)
- **Controls:** Score inputs + Complete/Forfeit buttons centered

### Match History
- **Access:** Click "Show History" button
- **View:** All completed/forfeited matches (newest first)
- **Edit:** Change scores directly and click "Save"
- **Colors:** Green = winner, Red = loser

### Player Management
- **Add:** Type name in session controls → "Add Player"
- **Remove:** Click "Remove" next to player name
- **Reactivate:** Click "Reactivate" on inactive players
- **Status:** Active (normal), Inactive (grayed out)

## 🎮 Quick Actions

| Action | How To | Effect |
|--------|--------|--------|
| Complete Match | Enter scores → "Complete" | Match ends, stats updated, new match created |
| Forfeit Match | Click "Forfeit" → Confirm | No stats recorded, court freed, new match created |
| Edit Score | Show History → Change values → "Save" | Stats recalculated, winner/loser updated |
| Add Player | Type name → "Add Player" | Player joins queue, new matches evaluated |
| Remove Player | Click "Remove" → Confirm | Active matches forfeited, player marked inactive |
| View History | Click "Show History" | All matches displayed |
| View Stats | Click "Show Statistics" | Player stats cards shown |
| Edit Session | Click "Edit Session" → Confirm | Players kept, return to setup, change settings |
| End Session | Click "End Session" → Confirm | Everything cleared, fresh start |

## 🎨 Visual Indicators

### Match Status Colors
- 🟡 **Yellow** = Waiting
- 🟢 **Green** = In Progress
- ⚪ **Gray** = Completed
- 🔴 **Red** = Forfeited

### Team Colors
- 🔵 **Blue border** = Team 1
- 🟣 **Purple border** = Team 2

### History Colors
- 🟢 **Green background** = Winner
- 🔴 **Red background** = Loser

## 📋 Keyboard Shortcuts

- **Enter** after typing player name = Add player (setup & session)
- **Tab** to navigate between score inputs
- **Enter** in score input = Focus next input

## 🔄 Automatic Behaviors

The system automatically:
- ✅ Creates matches when courts available
- ✅ Starts matches immediately
- ✅ Evaluates after score entry
- ✅ Evaluates after forfeit
- ✅ Evaluates after player add/remove
- ✅ Prioritizes waiting players
- ✅ Balances games played
- ✅ Respects banned pairs

## 🏆 Game Modes

### Round Robin
- Partners change every game
- Maximizes diversity
- Fair rotation

### King of the Court
- Winners stay on court
- Losers go to waiting queue
- Competitive mode

### Teams
- Partners stay together
- Only opponents change
- Team building mode

## 📊 Statistics Tracked

Per Player:
- Games Played
- Wins / Losses
- Win Rate %
- Times Waited
- Unique Partners
- Unique Opponents

## 🎯 Best Practices

### Starting Session
1. Add all expected players first
2. Set banned pairs if needed
3. Configure courts correctly
4. Start session

### During Play
1. Let system auto-create matches
2. Enter scores promptly
3. Use forfeit only when needed
4. Add late arrivals immediately

### Score Entry
1. Double-check before clicking Complete
2. Use History to correct mistakes
3. Edit scores right away if error noticed

### Player Management
1. Confirm before removing players
2. Reactivate if player returns
3. Keep active list current

## ⚠️ Common Pitfalls

### ❌ DON'T
- Don't close/refresh browser (loses data)
- Don't remove player without confirming
- Don't forfeit matches unnecessarily
- Don't edit scores multiple times (confusing)

### ✅ DO
- Enter scores accurately first time
- Use forfeit for genuine issues
- Add all players at start when possible
- Review history periodically

## 🐛 Troubleshooting

### No Matches Being Created
- **Check:** Enough active players?
- **Doubles:** Need 4+ players
- **Singles:** Need 2+ players

### Player Can't Be Added
- **Check:** Already in player list?
- **Fix:** Can't add duplicates

### Score Won't Save
- **Check:** Valid numbers entered?
- **Fix:** Must be positive integers

### History Not Showing
- **Check:** Any completed matches?
- **Fix:** Complete at least one match first

## 🔢 Minimum Requirements

### Doubles
- **Minimum:** 4 players
- **Optimal:** 8+ players (2 courts)
- **Max Courts:** Limited by players (4 per court)

### Singles  
- **Minimum:** 2 players
- **Optimal:** 4+ players (2 courts)
- **Max Courts:** Limited by players (2 per court)

## 💾 Data Persistence

### ⚠️ Important
- **Not Saved:** Session data lost on refresh
- **Not Saved:** History cleared on session end
- **Saved:** Nothing persists currently

### Workaround
- Take screenshots of stats/history
- Manual record keeping
- Plan for future: localStorage

## 📱 Device Support

### Desktop
- ✅ Full features
- ✅ Optimal layout
- ✅ Best experience

### Tablet
- ✅ Full features
- ✅ Touch-friendly
- ⚠️ Slightly condensed

### Mobile
- ✅ Works but limited
- ⚠️ Teams may stack vertically
- ⚠️ Smaller touch targets

## 🎓 Tips & Tricks

### For Organizers
1. **Pre-populate banned pairs** before starting
2. **Add all players first** to avoid mid-session additions
3. **Check history** to ensure fair rotation
4. **Take screenshots** for records

### For Players
1. **Check stats** to see your progress
2. **Review history** to see who you've played
3. **Be ready** when you're up next (check waiting area)

### For Score Keeping
1. **Announce scores clearly** before entering
2. **Double-check** before clicking Complete
3. **Edit immediately** if mistake noticed
4. **Use history** to verify past scores

## 🚀 Performance Tips

- ✅ Close unused browser tabs
- ✅ Use modern browser (Chrome/Firefox/Edge)
- ✅ Clear browser cache if slow
- ✅ Limit to ~20-30 players max

## 🎯 Session Flow Example

```
1. Setup (5 min)
   - Add players
   - Set mode & courts
   - Add banned pairs
   
2. Start Session
   - Matches auto-created
   - Players assigned
   
3. Play (2-3 hours)
   - Complete matches
   - Scores entered
   - New matches auto-created
   - Players rotated fairly
   
4. Review
   - Check history
   - View stats
   - Identify top performers
   
5. End
   - Take screenshots
   - End session
```

## 📞 Support

- **Documentation:** README.md
- **Examples:** EXAMPLES.md
- **Features:** FEATURES.md
- **Changes:** CHANGELOG.md
- **UI Guide:** UI_GUIDE.md

---

**Version:** 2.1  
**Last Updated:** October 31, 2025  
**Access:** http://localhost:5173
