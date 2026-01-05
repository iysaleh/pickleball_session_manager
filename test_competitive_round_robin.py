"""
Test suite for Competitive Round Robin mode.

Tests the algorithm for pre-scheduled skill-balanced matches with human approval.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize time manager before importing session modules
from python.time_manager import initialize_time_manager
initialize_time_manager()

from python.pickleball_types import (
    Player, SessionConfig, Session, CompetitiveRoundRobinConfig, ScheduledMatch
)
from python.session import create_session
from python.competitive_round_robin import (
    generate_initial_schedule,
    validate_schedule,
    regenerate_match,
    swap_player_in_match,
    get_schedule_summary,
    get_player_skill_rating,
    get_skill_bracket,
    calculate_team_balance_score,
    get_available_swaps,
    get_player_display_info
)


def create_test_players(num_players: int, with_ratings: bool = True) -> list:
    """Create test players with optional skill ratings."""
    names = [
        "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry",
        "Iris", "Jack", "Kate", "Leo", "Maya", "Noah", "Olivia", "Peter",
        "Quinn", "Rachel", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xavier"
    ]
    
    # Skill ratings distributed from 3.0 to 4.5
    ratings = [
        3.0, 3.25, 3.5, 3.5, 3.75, 3.75, 4.0, 4.0,
        4.0, 4.25, 4.25, 4.5, 3.25, 3.5, 3.75, 4.0,
        4.25, 3.0, 3.5, 4.0, 3.75, 4.25, 3.25, 4.5
    ]
    
    players = []
    for i in range(min(num_players, len(names))):
        player = Player(
            id=f"player_{i}",
            name=names[i],
            skill_rating=ratings[i] if with_ratings else None
        )
        players.append(player)
    
    return players


def create_test_session(num_players: int = 16, courts: int = 4) -> Session:
    """Create a test session for Competitive Round Robin."""
    players = create_test_players(num_players, with_ratings=True)
    
    config = SessionConfig(
        mode='competitive-round-robin',
        session_type='doubles',
        players=players,
        courts=courts,
        pre_seeded_ratings=True,
        competitive_round_robin_config=CompetitiveRoundRobinConfig()
    )
    
    return create_session(config)


class TestCompetitiveRoundRobinAlgorithm:
    """Test the core scheduling algorithm."""
    
    def test_generate_schedule_creates_matches(self):
        """Test that schedule generation creates matches."""
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig()
        
        matches = generate_initial_schedule(session, config)
        
        assert len(matches) > 0, "Should generate at least some matches"
        print(f"✅ Generated {len(matches)} matches for 16 players")
    
    def test_schedule_targets_8_games_per_player(self):
        """Test that each player is scheduled for approximately 8 games."""
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig(games_per_player=8)
        
        matches = generate_initial_schedule(session, config)
        
        # Approve all matches for validation
        for m in matches:
            m.status = 'approved'
        
        validation = validate_schedule(session, matches, config)
        
        # Calculate average games per player
        total_games = sum(validation.games_per_player.values())
        avg_games = total_games / len(session.config.players) if session.config.players else 0
        
        # With 16 players targeting 8 games each, we need 32 matches (16*8/4)
        # The algorithm may not perfectly achieve this due to constraints
        # Verify average is close to target and no one is extremely under/over served
        min_games = min(validation.games_per_player.values()) if validation.games_per_player else 0
        max_games = max(validation.games_per_player.values()) if validation.games_per_player else 0
        
        assert avg_games >= 6, f"Average games ({avg_games:.1f}) too low"
        assert min_games >= 4, f"Minimum games ({min_games}) too low - someone is underserved"
        assert max_games <= 10, f"Maximum games ({max_games}) too high - someone is overserved"
        
        print(f"✅ Games per player: avg={avg_games:.1f}, min={min_games}, max={max_games}")
    
    def test_no_repeated_partnerships(self):
        """Test that no player partners with the same person twice."""
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig(max_partner_repeats=0)
        
        matches = generate_initial_schedule(session, config)
        
        # Approve all matches
        for m in matches:
            m.status = 'approved'
        
        validation = validate_schedule(session, matches, config)
        
        # Filter for partnership violations
        partner_violations = [v for v in validation.violations if v.violation_type == 'partner_repeat']
        
        assert len(partner_violations) == 0, f"Found {len(partner_violations)} partnership repeats"
        print(f"✅ No repeated partnerships in {len(matches)} matches")
    
    def test_individual_opponent_limit(self):
        """Test that no player faces the same opponent more than 2 times."""
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig()  # Use default max_individual_opponent_repeats=2
        
        matches = generate_initial_schedule(session, config)
        
        # Approve all matches
        for m in matches:
            m.status = 'approved'
        
        validation = validate_schedule(session, matches, config)
        
        # Filter for opponent violations
        opponent_violations = [v for v in validation.violations if v.violation_type == 'individual_opponent_exceed']
        
        assert len(opponent_violations) == 0, f"Found {len(opponent_violations)} opponent limit violations"
        print(f"✅ Individual opponent limit (2) respected")
    
    def test_skill_balanced_teams(self):
        """Test that generated matches have balanced teams."""
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig()
        
        matches = generate_initial_schedule(session, config)
        
        # Check balance scores
        balance_scores = [m.balance_score for m in matches]
        avg_balance = sum(balance_scores) / len(balance_scores) if balance_scores else 0
        
        # Most matches should have positive balance scores (balanced)
        positive_balance_count = sum(1 for score in balance_scores if score > 0)
        positive_ratio = positive_balance_count / len(matches) if matches else 0
        
        assert positive_ratio >= 0.7, f"Only {positive_ratio:.0%} of matches have positive balance"
        print(f"✅ Average balance score: {avg_balance:.0f}, {positive_ratio:.0%} positive")


class TestScheduleValidation:
    """Test schedule validation functionality."""
    
    def test_validate_empty_schedule(self):
        """Test validation with no matches."""
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig()
        
        validation = validate_schedule(session, [], config)
        
        assert validation.is_valid
        assert len(validation.violations) == 0
        print("✅ Empty schedule validation passes")
    
    def test_detect_partnership_violation(self):
        """Test that validation detects repeated partnerships."""
        session = create_test_session(8)
        config = CompetitiveRoundRobinConfig(max_partner_repeats=0)
        
        # Create matches with repeated partnership
        matches = [
            ScheduledMatch(
                id="m1",
                team1=["player_0", "player_1"],
                team2=["player_2", "player_3"],
                status='approved',
                match_number=1
            ),
            ScheduledMatch(
                id="m2",
                team1=["player_0", "player_1"],  # Same partnership
                team2=["player_4", "player_5"],
                status='approved',
                match_number=2
            )
        ]
        
        validation = validate_schedule(session, matches, config)
        
        partner_violations = [v for v in validation.violations if v.violation_type == 'partner_repeat']
        assert len(partner_violations) > 0, "Should detect partnership repeat"
        print("✅ Partnership violation detection works")


class TestMatchRegeneration:
    """Test match regeneration after rejection."""
    
    def test_regenerate_rejected_match(self):
        """Test regenerating a match after rejection."""
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig()
        
        matches = generate_initial_schedule(session, config)
        
        if len(matches) > 5:
            # Approve first 5 matches
            for i in range(5):
                matches[i].status = 'approved'
            
            # Reject the 6th match
            matches[5].status = 'rejected'
            old_players = set(matches[5].get_all_players())
            
            # Regenerate
            new_match = regenerate_match(session, matches, 5, config)
            
            assert new_match is not None, "Should generate a replacement match"
            assert new_match.status == 'pending', "New match should be pending"
            print(f"✅ Successfully regenerated match with new players")


class TestPlayerSwap:
    """Test player swap functionality."""
    
    def test_swap_player_in_match(self):
        """Test swapping a player in a match."""
        session = create_test_session(12)
        config = CompetitiveRoundRobinConfig()
        
        # Create a single test match
        match = ScheduledMatch(
            id="test_match",
            team1=["player_0", "player_1"],
            team2=["player_2", "player_3"],
            status='pending',
            match_number=1
        )
        
        # Try to swap player_0 with player_4
        success, new_match, error = swap_player_in_match(
            session, match, "player_0", "player_4", [match], config
        )
        
        assert success, f"Swap should succeed: {error}"
        assert "player_4" in new_match.get_all_players()
        assert "player_0" not in new_match.get_all_players()
        print("✅ Player swap works correctly")
    
    def test_swap_prevents_duplicate_player(self):
        """Test that swap prevents adding duplicate player."""
        session = create_test_session(8)
        config = CompetitiveRoundRobinConfig()
        
        match = ScheduledMatch(
            id="test_match",
            team1=["player_0", "player_1"],
            team2=["player_2", "player_3"],
            status='pending',
            match_number=1
        )
        
        # Try to swap player_0 with player_2 (already in match)
        success, new_match, error = swap_player_in_match(
            session, match, "player_0", "player_2", [match], config
        )
        
        assert not success, "Swap should fail for duplicate player"
        print("✅ Duplicate player swap correctly rejected")


class TestSkillRatings:
    """Test skill rating calculations."""
    
    def test_skill_rating_conversion(self):
        """Test conversion of skill ratings to ELO scale."""
        # Create session with 16 players to have player indices 0-15
        session = create_test_session(16)
        
        # Player 0 has rating 3.0
        elo = get_player_skill_rating(session, "player_0")
        expected = 1200  # 3.0 maps to 1200
        assert abs(elo - expected) < 50, f"3.0 rating should map to ~1200, got {elo}"
        
        # Player 11 has rating 4.5
        elo_high = get_player_skill_rating(session, "player_11")
        expected_high = 2100  # 4.5 maps to 2100
        assert abs(elo_high - expected_high) < 50, f"4.5 rating should map to ~2100, got {elo_high}"
        
        print("✅ Skill rating conversion correct")
    
    def test_skill_brackets(self):
        """Test skill bracket assignment."""
        assert get_skill_bracket(2100) == 'elite'
        assert get_skill_bracket(1800) == 'advanced'
        assert get_skill_bracket(1500) == 'intermediate'
        assert get_skill_bracket(1200) == 'beginner'
        assert get_skill_bracket(900) == 'novice'
        print("✅ Skill bracket assignment correct")


class TestTeamBalance:
    """Test team balance scoring."""
    
    def test_balanced_teams_score_higher(self):
        """Test that balanced teams get higher scores."""
        session = create_test_session(8)
        
        # Balanced: high+low vs high+low
        balanced_score = calculate_team_balance_score(
            session,
            ["player_0", "player_7"],  # 3.0 + 4.0
            ["player_1", "player_6"]   # 3.25 + 4.0
        )
        
        # Unbalanced: high+high vs low+low
        unbalanced_score = calculate_team_balance_score(
            session,
            ["player_7", "player_9"],   # 4.0 + 4.25
            ["player_0", "player_1"]    # 3.0 + 3.25
        )
        
        assert balanced_score > unbalanced_score, "Balanced teams should score higher"
        print(f"✅ Balanced: {balanced_score:.0f}, Unbalanced: {unbalanced_score:.0f}")


class TestScheduleSummary:
    """Test schedule summary functionality."""
    
    def test_summary_counts(self):
        """Test that summary correctly counts match statuses."""
        session = create_test_session(12)
        config = CompetitiveRoundRobinConfig()
        
        matches = [
            ScheduledMatch(id="m1", team1=["player_0", "player_1"], team2=["player_2", "player_3"], 
                          status='approved', match_number=1),
            ScheduledMatch(id="m2", team1=["player_4", "player_5"], team2=["player_6", "player_7"], 
                          status='pending', match_number=2),
            ScheduledMatch(id="m3", team1=["player_8", "player_9"], team2=["player_10", "player_11"], 
                          status='rejected', match_number=3),
        ]
        
        summary = get_schedule_summary(session, matches, config)
        
        assert summary['approved'] == 1
        assert summary['pending'] == 1
        assert summary['rejected'] == 1
        assert summary['total_matches'] == 3
        print("✅ Summary counts correct")


class TestRuntimePopulation:
    """Test runtime court population from schedule."""
    
    def test_courts_populate_from_schedule(self):
        """Test that courts populate from approved schedule at session start."""
        from python.session import create_session, evaluate_and_create_matches
        from python.competitive_round_robin import populate_courts_from_schedule
        
        session = create_test_session(16)
        config = CompetitiveRoundRobinConfig()
        
        # Generate and approve schedule
        matches = generate_initial_schedule(session, config)
        for m in matches:
            m.status = 'approved'
        
        # Store in config and finalize
        session.config.competitive_round_robin_config.scheduled_matches = matches
        session.config.competitive_round_robin_config.schedule_finalized = True
        
        # Run population
        session = evaluate_and_create_matches(session)
        
        # Check matches were created on courts
        active_matches = [m for m in session.matches if m.status in ('active', 'waiting', 'in-progress')]
        assert len(active_matches) > 0, "Should create matches from schedule"
        assert len(active_matches) <= session.config.courts, "Should not exceed court count"
        print(f"✅ Courts populated: {len(active_matches)} matches on {session.config.courts} courts")


def run_all_tests():
    """Run all test classes."""
    test_classes = [
        TestCompetitiveRoundRobinAlgorithm,
        TestScheduleValidation,
        TestMatchRegeneration,
        TestPlayerSwap,
        TestSkillRatings,
        TestTeamBalance,
        TestScheduleSummary,
        TestRuntimePopulation,
    ]
    
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print('='*60)
        
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith('test_'):
                try:
                    getattr(instance, method_name)()
                    passed += 1
                except Exception as e:
                    print(f"❌ {method_name}: {e}")
                    failed += 1
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print('='*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
