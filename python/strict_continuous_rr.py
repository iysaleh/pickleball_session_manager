"""
Strict Continuous Round Robin Algorithm

This mode is similar to Continuous Round Robin but with STRICT queue ordering:
- The match queue is populated just like continuous round robin
- However, matches MUST be played in queue order - no skipping allowed
- If players for match N are not available, we wait (don't make match N+1)
- Once match N's players are available, match N starts
- This ensures fair, predictable match ordering

SINGLES DEFAULT: This mode defaults to singles play.

RANKING SYSTEM (shared with Continuous Round Robin):
1. First rank by wins/losses (most wins first, then fewest losses)
2. For 2-player ties: head-to-head result determines winner
3. For 3+ player ties: point differential determines ranking
"""

from typing import List, Dict, Tuple, Optional, Set
import uuid
import random

from .pickleball_types import (
    Session, Match, QueuedMatch, Player, PlayerStats, MatchStatus
)
from .roundrobin import generate_round_robin_queue
from .time_manager import now


def populate_courts_strict_continuous(session: Session) -> None:
    """
    Populate empty courts from the match queue in STRICT order.
    
    STRICT OPERATION:
    - Process queue from front to back
    - If a player has an earlier unplayed match in the queue, they CANNOT play
    - This ensures Tommy vs Barb finishes before Tommy vs Ibraheem can be made
    - Matches with completely disjoint player sets can still proceed
    """
    if session.config.mode != 'strict-continuous-rr':
        return
    
    from .queue_manager import get_empty_courts
    
    # Get empty courts
    empty_courts = get_empty_courts(session)
    
    if not empty_courts or not session.match_queue:
        return
    
    # Check player availability (not in active match)
    players_in_active_matches = set()
    for match in session.matches:
        if match.status in ['waiting', 'in-progress']:
            players_in_active_matches.update(match.team1)
            players_in_active_matches.update(match.team2)
    
    # STRICT ORDERING: Track which players have pending earlier matches
    # A player is "blocked" if they appear in an earlier unassigned queue match
    players_blocked_by_earlier_match = set()
    
    matches_to_remove = []
    courts_filled = 0
    
    for i, queued_match in enumerate(session.match_queue):
        if courts_filled >= len(empty_courts):
            break
            
        match_players = set(queued_match.team1 + queued_match.team2)
        
        # Check if all players are still active in session
        if not match_players.issubset(session.active_players):
            matches_to_remove.append(i)  # Remove invalid match
            continue
        
        # STRICT CHECK 1: Players in active matches cannot play
        if match_players & players_in_active_matches:
            # These players are busy - they are now blocked for later matches too
            players_blocked_by_earlier_match.update(match_players)
            continue
        
        # STRICT CHECK 2: Players blocked by earlier unplayed matches cannot play
        if match_players & players_blocked_by_earlier_match:
            # This match is blocked - add its players to the blocked set
            players_blocked_by_earlier_match.update(match_players)
            continue
        
        # All players available AND not blocked by earlier matches - create the match!
        court_number = empty_courts[courts_filled]
        
        match = Match(
            id=f"match_{uuid.uuid4().hex[:8]}",
            court_number=court_number,
            team1=queued_match.team1[:],
            team2=queued_match.team2[:],
            status='waiting',
            start_time=now()
        )
        session.matches.append(match)
        
        # Mark for removal from queue
        matches_to_remove.append(i)
        
        # Mark players as active (for subsequent iterations)
        players_in_active_matches.update(match_players)
        courts_filled += 1
    
    # Remove assigned matches from queue (in reverse order to maintain indices)
    for i in sorted(matches_to_remove, reverse=True):
        if i < len(session.match_queue):
            session.match_queue.pop(i)


def generate_strict_rr_queue(session: Session) -> List[QueuedMatch]:
    """
    Generate the match queue for Strict Continuous Round Robin.
    
    Uses the same algorithm as regular continuous round robin,
    but the resulting queue will be processed STRICTLY in order.
    
    For singles: generates all possible 1v1 matchups.
    For doubles: uses the standard round robin generation.
    """
    players = [p for p in session.config.players if p.id in session.active_players]
    
    if session.config.session_type == 'singles':
        return _generate_singles_round_robin_queue(
            players,
            session.config.banned_pairs,
            session.max_queue_size,
            session.player_stats
        )
    else:
        return generate_round_robin_queue(
            players,
            session.config.session_type,
            session.config.banned_pairs,
            session.max_queue_size,
            session.config.locked_teams,
            session.player_stats,
            session.matches,
            session.config.first_bye_players
        )


def _generate_singles_round_robin_queue(
    players: List[Player],
    banned_pairs: List[Tuple[str, str]],
    max_matches: int = 100,
    player_stats: Optional[Dict[str, PlayerStats]] = None,
    num_courts: int = 3
) -> List[QueuedMatch]:
    """
    Generate a round robin queue for singles play optimized for court utilization.
    
    CRITICAL: Matches are organized into "rounds" where each player appears at most
    once per round. This ensures maximum court utilization - when all courts finish,
    all courts can be refilled immediately.
    
    Algorithm (Circle Method for Round Robin Scheduling):
    1. If odd number of players, add a "bye" placeholder
    2. Fix player 0, rotate others around the circle
    3. Each rotation produces one "round" of matches
    4. Within each round, each player plays exactly once (or has bye)
    
    Example with 6 players, 3 courts:
    - Round 1: p1 vs p6, p2 vs p5, p3 vs p4  (3 matches, fills all courts)
    - Round 2: p1 vs p5, p6 vs p4, p2 vs p3  (3 matches, fills all courts)
    - etc.
    """
    from .utils import is_pair_banned
    
    if len(players) < 2:
        return []
    
    player_ids = [p.id for p in players]
    n = len(player_ids)
    
    # Use the circle/polygon method for round-robin scheduling
    # If odd number, add a "BYE" placeholder
    if n % 2 == 1:
        player_ids = player_ids + ["__BYE__"]
        n += 1
    
    # Build banned set for quick lookup
    banned_set = set()
    for p1, p2 in banned_pairs:
        banned_set.add(frozenset([p1, p2]))
    
    matches: List[QueuedMatch] = []
    used_matchups: Set[frozenset] = set()
    
    # Circle method: fix position 0, rotate others
    # Number of rounds = n - 1 (each player plays everyone else once)
    circle = player_ids[:]
    
    for round_num in range(n - 1):
        round_matches: List[QueuedMatch] = []
        
        # In each round, pair up: position i with position (n-1-i)
        for i in range(n // 2):
            p1 = circle[i]
            p2 = circle[n - 1 - i]
            
            # Skip if either is BYE
            if p1 == "__BYE__" or p2 == "__BYE__":
                continue
            
            # Skip banned pairs
            if frozenset([p1, p2]) in banned_set:
                continue
            
            matchup_key = frozenset([p1, p2])
            if matchup_key in used_matchups:
                continue
            
            used_matchups.add(matchup_key)
            
            # Randomize team sides
            if random.random() < 0.5:
                p1, p2 = p2, p1
            
            round_matches.append(QueuedMatch(team1=[p1], team2=[p2]))
        
        matches.extend(round_matches)
        
        if len(matches) >= max_matches:
            break
        
        # Rotate: keep position 0 fixed, rotate positions 1 through n-1
        # [0, 1, 2, 3, 4, 5] -> [0, 5, 1, 2, 3, 4]
        circle = [circle[0]] + [circle[-1]] + circle[1:-1]
    
    return matches[:max_matches]


def calculate_round_robin_standings(
    session: Session
) -> List[Dict]:
    """
    Calculate standings for Continuous Round Robin and Strict Continuous Round Robin modes.
    
    RANKING RULES:
    1. Primary: Wins (descending) - Losses (ascending)
    2. For 2-way ties: Head-to-head result
    3. For 3+ way ties: Point differential (descending)
    
    Returns:
        List of player standings dicts, sorted by rank:
        [{player_id, name, wins, losses, pts_for, pts_against, pt_diff, win_pct, rank, games_played, head_to_head}]
    """
    # Build standings from player stats
    standings: List[Dict] = []
    
    for player in session.config.players:
        if player.id not in session.active_players:
            continue
        
        stats = session.player_stats.get(player.id)
        if not stats:
            continue
        
        pt_diff = stats.total_points_for - stats.total_points_against
        win_pct = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0.0
        
        standings.append({
            'player_id': player.id,
            'name': player.name,
            'wins': stats.wins,
            'losses': stats.losses,
            'pts_for': stats.total_points_for,
            'pts_against': stats.total_points_against,
            'pt_diff': pt_diff,
            'win_pct': win_pct,
            'games_played': stats.games_played,
            'head_to_head': {}  # Will be populated below
        })
    
    # Build head-to-head records from completed matches
    for match in session.matches:
        if match.status != 'completed' or not match.score:
            continue
        
        t1_score = match.score.get('team1_score', 0)
        t2_score = match.score.get('team2_score', 0)
        
        # For each player in team1, record result against team2 players
        for p1 in match.team1:
            for p2 in match.team2:
                # Find standings entries
                p1_standing = next((s for s in standings if s['player_id'] == p1), None)
                p2_standing = next((s for s in standings if s['player_id'] == p2), None)
                
                if p1_standing and p2_standing:
                    if t1_score > t2_score:
                        p1_standing['head_to_head'][p2] = 'W'
                        p2_standing['head_to_head'][p1] = 'L'
                    else:
                        p1_standing['head_to_head'][p2] = 'L'
                        p2_standing['head_to_head'][p1] = 'W'
    
    # Sort by wins (desc), then losses (asc), then pt_diff (desc)
    standings.sort(key=lambda x: (-x['wins'], x['losses'], -x['pt_diff']))
    
    # Apply head-to-head tiebreaker for 2-way ties
    standings = _apply_rr_head_to_head_tiebreaker(standings)
    
    # Assign ranks
    for i, s in enumerate(standings):
        s['rank'] = i + 1
    
    return standings


def _apply_rr_head_to_head_tiebreaker(standings: List[Dict]) -> List[Dict]:
    """
    Apply head-to-head tiebreaker for 2-way ties, point differential for 3+ way ties.
    
    Rules:
    - Players are already sorted by wins (desc), losses (asc), pt_diff (desc)
    - For a 2-way tie (same W-L record): winner of head-to-head match ranks higher
    - For a 3+ way tie (same W-L record): point differential already applied
    """
    if len(standings) <= 1:
        return standings
    
    result = []
    i = 0
    
    while i < len(standings):
        # Find group of players with same W-L record
        wins = standings[i]['wins']
        losses = standings[i]['losses']
        group = [standings[i]]
        j = i + 1
        
        while j < len(standings) and standings[j]['wins'] == wins and standings[j]['losses'] == losses:
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
        elif len(group) > 2:
            # 3+ way tie: sort by point differential (already done in initial sort)
            # Keep current order as it's already sorted by pt_diff
            pass
        
        result.extend(group)
        i = j
    
    return result


def get_strict_rr_standings_for_display(session: Session) -> List[Tuple]:
    """
    Get standings formatted for display in the statistics dialog.
    
    Returns list of tuples: (name, wins, losses, games_played, win_pct, pt_diff, rank)
    """
    standings = calculate_round_robin_standings(session)
    
    display_data = []
    for s in standings:
        display_data.append((
            s['name'],
            s['wins'],
            s['losses'],
            s['games_played'],
            s['win_pct'],
            s['pt_diff'],
            s['rank']
        ))
    
    return display_data
