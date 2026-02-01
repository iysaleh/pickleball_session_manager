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
        
        # Update stats for team1 players
        for pid in match.team1:
            if pid in stats:
                stats[pid]['pts_for'] += t1_score
                stats[pid]['pts_against'] += t2_score
                stats[pid]['games_played'] += 1
                if t1_score > t2_score:
                    stats[pid]['wins'] += 1
                    for opp in match.team2:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'W'
                else:
                    stats[pid]['losses'] += 1
                    for opp in match.team2:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'L'
        
        # Update stats for team2 players
        for pid in match.team2:
            if pid in stats:
                stats[pid]['pts_for'] += t2_score
                stats[pid]['pts_against'] += t1_score
                stats[pid]['games_played'] += 1
                if t2_score > t1_score:
                    stats[pid]['wins'] += 1
                    for opp in match.team1:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'W'
                else:
                    stats[pid]['losses'] += 1
                    for opp in match.team1:
                        if opp in stats:
                            stats[pid]['head_to_head'][opp] = 'L'
    
    # Calculate derived stats
    standings = []
    for pid, s in stats.items():
        s['pt_diff'] = s['pts_for'] - s['pts_against']
        games = s['games_played']
        s['win_pct'] = (s['wins'] / games * 100) if games > 0 else 0.0
        standings.append(s)
    
    # Sort by: wins (desc), pt_diff (desc), pts_for (desc)
    standings.sort(key=lambda x: (-x['wins'], -x['pt_diff'], -x['pts_for']))
    
    # Assign ranks
    for i, s in enumerate(standings):
        s['rank'] = i + 1
    
    return standings


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
    
    # Find best available match
    best_match: Optional[PooledMatch] = None
    best_score = float('inf')  # Lower is better (fewer games played)
    
    # Check pool matches first
    if not config.crossover_active:
        for match in config.scheduled_pool_matches:
            if match.pool_id not in incomplete_pools:
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
            
            if total_games < best_score:
                best_score = total_games
                best_match = match
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
    Combines pool standings with crossover results.
    
    Args:
        session: The session
        config: Pool configuration (optional)
    
    Returns:
        List of player rankings with medals (top 3)
    """
    if config is None:
        config = session.config.pooled_continuous_rr_config
    
    # Aggregate all stats
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
