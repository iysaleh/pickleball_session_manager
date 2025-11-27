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

# Check Imports
try:
    import python
    print(f"Successfully imported 'python' package: {python}")
except ImportError as e:
    print(f"Import 'python' FAILED: {e}")

print("--- END DIAGNOSTICS ---")


# --- APPLICATION CODE ---

try:
    # Import backend modules
    try:
        from python.types import Player, SessionConfig, GameMode, SessionType
        from python.session import (
            create_session, add_player_to_session, remove_player_from_session,
            complete_match, forfeit_match, get_player_name, get_active_matches,
            get_completed_matches, create_manual_match, update_match_teams
        )
        from python.queue_manager import (
            populate_empty_courts, get_match_for_court, get_waiting_players, 
            get_queued_matches_for_display, get_session_summary, get_empty_courts
        )
        from python.utils import calculate_match_duration, format_duration
        from python.competitive_variety import calculate_elo_rating
    except ImportError as ie:
        show_error(f"Module Import Failed:\n{ie}\n\nSee console for diagnostics.")
        raise ie

    # Global State
    current_session = None
    setup_players = []
    
    # Setup phase configuration (for before session starts)
    setup_locked_teams = []
    setup_banned_pairs = []
    
    # Session UI State
    show_wait_times = False

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
        
        if any(p.name == name for p in setup_players):
            window.alert("Player already exists!")
            return

        player = Player(id=f"player_{len(setup_players)}_{datetime.now().timestamp()}", name=name)
        setup_players.append(player)
        
        update_player_list_ui()
        input_el.value = ""
        input_el.focus()

    def add_test_players_handler(event):
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
        global current_session
        
        if len(setup_players) < 2:
            window.alert("Need at least 2 players!")
            return

        mode_val = get_el("mode-select").value
        type_val = get_el("type-select").value
        courts_val = int(get_el("courts-input").value)
        sliding_val = get_el("sliding-select").value
        
        config = SessionConfig(
            mode=mode_val,
            session_type=type_val,
            players=setup_players,
            courts=courts_val,
            banned_pairs=setup_banned_pairs,
            locked_teams=setup_locked_teams,
            court_sliding_mode=sliding_val,
            randomize_player_order=False
        )
        
        try:
            current_session = create_session(config)
            
            get_el("setup-view").style.display = "none"
            get_el("session-view").style.display = "block"
            
            asyncio.create_task(refresh_loop())
            
        except Exception as e:
            window.alert(f"Error starting session: {str(e)}")
            print(e)

    # --- Session Management ---

    async def refresh_loop():
        while True:
            if current_session:
                try:
                    populate_empty_courts(current_session)
                    refresh_display()
                except Exception as e:
                    print(f"Error in refresh loop: {e}")
            await asyncio.sleep(1)

    def refresh_display():
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
    custom_court_titles = {} # Map court_num -> title

    def render_courts():
        container = get_el("courts-container")
        
        if container.children.length != current_session.config.courts:
            container.innerHTML = ""
            for _ in range(current_session.config.courts):
                col = document.createElement("div")
                col.className = "col-12 col-md-6" 
                container.appendChild(col)

        court_cols = container.children
        
        for i in range(current_session.config.courts):
            court_num = i + 1
            col = court_cols[i]
            match = get_match_for_court(current_session, court_num)
            
            match_id = match.id if match else None
            
            # Check if render needed (state change OR title update might be needed, but title update handled by rebuild)
            # We should rebuild if match changes OR if we haven't rendered this court yet.
            # We can also just update the timer without full rebuild.
            
            should_render = False
            if court_num not in last_court_state:
                should_render = True
            elif last_court_state[court_num] != match_id:
                should_render = True
            
            if should_render:
                last_court_state[court_num] = match_id
                
                card = document.createElement("div")
                card.className = "card court-card h-100"
                
                # Header (Clickable for Swap)
                header = document.createElement("div")
                header.className = "card-header d-flex justify-content-between align-items-center"
                header.style.cursor = "pointer" if match else "default"
                
                court_title = custom_court_titles.get(court_num, f"Court {court_num}")
                
                # Title Span (Clickable for Rename)
                title_span = document.createElement("span")
                title_span.className = "clickable-header"
                title_span.innerText = court_title
                title_span.title = "Double-click to rename"
                
                def rename_cb(evt, cn=court_num):
                    evt.stopPropagation() # Don't trigger header click
                    new_name = window.prompt("Rename Court:", custom_court_titles.get(cn, f"Court {cn}"))
                    if new_name is not None:
                        custom_court_titles[cn] = new_name if new_name.strip() else f"Court {cn}"
                        # Force re-render of this court next loop by invalidating state
                        last_court_state.pop(cn, None)
                        refresh_display()
                        
                title_span.ondblclick = rename_cb
                
                timer_badge = document.createElement("span")
                timer_badge.className = "badge bg-dark timer-badge"
                timer_badge.innerText = "00:00"
                
                header.appendChild(title_span)
                header.appendChild(timer_badge)
                
                if match:
                    def edit_cb(evt, cn=court_num, m_id=match_id):
                        # Prevent triggering if clicking controls or double clicking title
                        if evt.target.tagName in ["BUTTON", "INPUT"]: return
                        # Simple debounce/check to distinguish from title dblclick? 
                        # Actually title stopPropagation handles dblclick on title. 
                        # But single click on title might trigger this. 
                        # Let's allow click anywhere on header except inputs/buttons.
                        edit_court_handler(cn, m_id)
                    header.onclick = edit_cb
                    card.title = "Click header to swap players"

                body = document.createElement("div")
                body.className = "card-body"
                
                if match:
                    card.classList.add("court-active")
                    team1_names = [get_player_name(current_session, pid) for pid in match.team1]
                    team2_names = [get_player_name(current_session, pid) for pid in match.team2]
                    
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
                # Just update timer if already rendered
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
            item_text = name
            
            if show_wait_times:
                if pid in current_session.player_stats:
                    stats = current_session.player_stats[pid]
                    # Calculate current wait
                    from python.utils import get_current_wait_time
                    current_wait = get_current_wait_time(stats)
                    total_wait = stats.total_wait_time + current_wait
                    
                    cw_str = format_duration(current_wait)
                    tw_str = format_duration(total_wait)
                    item_text = f"{name} [{cw_str} / {tw_str}]"
            
            li = document.createElement("li")
            li.className = "list-group-item bg-transparent text-white"
            li.innerText = item_text
            list_el.appendChild(li)

    def toggle_wait_times_handler(event):
        global show_wait_times
        show_wait_times = not show_wait_times
        btn = get_el("toggle-wait-time-btn")
        btn.innerText = "Hide Time" if show_wait_times else "Show Time"
        refresh_display()

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
            li.className = "list-group-item bg-transparent text-white border-secondary clickable-header"
            li.innerHTML = f"""
                <div class="d-flex justify-content-between">
                    <span class="{t1_style}">{t1_names} ({s1})</span>
                </div>
                <div class="d-flex justify-content-between">
                    <span class="{t2_style}">{t2_names} ({s2})</span>
                </div>
            """
            
            def edit_cb(evt, m_id=match.id):
                edit_score_handler(m_id)
                
            li.onclick = edit_cb
            list_el.appendChild(li)

    def edit_score_handler(match_id):
        match = None
        for m in current_session.matches:
            if m.id == match_id:
                match = m
                break
        if not match or not match.score: return
        
        t1_names = ", ".join([get_player_name(current_session, pid) for pid in match.team1])
        t2_names = ", ".join([get_player_name(current_session, pid) for pid in match.team2])
        
        get_el("edit-score-match-id").value = match_id
        get_el("edit-score-team1-label").innerText = t1_names
        get_el("edit-score-team2-label").innerText = t2_names
        
        get_el("edit-score-team1-input").value = match.score.get('team1_score', 0)
        get_el("edit-score-team2-input").value = match.score.get('team2_score', 0)
        
        js.bootstrap.Modal.getOrCreateInstance(get_el("editScoreModal")).show()

    def save_score_handler(event):
        match_id = get_el("edit-score-match-id").value
        s1 = int(get_el("edit-score-team1-input").value)
        s2 = int(get_el("edit-score-team2-input").value)
        
        if s1 == s2:
            window.alert("Scores cannot be tied")
            return
            
        match = None
        for m in current_session.matches:
            if m.id == match_id:
                match = m
                break
        
        if match:
            # Note: This doesn't revert/recalc stats, it just patches the record for display/history.
            # Full ELO recalculation on edit is complex and typically requires replaying history.
            # For now, we just update the record.
            match.score = {'team1_score': s1, 'team2_score': s2}
            js.bootstrap.Modal.getInstance(get_el("editScoreModal")).hide()
            refresh_display()

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
            
            from python.utils import get_current_wait_time
            current_wait = get_current_wait_time(stats)
            total_wait_seconds = stats.total_wait_time + current_wait
            total_wait = format_duration(total_wait_seconds)
            
            # ELO
            elo = 0
            if current_session.config.mode == 'competitive-variety':
                try:
                    elo = calculate_elo_rating(stats)
                except: pass
            else:
                elo = 1500 + (stats.wins - stats.losses) * 50
                
            avg_diff = (stats.total_points_for - stats.total_points_against) / stats.games_played if stats.games_played > 0 else 0
            
            player_data.append({
                "name": player.name, "elo": elo, "wins": stats.wins, "losses": stats.losses,
                "games": stats.games_played, "win_pct": win_pct, "waited": stats.games_waited,
                "wait_time": total_wait,
                "partners": len(stats.partners_played),
                "opponents": len(stats.opponents_played),
                "avg_diff": avg_diff,
                "pts_for": stats.total_points_for,
                "pts_against": stats.total_points_against
            })
        
        # Sort
        if current_session.config.mode == 'competitive-variety':
            player_data.sort(key=lambda x: x["elo"], reverse=True)
        else:
            # Sort by Wins, then Games, then Pt Diff
            player_data.sort(key=lambda x: (x["wins"], -x["losses"], x["avg_diff"]), reverse=True)
        
        for p in player_data:
            tr = document.createElement("tr")
            # Construct row HTML as a single, long f-string line
            tr.innerHTML = f"<td>{p['name']}</td><td>{p['elo']:.0f}</td><td>{p['wins']}-{p['losses']}</td><td>{p['games']}</td><td>{p['win_pct']:.1f}%</td><td>{p['waited']}</td><td>{p['wait_time']}</td><td>{p['partners']}</td><td>{p['opponents']}</td><td>{p['avg_diff']:.1f}</td><td>{p['pts_for']}</td><td>{p['pts_against']}</td>"
            tbody.appendChild(tr)
        
        js.bootstrap.Modal.getOrCreateInstance(get_el("statsModal")).show()

    # --- LOCKS & BANS HANDLER (Unified for Setup & Session) ---
    def manage_locks_handler(event):
        # Determine which lists to edit
        is_active = (current_session is not None)
        
        if is_active:
            target_locks = current_session.config.locked_teams
            target_bans = current_session.config.banned_pairs
            if target_locks is None: current_session.config.locked_teams = []; target_locks = current_session.config.locked_teams
            if target_bans is None: current_session.config.banned_pairs = []; target_bans = current_session.config.banned_pairs
            # Active players
            all_players = sorted(current_session.config.players, key=lambda p: p.name)
        else:
            target_locks = setup_locked_teams
            target_bans = setup_banned_pairs
            # Setup players
            all_players = sorted(setup_players, key=lambda p: p.name)
        
        if not all_players:
            window.alert("Add players first.")
            return

        # Helpers
        def get_name(pid):
            for p in all_players:
                if p.id == pid: return p.name
            return pid

        def fill_select(sel_id):
            sel = get_el(sel_id)
            sel.innerHTML = ""
            for p in all_players:
                opt = document.createElement("option")
                opt.value = p.id
                opt.innerText = p.name
                sel.appendChild(opt)
        
        fill_select("lock-p1"); fill_select("lock-p2")
        fill_select("ban-p1"); fill_select("ban-p2")
        
        def render_lists():
            # Locks
            l_list = get_el("locks-list")
            l_list.innerHTML = ""
            for idx, team in enumerate(target_locks):
                names = [get_name(pid) for pid in team]
                li = document.createElement("li")
                li.className = "list-group-item d-flex justify-content-between"
                li.innerHTML = f"{'+ '.join(names)} <button class='btn btn-sm btn-danger rm-lock' data-idx='{idx}'>&times;</button>"
                
                def rm_cb(evt, i=idx):
                    target_locks.pop(i)
                    render_lists()
                li.querySelector(".rm-lock").onclick = rm_cb
                l_list.appendChild(li)
            
            # Bans
            b_list = get_el("bans-list")
            b_list.innerHTML = ""
            for idx, pair in enumerate(target_bans):
                names = [get_name(pid) for pid in pair]
                li = document.createElement("li")
                li.className = "list-group-item d-flex justify-content-between"
                li.innerHTML = f"{ ' <> '.join(names)} <button class='btn btn-sm btn-danger rm-ban' data-idx='{idx}'>&times;</button>"
                
                def rm_cb(evt, i=idx):
                    target_bans.pop(i)
                    render_lists()
                li.querySelector(".rm-ban").onclick = rm_cb
                b_list.appendChild(li)

        render_lists()
        
        def add_lock(evt):
            p1 = get_el("lock-p1").value
            p2 = get_el("lock-p2").value
            if p1 == p2: 
                window.alert("Select different players"); return
            
            # Check duplicates
            for team in target_locks:
                if p1 in team or p2 in team:
                    window.alert("One player is already locked."); return
            
            target_locks.append([p1, p2])
            render_lists()

        def add_ban(evt):
            p1 = get_el("ban-p1").value
            p2 = get_el("ban-p2").value
            if p1 == p2: 
                window.alert("Select different players"); return
            
            target_bans.append([p1, p2])
            render_lists()

        get_el("add-lock-btn").onclick = add_lock
        get_el("add-ban-btn").onclick = add_ban
        
        js.bootstrap.Modal.getOrCreateInstance(get_el("locksModal")).show()

    # Re-bind these since we use them in multiple places
    def manage_players_handler(event):
        list_el = get_el("modal-player-list")
        list_el.innerHTML = ""
        for player in current_session.config.players:
            if player.id in current_session.active_players:
                li = document.createElement("li")
                li.className = "list-group-item d-flex justify-content-between align-items-center"
                li.innerHTML = f"{player.name} <button class='btn btn-sm btn-danger remove-player-btn' data-id='{player.id}'>&times;</button>"
                list_el.appendChild(li)
                def remove_cb(evt, pid=player.id):
                    if window.confirm(f"Remove {get_player_name(current_session, pid)}?"):
                        remove_player_from_session(current_session, pid)
                        manage_players_handler(None)
                        refresh_display()
                li.querySelector(".remove-player-btn").onclick = remove_cb

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

    # --- MAKE COURT HANDLER ---
    def make_court_handler(event):
        if not current_session: return
        empty_courts = get_empty_courts(current_session)
        if not empty_courts:
            window.alert("No empty courts available.")
            return

        # Setup Court Select
        court_sel = get_el("make-court-select")
        court_sel.innerHTML = ""
        for c in empty_courts:
            opt = document.createElement("option")
            opt.value = str(c)
            opt.innerText = f"Court {c}"
            court_sel.appendChild(opt)

        waiting = get_waiting_players(current_session)
        waiting_objs = [p for p in current_session.config.players if p.id in waiting]
        waiting_objs.sort(key=lambda x: x.name)
        
        is_doubles = current_session.config.session_type == 'doubles'
        num_per_team = 2 if is_doubles else 1
        
        # Helper to create player selects
        def render_teams(team_id):
            container = get_el(team_id)
            container.innerHTML = ""
            selects = []
            for i in range(num_per_team):
                sel = document.createElement("select")
                sel.className = "form-select player-select"
                opt0 = document.createElement("option")
                opt0.value = ""
                opt0.innerText = "Select Player..."
                sel.appendChild(opt0)
                for p in waiting_objs:
                    opt = document.createElement("option")
                    opt.value = p.id
                    opt.innerText = p.name
                    sel.appendChild(opt)
                container.appendChild(sel)
                selects.append(sel)
            return selects

        t1_selects = render_teams("make-court-team1")
        t2_selects = render_teams("make-court-team2")

        def confirm_cb(evt):
            c_val = court_sel.value
            if not c_val: return
            court_num = int(c_val)
            
            t1 = [s.value for s in t1_selects if s.value]
            t2 = [s.value for s in t2_selects if s.value]
            
            if len(t1) != num_per_team or len(t2) != num_per_team:
                window.alert(f"Need {num_per_team} players per team.")
                return
            
            # Check unique
            all_p = t1 + t2
            if len(set(all_p)) != len(all_p):
                window.alert("Duplicate players selected.")
                return

            if create_manual_match(current_session, court_num, t1, t2):
                js.bootstrap.Modal.getInstance(get_el("makeCourtModal")).hide()
                refresh_display()
            else:
                window.alert("Failed to create match.")

        get_el("confirm-make-court-btn").onclick = confirm_cb
        js.bootstrap.Modal.getOrCreateInstance(get_el("makeCourtModal")).show()

    # --- EDIT COURT (SWAP) HANDLER ---
    def edit_court_handler(court_num, match_id):
        match = get_match_for_court(current_session, court_num)
        if not match: return

        # Players in this match + waiting players
        waiting = get_waiting_players(current_session)
        pool_ids = waiting + match.team1 + match.team2
        pool_objs = [p for p in current_session.config.players if p.id in pool_ids]
        pool_objs.sort(key=lambda x: x.name)

        is_doubles = current_session.config.session_type == 'doubles'
        num_per_team = 2 if is_doubles else 1
        
        t1_selects = []
        t2_selects = []

        def render_team_selects(container_id, current_team_ids, selects_list):
            container = get_el(container_id)
            container.innerHTML = ""
            for i in range(num_per_team):
                sel = document.createElement("select")
                sel.className = "form-select"
                opt0 = document.createElement("option")
                opt0.value = ""
                opt0.innerText = "(None)"
                sel.appendChild(opt0)
                
                curr_val = current_team_ids[i] if i < len(current_team_ids) else ""
                
                for p in pool_objs:
                    opt = document.createElement("option")
                    opt.value = p.id
                    opt.innerText = p.name
                    if p.id == curr_val: opt.selected = True
                    sel.appendChild(opt)
                
                container.appendChild(sel)
                selects_list.append(sel)

        render_team_selects("edit-court-team1", match.team1, t1_selects)
        render_team_selects("edit-court-team2", match.team2, t2_selects)

        def save_swap(evt):
            t1 = [s.value for s in t1_selects if s.value]
            t2 = [s.value for s in t2_selects if s.value]
            
            if len(t1) != num_per_team or len(t2) != num_per_team:
                window.alert(f"Each team needs {num_per_team} players.")
                return
            
            all_p = t1 + t2
            if len(set(all_p)) != len(all_p):
                window.alert("Duplicate players selected.")
                return
                
            if update_match_teams(current_session, match_id, t1, t2):
                js.bootstrap.Modal.getInstance(get_el("editCourtModal")).hide()
                refresh_display()
            else:
                window.alert("Failed to update match.")
        
        def swap_sides(evt):
            # Read current values
            v1 = [s.value for s in t1_selects]
            v2 = [s.value for s in t2_selects]
            # Write swapped
            for i, s in enumerate(t1_selects): s.value = v2[i] if i < len(v2) else ""
            for i, s in enumerate(t2_selects): s.value = v1[i] if i < len(v1) else ""

        get_el("confirm-edit-court-btn").onclick = save_swap
        get_el("swap-teams-btn").onclick = swap_sides
        
        js.bootstrap.Modal.getOrCreateInstance(get_el("editCourtModal")).show()

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
        get_el("make-court-btn").onclick = make_court_handler
        get_el("export-btn").onclick = export_handler
        get_el("end-session-btn").onclick = lambda e: window.location.reload()
        
        # New Handlers
        get_el("setup-locks-btn").onclick = manage_locks_handler
        get_el("manage-locks-btn").onclick = manage_locks_handler
        get_el("toggle-wait-time-btn").onclick = toggle_wait_times_handler
        get_el("save-score-btn").onclick = save_score_handler

    init()

except Exception as e:
    show_error(f"Application Error:\n{traceback.format_exc()}")
    print(e)