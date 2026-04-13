#!/usr/bin/env python3
"""
Correct session ELO rankings using enhanced algorithm that includes point differential
"""
import re
import sys
from collections import defaultdict
from pathlib import Path
import math

def calculate_enhanced_elo_rating(wins, games, pts_for, pts_against, base_rating=1500, min_rating=800, max_rating=2200):
    """
    Calculate enhanced ELO rating that includes point differential
    Matches the algorithm in kingofcourt.py calculate_player_rating()
    """
    if games == 0:
        return base_rating
    
    win_rate = wins / games
    
    # Win rate adjustment with logarithmic scaling
    rating = base_rating + math.log(1 + win_rate * 9) * 200 - 200
    
    # Point differential adjustment
    if games > 0:
        avg_point_diff = (pts_for - pts_against) / games
        if avg_point_diff != 0:
            rating += math.log(1 + abs(avg_point_diff)) * 50 * (1 if avg_point_diff > 0 else -1)
    
    # Consistency bonus for strong players (60%+ win rate)
    if win_rate >= 0.6 and games > 0:
        rating += math.log(games) * 30
    
    # Clamp to min/max
    rating = max(min_rating, min(rating, max_rating))
    return rating

def parse_player_statistics(content):
    """Extract player statistics from session file"""
    stats_idx = content.find("PLAYER STATISTICS")
    if stats_idx == -1:
        return {}
    
    stats_section = content[stats_idx:]
    lines = stats_section.split('\n')
    
    # Find the start of actual data (skip header)
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith('-'):
            data_start = i + 1
            break
    
    player_stats = {}
    for line in lines[data_start:]:
        line = line.strip()
        if not line or line.startswith('=') or line.startswith('MATCH'):
            break
        
        # Parse player statistics line
        match = re.search(r'(.+?)\s+(\d+)\s+(\d+-\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+:\d+)\s+([-\d.]+)\s+(\d+)\s+(\d+)', line)
        if match:
            player_name = match.group(1).strip()
            old_elo = int(match.group(2))
            wl = match.group(3)
            games = int(match.group(4))
            win_pct = match.group(5)
            wait_time = match.group(6)
            avg_pt_diff = float(match.group(7))
            pts_for = int(match.group(8))
            pts_against = int(match.group(9))
            
            # Calculate wins from W-L record
            wins = int(wl.split('-')[0])
            
            # Calculate enhanced ELO
            enhanced_elo = calculate_enhanced_elo_rating(wins, games, pts_for, pts_against)
            
            player_stats[player_name] = {
                'old_elo': old_elo,
                'enhanced_elo': enhanced_elo,
                'wl': wl,
                'games': games,
                'wins': wins,
                'win_pct': win_pct,
                'wait_time': wait_time,
                'avg_pt_diff': avg_pt_diff,
                'pts_for': pts_for,
                'pts_against': pts_against
            }
    
    return player_stats

def correct_session(filename):
    """Parse session file and output corrected rankings"""
    
    if not Path(filename).exists():
        print(f"Error: File not found: {filename}")
        sys.exit(1)
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Parse player statistics
    player_stats = parse_player_statistics(content)
    
    if not player_stats:
        print("Error: No player statistics found in session")
        sys.exit(1)
    
    print(f"CORRECTED SESSION RANKINGS: {Path(filename).name}")
    print("=" * 70)
    print()
    
    # Sort by enhanced ELO (descending)
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['enhanced_elo'], reverse=True)
    
    print("CORRECTED PLAYER STATISTICS (sorted by Enhanced ELO):")
    print(f"{'Rank':<5} {'Player':<25} {'Old ELO':<8} {'New ELO':<8} {'Diff':<8} {'W-L':<8} {'Games':<7} {'Win%':<8} {'Wait Time':<10} {'Avg Pt Diff':<13} {'Pts For':<10} {'Pts Against':<12}")
    print("-" * 130)
    
    for rank, (player, stats) in enumerate(sorted_players, 1):
        elo_diff = stats['enhanced_elo'] - stats['old_elo']
        elo_diff_str = f"+{elo_diff:.0f}" if elo_diff >= 0 else f"{elo_diff:.0f}"
        
        print(f"{rank:<5} {player:<25} {stats['old_elo']:<8} {stats['enhanced_elo']:<8.0f} {elo_diff_str:<8} {stats['wl']:<8} {stats['games']:<7} {stats['win_pct']:<8} {stats['wait_time']:<10} {stats['avg_pt_diff']:<13.1f} {stats['pts_for']:<10} {stats['pts_against']:<12}")
    
    print("\n" + "=" * 70)
    print("CSV OUTPUT - CORRECTED RANKINGS")
    print("=" * 70)
    print("Rank,Player,ELO,W-L,Games,Win%,WaitTime,AvgPtDiff,PtsFor,PtsAgainst")
    
    for rank, (player, stats) in enumerate(sorted_players, 1):
        print(f"{rank},{player},{stats['enhanced_elo']:.0f},{stats['wl']},{stats['games']},{stats['win_pct']},{stats['wait_time']},{stats['avg_pt_diff']},{stats['pts_for']},{stats['pts_against']}")
    
    print("\n" + "=" * 70)
    print("RANKING CHANGES")
    print("=" * 70)
    
    # Compare old vs new rankings
    old_rankings = sorted(player_stats.items(), key=lambda x: x[1]['old_elo'], reverse=True)
    new_rankings = sorted_players
    
    old_rank_map = {player: rank for rank, (player, _) in enumerate(old_rankings, 1)}
    new_rank_map = {player: rank for rank, (player, _) in enumerate(new_rankings, 1)}
    
    changes = []
    for player in player_stats.keys():
        old_rank = old_rank_map[player]
        new_rank = new_rank_map[player]
        if old_rank != new_rank:
            change = old_rank - new_rank  # Positive = moved up, negative = moved down
            changes.append((player, old_rank, new_rank, change, player_stats[player]['enhanced_elo']))
    
    if changes:
        # Sort by magnitude of change (biggest movers first)
        changes.sort(key=lambda x: abs(x[3]), reverse=True)
        
        print(f"{'Player':<25} {'Old Rank':<10} {'New Rank':<10} {'Change':<10} {'New ELO':<10}")
        print("-" * 75)
        
        for player, old_rank, new_rank, change, new_elo in changes:
            change_str = f"+{change}" if change > 0 else str(change)
            direction = "↑" if change > 0 else "↓"
            print(f"{player:<25} {old_rank:<10} {new_rank:<10} {change_str:<3} {direction:<6} {new_elo:<10.0f}")
    else:
        print("No ranking changes - all players maintain same relative positions")

def get_latest_session_file():
    """Find the latest session file based on timestamp in filename"""
    session_files = list(Path('.').glob('pickleball_session*.txt'))
    if not session_files:
        return None
    
    # Extract timestamp from filename and sort by it
    def extract_timestamp(filepath):
        match = re.search(r'(\d{8}_\d{6})', filepath.name)
        if match:
            return match.group(1)
        return ""
    
    sorted_files = sorted(session_files, key=extract_timestamp, reverse=True)
    return sorted_files[0] if sorted_files else None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Use the latest session file
        latest_file = get_latest_session_file()
        if latest_file:
            print(f"Using most recent session: {latest_file.name}")
            print()
            correct_session(latest_file)
        else:
            print("No session files found. Usage: python correct_session.py <session_file>")
            sys.exit(1)
    else:
        correct_session(sys.argv[1])