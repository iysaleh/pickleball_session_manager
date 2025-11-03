# 🎾 Pickleball Session Manager

A client-side TypeScript web application for managing pickleball play sessions with multiple game modes and intelligent matchmaking.

## 🚀 Live Demo

**Visit the live app:** [https://YOUR-USERNAME.github.io/pickleball/](https://YOUR-USERNAME.github.io/pickleball/)

> **Note:** Replace `YOUR-USERNAME` with your actual GitHub username once deployed.

## ✨ Key Highlights

- 💯 **100% Client-Side** - No server required!
- 💾 **Auto-Save** - All data persists in your browser
- 🆓 **Free to Use** - Hosted on GitHub Pages
- 📱 **Mobile Friendly** - Works on all devices

## Features

### Game Modes
- **Round Robin**: Maximizes the number of different partners you play with
- **King of the Court**: Winners stay on court, losers rotate out
- **Teams**: Locked partners throughout the session

### Session Types
- **Doubles**: 2v2 matches
- **Singles**: 1v1 matches

### Core Functionality
- ✅ **Continuous Queue System**: Matches automatically created as courts become available
- ✅ **Dynamic Player Management**: Add/remove players during active sessions
- ✅ **Player Status**: Mark players as inactive (they leave early) or reactivate them
- ✅ **Match History**: View all completed/forfeited matches
- ✅ **Edit Match Scores**: Correct mistakes in historical match scores
- ✅ **Match Queue**: View all scheduled matches for round-robin (paginated)
- ✅ **Dark/Light Mode**: Toggle theme with moon (🌙) / sun (☀️) button in header
- ✅ Multiple court support
- ✅ Intelligent waiting queue system
- ✅ Fair rotation ensuring everyone plays
- ✅ Banned pairs support (for players who don't want to play together)
- ✅ Live score input and match completion
- ✅ **Match Forfeiting**: Forfeit matches without recording stats
- ✅ Comprehensive player statistics
- ✅ Partner diversity optimization in round-robin mode
- ✅ Real-time court availability tracking
- ✅ Automatic match generation when scores are submitted
- ✅ **Improved Court Layout**: Team 1 on left, controls in middle, Team 2 on right

### Statistics Tracking
For each player, the system tracks:
- Games played
- Wins and losses
- Win rate
- Times waited
- Unique partners played with
- Unique opponents faced

## Getting Started

### Prerequisites
- Node.js (v20+ recommended)
- npm

### Installation

```bash
# Clone or download the project
cd pickleball

# The application uses npx to run without local installations
```

### Running the Application

```bash
# Start the development server
npx -y vite@latest

# Open your browser to http://localhost:5173
```

The application will start and be accessible at `http://localhost:5173`.

#### Test Mode

For quick testing, you can enable test mode with a query parameter:

```
http://localhost:5173/?test=true
```

This displays a special "Add 18 Test Players" button that instantly adds 18 players with realistic first and last names. Perfect for testing the application without manually entering names each time!

### Running Tests

```bash
# Run all tests
npx -y vitest@3.2.4 run

# Run tests in watch mode
npx -y vitest@3.2.4

# Run tests with UI
npx -y vitest@3.2.4 --ui
```

Note: When first running tests, you may be prompted to install `happy-dom`. Press 'y' to accept.

### Building for Production

```bash
# Build the application
npx -y tsc && npx -y vite@latest build

# Preview the production build
npx -y vite@latest preview
```

## How to Use

### 1. Session Setup
1. Select your game mode (Round Robin, King of the Court, or Teams)
2. Choose session type (Doubles or Singles)
3. Set the number of available courts
4. Add players by entering their names
5. Optionally add banned pairs (players who won't play together)
6. Click "Start Session"

### 2. During the Session
- **Matches are automatically created** when courts are available
- **Add players mid-session** by entering their name in the session controls
- **Remove players** who need to leave early (their active matches will be forfeited)
- Enter scores when matches complete, OR
- Forfeit a match if needed (no stats recorded)
- The system will **automatically**:
  - Create new matches when a court becomes available
  - Track who's waiting
  - Prioritize players who have waited longest
  - Balance games played across all players
  - Maximize partner diversity in round-robin mode

### 3. View History & Statistics
- Click "Show History" to see all completed matches
- Edit scores of any historical match if there was a mistake
  - Simply change the score values and click "Save"
  - Statistics automatically recalculated
- Click "Show Statistics" to view detailed player stats
  - Wins, losses, win rates
  - Partner and opponent diversity

### 4. Edit or End Session
- **Edit Session**: Keeps players but lets you change mode/courts
  - Click "Edit Session"
  - Players and banned pairs preserved
  - Returns to setup screen
  - Reconfigure and start new session
- **End Session**: Clears everything and starts fresh
  - Click "End Session"
  - All data (players, matches, stats) lost
  - Returns to setup screen

## Project Structure

```
pickleball/
├── src/
│   ├── types.ts           # TypeScript type definitions
│   ├── utils.ts           # Utility functions
│   ├── matchmaking.ts     # Matchmaking logic
│   ├── session.ts         # Session management
│   ├── main.ts            # Main application code & UI logic
│   ├── utils.test.ts      # Utils tests
│   ├── matchmaking.test.ts # Matchmaking tests
│   └── session.test.ts    # Session tests
├── index.html             # Main HTML file with embedded styles
├── package.json           # Project configuration
├── tsconfig.json          # TypeScript configuration
├── vitest.config.ts       # Vitest test configuration
└── vite.config.ts         # Vite build configuration
```

## Testing

The project includes comprehensive unit tests covering:

### Utils Tests
- ID generation
- Array shuffling
- Banned pair checking
- Player statistics creation and management
- Fair rotation algorithms

### Matchmaking Tests
- Player selection for matches
- Banned pair enforcement
- Partner diversity optimization
- Singles and doubles match creation
- Statistics tracking

### Session Tests  
- Session creation and configuration
- Player management (add/remove)
- Round generation
- Match lifecycle (waiting → in-progress → completed)
- King of the Court mode
- Waiting queue management
- Court availability checking

### Running Specific Tests

```bash
# Run tests for a specific file
npx vitest run src/utils.test.ts

# Run tests in watch mode for a specific file
npx vitest src/session.test.ts
```

## Algorithm Details

### Continuous Queue System
- **No rounds** - matches are created continuously as courts become available
- When a match completes or is forfeited, the system immediately evaluates if new matches can be created
- Automatic match generation happens on:
  - Session start
  - Match completion
  - Match forfeit
  - Player added to session
  - Player removed from session

### Round Robin Mode
- Prioritizes players with fewest games played
- Optimizes for partner diversity (tries to pair players who haven't played together)
- Respects banned pairs
- Balances waiting times fairly

### King of the Court Mode
- Winning team stays on court
- Losing team moves to waiting queue
- Next game features waiting players vs. current champions
- Automatically creates new match when previous one completes

### Teams Mode
- Partners stay locked throughout the session
- Only opponents change between matches
- Validates that banned pairs aren't on same team

### Waiting Queue
- Tracks how many times each player has waited
- Prioritizes players who have waited most
- Ensures fair rotation when courts become available
- Dynamically updates as players join/leave

### Dynamic Player Management
- **Add players**: Instantly available for next match creation
- **Remove players**: Marked as inactive, forfeits any active matches, court freed for new match
- **Reactivate players**: Can rejoin the session later
- Historical stats preserved even for inactive players

## Technologies Used

- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Vitest**: Unit testing framework
- **Happy-DOM**: Lightweight DOM implementation for testing
- **Pure CSS**: No framework dependencies for styling

## Browser Support

The application uses modern JavaScript/TypeScript features and requires a recent browser version:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## License

ISC

## Contributing

Feel free to submit issues or pull requests to improve the application!

## 🌐 Deploying to GitHub Pages

This app is ready to deploy to GitHub Pages! See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Quick Deploy:

1. **Update vite.config.ts** - Set `base: '/your-repo-name/'`
2. **Install dependencies** - `npm install`
3. **Deploy** - `npm run deploy`
4. **Access** - `https://YOUR-USERNAME.github.io/your-repo-name/`

**Note:** All data is stored locally in each user's browser using localStorage. No backend or database required!

## Future Enhancements

Potential features for future development:
- Export session statistics to CSV/JSON
- Custom scoring rules
- Tournament brackets
- Elo rating system
- Player profiles with avatars
- Session templates
