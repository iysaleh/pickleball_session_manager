"""
Analyze pickleball session exports to find partnership and opponent stats
"""
import re
import sys
from collections import defaultdict
from pathlib import Path


def analyze_session(filename):
    """Parse session file and analyze partnerships and opponents"""
    
    if not Path(filename).exists():
        print(f"Error: File not found: {filename}")
        sys.exit(1)
    
    with open(filename, 'r') as f:
        content = f.read()
    
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
        
        # Parse match: "Player1, Player2: 11 beat Player3, Player4: 7"
        # The format is: "p1, p2: X beat p3, p4: Y [time]" or similar
        match = re.match(r'(.+?),\s*(.+?):\s*(\d+)\s+beat\s+(.+?),\s*(.+?):\s*(\d+)', line)
        
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
