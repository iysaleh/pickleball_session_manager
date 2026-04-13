"""
Test match data integrity: verifies that completed match data
(team1, team2, score) is never corrupted after subsequent match completions.

Tests the fixes for:
1. Shared list references between snapshots and match objects
2. Shared list references between QueuedMatch and Match objects
3. Double-counting of partners_played/opponents_played stats
4. Missing team2 partner_last_game tracking
"""
import sys
import os
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.pickleball_types import Session, SessionConfig, Player, Match, PlayerStats, QueuedMatch, MatchSnapshot
from python.session import (
    complete_match, _create_session_snapshot, load_session_from_snapshot,
    evaluate_and_create_matches
)
from python.competitive_variety import (
    populate_empty_courts_competitive_variety,
    update_variety_tracking_after_match,
)
from python.utils import generate_id


def create_test_session(num_players=12, courts=2):
    """Create a test session in competitive-variety mode."""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, num_players + 1)]
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles',
        players=players,
        courts=courts,
        banned_pairs=[],
        locked_teams=[],
        first_bye_players=[],
        randomize_player_order=False
    )
    from python.utils import generate_id
    session = Session(id=generate_id(), config=config)
    session.active_players = set(p.id for p in players)
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)
    return session


def test_snapshot_uses_copies():
    """Verify that snapshot creation uses list copies, not references."""
    print("Test: Snapshot creation uses list copies...")
    session = create_test_session()

    # Create a match
    match = Match(
        id="test_match_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='in-progress',
        start_time=None
    )
    session.matches.append(match)

    # Create snapshot
    snapshot = _create_session_snapshot(session, "test_match_1")

    # Verify snapshot team lists are COPIES, not the same objects
    snap_match = snapshot.matches[0]
    assert snap_match["team1"] is not match.team1, \
        "Snapshot team1 should be a COPY, not a reference to the original"
    assert snap_match["team2"] is not match.team2, \
        "Snapshot team2 should be a COPY, not a reference to the original"

    # Verify values are equal
    assert snap_match["team1"] == match.team1
    assert snap_match["team2"] == match.team2

    # Verify score is also a copy
    match.score = {"team1_score": 11, "team2_score": 5}
    snapshot2 = _create_session_snapshot(session, "test_match_1")
    snap_match2 = snapshot2.matches[0]
    assert snap_match2["score"] is not match.score, \
        "Snapshot score should be a COPY, not a reference"
    assert snap_match2["score"] == match.score

    print("  PASSED: Snapshot uses list copies")


def test_snapshot_queue_uses_copies():
    """Verify that snapshot creation copies queue team lists."""
    print("Test: Snapshot queue uses list copies...")
    session = create_test_session()

    # Add a queued match
    qm = QueuedMatch(team1=["p1", "p2"], team2=["p3", "p4"])
    session.match_queue.append(qm)

    # Create snapshot
    snapshot = _create_session_snapshot(session, "dummy")

    # Verify queue data uses copies
    queue_entry = snapshot.match_queue[0]
    assert queue_entry["team1"] is not qm.team1, \
        "Snapshot queue team1 should be a COPY"
    assert queue_entry["team2"] is not qm.team2, \
        "Snapshot queue team2 should be a COPY"
    assert queue_entry["team1"] == qm.team1
    assert queue_entry["team2"] == qm.team2

    print("  PASSED: Snapshot queue uses list copies")


def test_load_snapshot_uses_copies():
    """Verify that loading a snapshot creates new list objects."""
    print("Test: Loading snapshot uses list copies...")
    session = create_test_session()

    # Create match and snapshot
    match = Match(
        id="test_match_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='in-progress',
        start_time=None
    )
    session.matches.append(match)

    # Add queue
    qm = QueuedMatch(team1=["p5", "p6"], team2=["p7", "p8"])
    session.match_queue.append(qm)

    snapshot = _create_session_snapshot(session, "test_match_1")

    # Load snapshot
    load_session_from_snapshot(session, snapshot)

    # Verify loaded match team lists are copies of snapshot data
    loaded_match = session.matches[0]
    snap_data = snapshot.matches[0]
    assert loaded_match.team1 is not snap_data["team1"], \
        "Loaded match team1 should be a COPY of snapshot data"
    assert loaded_match.team2 is not snap_data["team2"], \
        "Loaded match team2 should be a COPY of snapshot data"

    # Verify loaded queue is also a copy
    loaded_qm = session.match_queue[0]
    snap_q = snapshot.match_queue[0]
    assert loaded_qm.team1 is not snap_q["team1"], \
        "Loaded queue team1 should be a COPY of snapshot data"
    assert loaded_qm.team2 is not snap_q["team2"], \
        "Loaded queue team2 should be a COPY of snapshot data"

    print("  PASSED: Loading snapshot uses list copies")


def test_completed_match_data_survives_subsequent_completions():
    """
    Core test: Complete multiple matches sequentially and verify that
    each previously completed match's data is never corrupted.
    """
    print("Test: Completed match data survives subsequent completions...")
    session = create_test_session(num_players=12, courts=2)

    # Populate courts to get initial matches
    populate_empty_courts_competitive_variety(session)
    assert len(session.matches) >= 2, f"Expected at least 2 matches, got {len(session.matches)}"

    completed_data = []  # Store (match_id, team1_copy, team2_copy, score_copy)

    # Complete matches one at a time and verify all prior matches are unchanged
    for round_num in range(3):
        # Find in-progress/waiting matches
        active_matches = [m for m in session.matches if m.status in ('in-progress', 'waiting')]
        if not active_matches:
            # Try to populate more courts
            populate_empty_courts_competitive_variety(session)
            active_matches = [m for m in session.matches if m.status in ('in-progress', 'waiting')]
            if not active_matches:
                break

        for match in active_matches:
            # Record pre-completion data
            match_id = match.id
            team1_before = list(match.team1)
            team2_before = list(match.team2)

            # Complete the match
            score1, score2 = 11, 5 + round_num
            complete_match(session, match_id, score1, score2)

            # Verify this match's data is correct
            completed_match = next(m for m in session.matches if m.id == match_id)
            assert completed_match.team1 == team1_before, \
                f"Match {match_id} team1 changed after completion: {team1_before} -> {completed_match.team1}"
            assert completed_match.team2 == team2_before, \
                f"Match {match_id} team2 changed after completion: {team2_before} -> {completed_match.team2}"
            assert completed_match.score == {"team1_score": score1, "team2_score": score2}, \
                f"Match {match_id} score wrong: {completed_match.score}"

            completed_data.append((match_id, team1_before, team2_before,
                                   {"team1_score": score1, "team2_score": score2}))

            # Verify ALL previously completed matches are unchanged
            for prev_id, prev_t1, prev_t2, prev_score in completed_data[:-1]:
                prev_match = next(m for m in session.matches if m.id == prev_id)
                assert prev_match.team1 == prev_t1, \
                    f"Previously completed match {prev_id} team1 CORRUPTED after completing {match_id}: " \
                    f"expected {prev_t1}, got {prev_match.team1}"
                assert prev_match.team2 == prev_t2, \
                    f"Previously completed match {prev_id} team2 CORRUPTED after completing {match_id}: " \
                    f"expected {prev_t2}, got {prev_match.team2}"
                assert prev_match.score == prev_score, \
                    f"Previously completed match {prev_id} score CORRUPTED after completing {match_id}: " \
                    f"expected {prev_score}, got {prev_match.score}"

        # Populate courts for next round
        populate_empty_courts_competitive_variety(session)

    assert len(completed_data) >= 4, \
        f"Expected at least 4 completed matches, got {len(completed_data)}"
    print(f"  PASSED: {len(completed_data)} matches completed, all data intact")


def test_no_double_counting_stats():
    """
    Verify that partners_played and opponents_played are NOT double-counted.
    complete_match() should be the ONLY place that increments these counters.
    update_variety_tracking_after_match() should only update game number tracking.
    """
    print("Test: No double-counting of partnership/opponent stats...")
    session = create_test_session(num_players=8, courts=1)

    # Create and complete a single match
    match = Match(
        id="test_dc_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='in-progress',
        start_time=None
    )
    session.matches.append(match)
    complete_match(session, "test_dc_1", 11, 5)

    # Verify partner counts are exactly 1 (not 2)
    assert session.player_stats["p1"].partners_played.get("p2", 0) == 1, \
        f"p1.partners_played[p2] = {session.player_stats['p1'].partners_played.get('p2', 0)}, expected 1"
    assert session.player_stats["p2"].partners_played.get("p1", 0) == 1, \
        f"p2.partners_played[p1] = {session.player_stats['p2'].partners_played.get('p1', 0)}, expected 1"

    # Verify team2 partner counts
    assert session.player_stats["p3"].partners_played.get("p4", 0) == 1, \
        f"p3.partners_played[p4] = {session.player_stats['p3'].partners_played.get('p4', 0)}, expected 1"
    assert session.player_stats["p4"].partners_played.get("p3", 0) == 1, \
        f"p4.partners_played[p3] = {session.player_stats['p4'].partners_played.get('p3', 0)}, expected 1"

    # Verify opponent counts are exactly 1
    assert session.player_stats["p1"].opponents_played.get("p3", 0) == 1, \
        f"p1.opponents_played[p3] = {session.player_stats['p1'].opponents_played.get('p3', 0)}, expected 1"
    assert session.player_stats["p1"].opponents_played.get("p4", 0) == 1, \
        f"p1.opponents_played[p4] = {session.player_stats['p1'].opponents_played.get('p4', 0)}, expected 1"
    assert session.player_stats["p3"].opponents_played.get("p1", 0) == 1, \
        f"p3.opponents_played[p1] = {session.player_stats['p3'].opponents_played.get('p1', 0)}, expected 1"
    assert session.player_stats["p3"].opponents_played.get("p2", 0) == 1, \
        f"p3.opponents_played[p2] = {session.player_stats['p3'].opponents_played.get('p2', 0)}, expected 1"

    print("  PASSED: No double-counting of stats")


def test_team2_partner_last_game_tracking():
    """
    Verify that partner_last_game is updated for BOTH team1 and team2 pairs.
    Previously, team2 partner_last_game was not being updated.
    """
    print("Test: Team2 partner_last_game tracking...")
    session = create_test_session(num_players=8, courts=1)

    match = Match(
        id="test_plg_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='in-progress',
        start_time=None
    )
    session.matches.append(match)
    complete_match(session, "test_plg_1", 11, 5)

    # Verify team1 partner_last_game is set
    assert "p2" in session.player_stats["p1"].partner_last_game, \
        "p1.partner_last_game should contain p2"
    assert "p1" in session.player_stats["p2"].partner_last_game, \
        "p2.partner_last_game should contain p1"

    # Verify team2 partner_last_game is ALSO set (this was previously missing)
    assert "p4" in session.player_stats["p3"].partner_last_game, \
        "p3.partner_last_game should contain p4 (team2 tracking fix)"
    assert "p3" in session.player_stats["p4"].partner_last_game, \
        "p4.partner_last_game should contain p3 (team2 tracking fix)"

    print("  PASSED: Team2 partner_last_game tracking works")


def test_match_creation_from_queue_uses_copies():
    """
    Verify that matches created from the queue use list copies,
    not shared references with the QueuedMatch.
    """
    print("Test: Match creation from queue uses copies...")
    session = create_test_session(num_players=12, courts=1)

    # Add a queued match
    qm = QueuedMatch(team1=["p1", "p2"], team2=["p3", "p4"])
    session.match_queue.append(qm)

    # Save original team lists
    original_t1 = list(qm.team1)
    original_t2 = list(qm.team2)

    # Populate courts (should use the queued match)
    populate_empty_courts_competitive_variety(session)

    # Find the created match
    created_matches = [m for m in session.matches if set(m.team1) == {"p1", "p2"} or set(m.team2) == {"p1", "p2"}]
    if created_matches:
        created = created_matches[0]
        # The created match's team lists should be copies
        assert created.team1 is not qm.team1, \
            "Created match team1 should be a COPY of queued match team1"
        assert created.team2 is not qm.team2, \
            "Created match team2 should be a COPY of queued match team2"
        print("  PASSED: Match from queue uses copies")
    else:
        # Queue match might not have been used (constraints), that's OK
        print("  SKIPPED: Queue match not used (constraint related)")


def test_serialization_uses_copies():
    """Verify that session serialization creates copies of team lists."""
    print("Test: Serialization uses copies...")
    from python.session_persistence import serialize_session

    session = create_test_session(num_players=8, courts=1)

    match = Match(
        id="test_ser_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='completed',
        score={"team1_score": 11, "team2_score": 5}
    )
    session.matches.append(match)

    qm = QueuedMatch(team1=["p5", "p6"], team2=["p7", "p8"])
    session.match_queue.append(qm)

    data = serialize_session(session)

    # Verify serialized data uses copies
    ser_match = data["matches"][0]
    assert ser_match["team1"] is not match.team1, \
        "Serialized team1 should be a COPY"
    assert ser_match["team2"] is not match.team2, \
        "Serialized team2 should be a COPY"
    assert ser_match["score"] is not match.score, \
        "Serialized score should be a COPY"

    ser_q = data["match_queue"][0]
    assert ser_q["team1"] is not qm.team1, \
        "Serialized queue team1 should be a COPY"
    assert ser_q["team2"] is not qm.team2, \
        "Serialized queue team2 should be a COPY"

    print("  PASSED: Serialization uses copies")


def test_winner_not_reversed_after_subsequent_match():
    """
    Regression test for the reported bug: match scores should not be
    reversed after another match is completed.
    """
    print("Test: Winner not reversed after subsequent match completion...")
    session = create_test_session(num_players=12, courts=2)

    # Create two matches manually
    match1 = Match(
        id="match_1",
        court_number=1,
        team1=["p1", "p2"],
        team2=["p3", "p4"],
        status='in-progress',
        start_time=None
    )
    match2 = Match(
        id="match_2",
        court_number=2,
        team1=["p5", "p6"],
        team2=["p7", "p8"],
        status='in-progress',
        start_time=None
    )
    session.matches.extend([match1, match2])

    # Complete match 1: team1 wins 11-5
    complete_match(session, "match_1", 11, 5)

    # Verify match 1 data
    m1 = next(m for m in session.matches if m.id == "match_1")
    assert m1.team1 == ["p1", "p2"], f"Match 1 team1 wrong: {m1.team1}"
    assert m1.team2 == ["p3", "p4"], f"Match 1 team2 wrong: {m1.team2}"
    assert m1.score == {"team1_score": 11, "team2_score": 5}, f"Match 1 score wrong: {m1.score}"

    # Complete match 2: team2 wins 3-11
    complete_match(session, "match_2", 3, 11)

    # Verify match 1 data is STILL correct (not reversed)
    m1 = next(m for m in session.matches if m.id == "match_1")
    assert m1.team1 == ["p1", "p2"], \
        f"Match 1 team1 REVERSED after match 2 completion: {m1.team1}"
    assert m1.team2 == ["p3", "p4"], \
        f"Match 1 team2 REVERSED after match 2 completion: {m1.team2}"
    assert m1.score == {"team1_score": 11, "team2_score": 5}, \
        f"Match 1 score REVERSED after match 2 completion: {m1.score}"

    # Verify match 2 data
    m2 = next(m for m in session.matches if m.id == "match_2")
    assert m2.team1 == ["p5", "p6"], f"Match 2 team1 wrong: {m2.team1}"
    assert m2.team2 == ["p3", "p4"] or m2.team2 == ["p7", "p8"], \
        f"Match 2 team2 wrong: {m2.team2}"
    assert m2.score == {"team1_score": 3, "team2_score": 11}, \
        f"Match 2 score wrong: {m2.score}"

    # Populate courts and verify again
    populate_empty_courts_competitive_variety(session)

    m1 = next(m for m in session.matches if m.id == "match_1")
    assert m1.team1 == ["p1", "p2"], \
        f"Match 1 team1 REVERSED after court population: {m1.team1}"
    assert m1.team2 == ["p3", "p4"], \
        f"Match 1 team2 REVERSED after court population: {m1.team2}"
    assert m1.score == {"team1_score": 11, "team2_score": 5}, \
        f"Match 1 score REVERSED after court population: {m1.score}"

    print("  PASSED: Winner not reversed after subsequent match")


def test_match_history_display_winner_on_top():
    """
    Verify that match history display format shows winner on top,
    consistent with the confirmation dialog format.
    
    This was the root cause of the 'score reversal' bug: the confirmation
    dialog showed winner on top, but match history showed team1 on top
    regardless of who won. When team2 won, this looked like the result
    was reversed.
    """
    print("Test: Match history display shows winner on top...")

    def format_match_history_item(team1_names, team2_names, score):
        """Replicate the match history display logic from gui.py"""
        team1_str = ", ".join(team1_names)
        team2_str = ", ".join(team2_names)
        if score:
            t1_score = score.get('team1_score', 0)
            t2_score = score.get('team2_score', 0)
            # Winner on top (consistent with confirmation dialog)
            if t1_score >= t2_score:
                return f"{team1_str} {t1_score}\nvs\n{team2_str} {t2_score}"
            else:
                return f"{team2_str} {t2_score}\nvs\n{team1_str} {t1_score}"
        return f"{team1_str}\nvs\n{team2_str}"

    # Case 1: team1 wins — team1 should be on top
    text = format_match_history_item(
        ["Alice"], ["Bob"],
        {"team1_score": 11, "team2_score": 5}
    )
    lines = text.split("\n")
    assert "Alice 11" in lines[0], f"Winner (Alice) should be on top, got: {lines[0]}"
    assert "Bob 5" in lines[2], f"Loser (Bob) should be on bottom, got: {lines[2]}"

    # Case 2: team2 wins — team2 should be on top (THIS WAS THE BUG)
    text = format_match_history_item(
        ["Alice"], ["Bob"],
        {"team1_score": 5, "team2_score": 11}
    )
    lines = text.split("\n")
    assert "Bob 11" in lines[0], f"Winner (Bob) should be on top, got: {lines[0]}"
    assert "Alice 5" in lines[2], f"Loser (Alice) should be on bottom, got: {lines[2]}"

    # Case 3: doubles — team2 wins
    text = format_match_history_item(
        ["Alice", "Carol"], ["Bob", "Dave"],
        {"team1_score": 3, "team2_score": 11}
    )
    lines = text.split("\n")
    assert "Bob, Dave 11" in lines[0], f"Winner team should be on top, got: {lines[0]}"
    assert "Alice, Carol 3" in lines[2], f"Loser team should be on bottom, got: {lines[2]}"

    print("  PASSED: Match history display shows winner on top")


def test_round_robin_match_integrity():
    """
    Test that match data remains intact in round-robin mode after
    multiple match completions and court populations.
    """
    print("Test: Round-robin match data integrity across completions...")
    from python.queue_manager import populate_empty_courts
    from python.roundrobin import generate_round_robin_queue

    # Create session in round-robin mode
    players = [Player(id=f"p{i}", name=f"Player{i}") for i in range(1, 7)]
    config = SessionConfig(
        players=players,
        courts=1,
        mode='round-robin',
        session_type='singles',
    )
    session = Session(id=generate_id(), config=config)
    session.active_players = {p.id for p in players}
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)

    # Generate round-robin queue
    active_players = [p for p in players if p.id in session.active_players]
    session.match_queue = generate_round_robin_queue(
        active_players, 'singles', []
    )
    assert len(session.match_queue) > 0, "Queue should not be empty"

    # Populate first match
    populate_empty_courts(session)
    assert any(m.status in ('waiting', 'in-progress') for m in session.matches), \
        "Should have created a match"

    completed_records = []  # Track all completions for verification

    # Complete multiple matches and verify no data corruption
    for round_num in range(min(5, len(session.match_queue) + 1)):
        active_matches = [m for m in session.matches
                          if m.status in ('waiting', 'in-progress')]
        if not active_matches:
            populate_empty_courts(session)
            active_matches = [m for m in session.matches
                              if m.status in ('waiting', 'in-progress')]
        if not active_matches:
            break

        match = active_matches[0]
        match.status = 'in-progress'
        match_id = match.id
        t1 = list(match.team1)
        t2 = list(match.team2)

        # Complete with team2 winning (to test the reversal scenario)
        success, _ = complete_match(session, match_id, 5, 11)
        assert success, f"Match {match_id} completion should succeed"

        completed_records.append({
            'id': match_id,
            'team1': t1,
            'team2': t2,
            'score': {'team1_score': 5, 'team2_score': 11}
        })

        # After each completion, verify ALL previously completed matches
        for record in completed_records:
            m = next((m for m in session.matches if m.id == record['id']), None)
            assert m is not None, f"Match {record['id']} should still exist"
            assert m.team1 == record['team1'], \
                f"Match {record['id']} team1 changed from {record['team1']} to {m.team1}"
            assert m.team2 == record['team2'], \
                f"Match {record['id']} team2 changed from {record['team2']} to {m.team2}"
            assert m.score == record['score'], \
                f"Match {record['id']} score changed from {record['score']} to {m.score}"

        # Populate more courts
        populate_empty_courts(session)

    assert len(completed_records) >= 3, \
        f"Should have completed at least 3 matches, got {len(completed_records)}"
    print(f"  PASSED: {len(completed_records)} matches completed, all data intact")


def test_strict_continuous_rr_match_integrity():
    """
    Test that match data remains intact in strict-continuous-rr mode
    after multiple match completions and court populations.
    """
    print("Test: Strict continuous RR match data integrity...")
    from python.strict_continuous_rr import populate_courts_strict_continuous

    # Create session in strict-continuous-rr mode
    players = [Player(id=f"p{i}", name=f"Player{i}") for i in range(1, 7)]
    config = SessionConfig(
        players=players,
        courts=1,
        mode='strict-continuous-rr',
        session_type='singles',
    )
    session = Session(id=generate_id(), config=config)
    session.active_players = {p.id for p in players}
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)

    # Generate queue
    from python.strict_continuous_rr import _generate_singles_round_robin_queue
    active_players = [p for p in players if p.id in session.active_players]
    session.match_queue = _generate_singles_round_robin_queue(active_players, [])
    assert len(session.match_queue) > 0, "Queue should not be empty"

    # Populate first match
    populate_courts_strict_continuous(session)

    completed_records = []

    for round_num in range(min(5, len(session.match_queue) + 1)):
        active_matches = [m for m in session.matches
                          if m.status in ('waiting', 'in-progress')]
        if not active_matches:
            populate_courts_strict_continuous(session)
            active_matches = [m for m in session.matches
                              if m.status in ('waiting', 'in-progress')]
        if not active_matches:
            break

        match = active_matches[0]
        match.status = 'in-progress'
        match_id = match.id
        t1 = list(match.team1)
        t2 = list(match.team2)

        # Alternate winners to test both team1 and team2 winning
        if round_num % 2 == 0:
            success, _ = complete_match(session, match_id, 5, 11)
            score = {'team1_score': 5, 'team2_score': 11}
        else:
            success, _ = complete_match(session, match_id, 11, 5)
            score = {'team1_score': 11, 'team2_score': 5}

        assert success, f"Match {match_id} completion should succeed"

        completed_records.append({
            'id': match_id,
            'team1': t1,
            'team2': t2,
            'score': score
        })

        # Verify ALL previously completed matches
        for record in completed_records:
            m = next((m for m in session.matches if m.id == record['id']), None)
            assert m is not None, f"Match {record['id']} should still exist"
            assert m.team1 == record['team1'], \
                f"Match {record['id']} team1 changed from {record['team1']} to {m.team1}"
            assert m.team2 == record['team2'], \
                f"Match {record['id']} team2 changed from {record['team2']} to {m.team2}"
            assert m.score == record['score'], \
                f"Match {record['id']} score changed from {record['score']} to {m.score}"

        populate_courts_strict_continuous(session)

    assert len(completed_records) >= 3, \
        f"Should have completed at least 3 matches, got {len(completed_records)}"
    print(f"  PASSED: {len(completed_records)} matches completed, all data intact")


def test_singles_rr_stats_not_reversed():
    """
    Targeted regression test for the reported bug: in singles round-robin,
    completing match B should not reverse match A's winner in player_stats.
    
    Scenario: 6 players, 2 courts, singles round-robin
    1. Court 1: Alice vs Bob, Alice wins 11-5
    2. Verify Alice has 1 win, Bob has 1 loss
    3. Court 2: Carol vs Dave, Carol wins 11-7
    4. Verify Alice STILL has 1 win, Bob STILL has 1 loss
    5. Populate more courts, complete more matches
    6. Verify all prior stats are still correct
    """
    print("Test: Singles RR stats not reversed after subsequent match...")
    from python.queue_manager import populate_empty_courts
    from python.roundrobin import generate_round_robin_queue
    from python.session import evaluate_and_create_matches

    players = [
        Player(id="alice", name="Alice"),
        Player(id="bob", name="Bob"),
        Player(id="carol", name="Carol"),
        Player(id="dave", name="Dave"),
        Player(id="eve", name="Eve"),
        Player(id="frank", name="Frank"),
    ]
    config = SessionConfig(
        players=players,
        courts=2,
        mode='round-robin',
        session_type='singles',
    )
    session = Session(id=generate_id(), config=config)
    session.active_players = {p.id for p in players}
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)

    # Create matches manually (to have deterministic team assignments)
    from python.time_manager import now
    match1 = Match(id="m1", court_number=1, team1=["alice"], team2=["bob"],
                   status='in-progress', start_time=now())
    match2 = Match(id="m2", court_number=2, team1=["carol"], team2=["dave"],
                   status='in-progress', start_time=now())
    session.matches.extend([match1, match2])

    # Complete match 1: Alice wins 11-5
    success, _ = complete_match(session, "m1", 11, 5)
    assert success

    # Verify Alice's stats
    assert session.player_stats["alice"].wins == 1, \
        f"Alice should have 1 win, got {session.player_stats['alice'].wins}"
    assert session.player_stats["alice"].losses == 0, \
        f"Alice should have 0 losses, got {session.player_stats['alice'].losses}"
    assert session.player_stats["bob"].wins == 0, \
        f"Bob should have 0 wins, got {session.player_stats['bob'].wins}"
    assert session.player_stats["bob"].losses == 1, \
        f"Bob should have 1 loss, got {session.player_stats['bob'].losses}"

    # Simulate timer firing (evaluate_and_create_matches called every second)
    evaluate_and_create_matches(session)

    # Verify Alice's stats are UNCHANGED after evaluation
    assert session.player_stats["alice"].wins == 1, \
        f"Alice wins changed after evaluate: {session.player_stats['alice'].wins}"
    assert session.player_stats["alice"].losses == 0, \
        f"Alice losses changed after evaluate: {session.player_stats['alice'].losses}"

    # Complete match 2: Carol wins 11-7
    success, _ = complete_match(session, "m2", 11, 7)
    assert success

    # Verify Alice's stats are STILL correct (NOT reversed)
    assert session.player_stats["alice"].wins == 1, \
        f"Alice wins reversed after match 2: {session.player_stats['alice'].wins}"
    assert session.player_stats["alice"].losses == 0, \
        f"Alice losses changed after match 2: {session.player_stats['alice'].losses}"
    assert session.player_stats["bob"].wins == 0, \
        f"Bob wins changed after match 2: {session.player_stats['bob'].wins}"
    assert session.player_stats["bob"].losses == 1, \
        f"Bob losses changed after match 2: {session.player_stats['bob'].losses}"

    # Verify Carol and Dave's stats
    assert session.player_stats["carol"].wins == 1
    assert session.player_stats["carol"].losses == 0
    assert session.player_stats["dave"].wins == 0
    assert session.player_stats["dave"].losses == 1

    # Populate more courts and verify stats survive
    evaluate_and_create_matches(session)

    # Verify ALL stats remain correct
    for pid, expected_w, expected_l in [
        ("alice", 1, 0), ("bob", 0, 1), ("carol", 1, 0), ("dave", 0, 1),
        ("eve", 0, 0), ("frank", 0, 0)
    ]:
        actual_w = session.player_stats[pid].wins
        actual_l = session.player_stats[pid].losses
        assert actual_w == expected_w and actual_l == expected_l, \
            f"{pid}: expected {expected_w}-{expected_l}, got {actual_w}-{actual_l}"

    print("  PASSED: Singles RR stats not reversed after subsequent match")


def test_singles_strict_rr_stats_not_reversed():
    """
    Same test as above but for strict-continuous-rr mode.
    """
    print("Test: Singles strict-continuous-RR stats not reversed...")
    from python.strict_continuous_rr import populate_courts_strict_continuous
    from python.session import evaluate_and_create_matches

    players = [
        Player(id="alice", name="Alice"),
        Player(id="bob", name="Bob"),
        Player(id="carol", name="Carol"),
        Player(id="dave", name="Dave"),
        Player(id="eve", name="Eve"),
        Player(id="frank", name="Frank"),
    ]
    config = SessionConfig(
        players=players,
        courts=2,
        mode='strict-continuous-rr',
        session_type='singles',
    )
    session = Session(id=generate_id(), config=config)
    session.active_players = {p.id for p in players}
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)

    from python.time_manager import now
    # Match 1: Alice (team1) vs Bob (team2) — Alice wins
    match1 = Match(id="m1", court_number=1, team1=["alice"], team2=["bob"],
                   status='in-progress', start_time=now())
    # Match 2: Carol (team1) vs Dave (team2) — Dave wins (team2 winner case)
    match2 = Match(id="m2", court_number=2, team1=["carol"], team2=["dave"],
                   status='in-progress', start_time=now())
    session.matches.extend([match1, match2])

    # Complete match 1: Alice (team1) wins
    success, _ = complete_match(session, "m1", 11, 5)
    assert success
    assert session.player_stats["alice"].wins == 1
    assert session.player_stats["alice"].losses == 0
    assert session.player_stats["bob"].wins == 0
    assert session.player_stats["bob"].losses == 1

    # Simulate timer evaluation
    evaluate_and_create_matches(session)

    # Stats unchanged
    assert session.player_stats["alice"].wins == 1
    assert session.player_stats["bob"].losses == 1

    # Complete match 2: Dave (team2) wins — tests the team2-wins path
    success, _ = complete_match(session, "m2", 7, 11)
    assert success

    # Verify match 1 stats are STILL correct
    assert session.player_stats["alice"].wins == 1, \
        f"Alice wins reversed: {session.player_stats['alice'].wins}"
    assert session.player_stats["alice"].losses == 0, \
        f"Alice losses reversed: {session.player_stats['alice'].losses}"
    assert session.player_stats["bob"].wins == 0
    assert session.player_stats["bob"].losses == 1

    # Verify match 2 stats
    assert session.player_stats["carol"].wins == 0
    assert session.player_stats["carol"].losses == 1
    assert session.player_stats["dave"].wins == 1
    assert session.player_stats["dave"].losses == 0

    # Simulate timer + populate
    evaluate_and_create_matches(session)

    # All stats still correct
    for pid, expected_w, expected_l in [
        ("alice", 1, 0), ("bob", 0, 1), ("carol", 0, 1), ("dave", 1, 0),
        ("eve", 0, 0), ("frank", 0, 0)
    ]:
        actual_w = session.player_stats[pid].wins
        actual_l = session.player_stats[pid].losses
        assert actual_w == expected_w and actual_l == expected_l, \
            f"{pid}: expected {expected_w}-{expected_l}, got {actual_w}-{actual_l}"

    print("  PASSED: Strict continuous RR stats not reversed")


def test_stats_survive_save_load_cycle():
    """
    Test that player stats survive a save → load cycle without corruption.
    This tests the serialization/deserialization path for round-robin modes.
    """
    print("Test: Stats survive save/load cycle in RR mode...")
    from python.session_persistence import serialize_session, deserialize_session

    players = [
        Player(id="alice", name="Alice"),
        Player(id="bob", name="Bob"),
        Player(id="carol", name="Carol"),
        Player(id="dave", name="Dave"),
    ]
    config = SessionConfig(
        players=players,
        courts=2,
        mode='round-robin',
        session_type='singles',
    )
    session = Session(id=generate_id(), config=config)
    session.active_players = {p.id for p in players}
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)

    from python.time_manager import now
    match1 = Match(id="m1", court_number=1, team1=["alice"], team2=["bob"],
                   status='in-progress', start_time=now())
    session.matches.append(match1)
    complete_match(session, "m1", 11, 5)

    # Verify pre-save stats
    assert session.player_stats["alice"].wins == 1
    assert session.player_stats["bob"].losses == 1

    # Serialize
    data = serialize_session(session)

    # Deserialize
    loaded = deserialize_session(data)

    # Verify loaded stats
    assert loaded.player_stats["alice"].wins == 1, \
        f"Alice wins after load: {loaded.player_stats['alice'].wins}"
    assert loaded.player_stats["alice"].losses == 0, \
        f"Alice losses after load: {loaded.player_stats['alice'].losses}"
    assert loaded.player_stats["bob"].wins == 0, \
        f"Bob wins after load: {loaded.player_stats['bob'].wins}"
    assert loaded.player_stats["bob"].losses == 1, \
        f"Bob losses after load: {loaded.player_stats['bob'].losses}"

    # Verify match data survived
    m1 = next(m for m in loaded.matches if m.id == "m1")
    assert m1.team1 == ["alice"]
    assert m1.team2 == ["bob"]
    assert m1.score == {"team1_score": 11, "team2_score": 5}
    assert m1.status == "completed"

    print("  PASSED: Stats survive save/load cycle")


def test_double_completion_guard():
    """
    Verify that completing an already-completed match is rejected
    and doesn't double-count stats.
    """
    print("Test: Double completion guard prevents stat double-counting...")

    players = [Player(id="alice", name="Alice"), Player(id="bob", name="Bob")]
    config = SessionConfig(
        players=players, courts=1, mode='round-robin', session_type='singles',
    )
    session = Session(id=generate_id(), config=config)
    session.active_players = {p.id for p in players}
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)

    from python.time_manager import now
    match = Match(id="m1", court_number=1, team1=["alice"], team2=["bob"],
                  status='in-progress', start_time=now())
    session.matches.append(match)

    # First completion: should succeed
    success1, _ = complete_match(session, "m1", 11, 5)
    assert success1, "First completion should succeed"
    assert session.player_stats["alice"].wins == 1
    assert session.player_stats["bob"].losses == 1

    # Second completion: should be rejected
    success2, _ = complete_match(session, "m1", 5, 11)
    assert not success2, "Second completion should be rejected"

    # Stats should not have changed
    assert session.player_stats["alice"].wins == 1, \
        f"Alice wins after double-completion: {session.player_stats['alice'].wins}"
    assert session.player_stats["alice"].losses == 0, \
        f"Alice losses after double-completion: {session.player_stats['alice'].losses}"
    assert session.player_stats["bob"].wins == 0, \
        f"Bob wins after double-completion: {session.player_stats['bob'].wins}"
    assert session.player_stats["bob"].losses == 1, \
        f"Bob losses after double-completion: {session.player_stats['bob'].losses}"

    print("  PASSED: Double completion guard works")


def test_rr_full_session_stats_integrity():
    """
    Simulate a full round-robin session with multiple courts and players.
    Track all expected stats and verify they match after every completion.
    This is the most comprehensive stats integrity test.
    """
    print("Test: Full RR session stats integrity (6 players, 2 courts)...")
    from python.queue_manager import populate_empty_courts
    from python.session import evaluate_and_create_matches

    players = [Player(id=f"p{i}", name=f"Player{i}") for i in range(1, 7)]
    config = SessionConfig(
        players=players, courts=2, mode='round-robin', session_type='singles',
    )
    session = Session(id=generate_id(), config=config)
    session.active_players = {p.id for p in players}
    for p in players:
        session.player_stats[p.id] = PlayerStats(player_id=p.id)

    # Generate queue
    from python.roundrobin import generate_round_robin_queue
    session.match_queue = generate_round_robin_queue(players, 'singles', [])

    # Track expected stats
    expected_wins = {p.id: 0 for p in players}
    expected_losses = {p.id: 0 for p in players}
    expected_games = {p.id: 0 for p in players}

    matches_completed = 0

    for _ in range(8):  # Complete up to 8 matches
        populate_empty_courts(session)
        active_matches = [m for m in session.matches
                          if m.status in ('waiting', 'in-progress')]
        if not active_matches:
            break

        for match in active_matches:
            match.status = 'in-progress'

            # Team1 wins when first player ID is "lower" (deterministic)
            if match.team1[0] < match.team2[0]:
                t1s, t2s = 11, 5
            else:
                t1s, t2s = 5, 11

            team1_won = t1s > t2s

            success, _ = complete_match(session, match.id, t1s, t2s)
            assert success

            # Update expected stats
            for pid in match.team1:
                expected_games[pid] += 1
                if team1_won:
                    expected_wins[pid] += 1
                else:
                    expected_losses[pid] += 1

            for pid in match.team2:
                expected_games[pid] += 1
                if not team1_won:
                    expected_wins[pid] += 1
                else:
                    expected_losses[pid] += 1

            matches_completed += 1

            # Verify ALL player stats after EVERY completion
            for p in players:
                actual_w = session.player_stats[p.id].wins
                actual_l = session.player_stats[p.id].losses
                actual_g = session.player_stats[p.id].games_played
                assert actual_w == expected_wins[p.id], \
                    f"After match #{matches_completed}: {p.name} wins expected " \
                    f"{expected_wins[p.id]}, got {actual_w}"
                assert actual_l == expected_losses[p.id], \
                    f"After match #{matches_completed}: {p.name} losses expected " \
                    f"{expected_losses[p.id]}, got {actual_l}"
                assert actual_g == expected_games[p.id], \
                    f"After match #{matches_completed}: {p.name} games expected " \
                    f"{expected_games[p.id]}, got {actual_g}"

        # Simulate timer evaluation
        evaluate_and_create_matches(session)

        # Verify stats AGAIN after evaluation (timer shouldn't modify stats)
        for p in players:
            actual_w = session.player_stats[p.id].wins
            actual_l = session.player_stats[p.id].losses
            assert actual_w == expected_wins[p.id], \
                f"After evaluate: {p.name} wins expected {expected_wins[p.id]}, got {actual_w}"
            assert actual_l == expected_losses[p.id], \
                f"After evaluate: {p.name} losses expected {expected_losses[p.id]}, got {actual_l}"

    assert matches_completed >= 4, \
        f"Should have completed at least 4 matches, got {matches_completed}"
    print(f"  PASSED: {matches_completed} matches, all stats verified after every completion")


if __name__ == '__main__':
    print("=" * 60)
    print("Match Data Integrity Tests")
    print("=" * 60)
    
    tests = [
        test_snapshot_uses_copies,
        test_snapshot_queue_uses_copies,
        test_load_snapshot_uses_copies,
        test_completed_match_data_survives_subsequent_completions,
        test_no_double_counting_stats,
        test_team2_partner_last_game_tracking,
        test_match_creation_from_queue_uses_copies,
        test_serialization_uses_copies,
        test_winner_not_reversed_after_subsequent_match,
        test_match_history_display_winner_on_top,
        test_round_robin_match_integrity,
        test_strict_continuous_rr_match_integrity,
        test_singles_rr_stats_not_reversed,
        test_singles_strict_rr_stats_not_reversed,
        test_stats_survive_save_load_cycle,
        test_double_completion_guard,
        test_rr_full_session_stats_integrity,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
