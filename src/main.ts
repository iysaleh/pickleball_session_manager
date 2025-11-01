import type { Session, Player, SessionConfig, Match } from './types';
import { createSession, addPlayerToSession, removePlayerFromSession, startMatch, completeMatch, forfeitMatch, checkForAvailableCourts, evaluateAndCreateMatches } from './session';
import { generateId } from './utils';

let currentSession: Session | null = null;
const players: Player[] = [];
const bannedPairs: [string, string][] = [];

// DOM Elements
const setupSection = document.getElementById('setup-section') as HTMLElement;
const controlSection = document.getElementById('control-section') as HTMLElement;
const courtsSection = document.getElementById('courts-section') as HTMLElement;
const statsSection = document.getElementById('stats-section') as HTMLElement;

const playerNameInput = document.getElementById('player-name') as HTMLInputElement;
const addPlayerBtn = document.getElementById('add-player-btn') as HTMLButtonElement;
const playerList = document.getElementById('player-list') as HTMLElement;

const gameModeSelect = document.getElementById('game-mode') as HTMLSelectElement;
const sessionTypeSelect = document.getElementById('session-type') as HTMLSelectElement;
const numCourtsInput = document.getElementById('num-courts') as HTMLInputElement;

const bannedPlayer1Select = document.getElementById('banned-player1') as HTMLSelectElement;
const bannedPlayer2Select = document.getElementById('banned-player2') as HTMLSelectElement;
const addBannedPairBtn = document.getElementById('add-banned-pair-btn') as HTMLButtonElement;
const bannedPairsList = document.getElementById('banned-pairs-list') as HTMLElement;

const startSessionBtn = document.getElementById('start-session-btn') as HTMLButtonElement;
const showStatsBtn = document.getElementById('show-stats-btn') as HTMLButtonElement;
const endSessionBtn = document.getElementById('end-session-btn') as HTMLButtonElement;
const activePlayersList = document.getElementById('active-players-list') as HTMLElement;
const sessionPlayerNameInput = document.getElementById('session-player-name') as HTMLInputElement;
const addSessionPlayerBtn = document.getElementById('add-session-player-btn') as HTMLButtonElement;

const courtsGrid = document.getElementById('courts-grid') as HTMLElement;
const waitingArea = document.getElementById('waiting-area') as HTMLElement;
const waitingPlayers = document.getElementById('waiting-players') as HTMLElement;
const statsGrid = document.getElementById('stats-grid') as HTMLElement;
const matchHistorySection = document.getElementById('match-history-section') as HTMLElement;
const matchHistoryList = document.getElementById('match-history-list') as HTMLElement;
const showHistoryBtn = document.getElementById('show-history-btn') as HTMLButtonElement;

// Event Listeners
addPlayerBtn.addEventListener('click', handleAddPlayer);
playerNameInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleAddPlayer();
});

addBannedPairBtn.addEventListener('click', handleAddBannedPair);
startSessionBtn.addEventListener('click', handleStartSession);
showStatsBtn.addEventListener('click', toggleStats);
showHistoryBtn.addEventListener('click', toggleHistory);
endSessionBtn.addEventListener('click', handleEndSession);
addSessionPlayerBtn.addEventListener('click', handleAddSessionPlayer);
sessionPlayerNameInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleAddSessionPlayer();
});

// Functions
function handleAddPlayer() {
  const name = playerNameInput.value.trim();
  if (!name) return;
  
  const player: Player = {
    id: generateId(),
    name,
  };
  
  players.push(player);
  playerNameInput.value = '';
  renderPlayerList();
  updateBannedPairSelects();
}

function handleRemovePlayer(playerId: string) {
  const index = players.findIndex(p => p.id === playerId);
  if (index > -1) {
    players.splice(index, 1);
    
    // Remove from banned pairs
    for (let i = bannedPairs.length - 1; i >= 0; i--) {
      if (bannedPairs[i][0] === playerId || bannedPairs[i][1] === playerId) {
        bannedPairs.splice(i, 1);
      }
    }
    
    renderPlayerList();
    updateBannedPairSelects();
    renderBannedPairs();
  }
}

function renderPlayerList() {
  playerList.innerHTML = '';
  players.forEach(player => {
    const tag = document.createElement('div');
    tag.className = 'player-tag';
    tag.innerHTML = `
      <span>${player.name}</span>
      <button onclick="window.removePlayer('${player.id}')">×</button>
    `;
    playerList.appendChild(tag);
  });
  
  startSessionBtn.disabled = players.length < 2;
}

function updateBannedPairSelects() {
  bannedPlayer1Select.innerHTML = '<option value="">Select Player 1</option>';
  bannedPlayer2Select.innerHTML = '<option value="">Select Player 2</option>';
  
  players.forEach(player => {
    const option1 = document.createElement('option');
    option1.value = player.id;
    option1.textContent = player.name;
    bannedPlayer1Select.appendChild(option1);
    
    const option2 = document.createElement('option');
    option2.value = player.id;
    option2.textContent = player.name;
    bannedPlayer2Select.appendChild(option2);
  });
}

function handleAddBannedPair() {
  const player1 = bannedPlayer1Select.value;
  const player2 = bannedPlayer2Select.value;
  
  if (!player1 || !player2 || player1 === player2) {
    alert('Please select two different players');
    return;
  }
  
  // Check if pair already banned
  const exists = bannedPairs.some(
    ([p1, p2]) => (p1 === player1 && p2 === player2) || (p1 === player2 && p2 === player1)
  );
  
  if (exists) {
    alert('This pair is already banned');
    return;
  }
  
  bannedPairs.push([player1, player2]);
  renderBannedPairs();
}

function handleRemoveBannedPair(index: number) {
  bannedPairs.splice(index, 1);
  renderBannedPairs();
}

function renderBannedPairs() {
  bannedPairsList.innerHTML = '';
  bannedPairs.forEach((pair, index) => {
    const player1 = players.find(p => p.id === pair[0]);
    const player2 = players.find(p => p.id === pair[1]);
    
    if (player1 && player2) {
      const tag = document.createElement('div');
      tag.className = 'banned-pair-tag';
      tag.innerHTML = `
        <span>${player1.name} & ${player2.name}</span>
        <button onclick="window.removeBannedPair(${index})">×</button>
      `;
      bannedPairsList.appendChild(tag);
    }
  });
}

function handleStartSession() {
  if (players.length < 2) {
    alert('Please add at least 2 players to start a session');
    return;
  }
  
  const config: SessionConfig = {
    mode: gameModeSelect.value as any,
    sessionType: sessionTypeSelect.value as any,
    players: [...players],
    courts: parseInt(numCourtsInput.value),
    bannedPairs: [...bannedPairs],
  };
  
  currentSession = createSession(config);
  // Automatically create initial matches
  currentSession = evaluateAndCreateMatches(currentSession);
  
  // Auto-start all initial matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  setupSection.classList.add('hidden');
  controlSection.classList.remove('hidden');
  courtsSection.classList.remove('hidden');
  
  renderSession();
  renderActivePlayers();
}

function handleAddSessionPlayer() {
  if (!currentSession) return;
  
  const name = sessionPlayerNameInput.value.trim();
  if (!name) return;
  
  const player: Player = {
    id: generateId(),
    name,
  };
  
  currentSession = addPlayerToSession(currentSession, player);
  sessionPlayerNameInput.value = '';
  
  // Auto-start any new matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
}

function handleRemoveSessionPlayer(playerId: string) {
  if (!currentSession) return;
  
  if (!confirm('Remove this player from the session? Any active matches will be forfeited.')) {
    return;
  }
  
  currentSession = removePlayerFromSession(currentSession, playerId);
  
  // Auto-start any new matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
}

function handleCompleteMatch(matchId: string, team1Score: number, team2Score: number) {
  if (!currentSession) return;
  
  currentSession = completeMatch(currentSession, matchId, team1Score, team2Score);
  
  // Auto-start any new matches created by evaluation
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
}

function handleForfeitMatch(matchId: string) {
  if (!currentSession) return;
  
  if (!confirm('Forfeit this match? No stats will be recorded.')) {
    return;
  }
  
  currentSession = forfeitMatch(currentSession, matchId);
  
  // Auto-start any new matches created by evaluation
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
}

function renderSession() {
  if (!currentSession) return;
  
  // Render courts
  courtsGrid.innerHTML = '';
  
  const activeMatches = currentSession.matches.filter(
    m => m.status === 'in-progress' || m.status === 'waiting'
  );
  
  activeMatches.forEach(match => {
    const courtDiv = document.createElement('div');
    courtDiv.className = 'court';
    
    const statusClass = `status-${match.status.replace('_', '-')}`;
    const statusText = match.status === 'in-progress' ? 'In Progress' : 'Waiting';
    
    let scoreHtml = '';
    if (match.status === 'in-progress') {
      scoreHtml = `
        <div class="match-controls">
          <div class="score-input">
            <input type="number" id="score1-${match.id}" min="0" placeholder="Score">
            <span class="vs-text">vs</span>
            <input type="number" id="score2-${match.id}" min="0" placeholder="Score">
          </div>
          <div class="control-buttons">
            <button class="btn-success" onclick="window.completeMatch('${match.id}')">Complete</button>
            <button class="btn-danger" onclick="window.forfeitMatch('${match.id}')">Forfeit</button>
          </div>
        </div>
      `;
    }
    
    courtDiv.innerHTML = `
      <div class="court-header">
        Court ${match.courtNumber}
        <span class="match-status ${statusClass}">${statusText}</span>
      </div>
      <div class="court-content">
        <div class="team team-left">
          <div class="team-label">Team 1</div>
          <div class="team-players">
            ${match.team1.map(id => {
              const player = currentSession!.config.players.find(p => p.id === id);
              return `<span class="player-name">${player?.name || 'Unknown'}</span>`;
            }).join('')}
          </div>
        </div>
        ${scoreHtml}
        <div class="team team-right">
          <div class="team-label">Team 2</div>
          <div class="team-players">
            ${match.team2.map(id => {
              const player = currentSession!.config.players.find(p => p.id === id);
              return `<span class="player-name">${player?.name || 'Unknown'}</span>`;
            }).join('')}
          </div>
        </div>
      </div>
    `;
    
    courtsGrid.appendChild(courtDiv);
  });
  
  // Render waiting players
  if (currentSession.waitingPlayers.length > 0) {
    waitingArea.style.display = 'block';
    waitingPlayers.innerHTML = '';
    
    currentSession.waitingPlayers.forEach(playerId => {
      const player = currentSession!.config.players.find(p => p.id === playerId);
      if (player) {
        const tag = document.createElement('div');
        tag.className = 'player-tag';
        tag.innerHTML = `<span>${player.name}</span>`;
        waitingPlayers.appendChild(tag);
      }
    });
  } else {
    waitingArea.style.display = 'none';
  }
}

function renderActivePlayers() {
  if (!currentSession) return;
  
  activePlayersList.innerHTML = '';
  
  // Show all players with active status
  currentSession.config.players.forEach(player => {
    const isActive = currentSession!.activePlayers.has(player.id);
    const tag = document.createElement('div');
    tag.className = `player-tag ${isActive ? '' : 'inactive-player'}`;
    tag.innerHTML = `
      <span>${player.name}${isActive ? '' : ' (Inactive)'}</span>
      ${isActive 
        ? `<button onclick="window.removeSessionPlayer('${player.id}')">Remove</button>`
        : `<button class="btn-success" onclick="window.reactivatePlayer('${player.id}')">Reactivate</button>`
      }
    `;
    activePlayersList.appendChild(tag);
  });
}

function toggleStats() {
  if (statsSection.classList.contains('hidden')) {
    renderStats();
    statsSection.classList.remove('hidden');
    showStatsBtn.textContent = 'Hide Statistics';
  } else {
    statsSection.classList.add('hidden');
    showStatsBtn.textContent = 'Show Statistics';
  }
}

function toggleHistory() {
  if (matchHistorySection.classList.contains('hidden')) {
    renderMatchHistory();
    matchHistorySection.classList.remove('hidden');
    showHistoryBtn.textContent = 'Hide History';
  } else {
    matchHistorySection.classList.add('hidden');
    showHistoryBtn.textContent = 'Show History';
  }
}

function renderMatchHistory() {
  if (!currentSession) return;
  
  matchHistoryList.innerHTML = '';
  
  const completedMatches = currentSession.matches.filter(
    m => m.status === 'completed' || m.status === 'forfeited'
  );
  
  if (completedMatches.length === 0) {
    matchHistoryList.innerHTML = '<p style="text-align: center; color: #666;">No completed matches yet</p>';
    return;
  }
  
  // Show most recent first
  const sortedMatches = [...completedMatches].reverse();
  
  sortedMatches.forEach(match => {
    const card = document.createElement('div');
    card.className = 'history-card';
    
    const team1Names = match.team1.map(id => {
      const player = currentSession!.config.players.find(p => p.id === id);
      return player?.name || 'Unknown';
    }).join(' & ');
    
    const team2Names = match.team2.map(id => {
      const player = currentSession!.config.players.find(p => p.id === id);
      return player?.name || 'Unknown';
    }).join(' & ');
    
    if (match.status === 'forfeited') {
      card.innerHTML = `
        <div class="history-header">
          <span class="history-court">Court ${match.courtNumber}</span>
          <span class="match-status status-forfeited">Forfeited</span>
        </div>
        <div class="history-teams">
          <div class="history-team">${team1Names}</div>
          <div class="vs-text">vs</div>
          <div class="history-team">${team2Names}</div>
        </div>
      `;
    } else if (match.score) {
      const team1Won = match.score.team1Score > match.score.team2Score;
      
      card.innerHTML = `
        <div class="history-header">
          <span class="history-court">Court ${match.courtNumber}</span>
          <span class="match-status status-completed">Completed</span>
        </div>
        <div class="history-teams">
          <div class="history-team ${team1Won ? 'winner' : 'loser'}">
            ${team1Names}
          </div>
          <div class="history-score">
            <input type="number" 
                   class="history-score-input" 
                   value="${match.score.team1Score}" 
                   id="history-score1-${match.id}"
                   min="0">
            <span class="vs-text">-</span>
            <input type="number" 
                   class="history-score-input" 
                   value="${match.score.team2Score}" 
                   id="history-score2-${match.id}"
                   min="0">
            <button class="btn-small" onclick="window.editMatchScore('${match.id}')">Save</button>
          </div>
          <div class="history-team ${team1Won ? 'loser' : 'winner'}">
            ${team2Names}
          </div>
        </div>
      `;
    }
    
    matchHistoryList.appendChild(card);
  });
}

function renderStats() {
  if (!currentSession) return;
  
  statsGrid.innerHTML = '';
  
  currentSession.config.players.forEach(player => {
    const stats = currentSession!.playerStats.get(player.id);
    if (!stats) return;
    
    const card = document.createElement('div');
    card.className = 'stat-card';
    
    const winRate = stats.gamesPlayed > 0 
      ? ((stats.wins / stats.gamesPlayed) * 100).toFixed(1)
      : '0.0';
    
    card.innerHTML = `
      <h4>${player.name}</h4>
      <div class="stat-line">
        <span>Games Played:</span>
        <strong>${stats.gamesPlayed}</strong>
      </div>
      <div class="stat-line">
        <span>Wins:</span>
        <strong>${stats.wins}</strong>
      </div>
      <div class="stat-line">
        <span>Losses:</span>
        <strong>${stats.losses}</strong>
      </div>
      <div class="stat-line">
        <span>Win Rate:</span>
        <strong>${winRate}%</strong>
      </div>
      <div class="stat-line">
        <span>Times Waited:</span>
        <strong>${stats.gamesWaited}</strong>
      </div>
      <div class="stat-line">
        <span>Unique Partners:</span>
        <strong>${stats.partnersPlayed.size}</strong>
      </div>
      <div class="stat-line">
        <span>Unique Opponents:</span>
        <strong>${stats.opponentsPlayed.size}</strong>
      </div>
    `;
    
    statsGrid.appendChild(card);
  });
}

function handleEndSession() {
  if (!confirm('Are you sure you want to end this session?')) return;
  
  currentSession = null;
  players.length = 0;
  bannedPairs.length = 0;
  
  setupSection.classList.remove('hidden');
  controlSection.classList.add('hidden');
  courtsSection.classList.add('hidden');
  statsSection.classList.add('hidden');
  
  renderPlayerList();
  updateBannedPairSelects();
  renderBannedPairs();
}

// Expose functions to window for onclick handlers
(window as any).removePlayer = handleRemovePlayer;
(window as any).removeBannedPair = handleRemoveBannedPair;
(window as any).removeSessionPlayer = handleRemoveSessionPlayer;
(window as any).reactivatePlayer = (playerId: string) => {
  if (!currentSession) return;
  const newActivePlayers = new Set(currentSession.activePlayers);
  newActivePlayers.add(playerId);
  currentSession = {
    ...currentSession,
    activePlayers: newActivePlayers,
  };
  currentSession = evaluateAndCreateMatches(currentSession);
  
  // Auto-start new matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
};
(window as any).completeMatch = (matchId: string) => {
  const score1Input = document.getElementById(`score1-${matchId}`) as HTMLInputElement;
  const score2Input = document.getElementById(`score2-${matchId}`) as HTMLInputElement;
  
  const score1 = parseInt(score1Input.value);
  const score2 = parseInt(score2Input.value);
  
  if (isNaN(score1) || isNaN(score2)) {
    alert('Please enter valid scores');
    return;
  }
  
  handleCompleteMatch(matchId, score1, score2);
};
(window as any).forfeitMatch = handleForfeitMatch;
(window as any).editMatchScore = (matchId: string) => {
  if (!currentSession) return;
  
  const score1Input = document.getElementById(`history-score1-${matchId}`) as HTMLInputElement;
  const score2Input = document.getElementById(`history-score2-${matchId}`) as HTMLInputElement;
  
  const score1 = parseInt(score1Input.value);
  const score2 = parseInt(score2Input.value);
  
  if (isNaN(score1) || isNaN(score2)) {
    alert('Please enter valid scores');
    return;
  }
  
  currentSession = completeMatch(currentSession, matchId, score1, score2);
  renderStats();
  renderMatchHistory();
  alert('Score updated successfully!');
};

// Initialize
renderPlayerList();
updateBannedPairSelects();
