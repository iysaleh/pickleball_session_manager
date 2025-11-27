import asyncio
from datetime import datetime
from pyscript import document, window
from pyodide.ffi import create_proxy
import js
import sys
import os
import traceback

# --- DIAGNOSTICS & SETUP ---
def show_error(msg):
    err_el = document.querySelector("#error-display")
    if err_el:
        err_el.innerText = msg
        err_el.style.display = "block"
    print(msg)

print("--- BOOT DIAGNOSTICS ---")
print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

# Ensure CWD is in path
cwd = os.getcwd()
if cwd not in sys.path:
    print(f"Adding {cwd} to sys.path")
    sys.path.append(cwd)

# Check File System
try:
    files = os.listdir('.')
    print(f"Root Files: {files}")
    if 'python' in files:
        py_files = os.listdir('python')
        print(f"python/ Files: {py_files}")
        if '__init__.py' not in py_files:
            print("CRITICAL: __init__.py missing in python/")
    else:
        print("CRITICAL: 'python' directory NOT FOUND in CWD")
except Exception as e:
    print(f"FS Check Error: {e}")

# Check Imports
try:
    import python
    print(f"Successfully imported 'python' package: {python}")
    print(f"python package file: {python.__file__}")
except ImportError as e:
    print(f"Import 'python' FAILED: {e}")
    if 'python' in sys.modules:
        print(f"'python' is already in sys.modules: {sys.modules['python']}")

print("--- END DIAGNOSTICS ---")


# --- APPLICATION CODE ---

try:
    # Import backend modules
    try:
        from python.types import Player, SessionConfig, GameMode, SessionType
        from python.session import (
            create_session, add_player_to_session, remove_player_from_session,
            complete_match, forfeit_match, get_player_name, get_active_matches,
            get_completed_matches
        )
        from python.queue_manager import (
            populate_empty_courts, get_match_for_court, get_waiting_players, 
            get_queued_matches_for_display, get_session_summary
        )
        from python.utils import calculate_match_duration, format_duration
    except ImportError as ie:
        show_error(f"Module Import Failed:\n{ie}\n\nSee console for diagnostics.")
        raise ie

    # Global State
    current_session = None
    setup_players = []

    # --- DOM Elements ---
    def get_el(id):
        return document.querySelector(f"#{id}")

    # --- Event Handlers ---

    def add_player_handler(event):
        """Add player in setup screen"""
        input_el = get_el("new-player-input")
        name = input_el.value.strip()
        if not name:
            return
        
        # Check duplicates
        if any(p.name == name for p in setup_players):
            window.alert("Player already exists!")
            return

        player = Player(id=f"player_{len(setup_players)}_{datetime.now().timestamp()}", name=name)
        setup_players.append(player)
        
        # Update UI
        update_player_list_ui()
        input_el.value = ""
        input_el.focus()

    def add_test_players_handler(event):
        """Add dummy players for testing"""
        names = [
            "Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince",
            "Eve Wilson", "Frank Castle", "Grace Lee", "Henry Davis",
            "Iris West", "Jack Ryan", "Kate Beckinsale", "Leo Martinez",
            "Maya Patel", "Noah Taylor", "Olivia Stone", "Peter Parker",
            "Quinn Adams", "Rachel Green"
        ]
        for name in names:
            if not any(p.name == name for p in setup_players):
                player = Player(id=f"player_{len(setup_players)}_{datetime.now().timestamp()}", name=name)
                setup_players.append(player)
        update_player_list_ui()

    def update_player_list_ui():
        """Render the player list in setup"""
        list_el = get_el("player-list")
        list_el.innerHTML = ""
        
        for i, player in enumerate(setup_players):
            li = document.createElement("li")
            li.className = "list-group-item d-flex justify-content-between align-items-center"
            li.innerHTML = f"{player.name} <button class='btn btn-sm btn-danger remove-btn' data-index='{i}'>&times;</button>"
            list_el.appendChild(li)
            
            btn = li.querySelector(".remove-btn")
            def remove_cb(evt, idx=i):
                setup_players.pop(idx)
                update_player_list_ui()
            
            btn.onclick = remove_cb

        get_el("player-count").innerText = str(len(setup_players))

    async def start_session_handler(event):
        """Start the session"""
        global current_session
        
        if len(setup_players) < 2:
            window.alert("Need at least 2 players!")
            return

        mode_val = get_el("mode-select").value
        type_val = get_el("type-select").value
        courts_val = int(get_el("courts-input").value)
        
        config = SessionConfig(
            mode=mode_val,
            session_type=type_val,
            players=setup_players,
            courts=courts_val,
            banned_pairs=[],
            locked_teams=[],
            randomize_player_order=False
        )
        
        try:
            current_session = create_session(config)
            
            # Switch View
            get_el("setup-view").style.display = "none"
            get_el("session-view").style.display = "block"
            
            # Start Refresh Loop
            asyncio.create_task(refresh_loop())
            
        except Exception as e:
            window.alert(f"Error starting session: {str(e)}")
            print(e)

    # --- Session Management ---

    async def refresh_loop():
        """Main loop to refresh UI every second"""
        while True:
            if current_session:
                try:
                    populate_empty_courts(current_session)
                    refresh_display()
                except Exception as e:
                    print(f"Error in refresh loop: {e}")
                    traceback.print_exc()
            await asyncio.sleep(1)

    def refresh_display():
        """Refresh all UI components"""
        if not current_session:
            return
            
        update_session_header()
        render_courts()
        render_waitlist()
        render_queue()
        render_history()

    def update_session_header():
        summary = get_session_summary(current_session)
        title = f"{current_session.config.mode.title()} - {current_session.config.session_type.title()}"
        subtitle = f"Courts: {summary['active_matches']}/{summary['total_courts']} | Queued: {summary['queued_matches']} | Completed: {summary['completed_matches']}"
        
        get_el("session-title").innerText = title
        get_el("session-subtitle").innerText = subtitle

    last_court_state = {}

    def render_courts():
        container = get_el("courts-container")
        
        # Ensure grid structure exists
        if container.children.length != current_session.config.courts:
            container.innerHTML = ""
            for _ in range(current_session.config.courts):
                col = document.createElement("div")
                # Force Nx2 grid (2 columns on md/lg)
                col.className = "col-12 col-md-6" 
                container.appendChild(col)

        court_cols = container.children
        
        for i in range(current_session.config.courts):
            court_num = i + 1
            col = court_cols[i]
            match = get_match_for_court(current_session, court_num)
            
            match_id = match.id if match else None
            
            should_render = False
            if court_num not in last_court_state:
                should_render = True
            elif last_court_state[court_num] != match_id:
                should_render = True
            
            if should_render:
                last_court_state[court_num] = match_id
                
                card = document.createElement("div")
                card.className = "card court-card h-100"
                
                header = document.createElement("div")
                header.className = "card-header d-flex justify-content-between align-items-center"
                header.innerHTML = f"<strong>Court {court_num}</strong> <span class='badge bg-dark timer-badge'>00:00</span>"
                
                body = document.createElement("div")
                body.className = "card-body"
                
                if match:
                    card.classList.add("court-active")
                    team1_names = [get_player_name(current_session, pid) for pid in match.team1]
                    team2_names = [get_player_name(current_session, pid) for pid in match.team2]
                    
                    # Fix f-string rendering of joined lists
                    team1_str = ', '.join(team1_names)
                    team2_str = ', '.join(team2_names)
                    
                    html = f"""
                        <div class="team-box team1 mb-2">
                            <div class="fw-bold text-danger">Team 1</div>
                            <div>{team1_str}</div>
                            <div class="mt-2">
                                <input type="number" class="form-control form-control-sm score-input" 
                                    id="score-c{court_num}-t1" value="0" min="0" max="30">
                            </div>
                        </div>
                        <div class="text-center fw-bold my-1">VS</div>
                        <div class="team-box team2 mb-2">
                            <div class="fw-bold text-primary">Team 2</div>
                            <div>{team2_str}</div>
                            <div class="mt-2">
                                <input type="number" class="form-control form-control-sm score-input" 
                                    id="score-c{court_num}-t2" value="0" min="0" max="30">
                            </div>
                        </div>
                        <div class="d-flex justify-content-between mt-3">
                            <button class="btn btn-success btn-sm w-50 me-1 btn-complete">✓ Complete</button>
                            <button class="btn btn-danger btn-sm w-50 ms-1 btn-forfeit">✗ Forfeit</button>
                        </div>
                    """
                    body.innerHTML = html
                    
                    def complete_cb(evt, cn=court_num, m_id=match_id):
                        s1_el = document.getElementById(f"score-c{cn}-t1")
                        s2_el = document.getElementById(f"score-c{cn}-t2")
                        if not s1_el or not s2_el: return 
                        
                        s1 = int(s1_el.value)
                        s2 = int(s2_el.value)
                        if s1 == s2:
                            window.alert("Scores cannot be tied!")
                            return
                        
                        success, _ = complete_match(current_session, m_id, s1, s2)
                        if success: refresh_display()

                    def forfeit_cb(evt, m_id=match_id):
                        if window.confirm("Forfeit match?"):
                            forfeit_match(current_session, m_id)
                            refresh_display()

                    body.querySelector(".btn-complete").onclick = complete_cb
                    body.querySelector(".btn-forfeit").onclick = forfeit_cb
                    
                else:
                    card.classList.add("court-empty")
                    body.innerHTML = "<div class='text-center text-muted py-4'><em>Waiting for players...</em></div>"
                    header.querySelector(".timer-badge").style.display = "none"

                card.appendChild(header)
                card.appendChild(body)
                col.innerHTML = ""
                col.appendChild(card)
                
            else:
                if match:
                    timer_badge = col.querySelector(".timer-badge")
                    if timer_badge:
                        delta = datetime.now() - match.start_time
                        mins, secs = divmod(int(delta.total_seconds()), 60)
                        timer_badge.innerText = f"{mins:02d}:{secs:02d}"

    def render_waitlist():
        list_el = get_el("waitlist")
        waiting_ids = get_waiting_players(current_session)
        get_el("waitlist-count").innerText = str(len(waiting_ids))
        
        list_el.innerHTML = ""
        for pid in waiting_ids:
            name = get_player_name(current_session, pid)
            li = document.createElement("li")
            li.className = "list-group-item bg-transparent text-white"
            li.innerText = name
            list_el.appendChild(li)

    def render_queue():
        list_el = get_el("queue-list")
        queued = get_queued_matches_for_display(current_session)
        get_el("queue-count").innerText = str(len(queued))
        
        list_el.innerHTML = ""
        for team1, team2 in queued:
            li = document.createElement("li")
            li.className = "list-group-item bg-transparent text-white border-secondary"
            li.innerHTML = f"<small>{team1}<br>vs<br>{team2}</small>"
            list_el.appendChild(li)

    def render_history():
        list_el = get_el("history-list")
        completed = get_completed_matches(current_session)
        completed = sorted(completed, key=lambda m: m.end_time or datetime.min, reverse=True)
        get_el("history-count").innerText = str(len(completed))
        
        list_el.innerHTML = ""
        for match in completed:
            t1_names = ", ".join([get_player_name(current_session, pid) for pid in match.team1])
            t2_names = ", ".join([get_player_name(current_session, pid) for pid in match.team2])
            
            s1 = match.score.get('team1_score', 0)
            s2 = match.score.get('team2_score', 0)
            
            t1_style = "fw-bold text-success" if s1 > s2 else "text-muted"
            t2_style = "fw-bold text-success" if s2 > s1 else "text-muted"
            
            li = document.createElement("li")
            li.className = "list-group-item bg-transparent text-white border-secondary"
            li.innerHTML = f"""
                <div class="d-flex justify-content-between">
                    <span class="{t1_style}">{t1_names} ({s1})</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="{t2_style}">{t2_names} ({s2})</span>
                </div>
            """
            list_el.appendChild(li)

    def show_stats_handler(event):
        if not current_session: return
        
        tbody = get_el("stats-table").querySelector("tbody")
        tbody.innerHTML = ""
        
        player_data = []
        for player in current_session.config.players:
            if player.id not in current_session.active_players:
                continue
            stats = current_session.player_stats[player.id]
            
            win_pct = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0
            total_wait = format_duration(stats.total_wait_time)
            
            elo = 1500 + (stats.wins - stats.losses) * 50
            
            player_data.append({
                "name": player.name,
                "elo": elo,
                "wins": stats.wins,
                "losses": stats.losses,
                "games": stats.games_played,
                "win_pct": win_pct,
                "waited": stats.games_waited,
                "wait_time": total_wait
            })
        
        player_data.sort(key=lambda x: x["elo"], reverse=True)
        
        for p in player_data:
            tr = document.createElement("tr")
            tr.innerHTML = f"""
                <td>{p['name']}</td>
                <td>{p['elo']}</td>
                <td>{p['wins']}-{p['losses']}</td>
                <td>{p['games']}</td>
                <td>{p['win_pct']:.1f}%</td>
                <td>{p['waited']}</td>
                <td>{p['wait_time']}</td>
            """
            tbody.appendChild(tr)
        
        js.bootstrap.Modal.getOrCreateInstance(get_el("statsModal")).show()

    def manage_players_handler(event):
        # Populate current player list
        list_el = get_el("modal-player-list")
        list_el.innerHTML = ""
        
        # Current active players
        for player in current_session.config.players:
            if player.id in current_session.active_players:
                li = document.createElement("li")
                li.className = "list-group-item d-flex justify-content-between align-items-center"
                li.innerHTML = f"{player.name} <button class='btn btn-sm btn-danger remove-player-btn' data-id='{player.id}'>&times;</button>"
                list_el.appendChild(li)
                
                def remove_cb(evt, pid=player.id):
                    if window.confirm(f"Remove {get_player_name(current_session, pid)}?"):
                        remove_player_from_session(current_session, pid)
                        manage_players_handler(None) # Refresh list
                        refresh_display()

                li.querySelector(".remove-player-btn").onclick = remove_cb

        # Add Handler
        def add_cb(evt):
            name = get_el("modal-player-input").value.strip()
            if not name: return
            
            if any(p.name == name for p in current_session.config.players):
                window.alert("Player exists")
                return

            new_player = Player(id=f"player_{datetime.now().timestamp()}", name=name)
            add_player_to_session(current_session, new_player)
            get_el("modal-player-input").value = ""
            manage_players_handler(None)
            refresh_display()
        
        get_el("modal-add-player-btn").onclick = add_cb
        
        js.bootstrap.Modal.getOrCreateInstance(get_el("playersModal")).show()

    def export_handler(event):
        if not current_session: return
        
        from python.session_persistence import serialize_session
        import json
        
        data = serialize_session(current_session)
        json_str = json.dumps(data, indent=2)
        
        blob = js.Blob.new([json_str], {{type: "application/json"}})
        url = js.URL.createObjectURL(blob)
        
        a = document.createElement("a")
        a.href = url
        a.download = f"pickleball_session_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.json"
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        js.URL.revokeObjectURL(url)

    def init():
        get_el("loading").style.display = "none"
        get_el("app-container").style.display = "block"
        
        get_el("add-player-btn").onclick = add_player_handler
        get_el("add-test-players-btn").onclick = add_test_players_handler
        get_el("start-session-btn").onclick = start_session_handler
        
        def on_input_key(evt):
            if evt.key == "Enter":
                evt.preventDefault()
                add_player_handler(None)
        
        get_el("new-player-input").onkeydown = on_input_key
        
        get_el("stats-btn").onclick = show_stats_handler
        get_el("manage-players-btn").onclick = manage_players_handler
        get_el("export-btn").onclick = export_handler
        get_el("end-session-btn").onclick = lambda e: window.location.reload()

    init()

except Exception as e:
    show_error(f"Application Error:\n{traceback.format_exc()}")
    print(e)