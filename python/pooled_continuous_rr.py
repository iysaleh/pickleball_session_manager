"""
Pooled Continuous Round Robin with Crossover Algorithm

This module implements a pool-based round robin tournament where:
- Players are divided into pools (minimum 2)
- Within each pool, everyone plays everyone once
- After all pools complete, crossover matches happen (rank vs rank)
- Courts can be dedicated to specific pools
- Match selection prioritizes players with fewest games for balanced completion
"""

from typing import List, Dict, Tuple, Optional, Set
from itertools import combinations
import random
import uuid

from .pickleball_types import (
    Session, Player, Match, PooledMatch, PooledContinuousRRConfig,
    SessionType, MatchStatus
)


def initialize_pools(session: Session, num_pools: int = 2) -> Dict[str, List[str]]:
    """
    Initialize pools by randomly distributing players evenly.
    
    Args:
        session: The session with players
        num_pools: Number of pools to create (default 2)
    
    Returns:
        Dict mapping pool_id to list of player_ids
    """
    player_ids = [p.id for p in session.config.players if p.id in session.active_players]
    random.shuffle(player_ids)
    
    pools: Dict[str, List[str]] = {}
    for i in range(num_pools):
        pool_id = f"Pool {i + 1}"
        pools[pool_id] = []
    
    # Distribute players round-robin style across pools
    pool_ids = list(pools.keys())
    for idx, player_id in enumerate(player_ids):
        pool_idx = idx % num_pools
        pools[pool_ids[pool_idx]].append(player_id)
    
    return pools


def redistribute_pools(pools: Dict[str, List[str]], num_pools: int) -> Dict[str, List[str]]:
    """
    Redistribute all players across a different number of pools.
    
    Args:
        pools: Current pool assignments
        num_pools: New number of pools
    
    Returns:
        New pool assignments
    """
    # Collect all players
    all_players = []
    for player_list in pools.values():
        all_players.extend(player_list)
    
    random.shuffle(all_players)
    
    # Create new pools
    new_pools: Dict[str, List[str]] = {}
    for i in range(num_pools):
        pool_id = f"Pool {i + 1}"
        new_pools[pool_id] = []
    
    # Distribute players
    pool_ids = list(new_pools.keys())
    for idx, player_id in enumerate(all_players):
        pool_idx = idx % num_pools
        new_pools[pool_ids[pool_idx]].append(player_id)
    
    return new_pools


def generate_pool_round_robin_matches(
    session: Session,
    pool_id: str,
    player_ids: List[str]
) -> List[PooledMatch]:
    """
    Generate round-robin matches for a single pool.
    In singles: everyone plays everyone once.
    In doubles: generate all possible team combinations where everyone plays everyone.
    
    Args:
        session: The session
        pool_id: ID of this pool
        player_ids: Players in this pool
    
    Returns:
        List of PooledMatch objects for this pool
    """
    matches: List[PooledMatch] = []
    session_type = session.config.session_type
    
    if session_type == 'singles':
        # Singles: each player plays every other player once
        for i, p1 in enumerate(player_ids):
            for p2 in player_ids[i + 1:]:
                match = PooledMatch(
                    id=f"pool_{pool_id}_{uuid.uuid4().hex[:8]}",
                    team1=[p1],
                    team2=[p2],
                    status='pending',
                    match_number=len(matches) + 1,
                    pool_id=pool_id,
                    is_crossover=False
                )
                matches.append(match)
    else:
        # Doubles: need to ensure everyone plays with and against everyone
        # Strategy: Generate all possible 4-player combinations, 
        # then for each, pick best team split
        if len(player_ids) < 4:
            return matches
        
        # Track partnerships and opponents to ensure variety
        partnership_count: Dict[str, Dict[str, int]] = {p: {} for p in player_ids}
        opponent_count: Dict[str, Dict[str, int]] = {p: {} for p in player_ids}
        used_matchups: Set[str] = set()
        
        def get_matchup_key(t1: List[str], t2: List[str]) -> str:
            s1 = ','.join(sorted(t1))
            s2 = ','.join(sorted(t2))
            return '|'.join(sorted([s1, s2]))
        
        def score_team_split(t1: List[str], t2: List[str]) -> float:
            """Score a team configuration (higher = better variety)"""
            score = 100.0
            
            # Penalize repeated partnerships
            for team in [t1, t2]:
                if len(team) == 2:
                    p1, p2 = team
                    count = partnership_count[p1].get(p2, 0)
                    score -= count * 50
            
            # Penalize repeated opponents
            for p1 in t1:
                for p2 in t2:
                    count = opponent_count[p1].get(p2, 0)
                    score -= count * 20
            
            return score
        
        # Generate all 4-player combinations
        all_combos = list(combinations(player_ids, 4))
        random.shuffle(all_combos)
        
        for combo in all_combos:
            # Try all 3 possible team splits
            splits = [
                ([combo[0], combo[1]], [combo[2], combo[3]]),
                ([combo[0], combo[2]], [combo[1], combo[3]]),
                ([combo[0], combo[3]], [combo[1], combo[2]]),
            ]
            
            best_split = None
            best_score = -float('inf')
            
            for t1, t2 in splits:
                key = get_matchup_key(t1, t2)
                if key in used_matchups:
                    continue
                score = score_team_split(t1, t2)
                if score > best_score:
                    best_score = score
                    best_split = (t1, t2)
            
            if best_split:
                t1, t2 = best_split
                
                match = PooledMatch(
                    id=f"pool_{pool_id}_{uuid.uuid4().hex[:8]}",
                    team1=list(t1),
                    team2=list(t2),
                    status='pending',
                    match_number=len(matches) + 1,
                    pool_id=pool_id,
                    is_crossover=False
                )
                matches.append(match)
                
                # Track for variety
                used_matchups.add(get_matchup_key(t1, t2))
                for p in t1:
                    for partner in t1:
                        if p != partner:
                            partnership_count[p][partner] = partnership_count[p].get(partner, 0) + 1
                    for opp in t2:
                        opponent_count[p][opp] = opponent_count[p].get(opp, 0) + 1
                for p in t2:
                    for partner in t2:
                        if p != partner:
                            partnership_count[p][partner] = partnership_count[p].get(partner, 0) + 1
                    for opp in t1:
                        opponent_count[p][opp] = opponent_count[p].get(opp, 0) + 1
    
    return matches


def generate_all_pool_schedules(session: Session, config: PooledContinuousRRConfig) -> List[PooledMatch]:
    """
    Generate round-robin schedules for all pools.
    
    Args:
        session: The session
        config: Pooled RR configuration with pool assignments
    
    Returns:
        Combined list of all pool matches
    """
    all_matches: List[PooledMatch] = []
    match_number = 1
    
    for pool_id, player_ids in config.pools.items():
        pool_matches = generate_pool_round_robin_matches(session, pool_id, player_ids)
        
        # Update match numbers to be sequential across all pools
        for match in pool_matches:
            match.match_number = match_number
            match_number += 1
        
        all_matches.extend(pool_matches)
    
    return all_matches


def calculate_pool_standings(
    session: Session,
    pool_id: str,
    config: PooledContinuousRRConfig = None
) -> List[Dict]:
    """
    Calculate standings for a specific pool.
    
    Args:
        session: The session
        pool_id: Pool to calculate standings for
        config: Pool configuration (optional, will use session config if not provided)
    
    Returns:
        List of player standings dicts, sorted by rank:
        [{player_id, name, wins, losses, pts_for, pts_against, pt_diff, win_pct, rank}]
    """
    # Get config from session if not provided
    if config is None:
        config = session.config.pooled_continuous_rr_config
    if config is None:
        return []
    
    player_ids = config.pools.get(pool_id, [])
    
    # Initialize stats for each player
    stats: Dict[str, Dict] = {}
    for pid in player_ids:
        player = next((p for p in session.config.players if p.id == pid), None)
        stats[pid] = {
            'player_id': pid,
            'name': player.name if player else pid,
            'wins': 0,
            'losses': 0,
            'pts_for': 0,
            'pts_against': 0,
            'pt_diff': 0,
            'win_pct': 0.0,
            'games_played': 0,
            'head_to_head': {}  # opponent_id -> 'W' or 'L'
        }
    
    # Count results from completed pool matches
    all_pool_matches = config.scheduled_pool_matches
    for match in all_pool_matches:
        if match.pool_id != pool_id:
            continue
        if match.status != 'approved':  # 'approved' means completed in our context
            continue
        
        # Find the corresponding completed match in session.matches
        session_match = next(
            (m for m in session.matches if m.id == match.id and m.status == 'completed'),
            None
        )
        if not session_match or not session_match.score:
            continue
        
        t1_score = session_match.score.get('team1_score', 0)
        t2_score = session_match.score.get('team2_score', 0)
        
        # Use session_match teams (may have been swapped during randomization)
        team1 = session_match.team1
        team2 = session_match.team2
        
        # Update stats for team1 players
        for pid in team1:
            if pid in stats:
                stats[pid]['pts_for'] += t1_score
                stats[pid]['pts_against'] += t2_score
                stats[pid]['games_played'] += 1
                if t1_score > t2_score:
                    stats[pid]['wins'] += 1
                    for opp in team2:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'W'
                else:
                    stats[pid]['losses'] += 1
                    for opp in team2:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'L'
        
        # Update stats for team2 players
        for pid in team2:
            if pid in stats:
                stats[pid]['pts_for'] += t2_score
                stats[pid]['pts_against'] += t1_score
                stats[pid]['games_played'] += 1
                if t2_score > t1_score:
                    stats[pid]['wins'] += 1
                    for opp in team1:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'W'
                else:
                    stats[pid]['losses'] += 1
                    for opp in team1:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'L'
    
    # Calculate derived stats
    standings = []
    for pid, s in stats.items():
        s['pt_diff'] = s['pts_for'] - s['pts_against']
        games = s['games_played']
        s['win_pct'] = (s['wins'] / games * 100) if games > 0 else 0.0
        standings.append(s)
    
    # Sort by wins first (desc), then apply tiebreakers
    standings.sort(key=lambda x: (-x['wins'], -x['pt_diff'], -x['pts_for']))
    
    # Apply head-to-head tiebreaker for 2-way ties within same win count
    standings = _apply_head_to_head_tiebreaker(standings)
    
    # Assign ranks
    for i, s in enumerate(standings):
        s['rank'] = i + 1
    
    return standings


def _apply_head_to_head_tiebreaker(standings: List[Dict]) -> List[Dict]:
    """
    Apply head-to-head tiebreaker for 2-way ties, point differential for 3+ way ties.
    
    Rules:
    - Players are already sorted by wins (desc)
    - For a 2-way tie (same wins): winner of head-to-head match ranks higher
    - For a 3+ way tie (same wins): use point differential (desc), then pts_for (desc)
    """
    if len(standings) <= 1:
        return standings
    
    result = []
    i = 0
    while i < len(standings):
        # Find group of players with same win count
        win_count = standings[i]['wins']
        group = [standings[i]]
        j = i + 1
        while j < len(standings) and standings[j]['wins'] == win_count:
            group.append(standings[j])
            j += 1
        
        if len(group) == 2:
            # 2-way tie: use head-to-head
            p1 = group[0]
            p2 = group[1]
            h2h = p1['head_to_head'].get(p2['player_id'])
            if h2h == 'L':
                # p1 lost to p2 head-to-head, swap them
                group = [p2, p1]
            # If h2h == 'W' or None, keep current order (p1 already ahead by pt_diff)
        # For 3+ way ties, keep existing sort by pt_diff (already sorted)
        
        result.extend(group)
        i = j
    
    return result


def check_pool_completion(session: Session, pool_id: str, config: PooledContinuousRRConfig) -> bool:
    """
    Check if all matches in a pool are completed.
    
    Args:
        session: The session
        pool_id: Pool to check
        config: Pool configuration
    
    Returns:
        True if all pool matches are completed
    """
    pool_matches = [m for m in config.scheduled_pool_matches if m.pool_id == pool_id]
    
    if not pool_matches:
        return False
    
    # Check if all are completed (status = 'approved' means played)
    for pm in pool_matches:
        # Find corresponding session match
        session_match = next(
            (m for m in session.matches if m.id == pm.id),
            None
        )
        if not session_match or session_match.status not in ['completed', 'forfeited']:
            return False
    
    return True


def check_all_pools_complete(session: Session, config: PooledContinuousRRConfig) -> bool:
    """
    Check if all pools have completed their matches.
    
    Args:
        session: The session
        config: Pool configuration
    
    Returns:
        True if all pools are complete
    """
    for pool_id in config.pools.keys():
        if not check_pool_completion(session, pool_id, config):
            return False
    return True


def generate_crossover_matches(session: Session, config: PooledContinuousRRConfig) -> List[PooledMatch]:
    """
    Generate crossover matches after all pools complete.
    Rank #1 from each pool plays rank #1 from other pools, etc.
    
    Args:
        session: The session
        config: Pool configuration
    
    Returns:
        List of crossover matches
    """
    crossover_matches: List[PooledMatch] = []
    
    # Get standings for each pool
    pool_standings: Dict[str, List[Dict]] = {}
    for pool_id in config.pools.keys():
        pool_standings[pool_id] = calculate_pool_standings(session, pool_id, config)
    
    # Find max rank to generate crossover matches for
    max_players = max(len(standings) for standings in pool_standings.values())
    pool_ids = list(config.pools.keys())
    
    session_type = session.config.session_type
    match_number = len(config.scheduled_pool_matches) + 1
    
    # For each rank, create matches between pools
    for rank in range(1, max_players + 1):
        # Get player at this rank from each pool
        rank_players: Dict[str, str] = {}  # pool_id -> player_id
        for pool_id, standings in pool_standings.items():
            if rank <= len(standings):
                rank_players[pool_id] = standings[rank - 1]['player_id']
        
        if len(rank_players) < 2:
            continue
        
        # Create crossover matches between pools
        pool_list = list(rank_players.keys())
        
        if session_type == 'singles':
            # Each player plays every other player of same rank from different pools
            for i, pool1 in enumerate(pool_list):
                for pool2 in pool_list[i + 1:]:
                    p1 = rank_players[pool1]
                    p2 = rank_players[pool2]
                    
                    match = PooledMatch(
                        id=f"crossover_rank{rank}_{uuid.uuid4().hex[:8]}",
                        team1=[p1],
                        team2=[p2],
                        status='pending',
                        match_number=match_number,
                        pool_id='',
                        is_crossover=True,
                        crossover_rank=rank
                    )
                    crossover_matches.append(match)
                    match_number += 1
        else:
            # Doubles: with 2 pools, match rank N from pool A with rank N from pool B
            # Each pool contributes one player to each team for balanced crossover
            if len(pool_list) >= 2:
                # Simple case: 2 pools - pair players cross-pool
                players_at_rank = [rank_players[p] for p in pool_list if p in rank_players]
                
                if len(players_at_rank) >= 2:
                    # For doubles crossover with 2 pools, we need 4 players
                    # Take rank N and rank N+1 from each pool to form teams
                    # Team1: Pool1 rank N + Pool2 rank N
                    # Team2: Pool1 rank N+1 + Pool2 rank N+1 (if available)
                    # Or simpler: just do singles-style for now
                    for i in range(0, len(players_at_rank) - 1, 2):
                        if i + 1 < len(players_at_rank):
                            p1, p2 = players_at_rank[i], players_at_rank[i + 1]
                            match = PooledMatch(
                                id=f"crossover_rank{rank}_{uuid.uuid4().hex[:8]}",
                                team1=[p1],
                                team2=[p2],
                                status='pending',
                                match_number=match_number,
                                pool_id='',
                                is_crossover=True,
                                crossover_rank=rank
                            )
                            crossover_matches.append(match)
                            match_number += 1
    
    return crossover_matches


def get_players_games_played(session: Session, config: PooledContinuousRRConfig) -> Dict[str, int]:
    """
    Get count of games played per player in this pooled session.
    
    Args:
        session: The session
        config: Pool configuration
    
    Returns:
        Dict mapping player_id to games_played count
    """
    games_count: Dict[str, int] = {}
    
    # Initialize all players
    for pool_players in config.pools.values():
        for pid in pool_players:
            games_count[pid] = 0
    
    # Count from completed matches
    for match in session.matches:
        if match.status in ['completed', 'forfeited']:
            for pid in match.team1 + match.team2:
                if pid in games_count:
                    games_count[pid] += 1
    
    return games_count


def get_next_match_for_court(
    session: Session,
    court_number: int,
    config: PooledContinuousRRConfig
) -> Optional[PooledMatch]:
    """
    Get the next match to play on a specific court.
    Prioritizes matches where players have played fewest games.
    
    Args:
        session: The session
        court_number: The court needing a match
        config: Pool configuration
    
    Returns:
        The best PooledMatch to play, or None if no matches available
    """
    # Determine which pools can play on this court
    allowed_pools: Set[str] = set()
    
    for pool_id, courts in config.pool_court_assignments.items():
        if not courts:  # Empty list = any court
            allowed_pools.add(pool_id)
        elif court_number in courts:
            allowed_pools.add(pool_id)
    
    # If no specific assignments, all pools can play anywhere
    if not allowed_pools:
        allowed_pools = set(config.pools.keys())
    
    # Check if any allowed pool is complete - if so, release court to others
    incomplete_pools = {p for p in allowed_pools if not config.pool_completed.get(p, False)}
    
    # If all assigned pools are complete, allow any incomplete pool
    if not incomplete_pools:
        incomplete_pools = {p for p in config.pools.keys() if not config.pool_completed.get(p, False)}
    
    # Get games played per player for prioritization
    games_played = get_players_games_played(session, config)
    
    # Get players currently in active matches
    active_players: Set[str] = set()
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            active_players.update(match.team1)
            active_players.update(match.team2)
            
    def _find_best_match_in_pools(pools_to_check: Set[str]) -> Tuple[Optional[PooledMatch], float]:
        """Helper to find best match in given pools"""
        local_best_match = None
        local_best_score = float('inf')
        
        for match in config.scheduled_pool_matches:
            if match.pool_id not in pools_to_check:
                continue
            
            # Skip already played matches
            session_match = next(
                (m for m in session.matches if m.id == match.id),
                None
            )
            if session_match:
                continue
            
            # Skip if any player is currently playing
            match_players = set(match.get_all_players())
            if match_players & active_players:
                continue
            
            # Score by total games played (lower = higher priority)
            total_games = sum(games_played.get(p, 0) for p in match.get_all_players())
            
            # Apply penalty for First Bye players if they haven't played yet
            if hasattr(session.config, 'first_bye_players') and session.config.first_bye_players:
                has_unplayed_bye_player = False
                for p in match.get_all_players():
                    if p in session.config.first_bye_players and games_played.get(p, 0) == 0:
                        has_unplayed_bye_player = True
                        break
                
                if has_unplayed_bye_player:
                    # Add penalty (0.5) to ensure they are picked after 0-game players but before 1-game players
                    total_games += 0.5
            
            if total_games < local_best_score:
                local_best_score = total_games
                local_best_match = match
        
        return local_best_match, local_best_score

    # Find best available match
    best_match: Optional[PooledMatch] = None
    
    # Check pool matches first
    if not config.crossover_active:
        # 1. Find best match in assigned/incomplete pools (Strict)
        best_match, best_score = _find_best_match_in_pools(incomplete_pools)
        
        # 2. Check override condition for First Bye
        # Only allow cross-pool switching when this court has NO specific pool assignment.
        # If pool_court_assignments restrict this court to certain pools, never switch.
        court_has_pool_restriction = any(
            court_number in courts 
            for courts in config.pool_court_assignments.values() 
            if courts
        )
        
        if not court_has_pool_restriction and (best_match is None or (0.4 < best_score < 0.6)):
            # Check other available pools
            all_incomplete = {p for p in config.pools.keys() if not config.pool_completed.get(p, False)}
            other_pools = all_incomplete - incomplete_pools
            
            if other_pools:
                match_other, score_other = _find_best_match_in_pools(other_pools)
                if match_other and score_other < best_score:
                    is_avoiding_bye = (0.4 < best_score < 0.6)
                    is_first_round_fill = (best_score > 0.6 and score_other < 0.1)
                    
                    if is_avoiding_bye or is_first_round_fill:
                        best_match = match_other
    else:
        # Crossover phase - select from crossover matches
        for match in config.crossover_matches:
            # Skip already played matches
            session_match = next(
                (m for m in session.matches if m.id == match.id),
                None
            )
            if session_match:
                continue
            
            # Skip if any player is currently playing
            match_players = set(match.get_all_players())
            if match_players & active_players:
                continue
            
            # For crossover, prioritize by rank (lower rank = higher priority)
            if best_match is None or match.crossover_rank < best_match.crossover_rank:
                best_match = match
    
    return best_match


def populate_courts_pooled_rr(session: Session) -> bool:
    """
    Main function to populate empty courts with pooled RR matches.
    
    Args:
        session: The session
    
    Returns:
        True if any courts were populated
    """
    config = session.config.pooled_continuous_rr_config
    if not config or not config.pools_finalized:
        return False
    
    # Update pool completion status
    for pool_id in config.pools.keys():
        config.pool_completed[pool_id] = check_pool_completion(session, pool_id, config)
    
    # Check if we need to start crossover
    if not config.crossover_active and check_all_pools_complete(session, config):
        config.crossover_active = True
        config.crossover_matches = generate_crossover_matches(session, config)
    
    # Find empty courts
    num_courts = session.config.courts
    occupied_courts: Set[int] = set()
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            occupied_courts.add(match.court_number)
    
    populated = False
    
    for court_num in range(1, num_courts + 1):
        if court_num in occupied_courts:
            continue
        
        next_match = get_next_match_for_court(session, court_num, config)
        if next_match:
            # Create the actual match
            from .session import create_match_from_pooled
            create_match_from_pooled(session, next_match, court_num)
            populated = True
            occupied_courts.add(court_num)
    
    return populated


def check_session_complete(session: Session, config: PooledContinuousRRConfig) -> bool:
    """
    Check if the entire session is complete (all pool + crossover matches).
    
    Args:
        session: The session
        config: Pool configuration
    
    Returns:
        True if session is complete
    """
    if not config.crossover_active:
        return False
    
    # Check all crossover matches are done
    for match in config.crossover_matches:
        session_match = next(
            (m for m in session.matches if m.id == match.id),
            None
        )
        if not session_match or session_match.status not in ['completed', 'forfeited']:
            return False
    
    return True


def get_final_rankings(session: Session, config: PooledContinuousRRConfig = None) -> List[Dict]:
    """
    Get final rankings after all matches complete.
    Winners are determined by crossover match results:
    - For 2 pools: Gold = winner of crossover #1, Silver = loser of crossover #1, Bronze = winner of crossover #2
    - For 3+ pools: Top 3 from crossover #1 matches, ranked by crossover wins then point differential
    
    Args:
        session: The session
        config: Pool configuration (optional)
    
    Returns:
        List of player rankings with medals (top 3)
    """
    if config is None:
        config = session.config.pooled_continuous_rr_config
    
    if not config or not config.crossover_matches:
        # Fallback to stats-based ranking if no crossover matches
        return _get_stats_based_rankings(session)
    
    # Get player name lookup
    player_names = {p.id: p.name for p in session.config.players}
    
    # Find completed crossover matches and their results
    crossover_results: Dict[int, List[Dict]] = {}  # rank -> list of {player_id, won, pt_diff}
    
    for crossover_match in config.crossover_matches:
        # Find the completed match in session.matches
        completed_match = next(
            (m for m in session.matches if m.id == crossover_match.id and m.status == 'completed'),
            None
        )
        
        if not completed_match or not completed_match.score:
            continue
        
        rank = crossover_match.crossover_rank
        if rank not in crossover_results:
            crossover_results[rank] = []
        
        team1_score = completed_match.score.get('team1_score', 0)
        team2_score = completed_match.score.get('team2_score', 0)
        
        # For singles, team1 and team2 are single-player lists
        for player_id in completed_match.team1:
            won = team1_score > team2_score
            pt_diff = team1_score - team2_score
            crossover_results[rank].append({
                'player_id': player_id,
                'name': player_names.get(player_id, player_id),
                'won': won,
                'pt_diff': pt_diff,
                'crossover_rank': rank
            })
        
        for player_id in completed_match.team2:
            won = team2_score > team1_score
            pt_diff = team2_score - team1_score
            crossover_results[rank].append({
                'player_id': player_id,
                'name': player_names.get(player_id, player_id),
                'won': won,
                'pt_diff': pt_diff,
                'crossover_rank': rank
            })
    
    # If no crossover results yet, fall back to stats
    if not crossover_results:
        return _get_stats_based_rankings(session)
    
    num_pools = len(config.pools)
    rankings = []
    
    if num_pools == 2:
        # For 2 pools: 
        # Gold = winner of crossover #1
        # Silver = loser of crossover #1  
        # Bronze = winner of crossover #2
        
        # Get rank 1 results
        rank1_results = crossover_results.get(1, [])
        rank1_winner = next((r for r in rank1_results if r['won']), None)
        rank1_loser = next((r for r in rank1_results if not r['won']), None)
        
        # Get rank 2 results
        rank2_results = crossover_results.get(2, [])
        rank2_winner = next((r for r in rank2_results if r['won']), None)
        
        if rank1_winner:
            rankings.append({
                'player_id': rank1_winner['player_id'],
                'name': rank1_winner['name'],
                'rank': 1,
                'medal': '🥇',
                'crossover_result': 'Crossover #1 Winner'
            })
        
        if rank1_loser:
            rankings.append({
                'player_id': rank1_loser['player_id'],
                'name': rank1_loser['name'],
                'rank': 2,
                'medal': '🥈',
                'crossover_result': 'Crossover #1 Runner-up'
            })
        
        if rank2_winner:
            rankings.append({
                'player_id': rank2_winner['player_id'],
                'name': rank2_winner['name'],
                'rank': 3,
                'medal': '🥉',
                'crossover_result': 'Crossover #2 Winner'
            })
    else:
        # For 3+ pools: Top 3 from crossover #1 matches
        # Ranked by: crossover wins (desc), then point differential (desc)
        rank1_results = crossover_results.get(1, [])
        
        # Sort by won (True first), then by pt_diff (descending)
        rank1_sorted = sorted(
            rank1_results,
            key=lambda x: (-int(x['won']), -x['pt_diff'])
        )
        
        medals = ['🥇', '🥈', '🥉']
        for i, result in enumerate(rank1_sorted[:3]):
            rankings.append({
                'player_id': result['player_id'],
                'name': result['name'],
                'rank': i + 1,
                'medal': medals[i] if i < 3 else '',
                'crossover_result': 'Crossover #1 Winner' if result['won'] else f'Crossover #1 (Diff: {result["pt_diff"]:+d})'
            })
    
    # Add stats from session for display
    for r in rankings:
        stats = session.player_stats.get(r['player_id'])
        if stats:
            r['wins'] = stats.wins
            r['losses'] = stats.losses
            r['pts_for'] = stats.total_points_for
            r['pts_against'] = stats.total_points_against
            r['pt_diff'] = stats.total_points_for - stats.total_points_against
            r['games_played'] = stats.games_played
            r['win_pct'] = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0.0
        else:
            r['wins'] = 0
            r['losses'] = 0
            r['pts_for'] = 0
            r['pts_against'] = 0
            r['pt_diff'] = 0
            r['games_played'] = 0
            r['win_pct'] = 0.0
    
    return rankings


def _get_stats_based_rankings(session: Session) -> List[Dict]:
    """
    Fallback ranking based on overall stats (used when crossover not complete).
    """
    all_stats: Dict[str, Dict] = {}
    
    for player in session.config.players:
        if player.id not in session.active_players:
            continue
        
        stats = session.player_stats.get(player.id)
        if not stats:
            continue
        
        all_stats[player.id] = {
            'player_id': player.id,
            'name': player.name,
            'wins': stats.wins,
            'losses': stats.losses,
            'pts_for': stats.total_points_for,
            'pts_against': stats.total_points_against,
            'pt_diff': stats.total_points_for - stats.total_points_against,
            'games_played': stats.games_played,
            'win_pct': (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0.0
        }
    
    # Sort by wins, then pt_diff, then pts_for
    rankings = sorted(
        all_stats.values(),
        key=lambda x: (-x['wins'], -x['pt_diff'], -x['pts_for'])
    )
    
    # Assign ranks and medals
    medals = ['🥇', '🥈', '🥉']
    for i, r in enumerate(rankings):
        r['rank'] = i + 1
        r['medal'] = medals[i] if i < 3 else ''
    
    return rankings


def calculate_overall_standings(session: Session) -> List[Dict]:
    """
    Calculate overall standings combining all pool and crossover results.
    Used for winners celebration dialog.
    
    Args:
        session: The session
    
    Returns:
        List of player standings sorted by rank
    """
    return get_final_rankings(session)


def get_match_crossover_info(session: Session, match_id: str) -> Optional[Dict]:
    """
    Get crossover information for a match (if it's a crossover match).
    
    Args:
        session: The session
        match_id: Match ID to check
    
    Returns:
        Dict with crossover info or None if not a crossover match
    """
    config = session.config.pooled_continuous_rr_config
    if not config:
        return None
    
    for match in config.crossover_matches:
        if match.id == match_id:
            return {
                'is_crossover': True,
                'crossover_rank': match.crossover_rank
            }
    
    return None


def get_match_pool_info(session: Session, match_id: str) -> Optional[Dict]:
    """
    Get pool information for a match.
    
    Args:
        session: The session
        match_id: Match ID to check
    
    Returns:
        Dict with pool info or None if not found
    """
    config = session.config.pooled_continuous_rr_config
    if not config:
        return None
    
    # Check pool matches
    for match in config.scheduled_pool_matches:
        if match.id == match_id:
            return {
                'pool_id': match.pool_id,
                'is_crossover': False
            }
    
    # Check crossover matches
    for match in config.crossover_matches:
        if match.id == match_id:
            return {
                'pool_id': '',
                'is_crossover': True,
                'crossover_rank': match.crossover_rank
            }
    
    return None
