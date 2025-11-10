# Usage Examples

## Example 1: Small Doubles Session (8 Players, 2 Courts)

### Scenario
8 players want to play doubles at a facility with 2 courts.

### Setup
1. Select "Round Robin" mode
2. Select "Doubles" session type
3. Set courts to 2
4. Add players:
   - Alice
   - Bob
   - Carol
   - Dave
   - Eve
   - Frank
   - Grace
   - Henry

### What Happens

**Round 1:**
- Court 1: Alice & Bob vs Carol & Dave
- Court 2: Eve & Frank vs Grace & Henry
- Waiting: None

**After matches complete:**
- System tracks: Alice played with Bob, against Carol & Dave
- All 8 players have played 1 game
- No one has waited

**Round 2:**
- Court 1: Alice & Carol vs Eve & Grace (new partners for all)
- Court 2: Bob & Dave vs Frank & Henry (new partners for all)
- Waiting: None

**Result**: Maximum partner diversity achieved!

---

## Example 2: Uneven Players (10 Players, 2 Courts)

### Scenario
10 players, only 2 courts available. Some must wait.

### Setup
Same as Example 1, but add:
- Iris
- Jack

### What Happens

**Round 1:**
- Court 1: 4 players
- Court 2: 4 players
- Waiting: Iris, Jack (2 players)
  - Iris: wait count = 1
  - Jack: wait count = 1

**Round 2:**
- System prioritizes Iris & Jack (they waited)
- Court 1: Iris & Jack vs [2 players who played least]
- Court 2: [4 other players]
- Waiting: 2 different players

**Result**: Fair rotation! Everyone waits equally over time.

---

## Example 3: King of the Court (6 Players, 1 Court)

### Scenario
Competitive mode with winners staying on court.

### Setup
1. Select "King of the Court" mode
2. Select "Doubles"
3. Set courts to 1
4. Add 6 players: Alice, Bob, Carol, Dave, Eve, Frank

### What Happens

**Round 1:**
- Court 1: Alice & Bob vs Carol & Dave
- Waiting: Eve, Frank

**Match ends: Alice & Bob win 11-7**

**Round 2:**
- Court 1: Alice & Bob (winners stay) vs Eve & Frank (challengers)
- Waiting: Carol, Dave (losers wait)

**Match ends: Eve & Frank win 11-9**

**Round 3:**
- Court 1: Eve & Frank (winners stay) vs Carol & Dave
- Waiting: Alice, Bob

**Result**: Winners defend their court, losers rotate!

---

## Example 4: Banned Pairs

### Scenario
Alice and Bob don't want to play together (they're too competitive with each other).

### Setup
1. Add all players
2. Select Alice from dropdown 1
3. Select Bob from dropdown 2
4. Click "Ban Pair"
5. See "Alice & Bob" in banned pairs list

### What Happens
- System will NEVER put Alice and Bob on the same team
- They can still play AGAINST each other
- If a match assignment would put them together, system retries
- Works in all game modes

### Example Matches Generated
- ✅ Alice & Carol vs Bob & Dave (Alice vs Bob: OK)
- ✅ Alice & Dave vs Carol & Eve (Alice and Bob not playing: OK)
- ❌ Alice & Bob vs Carol & Dave (NEVER happens - banned)

---

## Example 5: Singles Session

### Scenario
4 players want to play singles (1v1) on 2 courts.

### Setup
1. Select "Round Robin" mode
2. Select "Singles" session type
3. Set courts to 2
4. Add: Alice, Bob, Carol, Dave

### What Happens

**Round 1:**
- Court 1: Alice vs Bob
- Court 2: Carol vs Dave
- Waiting: None

**Round 2:**
- Court 1: Alice vs Carol (new opponent)
- Court 2: Bob vs Dave (new opponent)
- Waiting: None

**Round 3:**
- Court 1: Alice vs Dave (completes round-robin)
- Court 2: Bob vs Carol (completes round-robin)
- Waiting: None

**Result**: Everyone plays everyone exactly once!

---

## Example 6: Teams Mode

### Scenario
4 teams want to practice, partners stay together.

### Setup
1. Select "Teams" mode
2. Select "Doubles"
3. Set courts to 2
4. Add players (will auto-pair in order of addition):
   - Team 1: Alice & Bob
   - Team 2: Carol & Dave
   - Team 3: Eve & Frank
   - Team 4: Grace & Henry

### What Happens

**Round 1:**
- Court 1: Alice & Bob vs Carol & Dave
- Court 2: Eve & Frank vs Grace & Henry

**Round 2:**
- Court 1: Alice & Bob vs Eve & Frank (same partners, new opponents)
- Court 2: Carol & Dave vs Grace & Henry

**Result**: Partners stay together, great for team building!

---

## Example 7: Dynamic Player Management

### Scenario
Someone arrives late or has to leave early.

### Adding a Player Mid-Session
1. Session is running
2. New player arrives
3. Click "Add Player" (would need to restart session or add during setup)
4. Player joins waiting queue
5. Gets prioritized based on games played (0) and wait count

### Handling Early Departure
1. Player needs to leave
2. Complete their current match if playing
3. End session and restart without that player
4. Or simply note they're unavailable for next matches

**Note**: In current version, player changes require session restart. Future versions could support mid-session changes.

---

## Example 8: Score Tracking

### Scenario
Keeping accurate records of match results.

### During a Match
1. Match shows as "In Progress"
2. Players play pickleball
3. When match ends, scores are entered:
   - Team 1: 11
   - Team 2: 7
4. Click "Complete"

### What Gets Updated
- Match status → Completed
- Team 1 players: wins++, gamesPlayed++
- Team 2 players: losses++, gamesPlayed++
- Court becomes available
- System suggests next round if players waiting

### Statistics Available
```
Alice:
  Games Played: 3
  Wins: 2
  Losses: 1
  Win Rate: 66.7%
  Times Waited: 0
  Unique Partners: 3
  Unique Opponents: 4
```

---

## Example 9: Large Group (16 Players, 4 Courts)

### Scenario
Big group, multiple courts, maximize efficiency.

### Setup
- Mode: Round Robin
- Type: Doubles
- Courts: 4
- Players: 16

### What Happens

**Round 1:**
- All 4 courts active
- 16 players / 4 per match = 4 matches
- Waiting: 0 players
- Everyone plays immediately!

**Round 2:**
- System intelligently selects new combinations
- Tries to pair people who haven't played together
- Again, all 16 players active
- No waiting with perfect numbers

**Efficiency:**
- With 16 players and 4 courts (perfect ratio)
- Everyone plays every round
- Maximum throughput
- Optimal for leagues or tournaments

---

## Example 10: Statistics Analysis

### Scenario
After a 2-hour session, analyzing performance.

### Viewing Statistics
1. Click "Show Statistics"
2. See cards for each player

### Sample Analysis

**Alice - The Champion**
```
Games Played: 8
Wins: 7
Losses: 1
Win Rate: 87.5%
Times Waited: 1
Unique Partners: 6
Unique Opponents: 8
```
**Analysis**: Dominant player, played with many partners, waited minimally.

**Bob - The Consistent**
```
Games Played: 8
Wins: 4
Losses: 4
Win Rate: 50%
Times Waited: 1
Unique Partners: 7
Unique Opponents: 8
```
**Analysis**: Balanced record, great diversity, team player.

**Carol - The Beginner**
```
Games Played: 6
Wins: 1
Losses: 5
Win Rate: 16.7%
Times Waited: 3
Unique Partners: 5
Unique Opponents: 6
```
**Analysis**: Still learning, played less due to waiting, opportunity for improvement.

### Using Statistics
- Identify strong players for competitive teams
- Help beginners by pairing with experienced players
- Balance teams based on win rates
- Recognize players who need more playing time
- Track improvement over multiple sessions

---

## Tips for Best Experience

### For Organizers
1. **Add all players before starting** - easier than mid-session changes
2. **Use banned pairs sparingly** - limits matchmaking flexibility
3. **Have courts = multiple of 4 for doubles** - minimizes waiting
4. **Use King of Court for competitive groups** - keeps energy high
5. **Check statistics periodically** - ensure fair play distribution

### For Players
1. **Enter scores promptly** - keeps session flowing
2. **Be ready when called** - reduces downtime
3. **Embrace diverse partners** - round-robin is about meeting everyone
4. **Track your progress** - use stats to improve
5. **Have fun!** - the system handles the logistics

### Common Patterns

**Recreation League** (weekly play)
- Mode: Round Robin
- Emphasizes social play and meeting everyone
- Track statistics across weeks

**Competitive Night** (tournament-style)
- Mode: King of the Court
- Winners stay, losers work back up
- Creates competitive atmosphere

**Team Practice** (regular partners)
- Mode: Teams
- Same partners all session
- Focuses on team development

**Drop-in Play** (casual, varying attendees)
- Mode: Round Robin
- Singles or Doubles
- Easy for people to join/leave

---

## Troubleshooting Scenarios

### Issue: Can't create matches
**Likely cause**: Not enough players
- Doubles needs 4+ players
- Singles needs 2+ players
**Solution**: Add more players or change session type

### Issue: Some players waiting too long
**Likely cause**: Odd player count
- 10 players on 2 courts = 2 always waiting
**Solution**: 
- Add more courts if available
- Accept rotation is necessary
- System will balance wait times

### Issue: Banned pair keeps coming up
**Likely cause**: System is working correctly
**Explanation**: They can still play AGAINST each other
**Solution**: This is intentional - ban only prevents same team

### Issue: Lost all data
**Likely cause**: Page refresh
**Solution**: Current version doesn't persist data
**Workaround**: Take screenshot of statistics before refreshing

---

These examples demonstrate the versatility and power of the Pickleball Session Manager for various scenarios and group sizes!
