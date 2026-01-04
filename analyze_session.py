"""
Analyze pickleball session exports to find partnership and opponent stats
"""
import re
import sys
from collections import defaultdict
from pathlib import Path


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
        # Format: "Player                    ELO        W-L        Games      Win %      Wait Time    Avg Pt Diff     Pts For    Pts Against"
        # Example: "Alice                     1858       1-0        1          100.0%     00:00        6.0             11         5"
        match = re.search(r'(.+?)\s+(\d+)\s+(\d+-\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+:\d+)\s+([-\d.]+)\s+(\d+)\s+(\d+)', line)
        if match:
            player_name = match.group(1).strip()
            elo = match.group(2)
            wl = match.group(3)
            games = match.group(4)
            win_pct = match.group(5)
            wait_time = match.group(6)
            avg_pt_diff = match.group(7)
            pts_for = match.group(8)
            pts_against = match.group(9)
            
            player_stats[player_name] = {
                'elo': int(elo),
                'wl': wl,
                'games': int(games),
                'win_pct': win_pct,
                'wait_time': wait_time,
                'avg_pt_diff': float(avg_pt_diff),
                'pts_for': int(pts_for),
                'pts_against': int(pts_against)
            }
    
    return player_stats


def analyze_session(filename):
    """Parse session file and analyze partnerships and opponents"""
    
    if not Path(filename).exists():
        print(f"Error: File not found: {filename}")
        sys.exit(1)
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Parse player statistics
    player_stats = parse_player_statistics(content)
    
    # Find match history section
    match_history_idx = content.find("MATCH HISTORY:")
    if match_history_idx == -1:
        print("Error: No MATCH HISTORY section found")
        sys.exit(1)
    
    match_section = content[match_history_idx:]
    lines = match_section.split('\n')[2:]  # Skip header and dashes
    
    partnerships = defaultdict(int)  # (player1, player2) -> count
    opponents = defaultdict(int)      # (player1, player2) -> count
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('---') or line.startswith('='):
            continue
        
        # Parse match: "Player1 & Player2: 11 beat Player3 & Player4: 7"
        # The format is: "p1 & p2: X beat p3 & p4: Y [time]" for singles pairs
        match = re.match(r'(.+?)\s*&\s*(.+?):\s*(\d+)\s+beat\s+(.+?)\s*&\s*(.+?):\s*(\d+)', line)
        
        if match:
            p1, p2, p3, p4 = match.group(1).strip(), match.group(2).strip(), match.group(4).strip(), match.group(5).strip()
            
            # Count partnerships (teammates)
            key_partners = tuple(sorted([p1, p2]))
            partnerships[key_partners] += 1
            
            key_partners_2 = tuple(sorted([p3, p4]))
            partnerships[key_partners_2] += 1
            
            # Count opponents
            key_opp_1_vs_3 = tuple(sorted([p1, p3]))
            opponents[key_opp_1_vs_3] += 1
            
            key_opp_1_vs_4 = tuple(sorted([p1, p4]))
            opponents[key_opp_1_vs_4] += 1
            
            key_opp_2_vs_3 = tuple(sorted([p2, p3]))
            opponents[key_opp_2_vs_3] += 1
            
            key_opp_2_vs_4 = tuple(sorted([p2, p4]))
            opponents[key_opp_2_vs_4] += 1
    
    if not partnerships and not opponents:
        print("Error: No matches found in session")
        sys.exit(1)
    
    # Display results
    print(f"\n{'='*70}")
    print(f"SESSION ANALYSIS: {Path(filename).name}")
    print(f"{'='*70}\n")
    
    # Player Statistics Table
    if player_stats:
        print("PLAYER STATISTICS (sorted by ELO):")
        print(f"{'Rank':<5} {'Player':<25} {'ELO':<7} {'W-L':<8} {'Games':<7} {'Win%':<8} {'Wait Time':<10} {'Avg Pt Diff':<13} {'Pts For':<10} {'Pts Against':<12}")
        print("-" * 110)
        
        sorted_players = sorted(player_stats.items(), key=lambda x: int(x[1]['elo']), reverse=True)
        for rank, (player, stats) in enumerate(sorted_players, 1):
            print(f"{rank:<5} {player:<25} {stats['elo']:<7} {stats['wl']:<8} {stats['games']:<7} {stats['win_pct']:<8} {stats['wait_time']:<10} {stats['avg_pt_diff']:<13.1f} {stats['pts_for']:<10} {stats['pts_against']:<12}")
        print()
    
    # CSV Player Statistics
    if player_stats:
        print("CSV PLAYER STATISTICS")
        print("-" * 70)
        print("Rank,Player,ELO,W-L,Games,Win%,WaitTime,AvgPtDiff,PtsFor,PtsAgainst")
        
        # Sort by ELO descending
        sorted_players = sorted(player_stats.items(), key=lambda x: int(x[1]['elo']), reverse=True)
        for rank, (player, stats) in enumerate(sorted_players, 1):
            print(f"{rank},{player},{stats['elo']},{stats['wl']},{stats['games']},{stats['win_pct']},{stats['wait_time']},{stats['avg_pt_diff']},{stats['pts_for']},{stats['pts_against']}")
        print()
    
    # Most partnerships
    if partnerships:
        sorted_partnerships = sorted(partnerships.items(), key=lambda x: x[1], reverse=True)
        print("TOP PARTNERSHIPS (Players who played together most):")
        print(f"{'Rank':<5} {'Player 1':<20} {'Player 2':<20} {'Times':<5}")
        print("-" * 70)
        
        for i, ((p1, p2), count) in enumerate(sorted_partnerships[:10], 1):
            print(f"{i:<5} {p1:<20} {p2:<20} {count:<5}")
        
        max_partners = sorted_partnerships[0]
        print(f"\n>>> MOST PARTNERSHIPS: {max_partners[0][0]} and {max_partners[0][1]} "
              f"played together {max_partners[1]} times\n")
    
    # Most opponents
    if opponents:
        sorted_opponents = sorted(opponents.items(), key=lambda x: x[1], reverse=True)
        print("TOP OPPONENTS (Players who played against each other most):")
        print(f"{'Rank':<5} {'Player 1':<20} {'Player 2':<20} {'Times':<5}")
        print("-" * 70)
        
        for i, ((p1, p2), count) in enumerate(sorted_opponents[:10], 1):
            print(f"{i:<5} {p1:<20} {p2:<20} {count:<5}")
        
        max_opponents = sorted_opponents[0]
        print(f"\n>>> MOST OPPONENTS: {max_opponents[0][0]} and {max_opponents[0][1]} "
              f"played against each other {max_opponents[1]} times\n")


def get_latest_session_file():
    """Find the latest session file based on timestamp in filename"""
    session_files = list(Path('.').glob('pickleball_session*.txt'))
    if not session_files:
        return None
    
    # Extract timestamp from filename and sort by it
    # Format: pickleball_session_YYYYMMDD_HHMMSS.txt
    def extract_timestamp(filepath):
        # Extract the timestamp part: YYYYMMDD_HHMMSS
        match = re.search(r'(\d{8}_\d{6})', filepath.name)
        if match:
            return match.group(1)
        return ""
    
    # Sort by timestamp (descending to get latest)
    sorted_files = sorted(session_files, key=extract_timestamp, reverse=True)
    return sorted_files[0] if sorted_files else None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Try to find the most recent session file by timestamp
        filename = get_latest_session_file()
        if not filename:
            print("Usage: python analyze_session.py <session_file>")
            print("Or:    python analyze_session.py  (uses most recent session)")
            print("Or:    python analyze_session.py --help")
            sys.exit(1)
        print(f"Using most recent session: {filename}\n")
    elif sys.argv[1] in ['--help', '-h']:
        print("Session Analysis Script")
        print("=" * 70)
        print("\nUsage:")
        print("  python analyze_session.py                    # Analyzes most recent session")
        print("  python analyze_session.py <filename>         # Analyzes specific session")
        print("  python analyze_session.py --help             # Shows this help message")
        print("\nOutput:")
        print("  - Top 10 partnerships (players who played together most)")
        print("  - Top 10 opponent matchups (players who faced each other most)")
        print("\nExample:")
        print("  python analyze_session.py pickleball_session_20251203_211556.txt")
        sys.exit(0)
    else:
        filename = sys.argv[1]
    
    analyze_session(filename)
