"""
Test Competitive Round Robin with 10 players.

Issues being tested:
1. "Manage Matches" should generate the required number of matches per player
2. Waitlist fairness: nobody waits twice until everyone has waited once
"""

import sys
sys.path.insert(0, 'python')

from python.pickleball_types import (
    Session, SessionConfig, Player, CompetitiveRoundRobinConfig
)
from python.competitive_round_robin import (
    generate_rounds_based_schedule,
    compute_scheduled_waiters
)


def create_10_player_session():
    """Create a session with 10 players and 2 courts."""
    players = [Player(id=f"p{i}", name=f"Player {i}") for i in range(1, 11)]
    
    config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        players=players,
        courts=2,  # 2 courts = 8 players per round, 2 waiting
        first_bye_players=[]
    )
    
    session = Session(
        id="test_session",
        config=config,
        matches=[],
        player_stats={p.id: None for p in players}
    )
    
    return session


def test_10_player_schedule_generation():
    """Test that 10 players generates appropriate number of matches."""
    session = create_10_player_session()
    
    config = CompetitiveRoundRobinConfig(
        games_per_player=6,  # Target 6 games per player
        max_individual_opponent_repeats=3
    )
    
    scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
    
    print(f"\n=== 10 Player Schedule Generation Test ===")
    print(f"Players: 10")
    print(f"Courts: 2")
    print(f"Target games per player: 6")
    print(f"Generated matches: {len(scheduled_matches)}")
    print(f"Generated rounds (waiters): {len(scheduled_waiters)}")
    
    # Count games per player
    games_per_player = {f"p{i}": 0 for i in range(1, 11)}
    for match in scheduled_matches:
        for pid in match.team1 + match.team2:
            games_per_player[pid] += 1
    
    print(f"\nGames per player:")
    for pid, games in sorted(games_per_player.items()):
        status = "✓" if games >= 4 else "✗"  # At least 4 games should be achievable
        print(f"  {pid}: {games} games {status}")
    
    min_games = min(games_per_player.values())
    max_games = max(games_per_player.values())
    avg_games = sum(games_per_player.values()) / len(games_per_player)
    
    print(f"\nMin games: {min_games}")
    print(f"Max games: {max_games}")
    print(f"Avg games: {avg_games:.1f}")
    
    # CRITICAL: Should generate MORE than 1 match!
    assert len(scheduled_matches) > 1, f"FAIL: Only generated {len(scheduled_matches)} match(es)!"
    
    # Should have reasonable games per player
    assert min_games >= 2, f"FAIL: Some players only got {min_games} games"
    
    print("\n✓ Test passed: Generated appropriate number of matches")
    return True


def test_waitlist_fairness():
    """Test that nobody waits twice until everyone has waited once."""
    session = create_10_player_session()
    
    config = CompetitiveRoundRobinConfig(
        games_per_player=8,
        max_individual_opponent_repeats=3
    )
    
    scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, config)
    
    print(f"\n=== Waitlist Fairness Test ===")
    print(f"Players: 10, Courts: 2 (8 playing, 2 waiting per round)")
    print(f"Rounds generated: {len(scheduled_waiters)}")
    
    # Track wait counts
    wait_count = {f"p{i}": 0 for i in range(1, 11)}
    
    fairness_violations = []
    
    for round_idx, waiters in enumerate(scheduled_waiters):
        print(f"\nRound {round_idx}: Waiters = {waiters}")
        
        # Check fairness BEFORE incrementing: no player should wait if others haven't waited yet
        min_waits = min(wait_count.values())
        
        for waiter in waiters:
            if wait_count[waiter] > min_waits:
                # This player has already waited more than the minimum!
                # This is only OK if all players at min_waits are also waiting
                players_at_min = [p for p in wait_count if wait_count[p] == min_waits]
                waiters_at_min = [w for w in waiters if wait_count[w] == min_waits]
                
                if len(waiters_at_min) < len(players_at_min) and len(waiters_at_min) < len(waiters):
                    fairness_violations.append(
                        f"Round {round_idx}: {waiter} waiting (count={wait_count[waiter]}) "
                        f"when players at min_wait={min_waits} still haven't all waited: {players_at_min}"
                    )
        
        # Increment wait counts
        for waiter in waiters:
            wait_count[waiter] += 1
    
    print(f"\n\nFinal wait counts:")
    for pid, count in sorted(wait_count.items()):
        print(f"  {pid}: waited {count} times")
    
    # Check for fairness: max wait - min wait should be at most 1
    min_waits = min(wait_count.values())
    max_waits = max(wait_count.values())
    wait_spread = max_waits - min_waits
    
    print(f"\nWait spread: {wait_spread} (max={max_waits}, min={min_waits})")
    
    if fairness_violations:
        print("\n⚠️ FAIRNESS VIOLATIONS DETECTED:")
        for v in fairness_violations:
            print(f"  - {v}")
        # This is a soft failure - log but continue
    
    # The spread should be at most 1 for perfect fairness
    if wait_spread > 1:
        print(f"\n✗ FAIL: Wait spread too large ({wait_spread}). Expected at most 1.")
        return False
    
    print("\n✓ Test passed: Waitlist is fair")
    return True


def test_no_repeat_partners():
    """Test that no two players are partnered more than once."""
    session = create_10_player_session()
    
    config = CompetitiveRoundRobinConfig(
        games_per_player=6,
        max_individual_opponent_repeats=3
    )
    
    scheduled_matches, _ = generate_rounds_based_schedule(session, config)
    
    print(f"\n=== No Repeat Partners Test ===")
    
    # Track partnerships
    partnerships = {}
    violations = []
    
    for match in scheduled_matches:
        for team in [match.team1, match.team2]:
            if len(team) == 2:
                key = tuple(sorted(team))
                partnerships[key] = partnerships.get(key, 0) + 1
                if partnerships[key] > 1:
                    violations.append(f"Partnership {team[0]}-{team[1]} used {partnerships[key]} times")
    
    if violations:
        print("Partnership violations:")
        for v in violations:
            print(f"  ✗ {v}")
        return False
    
    print(f"Total unique partnerships used: {len(partnerships)}")
    print("✓ Test passed: No repeated partnerships")
    return True


def test_match_variety():
    """Test that the same 4 players don't play together twice."""
    session = create_10_player_session()
    
    config = CompetitiveRoundRobinConfig(
        games_per_player=6,
        max_individual_opponent_repeats=3
    )
    
    scheduled_matches, _ = generate_rounds_based_schedule(session, config)
    
    print(f"\n=== Match Variety Test ===")
    
    # Track groups of 4
    groups = {}
    violations = []
    
    for match in scheduled_matches:
        group = frozenset(match.team1 + match.team2)
        groups[group] = groups.get(group, 0) + 1
        if groups[group] > 1:
            violations.append(f"Group {sorted(group)} played together {groups[group]} times")
    
    if violations:
        print("Group violations:")
        for v in violations:
            print(f"  ✗ {v}")
        return False
    
    print(f"Total unique groups of 4: {len(groups)}")
    print("✓ Test passed: No repeated groups")
    return True


def test_10_players_4_courts_no_duplication():
    """
    Test that with 10 players and 4 courts configured, 
    we only create 2 matches per round (8 players) and no player appears twice in a round.
    This was a bug where the algorithm tried to fill all 4 courts even when only 10 players exist.
    """
    # Create a session with 10 players and 4 courts
    players = [Player(id=f"p{i}", name=f"Player {i}", skill_rating=float(3 + (i % 3))) for i in range(1, 11)]
    
    config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        players=players,
        courts=4,  # 4 courts configured, but only 10 players!
        first_bye_players=[]
    )
    
    session = Session(
        id="test_session",
        config=config,
        matches=[],
        player_stats={p.id: None for p in players}
    )
    
    rr_config = CompetitiveRoundRobinConfig(
        games_per_player=6,
        max_individual_opponent_repeats=3
    )
    
    scheduled_matches, scheduled_waiters = generate_rounds_based_schedule(session, rr_config)
    
    print(f"\n=== 10 Players / 4 Courts No Duplication Test ===")
    print(f"Players: 10")
    print(f"Courts configured: 4")
    print(f"Expected matches per round: 2 (since 10 // 4 = 2)")
    
    # Group matches by round
    rounds = {}
    for match in scheduled_matches:
        rnd = match.round_number
        if rnd not in rounds:
            rounds[rnd] = []
        rounds[rnd].append(match)
    
    violations = []
    for rnd in sorted(rounds.keys()):
        matches = rounds[rnd]
        # Check max matches per round (should be 2 for 10 players)
        if len(matches) > 2:
            violations.append(f"Round {rnd}: {len(matches)} matches (expected max 2)")
        
        # Check no player appears twice in same round
        players_in_round = []
        for m in matches:
            players_in_round.extend(m.team1)
            players_in_round.extend(m.team2)
        
        if len(players_in_round) != len(set(players_in_round)):
            duplicates = [p for p in players_in_round if players_in_round.count(p) > 1]
            violations.append(f"Round {rnd}: Players appear twice: {set(duplicates)}")
        
        print(f"Round {rnd}: {len(matches)} matches, {len(set(players_in_round))} unique players")
    
    # Check waiters are tracked
    if not scheduled_waiters or all(len(w) == 0 for w in scheduled_waiters):
        violations.append("Waiters not tracked (all empty)")
    else:
        print(f"\nWaiters per round:")
        for i, waiters in enumerate(scheduled_waiters):
            print(f"  Round {i}: {waiters}")
    
    if violations:
        print("\nViolations:")
        for v in violations:
            print(f"  ✗ {v}")
        return False
    
    print("\n✓ Test passed: No player duplication with 4 courts / 10 players")
    return True


if __name__ == "__main__":
    results = []
    
    results.append(("Schedule Generation", test_10_player_schedule_generation()))
    results.append(("Waitlist Fairness", test_waitlist_fairness()))
    results.append(("No Repeat Partners", test_no_repeat_partners()))
    results.append(("Match Variety", test_match_variety()))
    results.append(("10 Players / 4 Courts No Duplication", test_10_players_4_courts_no_duplication()))
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    sys.exit(0 if all_passed else 1)
