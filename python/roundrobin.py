"""
Round Robin matchmaking engine - maximizes partner and opponent diversity
"""

from typing import List, Dict, Tuple, Optional, Set
from itertools import combinations
from .pickleball_types import Player, PlayerStats, Match, QueuedMatch, SessionType
from .utils import is_pair_banned, generate_combinations


def generate_round_robin_queue(
    players: List[Player],
    session_type: SessionType,
    banned_pairs: List[Tuple[str, str]],
    max_matches: int = 100,
    locked_teams: Optional[List[List[str]]] = None,
    player_stats: Optional[Dict[str, PlayerStats]] = None,
    active_matches: Optional[List] = None,
    first_bye_players: Optional[List[str]] = None
) -> List[QueuedMatch]:
    """
    Generate a queue of round-robin matches optimized for partner and opponent diversity.
    
    Round Robin Strategy:
    - Maximize different partners each player plays with
    - Maximize different opponents each player faces
    - Respect banned pairs
    - Spread play time fairly
    - Never repeat the exact same 4-player combination if possible
    - Never queue matches currently being played
    - Respect first bye players (exclude them from initial matches)
    
    Args:
        players: List of Player objects
        session_type: 'singles' or 'doubles'
        banned_pairs: List of banned player pairs
        max_matches: Maximum matches to generate
        locked_teams: Pre-formed teams (if applicable)
        player_stats: Dict of player_id -> PlayerStats for session history
        active_matches: List of currently active Match objects to exclude from queue
        first_bye_players: List of player IDs to exclude from initial matches (first bye)
    """
    
    players_per_team = 1 if session_type == 'singles' else 2
    players_per_match = players_per_team * 2
    
    if len(players) < players_per_match:
        return []
    
    matches: List[QueuedMatch] = []
    player_ids = [p.id for p in players]
    
    # Track statistics for scoring
    partnership_count: Dict[str, Dict[str, int]] = {}
    opponent_count: Dict[str, Dict[str, int]] = {}
    four_player_group_count: Dict[str, int] = {}
    games_played: Dict[str, int] = {}
    used_matchups: Set[str] = set()
    
    # Calculate total games from session history (not from queue being generated)
    session_games_total = 0
    if player_stats:
        # Use average games played across all players as proxy for session progress
        for pid in player_ids:
            if pid in player_stats:
                session_games_total += player_stats[pid].games_played
        session_games_total = session_games_total // len(player_ids) if len(player_ids) > 0 else 0
    
    # Determine if first bye should be applied
    first_bye_players_set = set()
    apply_first_bye = first_bye_players and session_games_total == 0
    if apply_first_bye:
        first_bye_players_set = set(first_bye_players)
    
    # Pre-populate used_matchups with currently active matches
    if active_matches:
        for match in active_matches:
            if match.status in ['waiting', 'in-progress']:
                t1_sorted = ','.join(sorted(match.team1))
                t2_sorted = ','.join(sorted(match.team2))
                matchup_key = '|'.join(sorted([t1_sorted, t2_sorted]))
                used_matchups.add(matchup_key)
    
    for pid in player_ids:
        partnership_count[pid] = {}
        opponent_count[pid] = {}
        
        # Initialize from player_stats if provided
        if player_stats and pid in player_stats:
            stats = player_stats[pid]
            games_played[pid] = stats.games_played
            
            # Pre-populate partnerships from session history
            if isinstance(stats.partners_played, dict):
                for partner_id, count in stats.partners_played.items():
                    partnership_count[pid][partner_id] = partnership_count[pid].get(partner_id, 0) + count
            else:
                # Fallback for legacy sets
                for partner_id in stats.partners_played:
                    partnership_count[pid][partner_id] = partnership_count[pid].get(partner_id, 0) + 1
            
            # Pre-populate opponents from session history
            if isinstance(stats.opponents_played, dict):
                for opponent_id, count in stats.opponents_played.items():
                    opponent_count[pid][opponent_id] = opponent_count[pid].get(opponent_id, 0) + count
            else:
                # Fallback for legacy sets
                for opponent_id in stats.opponents_played:
                    opponent_count[pid][opponent_id] = opponent_count[pid].get(opponent_id, 0) + 1
        else:
            games_played[pid] = 0
    
    def get_matchup_key(team1: List[str], team2: List[str]) -> str:
        """Create a canonical key for a matchup"""
        sorted_t1 = ','.join(sorted(team1))
        sorted_t2 = ','.join(sorted(team2))
        return '|'.join(sorted([sorted_t1, sorted_t2]))
    
    def get_four_player_key(team1: List[str], team2: List[str]) -> str:
        """Create a key for the 4-player group"""
        return ','.join(sorted(team1 + team2))
    
    def is_valid_team_configuration(team1: List[str], team2: List[str]) -> bool:
        """Check if team configuration respects banned pairs and locked teams"""
        # Check Locked Teams
        if locked_teams and session_type == 'doubles':
            for team in locked_teams:
                # Check team1
                members_in_team1 = [p for p in team if p in team1]
                if members_in_team1:
                    # If any member is present, ALL must be present
                    if len(members_in_team1) != len(team):
                        return False
                
                # Check team2
                members_in_team2 = [p for p in team if p in team2]
                if members_in_team2:
                    # If any member is present, ALL must be present
                    if len(members_in_team2) != len(team):
                        return False
        
        # Check team1 for banned pairs
        for i in range(len(team1)):
            for j in range(i + 1, len(team1)):
                if is_pair_banned(team1[i], team1[j], banned_pairs):
                    return False
        
        # Check team2 for banned pairs
        for i in range(len(team2)):
            for j in range(i + 1, len(team2)):
                if is_pair_banned(team2[i], team2[j], banned_pairs):
                    return False
        
        return True
    
    def calculate_allowed_repetitions(num_players: int, total_games: int) -> int:
        """
        Calculate how many times players can repeat a partnership/opponent pairing
        based on session progress (total games played and player count).
        
        Logic:
        - Early in session (few games): strict uniqueness (allow 0 repetitions)
        - As games progress: gradually allow more repetition
        - Based on how many times we've "cycled through" all possible pairs
        
        Approach:
        - With N players, there are C(N,2) possible pairs
        - Each game creates ~2 pairs (one per team in doubles)
        - Expected pair appearances = (total_games * 2) / C(N,2)
        - We allow repetitions once expected appearances > threshold
        
        Examples:
        - 4 players, 10 games: 20 pair-slots / 6 possible pairs ~= 3.3 appearances per pair
          -> Allow ~2 repetitions (we should allow 3 to unblock 4-player sessions)
        - 6 players, 20 games: 40 pair-slots / 15 possible pairs ~= 2.7 appearances per pair
          -> Allow ~2 repetitions
        - 8 players, 40 games: 80 pair-slots / 28 possible pairs ~= 2.9 appearances per pair
          -> Allow ~2 repetitions
        """
        if num_players < 4:
            return 0
        
        # Calculate number of possible unique pairs
        num_pairs = (num_players * (num_players - 1)) // 2
        
        # In each match (2v2), we create approximately 2 new pairs
        # (1 on each team, though some might repeat)
        pair_slots_used = total_games * 2
        
        # Expected appearances of an average pair
        expected_appearances = pair_slots_used / num_pairs if num_pairs > 0 else 0
        
        # Allow repetitions based on how many cycles we've completed
        # For small player pools, we allow more repetitions faster
        # For large player pools, we stay strict longer
        
        # Threshold scaling: smaller pools get LOWER thresholds (more permissive)
        # Divide by pool_divisor to make small pools more permissive
        # At 12 players: divisor = 1.0, at 6 players: divisor = 1.5, at 4 players: divisor = 3.0
        pool_divisor = 12.0 / num_players
        
        threshold_1 = 1.5 / pool_divisor
        threshold_2 = 2.5 / pool_divisor
        threshold_3 = 3.5 / pool_divisor
        threshold_4 = 4.5 / pool_divisor
        
        if expected_appearances < threshold_1:
            return 0
        elif expected_appearances < threshold_2:
            return 1
        elif expected_appearances < threshold_3:
            return 2
        elif expected_appearances < threshold_4:
            return 3
        else:
            return 4
    
    def score_matchup(team1: List[str], team2: List[str]) -> float:
        """Score a potential matchup for quality"""
        matchup_key = get_matchup_key(team1, team2)
        
        # Already used this exact matchup
        if matchup_key in used_matchups:
            return -1
        
        # Invalid configuration
        if not is_valid_team_configuration(team1, team2):
            return -1
        
        # Calculate dynamic threshold based on session history (not current queue)
        allowed_reps = calculate_allowed_repetitions(len(player_ids), session_games_total)
        
        score = 1000.0
        
        # Boost: new partnerships (players who haven't played together)
        for player_id in team1:
            for teammate_id in team1:
                if player_id != teammate_id:
                    if teammate_id not in partnership_count.get(player_id, {}):
                        score += 100
        
        for player_id in team2:
            for teammate_id in team2:
                if player_id != teammate_id:
                    if teammate_id not in partnership_count.get(player_id, {}):
                        score += 100
        
        # Penalty: repeated partnerships (apply dynamic threshold)
        for player_id in team1:
            for teammate_id in team1:
                if player_id != teammate_id:
                    count = partnership_count.get(player_id, {}).get(teammate_id, 0)
                    if count > allowed_reps:
                        score -= 2000  # Hard lock: force negative score
                    elif count > 0:
                        score -= 100  # Soft penalty for repetition within threshold
        
        for player_id in team2:
            for teammate_id in team2:
                if player_id != teammate_id:
                    count = partnership_count.get(player_id, {}).get(teammate_id, 0)
                    if count > allowed_reps:
                        score -= 2000  # Hard lock: force negative score
                    elif count > 0:
                        score -= 100  # Soft penalty for repetition within threshold
        
        # Boost: new opponents
        for p1 in team1:
            for p2 in team2:
                if p2 not in opponent_count.get(p1, {}):
                    score += 20
        
        # Penalty: repeated opponents (apply dynamic threshold)
        for p1 in team1:
            for p2 in team2:
                count = opponent_count.get(p1, {}).get(p2, 0)
                if count > allowed_reps:
                    score -= 2000  # Hard lock on opponent repetition too
                elif count > 0:
                    score -= 50  # Soft penalty for opponent repetition within threshold
        
        # Penalty: same 4-player group played recently (use dynamic threshold)
        four_key = get_four_player_key(team1, team2)
        group_count = four_player_group_count.get(four_key, 0)
        if group_count > allowed_reps:
            score -= 2000  # Hard lock same group
        elif group_count > 0:
            score -= 500  # Soft penalty for group repetition within threshold
        
        # Fair play: boost players with fewer games
        for player_id in team1 + team2:
            if games_played[player_id] < len(matches) // len(player_ids):
                score += 30
        
        return score
    
    # Generate all possible combinations
    all_combinations = generate_combinations(player_ids, players_per_match)
    
    # Convert to all possible team configurations
    all_matchups: List[Tuple[List[str], List[str]]] = []
    
    for combo in all_combinations:
        if players_per_team == 2:
            partitions = [
                ([combo[0], combo[1]], [combo[2], combo[3]]),
                ([combo[0], combo[2]], [combo[1], combo[3]]),
                ([combo[0], combo[3]], [combo[1], combo[2]]),
            ]
            all_matchups.extend(partitions)
        else:
            all_matchups.append(([combo[0]], [combo[1]]))
    
    iterations = 0
    max_iterations = len(all_matchups) * 10
    used_players_this_round: Set[str] = set()
    
    while iterations < max_iterations and len(matches) < max_matches:
        # Score all remaining matchups, excluding players already in this iteration
        scored = []
        
        for team1, team2 in all_matchups:
            # Skip if any player is already scheduled in this round
            all_players_in_matchup = set(team1 + team2)
            if all_players_in_matchup & used_players_this_round:
                continue
            
            score = score_matchup(team1, team2)
            if score >= 0:
                scored.append((score, team1, team2))
        
        if not scored:
            # No more valid matchups this round - reset for next round
            used_players_this_round.clear()
            
            # Try to find any valid matchup for next round
            scored = []
            for team1, team2 in all_matchups:
                score = score_matchup(team1, team2)
                if score >= 0:
                    scored.append((score, team1, team2))
            
            if not scored:
                break
        
        # Pick best matchup
        scored.sort(reverse=True, key=lambda x: x[0])
        _, best_team1, best_team2 = scored[0]
        
        # Add to results
        matches.append(QueuedMatch(team1=best_team1, team2=best_team2))
        matchup_key = get_matchup_key(best_team1, best_team2)
        used_matchups.add(matchup_key)
        
        # Track players used in this round
        used_players_this_round.update(best_team1)
        used_players_this_round.update(best_team2)
        
        # Update tracking
        for player_id in best_team1:
            for teammate_id in best_team1:
                if player_id != teammate_id:
                    partnership_count[player_id][teammate_id] = partnership_count[player_id].get(teammate_id, 0) + 1
            games_played[player_id] += 1
            for opponent_id in best_team2:
                opponent_count[player_id][opponent_id] = opponent_count[player_id].get(opponent_id, 0) + 1
        
        for player_id in best_team2:
            for teammate_id in best_team2:
                if player_id != teammate_id:
                    partnership_count[player_id][teammate_id] = partnership_count[player_id].get(teammate_id, 0) + 1
            games_played[player_id] += 1
            for opponent_id in best_team1:
                opponent_count[player_id][opponent_id] = opponent_count[player_id].get(opponent_id, 0) + 1
        
        four_key = get_four_player_key(best_team1, best_team2)
        four_player_group_count[four_key] = four_player_group_count.get(four_key, 0) + 1
        
        # Check if we can fit more matches in this round
        unused_players = set(player_ids) - used_players_this_round
        if len(unused_players) < players_per_match:
            # Not enough unused players for another match - reset for next round
            used_players_this_round.clear()
        
        iterations += 1
    
    # Apply first bye filtering: remove matches involving first bye players from the START of the queue
    # but keep them for later rounds (they should appear later in the queue)
    if apply_first_bye and first_bye_players_set:
        filtered_matches = []
        first_round_matches = []
        
        # Separate first round matches (those that don't involve first bye players)
        # and later round matches (those that do involve first bye players)
        for match in matches:
            match_players = set(match.team1 + match.team2)
            if match_players & first_bye_players_set:  # Match involves first bye players
                # Keep for later rounds
                filtered_matches.append(match)
            else:
                # Can be in first round
                first_round_matches.append(match)
        
        # Put first round matches at the beginning, then later round matches
        matches = first_round_matches + filtered_matches
    
    return matches


def _generate_locked_teams_round_robin_queue(
    locked_teams: List[List[str]],
    max_matches: int = 100
) -> List[QueuedMatch]:
    """
    Generate round-robin matches for locked teams mode.
    Teams stay together, only opponents change.
    """
    matches: List[QueuedMatch] = []
    
    # Each locked team is a unit (one or two players)
    team_indices = list(range(len(locked_teams)))
    used_pairings: Set[Tuple[int, int]] = set()
    
    while len(matches) < max_matches:
        # Find the best unused pairing
        best_pairing = None
        
        for i in range(len(team_indices)):
            for j in range(i + 1, len(team_indices)):
                idx1, idx2 = team_indices[i], team_indices[j]
                pairing = (min(idx1, idx2), max(idx1, idx2))
                
                if pairing not in used_pairings:
                    best_pairing = pairing
                    break
            
            if best_pairing:
                break
        
        if not best_pairing:
            break
        
        matches.append(QueuedMatch(
            team1=locked_teams[best_pairing[0]],
            team2=locked_teams[best_pairing[1]]
        ))
        used_pairings.add(best_pairing)
    
    return matches
