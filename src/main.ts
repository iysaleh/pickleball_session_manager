import type { Session, Player, SessionConfig, Match } from './types';
import { createSession, addPlayerToSession, removePlayerFromSession, addTeamToSession, removeTeamFromSession, startMatch, completeMatch, forfeitMatch, checkForAvailableCourts, evaluateAndCreateMatches, updateMaxQueueSize } from './session';
import { generateId, calculatePlayerRankings, calculateTeamRankings } from './utils';
import { generateRoundRobinQueue } from './queue';
import { calculatePlayerRating } from './kingofcourt';

let currentSession: Session | null = null;
let players: Player[] = [];
let bannedPairs: [string, string][] = [];
let lockedTeams: string[][] = []; // Array of locked team pairs

// Check for test mode
const urlParams = new URLSearchParams(window.location.search);
const isTestMode = urlParams.get('test') === 'true';

// DOM Elements
const setupSection = document.getElementById('setup-section') as HTMLElement;
const controlSection = document.getElementById('control-section') as HTMLElement;
const courtsSection = document.getElementById('courts-section') as HTMLElement;
const statsModal = document.getElementById('stats-modal') as HTMLElement;
const statsModalClose = document.getElementById('stats-modal-close') as HTMLButtonElement;
const testModeContainer = document.getElementById('test-mode-container') as HTMLElement;
const addTestPlayersBtn = document.getElementById('add-test-players-btn') as HTMLButtonElement;

const playerNameInput = document.getElementById('player-name') as HTMLInputElement;
const addPlayerBtn = document.getElementById('add-player-btn') as HTMLButtonElement;
const playerList = document.getElementById('player-list') as HTMLElement;

const gameModeSelect = document.getElementById('game-mode') as HTMLSelectElement;
const sessionTypeSelect = document.getElementById('session-type') as HTMLSelectElement;
const numCourtsInput = document.getElementById('num-courts') as HTMLInputElement;
const setupMaxQueueSizeInput = document.getElementById('setup-max-queue-size') as HTMLInputElement;

const bannedPlayer1Select = document.getElementById('banned-player1') as HTMLSelectElement;
const bannedPlayer2Select = document.getElementById('banned-player2') as HTMLSelectElement;
const addBannedPairBtn = document.getElementById('add-banned-pair-btn') as HTMLButtonElement;
const bannedPairsList = document.getElementById('banned-pairs-list') as HTMLElement;

const startSessionBtn = document.getElementById('start-session-btn') as HTMLButtonElement;
const setupEndSessionClearBtn = document.getElementById('setup-end-session-clear-btn') as HTMLButtonElement;
const setupEndSessionKeepBtn = document.getElementById('setup-end-session-keep-btn') as HTMLButtonElement;
const showRankingsBtn = document.getElementById('show-rankings-btn') as HTMLButtonElement;
const showStatsBtn = document.getElementById('show-stats-btn') as HTMLButtonElement;
const showHistoryBtn = document.getElementById('show-history-btn') as HTMLButtonElement;
const exportSessionBtn = document.getElementById('export-session-btn') as HTMLButtonElement;
const editSessionBtn = document.getElementById('edit-session-btn') as HTMLButtonElement;
const clearSessionBtn = document.getElementById('clear-session-btn') as HTMLButtonElement;
const endSessionClearBtn = document.getElementById('end-session-clear-btn') as HTMLButtonElement;
const endSessionKeepBtn = document.getElementById('end-session-keep-btn') as HTMLButtonElement;
const rankingsModal = document.getElementById('rankings-modal') as HTMLElement;
const rankingsModalClose = document.getElementById('rankings-modal-close') as HTMLButtonElement;
const rankingsList = document.getElementById('rankings-list') as HTMLElement;
const activePlayersList = document.getElementById('active-players-list') as HTMLElement;
const sessionPlayerNameInput = document.getElementById('session-player-name') as HTMLInputElement;
const addSessionPlayerBtn = document.getElementById('add-session-player-btn') as HTMLButtonElement;
const sessionPlayerControls = document.getElementById('session-player-controls') as HTMLElement;
const sessionTeamControls = document.getElementById('session-team-controls') as HTMLElement;
const sessionTeamPlayer1Input = document.getElementById('session-team-player1-name') as HTMLInputElement;
const sessionTeamPlayer2Input = document.getElementById('session-team-player2-name') as HTMLInputElement;
const addSessionTeamBtn = document.getElementById('add-session-team-btn') as HTMLButtonElement;

const courtsGrid = document.getElementById('courts-grid') as HTMLElement;
const courtsPerRowInput = document.getElementById('courts-per-row') as HTMLInputElement;
const applyLayoutBtn = document.getElementById('apply-courts-layout-btn') as HTMLButtonElement;
const waitingArea = document.getElementById('waiting-area') as HTMLElement;
const waitingPlayers = document.getElementById('waiting-players') as HTMLElement;
const statsGrid = document.getElementById('stats-grid') as HTMLElement;
const matchHistorySection = document.getElementById('match-history-section') as HTMLElement;
const matchHistoryList = document.getElementById('match-history-list') as HTMLElement;
const themeToggle = document.getElementById('theme-toggle') as HTMLButtonElement;
const advancedConfigToggle = document.getElementById('advanced-config-toggle') as HTMLButtonElement;
const advancedConfigSection = document.getElementById('advanced-config-section') as HTMLElement;

const queueSection = document.getElementById('queue-section') as HTMLElement;
const queueList = document.getElementById('queue-list') as HTMLElement;
const showQueueBtn = document.getElementById('show-queue-btn') as HTMLButtonElement;
const maxQueueSizeInput = document.getElementById('max-queue-size') as HTMLInputElement;
const matchesPerPageInput = document.getElementById('matches-per-page') as HTMLInputElement;
const applyQueuePaginationBtn = document.getElementById('apply-queue-pagination-btn') as HTMLButtonElement;
const queuePrevBtn = document.getElementById('queue-prev-btn') as HTMLButtonElement;
const queueNextBtn = document.getElementById('queue-next-btn') as HTMLButtonElement;
const queuePageInfo = document.getElementById('queue-page-info') as HTMLElement;

// Locked teams elements
const lockedTeamsCheckbox = document.getElementById('locked-teams-checkbox') as HTMLInputElement;
const lockedTeamsContainer = document.getElementById('locked-teams-container') as HTMLElement;
const lockedTeamsSetup = document.getElementById('locked-teams-setup') as HTMLElement;
const addLockedTeamBtn = document.getElementById('add-locked-team-btn') as HTMLButtonElement;
const lockedTeamsList = document.getElementById('locked-teams-list') as HTMLElement;

// Court layout state
let courtsPerRow = 2;

// Theme state
let isDarkMode = true; // Default to dark mode

// Queue state
let queuePage = 0;
let matchesPerPage = 10;

// Event Listeners
addPlayerBtn.addEventListener('click', handleAddPlayer);
playerNameInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleAddPlayer();
});

// Test mode
if (isTestMode && testModeContainer) {
  testModeContainer.style.display = 'block';
  addTestPlayersBtn.addEventListener('click', handleAddTestPlayers);
}

addBannedPairBtn.addEventListener('click', handleAddBannedPair);
startSessionBtn.addEventListener('click', handleStartSession);
setupEndSessionClearBtn.addEventListener('click', handleEndSessionAndClearData);
setupEndSessionKeepBtn.addEventListener('click', handleEndSessionAndKeepPlayers);
showRankingsBtn.addEventListener('click', openRankingsModal);
rankingsModalClose.addEventListener('click', closeRankingsModal);
rankingsModal.addEventListener('click', (e) => {
  if (e.target === rankingsModal) {
    closeRankingsModal();
  }
});
showStatsBtn.addEventListener('click', openStatsModal);
statsModalClose.addEventListener('click', closeStatsModal);
statsModal.addEventListener('click', (e) => {
  if (e.target === statsModal) {
    closeStatsModal();
  }
});
showHistoryBtn.addEventListener('click', toggleHistory);
exportSessionBtn.addEventListener('click', handleExportSession);
editSessionBtn.addEventListener('click', handleEditSession);
clearSessionBtn.addEventListener('click', handleClearSessionData);
endSessionClearBtn.addEventListener('click', handleEndSessionAndClearData);
endSessionKeepBtn.addEventListener('click', handleEndSessionAndKeepPlayers);
addSessionPlayerBtn.addEventListener('click', handleAddSessionPlayer);
sessionPlayerNameInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleAddSessionPlayer();
});
addSessionTeamBtn.addEventListener('click', handleAddSessionTeam);
sessionTeamPlayer1Input.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    sessionTeamPlayer2Input.focus();
  }
});
sessionTeamPlayer2Input.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    handleAddSessionTeam();
  }
});
applyLayoutBtn.addEventListener('click', handleApplyLayout);
themeToggle.addEventListener('click', toggleTheme);
advancedConfigToggle.addEventListener('click', toggleAdvancedConfig);
showQueueBtn.addEventListener('click', toggleQueue);
applyQueuePaginationBtn.addEventListener('click', handleApplyQueuePagination);
queuePrevBtn.addEventListener('click', () => { queuePage = Math.max(0, queuePage - 1); renderQueue(); });
queueNextBtn.addEventListener('click', () => { queuePage++; renderQueue(); });

// Locked teams event listeners
sessionTypeSelect.addEventListener('change', handleSessionTypeChange);
lockedTeamsCheckbox.addEventListener('change', handleLockedTeamsToggle);
addLockedTeamBtn.addEventListener('click', handleAddLockedTeam);

// Add enter key support for team name inputs
const teamPlayer1NameInput = document.getElementById('team-player1-name') as HTMLInputElement;
const teamPlayer2NameInput = document.getElementById('team-player2-name') as HTMLInputElement;
if (teamPlayer1NameInput) {
  teamPlayer1NameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      teamPlayer2NameInput.focus();
    }
  });
}
if (teamPlayer2NameInput) {
  teamPlayer2NameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddLockedTeam();
    }
  });
}

// Initialize theme
initializeTheme();

// Initialize locked teams visibility
handleSessionTypeChange();

// Load saved state from localStorage
loadStateFromLocalStorage();

// Functions
function initializeTheme() {
  // Check localStorage first, otherwise default to dark
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    isDarkMode = savedTheme === 'dark';
  }
  
  // Apply theme
  if (isDarkMode) {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeToggle.textContent = '🌙';
  } else {
    document.documentElement.removeAttribute('data-theme');
    themeToggle.textContent = '☀️';
  }
}

function toggleTheme() {
  isDarkMode = !isDarkMode;
  
  if (isDarkMode) {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeToggle.textContent = '🌙';
    localStorage.setItem('theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
    themeToggle.textContent = '☀️';
    localStorage.setItem('theme', 'light');
  }
}

function toggleAdvancedConfig() {
  advancedConfigSection.classList.toggle('hidden');
}

// LocalStorage functions
function saveStateToLocalStorage() {
  try {
    const state = {
      currentSession: currentSession ? serializeSession(currentSession) : null,
      players: players,
      bannedPairs: bannedPairs,
      lockedTeams: lockedTeams,
      courtsPerRow: courtsPerRow,
      queuePage: queuePage,
      matchesPerPage: matchesPerPage,
      timestamp: Date.now()
    };
    localStorage.setItem('pickleballSessionState', JSON.stringify(state));
  } catch (error) {
    console.error('Failed to save state to localStorage:', error);
  }
}

function loadStateFromLocalStorage() {
  try {
    const savedState = localStorage.getItem('pickleballSessionState');
    if (!savedState) return;
    
    const state = JSON.parse(savedState);
    
    // Restore setup state
    if (state.players) {
      players = state.players;
      renderPlayerList();
      updateBannedPairSelects();
    }
    
    if (state.bannedPairs) {
      bannedPairs = state.bannedPairs;
      renderBannedPairs();
    }
    
    if (state.lockedTeams) {
      lockedTeams = state.lockedTeams;
      renderLockedTeams();
    }
    
    if (state.courtsPerRow) {
      courtsPerRow = state.courtsPerRow;
      courtsPerRowInput.value = courtsPerRow.toString();
    }
    
    if (state.matchesPerPage) {
      matchesPerPage = state.matchesPerPage;
      matchesPerPageInput.value = matchesPerPage.toString();
    }
    
    if (state.queuePage !== undefined) {
      queuePage = state.queuePage;
    }
    
    // Restore active session
    if (state.currentSession) {
      currentSession = deserializeSession(state.currentSession);
      
      // Lock configuration inputs since session is active
      lockConfigurationInputs();
      
      // Switch to control view
      setupSection.classList.add('hidden');
      controlSection.classList.remove('hidden');
      courtsSection.classList.remove('hidden');
      queueSection.classList.remove('hidden');
      showQueueBtn.textContent = 'Hide Queue';
      matchHistorySection.classList.remove('hidden');
      showHistoryBtn.textContent = 'Hide History';
      
      // Apply layout
      updateCourtsGridLayout();
      
      // Render everything
      renderSession();
      renderActivePlayers();
      renderQueue();
      
      // Sync max queue size input
      if (currentSession) {
        maxQueueSizeInput.value = currentSession.maxQueueSize.toString();
      }
    }
  } catch (error) {
    console.error('Failed to load state from localStorage:', error);
  }
}

function serializeSession(session: Session): any {
  return {
    id: session.id,
    config: session.config,
    matches: session.matches,
    waitingPlayers: session.waitingPlayers,
    playerStats: Array.from(session.playerStats.entries()).map(([id, stats]) => ({
      playerId: stats.playerId,
      gamesPlayed: stats.gamesPlayed,
      gamesWaited: stats.gamesWaited,
      wins: stats.wins,
      losses: stats.losses,
      partnersPlayed: Array.from(stats.partnersPlayed),
      opponentsPlayed: Array.from(stats.opponentsPlayed),
      totalPointsFor: stats.totalPointsFor,
      totalPointsAgainst: stats.totalPointsAgainst,
    })),
    activePlayers: Array.from(session.activePlayers),
    matchQueue: session.matchQueue,
    maxQueueSize: session.maxQueueSize,
  };
}

function deserializeSession(data: any): Session {
  const playerStats = new Map();
  data.playerStats.forEach((stats: any) => {
    playerStats.set(stats.playerId, {
      ...stats,
      partnersPlayed: new Set(stats.partnersPlayed),
      opponentsPlayed: new Set(stats.opponentsPlayed),
    });
  });
  
  return {
    id: data.id,
    config: data.config,
    matches: data.matches,
    waitingPlayers: data.waitingPlayers,
    playerStats: playerStats,
    activePlayers: new Set(data.activePlayers),
    matchQueue: data.matchQueue,
    maxQueueSize: data.maxQueueSize,
  };
}

function clearLocalStorageState() {
  try {
    localStorage.removeItem('pickleballSessionState');
  } catch (error) {
    console.error('Failed to clear localStorage:', error);
  }
}

function handleApplyLayout() {
  const value = parseInt(courtsPerRowInput.value);
  if (value && value >= 1 && value <= 6) {
    courtsPerRow = value;
    updateCourtsGridLayout();
    renderSession();
  } else {
    alert('Please enter a value between 1 and 6');
  }
}

function updateCourtsGridLayout() {
  courtsGrid.style.gridTemplateColumns = `repeat(${courtsPerRow}, 1fr)`;
}

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
  saveStateToLocalStorage();
}

function handleAddTestPlayers() {
  // Check if we're in locked teams mode
  if (lockedTeamsCheckbox.checked) {
    // Add 9 teams
    const teamNames = [
      ['James Anderson', 'Sarah Mitchell'],
      ['Michael Chen', 'Emily Rodriguez'],
      ['David Thompson', 'Jessica Williams'],
      ['Christopher Lee', 'Amanda Martinez'],
      ['Daniel Brown', 'Lauren Davis'],
      ['Matthew Wilson', 'Ashley Garcia'],
      ['Joshua Taylor', 'Rachel Johnson'],
      ['Andrew Miller', 'Nicole White'],
      ['Brandon Moore', 'Stephanie Harris']
    ];
    
    // Clear existing players and teams first
    players = [];
    lockedTeams = [];
    bannedPairs = [];
    
    teamNames.forEach(([name1, name2]) => {
      const player1: Player = {
        id: generateId(),
        name: name1,
      };
      
      const player2: Player = {
        id: generateId(),
        name: name2,
      };
      
      players.push(player1);
      players.push(player2);
      lockedTeams.push([player1.id, player2.id]);
    });
    
    renderLockedTeams();
    updateBannedPairSelects();
    renderBannedPairs();
    
    alert('✅ Added 9 test teams!');
  } else {
    // Add 18 individual players
    const testNames = [
      'James Anderson',
      'Sarah Mitchell',
      'Michael Chen',
      'Emily Rodriguez',
      'David Thompson',
      'Jessica Williams',
      'Christopher Lee',
      'Amanda Martinez',
      'Daniel Brown',
      'Lauren Davis',
      'Matthew Wilson',
      'Ashley Garcia',
      'Joshua Taylor',
      'Rachel Johnson',
      'Andrew Miller',
      'Nicole White',
      'Brandon Moore',
      'Stephanie Harris'
    ];
    
    // Clear existing players first
    players = [];
    bannedPairs = [];
    
    testNames.forEach(name => {
      const player: Player = {
        id: generateId(),
        name,
      };
      players.push(player);
    });
    
    renderPlayerList();
    updateBannedPairSelects();
    renderBannedPairs();
    
    alert('✅ Added 18 test players!');
  }
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
    saveStateToLocalStorage();
  }
}

function renderPlayerList() {
  playerList.innerHTML = '';
  
  if (players.length === 0) {
    playerList.innerHTML = '<p style="color: var(--text-secondary); padding: 10px;">No players added yet</p>';
  } else {
    const list = document.createElement('ol');
    list.style.paddingLeft = '0';
    list.style.marginLeft = '20px';
    list.style.color = 'var(--text-primary)';
    list.style.columns = 'auto';
    list.style.columnWidth = '250px';
    list.style.columnGap = '30px';
    list.style.listStylePosition = 'outside';
    list.style.width = '100%';
    
    // Estimate number of columns based on container width
    const containerWidth = playerList.offsetWidth || 1000;
    const columnWidth = 250 + 30; // columnWidth + gap
    const numColumns = Math.max(1, Math.floor(containerWidth / columnWidth));
    const itemsPerColumn = Math.ceil(players.length / numColumns);
    
    players.forEach((player, idx) => {
      const item = document.createElement('li');
      item.style.marginBottom = '8px';
      item.style.display = 'list-item';
      item.style.breakInside = 'avoid';
      item.style.paddingLeft = '10px';
      
      // Calculate which column this item is in
      const columnIndex = Math.floor(idx / itemsPerColumn);
      const bgClass = columnIndex % 2 === 0 ? 'player-list-item-bg-0' : 'player-list-item-bg-1';
      item.className = bgClass;
      
      const content = document.createElement('div');
      content.style.display = 'flex';
      content.style.justifyContent = 'space-between';
      content.style.alignItems = 'center';
      content.style.gap = '10px';
      
      const nameSpan = document.createElement('span');
      nameSpan.textContent = player.name;
      nameSpan.style.flex = '1';
      nameSpan.style.color = 'var(--text-primary)';
      
      const removeBtn = document.createElement('button');
      removeBtn.textContent = '×';
      removeBtn.onclick = () => (window as any).removePlayer(player.id);
      removeBtn.disabled = currentSession !== null; // Disable if session is active
      removeBtn.style.cssText = 'margin-left: 10px; color: #dc3545; background: transparent; border: 1px solid #dc3545; padding: 2px 8px; border-radius: 4px; cursor: pointer; flex-shrink: 0;';
      
      content.appendChild(nameSpan);
      content.appendChild(removeBtn);
      item.appendChild(content);
      list.appendChild(item);
    });
    
    playerList.appendChild(list);
  }
  
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
  saveStateToLocalStorage();
}

function handleRemoveBannedPair(index: number) {
  bannedPairs.splice(index, 1);
  renderBannedPairs();
  saveStateToLocalStorage();
}

function renderBannedPairs() {
  bannedPairsList.innerHTML = '';
  bannedPairs.forEach((pair, index) => {
    const player1 = players.find(p => p.id === pair[0]);
    const player2 = players.find(p => p.id === pair[1]);
    
    if (player1 && player2) {
      const tag = document.createElement('div');
      tag.className = 'banned-pair-tag';
      
      const nameSpan = document.createElement('span');
      nameSpan.textContent = `${player1.name} & ${player2.name}`;
      
      const removeBtn = document.createElement('button');
      removeBtn.textContent = '×';
      removeBtn.onclick = () => (window as any).removeBannedPair(index);
      removeBtn.disabled = currentSession !== null; // Disable if session is active
      
      tag.appendChild(nameSpan);
      tag.appendChild(removeBtn);
      bannedPairsList.appendChild(tag);
    }
  });
}

function handleSessionTypeChange() {
  // Show/hide locked teams checkbox based on session type
  if (sessionTypeSelect.value === 'doubles') {
    lockedTeamsContainer.style.display = 'block';
  } else {
    lockedTeamsContainer.style.display = 'none';
    lockedTeamsCheckbox.checked = false;
    lockedTeamsSetup.classList.add('hidden');
    document.getElementById('player-input-section')!.classList.remove('hidden');
  }
}

function handleLockedTeamsToggle() {
  if (lockedTeamsCheckbox.checked) {
    // Show team input interface, hide individual player interface
    lockedTeamsSetup.classList.remove('hidden');
    document.getElementById('player-input-section')!.classList.add('hidden');
    renderLockedTeams();
  } else {
    // Show individual player interface, hide team interface
    lockedTeamsSetup.classList.add('hidden');
    document.getElementById('player-input-section')!.classList.remove('hidden');
    lockedTeams = [];
    renderPlayerList();
  }
}

// No longer needed - players are added directly as teams
function updateTeamPlayerSelects() {
  // Deprecated - kept for backwards compatibility
}

function handleAddLockedTeam() {
  const player1Name = (document.getElementById('team-player1-name') as HTMLInputElement).value.trim();
  const player2Name = (document.getElementById('team-player2-name') as HTMLInputElement).value.trim();
  
  if (!player1Name || !player2Name) {
    alert('Please enter both player names');
    return;
  }
  
  if (player1Name === player2Name) {
    alert('Please enter two different player names');
    return;
  }
  
  // Create two new players
  const player1: Player = {
    id: generateId(),
    name: player1Name,
  };
  
  const player2: Player = {
    id: generateId(),
    name: player2Name,
  };
  
  // Add to players array
  players.push(player1);
  players.push(player2);
  
  // Add to locked teams
  lockedTeams.push([player1.id, player2.id]);
  
  // Clear inputs
  (document.getElementById('team-player1-name') as HTMLInputElement).value = '';
  (document.getElementById('team-player2-name') as HTMLInputElement).value = '';
  
  renderLockedTeams();
  updateBannedPairSelects();
  saveStateToLocalStorage();
}

function handleRemoveLockedTeam(index: number) {
  const team = lockedTeams[index];
  
  // Remove the team
  lockedTeams.splice(index, 1);
  
  // Remove the players from the players array
  players = players.filter(p => !team.includes(p.id));
  
  // Remove from banned pairs
  team.forEach(playerId => {
    for (let i = bannedPairs.length - 1; i >= 0; i--) {
      if (bannedPairs[i][0] === playerId || bannedPairs[i][1] === playerId) {
        bannedPairs.splice(i, 1);
      }
    }
  });
  
  renderLockedTeams();
  updateBannedPairSelects();
  renderBannedPairs();
  saveStateToLocalStorage();
}

function renderLockedTeams() {
  lockedTeamsList.innerHTML = '';
  
  if (lockedTeams.length === 0) {
    lockedTeamsList.innerHTML = '<p style="color: var(--text-secondary); padding: 10px;">No teams added yet</p>';
    return;
  }
  
  // Create a numbered list
  const list = document.createElement('ol');
  list.style.paddingLeft = '0';
  list.style.marginLeft = '20px';
  list.style.color = 'var(--text-primary)';
  list.style.columns = 'auto';
  list.style.columnWidth = '300px';
  list.style.columnGap = '30px';
  list.style.listStylePosition = 'outside';
  list.style.width = '100%';
  
  lockedTeams.forEach((team, index) => {
    const player1 = players.find(p => p.id === team[0]);
    const player2 = players.find(p => p.id === team[1]);
    
    if (player1 && player2) {
      const item = document.createElement('li');
      item.style.marginBottom = '8px';
      item.style.display = 'list-item';
      item.style.breakInside = 'avoid';
      item.style.paddingLeft = '10px';
      
      // Alternate background colors for columns
      const containerWidth = lockedTeamsList.offsetWidth || 1000;
      const columnWidth = 300 + 30;
      const numColumns = Math.max(1, Math.floor(containerWidth / columnWidth));
      const itemsPerColumn = Math.ceil(lockedTeams.length / numColumns);
      const columnIndex = Math.floor(index / itemsPerColumn);
      const bgClass = columnIndex % 2 === 0 ? 'player-list-item-bg-0' : 'player-list-item-bg-1';
      item.className = bgClass;
      
      const content = document.createElement('div');
      content.style.display = 'flex';
      content.style.justifyContent = 'space-between';
      content.style.alignItems = 'center';
      content.style.gap = '10px';
      
      const nameSpan = document.createElement('span');
      nameSpan.textContent = `${player1.name} & ${player2.name}`;
      nameSpan.style.flex = '1';
      nameSpan.style.color = 'var(--text-primary)';
      
      const removeBtn = document.createElement('button');
      removeBtn.textContent = '×';
      removeBtn.onclick = () => (window as any).removeLockedTeam(index);
      removeBtn.disabled = currentSession !== null; // Disable if session is active
      removeBtn.style.cssText = 'margin-left: 10px; color: #dc3545; background: transparent; border: 1px solid #dc3545; padding: 2px 8px; border-radius: 4px; cursor: pointer; flex-shrink: 0;';
      
      content.appendChild(nameSpan);
      content.appendChild(removeBtn);
      item.appendChild(content);
      list.appendChild(item);
    }
  });
  
  lockedTeamsList.appendChild(list);
  
  // Update start button state
  startSessionBtn.disabled = lockedTeams.length < 2;
}

function handleStartSession() {
  // Check if session already exists
  if (currentSession) {
    alert('A session is already active. Please end the current session before starting a new one.');
    return;
  }
  
  // Validate locked teams if enabled
  if (lockedTeamsCheckbox.checked) {
    if (lockedTeams.length < 2) {
      alert('Please create at least 2 locked teams to start a session');
      return;
    }
  } else {
    // Normal mode - just check player count
    if (players.length < 2) {
      alert('Please add at least 2 players to start a session');
      return;
    }
  }
  
  const config: SessionConfig = {
    mode: gameModeSelect.value as any,
    sessionType: sessionTypeSelect.value as any,
    players: [...players],
    courts: parseInt(numCourtsInput.value),
    bannedPairs: [...bannedPairs],
    lockedTeams: lockedTeamsCheckbox.checked ? [...lockedTeams] : undefined,
  };
  
  const maxQueueSize = parseInt(setupMaxQueueSizeInput.value) || 100;
  currentSession = createSession(config, maxQueueSize);
  
  // Sync the active session max queue size input with setup value
  maxQueueSizeInput.value = setupMaxQueueSizeInput.value;
  // Automatically create initial matches
  // For all modes (including king-of-court), use continuous flow
  currentSession = evaluateAndCreateMatches(currentSession);
  
  // Auto-start all initial matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  // Lock configuration inputs
  lockConfigurationInputs();
  
  // Switch to Active Session page and update UI
  queueSection.classList.remove('hidden'); // Show queue by default
  showQueueBtn.textContent = 'Hide Queue'; // Update button text
  matchHistorySection.classList.remove('hidden'); // Show history by default
  showHistoryBtn.textContent = 'Hide History'; // Update button text
  
  showPage('session');
  
  // Apply initial layout
  updateCourtsGridLayout();
  
  renderSession();
  renderActivePlayers();
  renderQueue(); // Render queue initially
  saveStateToLocalStorage();
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
  
  // Evaluate to create new matches if courts available
  currentSession = evaluateAndCreateMatches(currentSession);
  
  // Auto-start any new matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
  saveStateToLocalStorage();
}

function handleAddSessionTeam() {
  if (!currentSession) return;
  
  const name1 = sessionTeamPlayer1Input.value.trim();
  const name2 = sessionTeamPlayer2Input.value.trim();
  
  if (!name1 || !name2) return;
  
  const player1: Player = {
    id: generateId(),
    name: name1,
  };
  
  const player2: Player = {
    id: generateId(),
    name: name2,
  };
  
  currentSession = addTeamToSession(currentSession, player1, player2);
  sessionTeamPlayer1Input.value = '';
  sessionTeamPlayer2Input.value = '';
  
  // Evaluate to create new matches if courts available
  currentSession = evaluateAndCreateMatches(currentSession);
  
  // Auto-start any new matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
  saveStateToLocalStorage();
}

function handleRemoveSessionPlayer(playerId: string) {
  if (!currentSession) return;
  
  if (!confirm('Remove this player from the session? Any active matches will be forfeited.')) {
    return;
  }
  
  currentSession = removePlayerFromSession(currentSession, playerId);
  
  // Also remove from the setup players list
  const playerIndex = players.findIndex(p => p.id === playerId);
  if (playerIndex > -1) {
    players.splice(playerIndex, 1);
    
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
  
  // Auto-start any new matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
  saveStateToLocalStorage();
}

function handleRemoveSessionTeam(player1Id: string, player2Id: string) {
  if (!currentSession) return;
  
  if (!confirm('Remove this team from the session? Any active matches will be forfeited.')) {
    return;
  }
  
  currentSession = removeTeamFromSession(currentSession, player1Id, player2Id);
  
  // Also remove from the setup players list
  const player1Index = players.findIndex(p => p.id === player1Id);
  const player2Index = players.findIndex(p => p.id === player2Id);
  
  if (player1Index > -1) {
    players.splice(player1Index, 1);
  }
  if (player2Index > -1) {
    players.splice(player2Index, 1);
  }
  
  // Remove from banned pairs
  for (let i = bannedPairs.length - 1; i >= 0; i--) {
    if (bannedPairs[i][0] === player1Id || bannedPairs[i][1] === player1Id ||
        bannedPairs[i][0] === player2Id || bannedPairs[i][1] === player2Id) {
      bannedPairs.splice(i, 1);
    }
  }
  
  // Remove from locked teams
  for (let i = lockedTeams.length - 1; i >= 0; i--) {
    const team = lockedTeams[i];
    if ((team[0] === player1Id && team[1] === player2Id) ||
        (team[0] === player2Id && team[1] === player1Id)) {
      lockedTeams.splice(i, 1);
    }
  }
  
  renderPlayerList();
  updateBannedPairSelects();
  renderBannedPairs();
  renderLockedTeams();
  
  // Auto-start any new matches
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  renderSession();
  renderActivePlayers();
  saveStateToLocalStorage();
}

function handleCompleteMatch(matchId: string, team1Score: number, team2Score: number) {
  if (!currentSession) return;
  
  // Validate scores
  if (team1Score === team2Score) {
    alert('Invalid score: There must be a winner. Scores cannot be tied.');
    return;
  }
  
  if (team1Score < 0 || team2Score < 0) {
    alert('Invalid score: Scores cannot be negative.');
    return;
  }
  
  currentSession = completeMatch(currentSession, matchId, team1Score, team2Score);

  // Auto-start any new matches created by evaluation (all modes now use continuous flow)
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  // Update queue if visible
  if (!queueSection.classList.contains('hidden')) {
    renderQueue();
  }
  
  // Always update rankings if modal is open
  if (rankingsModal.classList.contains('show')) {
    renderRankings();
  }
  
  // Always update stats if modal is open
  if (statsModal.classList.contains('show')) {
    renderStats();
  }
  
  // Always update history if visible
  if (!matchHistorySection.classList.contains('hidden')) {
    renderMatchHistory();
  }
  
  renderSession();
  renderActivePlayers();
  saveStateToLocalStorage();
}

function handleForfeitMatch(matchId: string) {
  if (!currentSession) return;
  
  if (!confirm('Forfeit this match? No stats will be recorded.')) {
    return;
  }
  
  currentSession = forfeitMatch(currentSession, matchId);
  
  // Auto-start any new matches created by evaluation (all modes now use continuous flow)
  currentSession.matches.forEach(match => {
    if (match.status === 'waiting') {
      currentSession = startMatch(currentSession!, match.id);
    }
  });
  
  // Update queue if visible
  if (!queueSection.classList.contains('hidden')) {
    renderQueue();
  }
  
  renderSession();
  renderActivePlayers();
  saveStateToLocalStorage();
}

function renderSession() {
  if (!currentSession) return;
  
  // Always update match history (now always visible by default)
  renderMatchHistory();
  
  // Always update stats if modal is open
  if (statsModal.classList.contains('show')) {
    renderStats();
  }
  
  // Render courts - ALL courts in order, not just active ones
  courtsGrid.innerHTML = '';
  
  // Render each court from 1 to numCourts
  for (let courtNum = 1; courtNum <= currentSession.config.courts; courtNum++) {
    const activeMatch = currentSession.matches.find(
      m => m.courtNumber === courtNum && (m.status === 'in-progress' || m.status === 'waiting')
    );
    
    if (!activeMatch) {
      // Show empty court
      renderEmptyCourt(courtNum);
      continue;
    }
    
    const match = activeMatch;
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
  }
  
  // Render waiting players
  if (currentSession.config.mode === 'king-of-court') {
    // For King of Court, show players not currently in active matches
    const waitingPlayerIds = Array.from(currentSession.activePlayers).filter(id => {
      return !currentSession!.matches.some(match =>
        (match.status === 'in-progress' || match.status === 'waiting') &&
        (match.team1.includes(id) || match.team2.includes(id))
      );
    });
    
    if (waitingPlayerIds.length > 0) {
      waitingArea.style.display = 'block';
      waitingPlayers.innerHTML = '';

      waitingPlayerIds.forEach(playerId => {
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
  } else {
    // For other modes, use the session's waitingPlayers array
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
}

function renderEmptyCourt(courtNum: number) {
  if (!currentSession) return;
  
  const courtDiv = document.createElement('div');
  courtDiv.className = 'court empty-court';
  
  // Get history for this court
  const courtHistory = currentSession.matches.filter(
    m => m.courtNumber === courtNum && (m.status === 'completed' || m.status === 'forfeited')
  );
  
  let historyHtml = '';
  if (courtHistory.length > 0) {
    const recentMatches = courtHistory.slice(-3).reverse(); // Show last 3 matches
    historyHtml = `
      <div class="court-history">
        <div class="court-history-header">Recent Matches:</div>
        ${recentMatches.map(match => {
          const team1Names = match.team1.map(id => {
            const player = currentSession!.config.players.find(p => p.id === id);
            return player?.name.split(' ')[0] || '?'; // First name only
          }).join(' & ');
          
          const team2Names = match.team2.map(id => {
            const player = currentSession!.config.players.find(p => p.id === id);
            return player?.name.split(' ')[0] || '?';
          }).join(' & ');
          
          if (match.status === 'forfeited') {
            return `<div class="history-item">❌ ${team1Names} vs ${team2Names} (Forfeited)</div>`;
          } else if (match.score) {
            return `<div class="history-item">✓ ${team1Names} ${match.score.team1Score}-${match.score.team2Score} ${team2Names}</div>`;
          }
          return '';
        }).join('')}
        ${courtHistory.length > 3 ? `<div class="history-more">+${courtHistory.length - 3} more...</div>` : ''}
      </div>
    `;
  }
  
  courtDiv.innerHTML = `
    <div class="court-header">
      Court ${courtNum}
      <span class="match-status status-empty">Available</span>
    </div>
    <div class="empty-court-content">
      <div class="empty-message">
        ${courtHistory.length === 0 ? '🎾 Waiting for players...' : '🎾 Ready for next match'}
      </div>
      ${historyHtml}
    </div>
  `;
  
  courtsGrid.appendChild(courtDiv);
}

function renderActivePlayers() {
  if (!currentSession) return;
  
  activePlayersList.innerHTML = '';
  
  // Update controls visibility based on locked teams mode
  const isLockedTeamsMode = currentSession.config.lockedTeams && currentSession.config.lockedTeams.length > 0;
  if (isLockedTeamsMode) {
    sessionPlayerControls.style.display = 'none';
    sessionTeamControls.style.display = 'flex';
  } else {
    sessionPlayerControls.style.display = 'flex';
    sessionTeamControls.style.display = 'none';
  }
  
  // For locked teams, show teams instead of individual players
  if (isLockedTeamsMode) {
    const lockedTeams = currentSession.config.lockedTeams || [];
    if (lockedTeams.length === 0) {
      activePlayersList.innerHTML = '<p style="color: var(--text-secondary); padding: 10px;">No teams in session</p>';
      return;
    }
    
    const list = document.createElement('ol');
    list.style.paddingLeft = '0';
    list.style.marginLeft = '20px';
    list.style.color = 'var(--text-primary)';
    list.style.columns = 'auto';
    list.style.columnWidth = '300px';
    list.style.columnGap = '30px';
    list.style.listStylePosition = 'outside';
    list.style.width = '100%';
    
    // Estimate number of columns based on container width
    const containerWidth = activePlayersList.offsetWidth || 1000;
    const columnWidth = 300 + 30; // columnWidth + gap
    const numColumns = Math.max(1, Math.floor(containerWidth / columnWidth));
    const itemsPerColumn = Math.ceil(lockedTeams.length / numColumns);
    
    lockedTeams.forEach((team, idx) => {
      const player1 = currentSession!.config.players.find(p => p.id === team[0]);
      const player2 = currentSession!.config.players.find(p => p.id === team[1]);
      
      if (!player1 || !player2) return;
      
      const isActive = currentSession!.activePlayers.has(player1.id) && currentSession!.activePlayers.has(player2.id);
      const item = document.createElement('li');
      item.style.marginBottom = '8px';
      item.style.display = 'list-item';
      item.style.breakInside = 'avoid';
      item.style.paddingLeft = '10px';
      
      // Calculate which column this item is in
      const columnIndex = Math.floor(idx / itemsPerColumn);
      const bgClass = columnIndex % 2 === 0 ? 'player-list-item-bg-0' : 'player-list-item-bg-1';
      item.className = bgClass;
      
      if (!isActive) {
        item.style.opacity = '0.5';
      }
      
      const content = document.createElement('div');
      content.style.display = 'flex';
      content.style.justifyContent = 'space-between';
      content.style.alignItems = 'center';
      content.style.gap = '10px';
      
      const nameSpan = document.createElement('span');
      nameSpan.textContent = `${player1.name} & ${player2.name}${isActive ? '' : ' (Inactive)'}`;
      nameSpan.style.flex = '1';
      nameSpan.style.color = 'var(--text-primary)';
      
      const actionBtn = document.createElement('button');
      if (isActive) {
        actionBtn.textContent = '×';
        actionBtn.onclick = () => (window as any).removeSessionTeam(player1.id, player2.id);
        actionBtn.style.cssText = 'margin-left: 10px; color: #dc3545; background: transparent; border: 1px solid #dc3545; padding: 2px 8px; border-radius: 4px; cursor: pointer; flex-shrink: 0;';
      } else {
        actionBtn.textContent = '↻';
        actionBtn.onclick = () => (window as any).reactivateTeam(player1.id, player2.id);
        actionBtn.style.cssText = 'margin-left: 10px; color: #28a745; background: transparent; border: 1px solid #28a745; padding: 2px 8px; border-radius: 4px; cursor: pointer; flex-shrink: 0;';
      }
      
      content.appendChild(nameSpan);
      content.appendChild(actionBtn);
      item.appendChild(content);
      list.appendChild(item);
    });
    
    activePlayersList.appendChild(list);
  } else {
    // Regular players display
    if (currentSession.config.players.length === 0) {
      activePlayersList.innerHTML = '<p style="color: var(--text-secondary); padding: 10px;">No players in session</p>';
    } else {
      const list = document.createElement('ol');
      list.style.paddingLeft = '0';
      list.style.marginLeft = '20px';
      list.style.color = 'var(--text-primary)';
      list.style.columns = 'auto';
      list.style.columnWidth = '250px';
      list.style.columnGap = '30px';
      list.style.listStylePosition = 'outside';
      list.style.width = '100%';
      
      // Estimate number of columns based on container width
      const containerWidth = activePlayersList.offsetWidth || 1000;
      const columnWidth = 250 + 30; // columnWidth + gap
      const numColumns = Math.max(1, Math.floor(containerWidth / columnWidth));
      const itemsPerColumn = Math.ceil(currentSession.config.players.length / numColumns);
      
      currentSession.config.players.forEach((player, idx) => {
        const isActive = currentSession!.activePlayers.has(player.id);
        const item = document.createElement('li');
        item.style.marginBottom = '8px';
        item.style.display = 'list-item';
        item.style.breakInside = 'avoid';
        item.style.paddingLeft = '10px';
        
        // Calculate which column this item is in
        const columnIndex = Math.floor(idx / itemsPerColumn);
        const bgClass = columnIndex % 2 === 0 ? 'player-list-item-bg-0' : 'player-list-item-bg-1';
        item.className = bgClass;
        
        if (!isActive) {
          item.style.opacity = '0.5';
        }
        
        const content = document.createElement('div');
        content.style.display = 'flex';
        content.style.justifyContent = 'space-between';
        content.style.alignItems = 'center';
        content.style.gap = '10px';
        
        const nameSpan = document.createElement('span');
        nameSpan.textContent = player.name + (isActive ? '' : ' (Inactive)');
        nameSpan.style.flex = '1';
        nameSpan.style.color = 'var(--text-primary)';
        
        const actionBtn = document.createElement('button');
        if (isActive) {
          actionBtn.textContent = '×';
          actionBtn.onclick = () => (window as any).removeSessionPlayer(player.id);
          actionBtn.style.cssText = 'margin-left: 10px; color: #dc3545; background: transparent; border: 1px solid #dc3545; padding: 2px 8px; border-radius: 4px; cursor: pointer; flex-shrink: 0;';
        } else {
          actionBtn.textContent = '↻';
          actionBtn.onclick = () => (window as any).reactivatePlayer(player.id);
          actionBtn.style.cssText = 'margin-left: 10px; color: #28a745; background: transparent; border: 1px solid #28a745; padding: 2px 8px; border-radius: 4px; cursor: pointer; flex-shrink: 0;';
        }
        
        content.appendChild(nameSpan);
        content.appendChild(actionBtn);
        item.appendChild(content);
        list.appendChild(item);
      });
      
      activePlayersList.appendChild(list);
    }
  }
}

function openRankingsModal() {
  if (!currentSession) return;
  renderRankings();
  rankingsModal.classList.add('show');
  document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

function closeRankingsModal() {
  rankingsModal.classList.remove('show');
  document.body.style.overflow = ''; // Restore scrolling
}

function renderRankings() {
  if (!currentSession) return;
  
  rankingsList.innerHTML = '';
  
  // For locked teams, show team rankings instead of individual player rankings
  if (currentSession.config.lockedTeams && currentSession.config.lockedTeams.length > 0) {
    const rankings = calculateTeamRankings(currentSession.config.lockedTeams, currentSession.playerStats);
    
    if (rankings.length === 0) {
      rankingsList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">No rankings yet. Complete some games to see rankings!</p>';
      return;
    }
    
    rankings.forEach(ranking => {
      const player1 = currentSession!.config.players.find(p => p.id === ranking.team[0]);
      const player2 = currentSession!.config.players.find(p => p.id === ranking.team[1]);
      
      if (!player1 || !player2) return;
      
      const item = document.createElement('div');
      item.className = 'ranking-item';
      
      // Determine rank badge class
      let rankClass = '';
      if (ranking.rank === 1) rankClass = 'rank-1';
      else if (ranking.rank === 2) rankClass = 'rank-2';
      else if (ranking.rank === 3) rankClass = 'rank-3';
      
      // Determine color class for point differential
      let diffClass = '';
      if (ranking.avgPointDifferential > 0) diffClass = 'positive';
      else if (ranking.avgPointDifferential < 0) diffClass = 'negative';
      
      const diffSign = ranking.avgPointDifferential >= 0 ? '+' : '';
      
      item.innerHTML = `
        <div class="rank-badge ${rankClass}">
          ${ranking.rank === 1 ? '🥇' : ranking.rank === 2 ? '🥈' : ranking.rank === 3 ? '🥉' : ranking.rank}
        </div>
        <div class="ranking-info">
          <div class="ranking-name">${player1.name} & ${player2.name}</div>
          <div class="ranking-stats">
            <div class="ranking-stat">
              <div class="ranking-stat-label">Wins</div>
              <div class="ranking-stat-value">${ranking.wins}</div>
            </div>
            <div class="ranking-stat">
              <div class="ranking-stat-label">Losses</div>
              <div class="ranking-stat-value">${ranking.losses}</div>
            </div>
            <div class="ranking-stat">
              <div class="ranking-stat-label">Avg Pt Diff</div>
              <div class="ranking-stat-value ${diffClass}">${diffSign}${ranking.avgPointDifferential.toFixed(1)}</div>
            </div>
          </div>
        </div>
      `;
      
      rankingsList.appendChild(item);
    });
  } else {
    // Individual player rankings
    const playerIds = currentSession.config.players.map(p => p.id);
    
    // For King of Court, use ELO-style rating; otherwise use win-based ranking
    const isKingOfCourt = currentSession.config.mode === 'king-of-court';
    
    if (isKingOfCourt) {
      // Calculate KOC ratings and sort by rating
      const kocRankings = playerIds
        .map(playerId => {
          const stats = currentSession!.playerStats.get(playerId);
          if (!stats) return null;
          
          const rating = calculatePlayerRating(stats);
          const avgPointDifferential = stats.gamesPlayed > 0
            ? (stats.totalPointsFor - stats.totalPointsAgainst) / stats.gamesPlayed
            : 0;
          
          return {
            playerId,
            rating,
            wins: stats.wins,
            losses: stats.losses,
            avgPointDifferential,
            gamesPlayed: stats.gamesPlayed,
          };
        })
        .filter((data): data is NonNullable<typeof data> => data !== null)
        .sort((a, b) => b.rating - a.rating); // Sort by rating descending
      
      if (kocRankings.length === 0) {
        rankingsList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">No rankings yet. Complete some games to see rankings!</p>';
        return;
      }
      
      kocRankings.forEach((ranking, index) => {
        const player = currentSession!.config.players.find(p => p.id === ranking.playerId);
        if (!player) return;
        
        const rank = index + 1;
        const item = document.createElement('div');
        item.className = 'ranking-item';
        
        // Determine rank badge class
        let rankClass = '';
        if (rank === 1) rankClass = 'rank-1';
        else if (rank === 2) rankClass = 'rank-2';
        else if (rank === 3) rankClass = 'rank-3';
        
        // Determine color class for point differential
        let diffClass = '';
        if (ranking.avgPointDifferential > 0) diffClass = 'positive';
        else if (ranking.avgPointDifferential < 0) diffClass = 'negative';
        
        const diffSign = ranking.avgPointDifferential >= 0 ? '+' : '';
        
        // Provisional badge for new players (< 3 games)
        const provisionalBadge = ranking.gamesPlayed < 3 ? '<span style="font-size: 10px; color: var(--text-secondary); margin-left: 5px;">(Provisional)</span>' : '';
        
        item.innerHTML = `
          <div class="rank-badge ${rankClass}">
            ${rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : rank}
          </div>
          <div class="ranking-info">
            <div class="ranking-name">${player.name}${provisionalBadge}</div>
            <div class="ranking-stats">
              <div class="ranking-stat">
                <div class="ranking-stat-label">Rating</div>
                <div class="ranking-stat-value">${Math.round(ranking.rating)}</div>
              </div>
              <div class="ranking-stat">
                <div class="ranking-stat-label">Wins</div>
                <div class="ranking-stat-value">${ranking.wins}</div>
              </div>
              <div class="ranking-stat">
                <div class="ranking-stat-label">Losses</div>
                <div class="ranking-stat-value">${ranking.losses}</div>
              </div>
              <div class="ranking-stat">
                <div class="ranking-stat-label">Avg Pt Diff</div>
                <div class="ranking-stat-value ${diffClass}">${diffSign}${ranking.avgPointDifferential.toFixed(1)}</div>
              </div>
            </div>
          </div>
        `;
        
        rankingsList.appendChild(item);
      });
    } else {
      // Standard win-based rankings
      const rankings = calculatePlayerRankings(playerIds, currentSession.playerStats);
      
      if (rankings.length === 0) {
        rankingsList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">No rankings yet. Complete some games to see rankings!</p>';
        return;
      }
      
      rankings.forEach(ranking => {
        const player = currentSession!.config.players.find(p => p.id === ranking.playerId);
        if (!player) return;
        
        const item = document.createElement('div');
        item.className = 'ranking-item';
        
        // Determine rank badge class
        let rankClass = '';
        if (ranking.rank === 1) rankClass = 'rank-1';
        else if (ranking.rank === 2) rankClass = 'rank-2';
        else if (ranking.rank === 3) rankClass = 'rank-3';
        
        // Determine color class for point differential
        let diffClass = '';
        if (ranking.avgPointDifferential > 0) diffClass = 'positive';
        else if (ranking.avgPointDifferential < 0) diffClass = 'negative';
        
        const diffSign = ranking.avgPointDifferential >= 0 ? '+' : '';
        
        item.innerHTML = `
          <div class="rank-badge ${rankClass}">
            ${ranking.rank === 1 ? '🥇' : ranking.rank === 2 ? '🥈' : ranking.rank === 3 ? '🥉' : ranking.rank}
          </div>
          <div class="ranking-info">
            <div class="ranking-name">${player.name}</div>
            <div class="ranking-stats">
              <div class="ranking-stat">
                <div class="ranking-stat-label">Wins</div>
                <div class="ranking-stat-value">${ranking.wins}</div>
              </div>
              <div class="ranking-stat">
                <div class="ranking-stat-label">Losses</div>
                <div class="ranking-stat-value">${ranking.losses}</div>
              </div>
              <div class="ranking-stat">
                <div class="ranking-stat-label">Avg Pt Diff</div>
                <div class="ranking-stat-value ${diffClass}">${diffSign}${ranking.avgPointDifferential.toFixed(1)}</div>
              </div>
            </div>
          </div>
        `;
        
        rankingsList.appendChild(item);
      });
    }
  }
}

function openStatsModal() {
  if (!currentSession) return;
  renderStats();
  statsModal.classList.add('show');
  document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

function closeStatsModal() {
  statsModal.classList.remove('show');
  document.body.style.overflow = ''; // Restore scrolling
}

function toggleHistory() {
  if (matchHistorySection.classList.contains('hidden')) {
    matchHistorySection.classList.remove('hidden');
    showHistoryBtn.textContent = 'Hide History';
    renderMatchHistory();
  } else {
    matchHistorySection.classList.add('hidden');
    showHistoryBtn.textContent = 'Show History';
  }
}

function handleExportSession() {
  if (!currentSession) return;
  
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '-');
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }).replace(/:/g, '-');
  
  let exportText = '═══════════════════════════════════════════════════════\n';
  exportText += '   BETTER PICKLEBALL SESSIONS - SESSION EXPORT\n';
  exportText += '═══════════════════════════════════════════════════════\n\n';
  exportText += `Date: ${now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}\n`;
  exportText += `Time: ${now.toLocaleTimeString('en-US')}\n\n`;
  
  // Session Configuration
  exportText += '═══════════════════════════════════════════════════════\n';
  exportText += '   SESSION CONFIGURATION\n';
  exportText += '═══════════════════════════════════════════════════════\n\n';
  exportText += `Game Mode: ${currentSession.config.mode === 'king-of-court' ? 'King of the Court' : 'Round Robin'}\n`;
  exportText += `Session Type: ${currentSession.config.sessionType === 'doubles' ? 'Doubles' : 'Singles'}\n`;
  exportText += `Number of Courts: ${currentSession.config.courts}\n`;
  exportText += `Total Players: ${currentSession.config.players.length}\n`;
  exportText += `Active Players: ${currentSession.activePlayers.size}\n\n`;
  
  // Current Matches
  const activeMatches = currentSession.matches.filter(m => m.status === 'in-progress' || m.status === 'waiting');
  if (activeMatches.length > 0) {
    exportText += '═══════════════════════════════════════════════════════\n';
    exportText += '   CURRENT MATCHES\n';
    exportText += '═══════════════════════════════════════════════════════\n\n';
    
    activeMatches.forEach(match => {
      const team1Names = match.team1.map(id => {
        const player = currentSession!.config.players.find(p => p.id === id);
        return player ? player.name : 'Unknown';
      });
      const team2Names = match.team2.map(id => {
        const player = currentSession!.config.players.find(p => p.id === id);
        return player ? player.name : 'Unknown';
      });
      
      exportText += `Court ${match.courtNumber} [${match.status.toUpperCase()}]:\n`;
      exportText += `  ${team1Names.join(' & ')}\n`;
      exportText += `    vs\n`;
      exportText += `  ${team2Names.join(' & ')}\n\n`;
    });
  }
  
  // Waiting Players
  if (currentSession.config.mode === 'king-of-court') {
    const waitingPlayerIds = Array.from(currentSession.activePlayers).filter(id => {
      return !currentSession!.matches.some(match =>
        (match.status === 'in-progress' || match.status === 'waiting') &&
        (match.team1.includes(id) || match.team2.includes(id))
      );
    });
    
    if (waitingPlayerIds.length > 0) {
      exportText += '═══════════════════════════════════════════════════════\n';
      exportText += '   WAITING PLAYERS\n';
      exportText += '═══════════════════════════════════════════════════════\n\n';
      
      waitingPlayerIds.forEach((id, idx) => {
        const player = currentSession!.config.players.find(p => p.id === id);
        if (player) {
          exportText += `  ${idx + 1}. ${player.name}\n`;
        }
      });
      exportText += '\n';
    }
  } else if (currentSession.waitingPlayers.length > 0) {
    exportText += '═══════════════════════════════════════════════════════\n';
    exportText += '   WAITING PLAYERS\n';
    exportText += '═══════════════════════════════════════════════════════\n\n';
    
    currentSession.waitingPlayers.forEach((id, idx) => {
      const player = currentSession!.config.players.find(p => p.id === id);
      if (player) {
        exportText += `  ${idx + 1}. ${player.name}\n`;
      }
    });
    exportText += '\n';
  }
  
  // Match History
  const completedMatches = currentSession.matches.filter(m => m.status === 'completed' || m.status === 'forfeited');
  if (completedMatches.length > 0) {
    exportText += '═══════════════════════════════════════════════════════\n';
    exportText += '   MATCH HISTORY\n';
    exportText += '═══════════════════════════════════════════════════════\n\n';
    
    completedMatches.forEach((match, idx) => {
      const team1Names = match.team1.map(id => {
        const player = currentSession!.config.players.find(p => p.id === id);
        return player ? player.name : 'Unknown';
      });
      const team2Names = match.team2.map(id => {
        const player = currentSession!.config.players.find(p => p.id === id);
        return player ? player.name : 'Unknown';
      });
      
      exportText += `Match ${idx + 1} - Court ${match.courtNumber}`;
      if (match.status === 'forfeited') {
        exportText += ' [FORFEITED]:\n';
        exportText += `  ${team1Names.join(' & ')} vs ${team2Names.join(' & ')}\n\n`;
      } else if (match.score) {
        const winner = match.score.team1Score > match.score.team2Score ? team1Names : team2Names;
        exportText += `:\n`;
        exportText += `  ${team1Names.join(' & ')} (${match.score.team1Score})\n`;
        exportText += `    vs\n`;
        exportText += `  ${team2Names.join(' & ')} (${match.score.team2Score})\n`;
        exportText += `  Winner: ${winner.join(' & ')}\n\n`;
      }
    });
  }
  
  // Player Statistics Summary
  exportText += '═══════════════════════════════════════════════════════\n';
  exportText += '   PLAYER STATISTICS SUMMARY\n';
  exportText += '═══════════════════════════════════════════════════════\n\n';
  
  const playerIds = currentSession.config.players.map(p => p.id);
  const rankings = calculatePlayerRankings(playerIds, currentSession.playerStats);
  
  rankings.forEach(ranking => {
    const player = currentSession!.config.players.find(p => p.id === ranking.playerId);
    if (player) {
      const stats = currentSession!.playerStats.get(ranking.playerId);
      const winRate = stats && stats.gamesPlayed > 0 ? ((stats.wins / stats.gamesPlayed) * 100).toFixed(1) : '0.0';
      
      exportText += `${ranking.rank}. ${player.name}\n`;
      exportText += `   Wins: ${ranking.wins} | Losses: ${ranking.losses} | Win Rate: ${winRate}%\n`;
      exportText += `   Avg Point Diff: ${ranking.avgPointDifferential >= 0 ? '+' : ''}${ranking.avgPointDifferential.toFixed(1)}\n\n`;
    }
  });
  
  exportText += '═══════════════════════════════════════════════════════\n';
  exportText += '   END OF SESSION EXPORT\n';
  exportText += '═══════════════════════════════════════════════════════\n';
  
  // Create and download file
  const blob = new Blob([exportText], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pickleball-session-${dateStr}-${timeStr}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  alert('✅ Session exported successfully!');
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
  
  // Sort by completion time - most recent first (reverse chronological)
  const sortedMatches = [...completedMatches].sort((a, b) => {
    const timeA = a.endTime || 0;
    const timeB = b.endTime || 0;
    return timeB - timeA; // Most recent first
  });
  
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

function handleEditSession() {
  if (!currentSession) return;

  if (!confirm('This will end the current session but keep all players. You can then reconfigure and start a new session. Continue?')) {
    return;
  }

  // Keep players but clear session
  currentSession = null;
  
  // Unlock configuration inputs
  unlockConfigurationInputs();

  // Close modals if open
  closeStatsModal();
  closeRankingsModal();

  // Switch to setup page
  showPage('setup');

  // Reset locked teams UI state if needed
  if (lockedTeamsCheckbox.checked) {
    renderLockedTeams();
  } else {
    // Players are already in the players array, just re-render
    renderPlayerList();
  }
  updateBannedPairSelects();
  renderBannedPairs();

  alert('✅ Session ended. Players saved. You can now change settings and start a new session.');
  saveStateToLocalStorage();
}

function handleClearSessionData() {
  if (!confirm('This will clear all saved session data from your browser. Your current session will remain active. Continue?')) {
    return;
  }
  
  clearLocalStorageState();
  alert('✅ Session data cleared from browser storage.');
}

function handleEndSessionAndClearData() {
  if (!confirm('Are you sure you want to end the session and clear all data? All players and configuration will be lost.')) {
    return;
  }
  
  currentSession = null;
  players = [];
  bannedPairs = [];
  lockedTeams = [];
  
  // Unlock configuration inputs
  unlockConfigurationInputs();
  
  // Close modals if open
  closeStatsModal();
  closeRankingsModal();
  
  // Switch to setup page
  showPage('setup');
  
  renderPlayerList();
  updateBannedPairSelects();
  renderBannedPairs();
  renderLockedTeams();
  clearLocalStorageState();
  
  alert('✅ Session ended and all data cleared.');
}

function handleEndSessionAndKeepPlayers() {
  if (!confirm('Are you sure you want to end the session? Players will be kept for the next session.')) {
    return;
  }
  
  // Sync players array with all players from the session (including those added during session)
  if (currentSession) {
    players = [...currentSession.config.players];
  }
  
  currentSession = null;
  
  // Unlock configuration inputs
  unlockConfigurationInputs();
  
  // Close modals if open
  closeStatsModal();
  closeRankingsModal();
  
  // Switch to setup page
  showPage('setup');
  
  // Players, banned pairs, and locked teams are kept
  renderPlayerList();
  updateBannedPairSelects();
  renderBannedPairs();
  renderLockedTeams();
  saveStateToLocalStorage();
  
  alert('✅ Session ended. Players saved for next session.');
}

// Configuration locking functions
function lockConfigurationInputs() {
  // Disable all setup configuration inputs
  gameModeSelect.disabled = true;
  sessionTypeSelect.disabled = true;
  numCourtsInput.disabled = true;
  setupMaxQueueSizeInput.disabled = true;
  lockedTeamsCheckbox.disabled = true;
  
  // Disable player/team input
  playerNameInput.disabled = true;
  addPlayerBtn.disabled = true;
  teamPlayer1NameInput.disabled = true;
  teamPlayer2NameInput.disabled = true;
  addLockedTeamBtn.disabled = true;
  
  // Disable banned pairs controls
  bannedPlayer1Select.disabled = true;
  bannedPlayer2Select.disabled = true;
  addBannedPairBtn.disabled = true;
  
  // Re-render player/team lists to disable remove buttons
  if (lockedTeamsCheckbox.checked) {
    renderLockedTeams();
  } else {
    renderPlayerList();
  }
  renderBannedPairs();
  
  // Hide start session button, show end session buttons
  startSessionBtn.style.display = 'none';
  setupEndSessionClearBtn.style.display = 'inline-block';
  setupEndSessionKeepBtn.style.display = 'inline-block';
}

function unlockConfigurationInputs() {
  // Enable all setup configuration inputs
  gameModeSelect.disabled = false;
  sessionTypeSelect.disabled = false;
  numCourtsInput.disabled = false;
  setupMaxQueueSizeInput.disabled = false;
  lockedTeamsCheckbox.disabled = false;
  
  // Enable player/team input
  playerNameInput.disabled = false;
  addPlayerBtn.disabled = false;
  teamPlayer1NameInput.disabled = false;
  teamPlayer2NameInput.disabled = false;
  addLockedTeamBtn.disabled = false;
  
  // Enable banned pairs controls
  bannedPlayer1Select.disabled = false;
  bannedPlayer2Select.disabled = false;
  addBannedPairBtn.disabled = false;
  
  // Re-render to enable removal buttons
  if (lockedTeamsCheckbox.checked) {
    renderLockedTeams();
  } else {
    renderPlayerList();
  }
  renderBannedPairs();
  
  // Show start session button, hide end session buttons
  startSessionBtn.style.display = 'inline-block';
  setupEndSessionClearBtn.style.display = 'none';
  setupEndSessionKeepBtn.style.display = 'none';
  
  // Enable start session button if requirements met
  if (lockedTeamsCheckbox.checked) {
    startSessionBtn.disabled = lockedTeams.length < 2;
  } else {
    startSessionBtn.disabled = players.length < 2;
  }
}

// Expose functions to window for onclick handlers
(window as any).removePlayer = handleRemovePlayer;
(window as any).removeBannedPair = handleRemoveBannedPair;
(window as any).removeLockedTeam = handleRemoveLockedTeam;
(window as any).removeSessionPlayer = handleRemoveSessionPlayer;
(window as any).removeSessionTeam = handleRemoveSessionTeam;
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
  saveStateToLocalStorage();
};
(window as any).reactivateTeam = (player1Id: string, player2Id: string) => {
  if (!currentSession) return;
  const newActivePlayers = new Set(currentSession.activePlayers);
  newActivePlayers.add(player1Id);
  newActivePlayers.add(player2Id);
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
  saveStateToLocalStorage();
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
  
  // Validate scores
  if (score1 === score2) {
    alert('Invalid score: There must be a winner. Scores cannot be tied.');
    return;
  }
  
  if (score1 < 0 || score2 < 0) {
    alert('Invalid score: Scores cannot be negative.');
    return;
  }
  
  currentSession = completeMatch(currentSession, matchId, score1, score2);
  
  // Always update rankings if modal is open
  if (rankingsModal.classList.contains('show')) {
    renderRankings();
  }
  
  // Always update stats if modal is open
  if (statsModal.classList.contains('show')) {
    renderStats();
  }
  
  // Always update history if visible
  if (!matchHistorySection.classList.contains('hidden')) {
    renderMatchHistory();
  }
  
  saveStateToLocalStorage();
  alert('Score updated successfully!');
};

function toggleQueue() {
  if (queueSection.classList.contains('hidden')) {
    queueSection.classList.remove('hidden');
    showQueueBtn.textContent = 'Hide Queue';
    queuePage = 0;
    renderQueue();
  } else {
    queueSection.classList.add('hidden');
    showQueueBtn.textContent = 'Show Queue';
  }
}

function handleApplyQueuePagination() {
  const matchesValue = parseInt(matchesPerPageInput.value);
  const maxQueueValue = parseInt(maxQueueSizeInput.value);
  
  let updated = false;
  
  // Update matches per page
  if (matchesValue && matchesValue >= 5 && matchesValue <= 50) {
    matchesPerPage = matchesValue;
    queuePage = 0;
    updated = true;
  } else if (matchesValue) {
    alert('Matches per page must be between 5 and 50');
    matchesPerPageInput.value = matchesPerPage.toString();
  }
  
  // Update max queue size
  if (maxQueueValue && maxQueueValue >= 10 && maxQueueValue <= 1000) {
    if (currentSession) {
      currentSession = updateMaxQueueSize(currentSession, maxQueueValue);
      updated = true;
    }
  } else if (maxQueueValue) {
    alert('Max queue size must be between 10 and 1000');
    maxQueueSizeInput.value = currentSession?.maxQueueSize.toString() || '100';
  }
  
  if (updated) {
    renderQueue();
    saveStateToLocalStorage();
  }
}

function renderQueue() {
  if (!currentSession) return;
  
  // For round-robin, show the match queue
  if (currentSession.config.mode === 'round-robin') {
    // Calculate how many matches we need to display on this page
    // We need to account for already playing matches and show from the actual queue
    const displayQueue = [...currentSession.matchQueue];
    
    const startIdx = queuePage * matchesPerPage;
    const endIdx = startIdx + matchesPerPage;
    const pageMatches = displayQueue.slice(startIdx, endIdx);
    
    queuePageInfo.textContent = `Page ${queuePage + 1}`;
    
    queuePrevBtn.disabled = queuePage === 0;
    queueNextBtn.disabled = endIdx >= displayQueue.length;
    
    if (pageMatches.length === 0) {
      queueList.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary);">No queued matches</p>';
      return;
    }
    
    queueList.innerHTML = pageMatches.map((match, idx) => {
      const matchNumber = startIdx + idx + 1;
      const team1Players = match.team1.map(id => {
        const player = currentSession!.config.players.find(p => p.id === id);
        return player ? player.name : 'Unknown';
      });
      const team2Players = match.team2.map(id => {
        const player = currentSession!.config.players.find(p => p.id === id);
        return player ? player.name : 'Unknown';
      });
      
      return `
        <div class="queue-match">
          <div class="queue-match-number">#${matchNumber}</div>
          <div class="queue-teams">
            <div class="queue-team">
              ${team1Players.map(name => `<div class="queue-player">🎾 ${name}</div>`).join('')}
            </div>
            <div class="vs-text">VS</div>
            <div class="queue-team">
              ${team2Players.map(name => `<div class="queue-player">🎾 ${name}</div>`).join('')}
            </div>
          </div>
        </div>
      `;
    }).join('');
  } else if (currentSession.config.mode === 'king-of-court') {
    // For King of Court, the queue section doesn't show a traditional queue
    // Waiting players are shown in the main waiting area instead
    queueList.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary);">King of the Court mode uses dynamic matchmaking.<br>Waiting players are shown in the "Waiting Players" section above.</p>';
    queuePageInfo.textContent = '';
    queuePrevBtn.disabled = true;
    queueNextBtn.disabled = true;
  } else {
    queueList.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary);">Queue display not available for this mode</p>';
    queuePageInfo.textContent = '';
    queuePrevBtn.disabled = true;
    queueNextBtn.disabled = true;
  }
}

// Navigation
const navSetup = document.getElementById('nav-setup') as HTMLButtonElement;
const navSession = document.getElementById('nav-session') as HTMLButtonElement;
const navModes = document.getElementById('nav-modes') as HTMLButtonElement;
const navAbout = document.getElementById('nav-about') as HTMLButtonElement;
const modesPage = document.getElementById('modes-page') as HTMLElement;
const aboutPage = document.getElementById('about-page') as HTMLElement;
const aboutGotoSetup = document.getElementById('about-goto-setup') as HTMLButtonElement;

function showPage(page: 'setup' | 'session' | 'modes' | 'about') {
  // Hide all pages
  setupSection.classList.add('hidden');
  controlSection.classList.add('hidden');
  courtsSection.classList.add('hidden');
  modesPage.classList.add('hidden');
  aboutPage.classList.add('hidden');
  
  // Track whether queue/history were visible before
  const queueWasVisible = !queueSection.classList.contains('hidden');
  const historyWasVisible = !matchHistorySection.classList.contains('hidden');
  
  queueSection.classList.add('hidden');
  matchHistorySection.classList.add('hidden');
  
  // Remove active from all nav buttons
  [navSetup, navSession, navModes, navAbout].forEach(btn => btn.classList.remove('active'));
  
  // Show selected page
  switch (page) {
    case 'setup':
      setupSection.classList.remove('hidden');
      navSetup.classList.add('active');
      break;
    case 'session':
      if (currentSession) {
        controlSection.classList.remove('hidden');
        courtsSection.classList.remove('hidden');
        
        // Restore queue/history visibility state
        if (queueWasVisible) {
          queueSection.classList.remove('hidden');
          showQueueBtn.textContent = 'Hide Queue';
        } else {
          showQueueBtn.textContent = 'Show Queue';
        }
        
        if (historyWasVisible) {
          matchHistorySection.classList.remove('hidden');
          showHistoryBtn.textContent = 'Hide History';
        } else {
          showHistoryBtn.textContent = 'Show History';
        }
      } else {
        // No active session, show setup
        setupSection.classList.remove('hidden');
        navSetup.classList.add('active');
        return;
      }
      navSession.classList.add('active');
      break;
    case 'modes':
      modesPage.classList.remove('hidden');
      navModes.classList.add('active');
      break;
    case 'about':
      aboutPage.classList.remove('hidden');
      navAbout.classList.add('active');
      break;
  }
}

navSetup.addEventListener('click', () => showPage('setup'));
navSession.addEventListener('click', () => showPage('session'));
navModes.addEventListener('click', () => showPage('modes'));
navAbout.addEventListener('click', () => showPage('about'));
aboutGotoSetup.addEventListener('click', () => showPage('setup'));

// Initialize
renderPlayerList();
updateBannedPairSelects();
showPage('setup'); // Start on setup page
