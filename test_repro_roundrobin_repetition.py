
from python.roundrobin import generate_round_robin_queue
from python.pickleball_types import Player, PlayerStats
from python.session import Session

def test_round_robin_partnership_variety():
    # Create 12 players
    players = [Player(id=str(i), name=f"Player{i}") for i in range(12)]
    
    # Run the generator
    matches = generate_round_robin_queue(
        players=players,
        session_type='doubles',
        banned_pairs=[],
        max_matches=50
    )
    
    # Analyze partnerships
    partnerships = {}
    seen_pairs = set()
    repeats_found_at_index = []
    
    # Total possible pairs
    all_possible_pairs = set()
    from itertools import combinations
    for i in range(8):
        for j in range(i+1, 8):
            all_possible_pairs.add(tuple(sorted((str(i), str(j)))))
            
    print(f"Total possible pairs: {len(all_possible_pairs)}")
    
    for i, match in enumerate(matches):
        pairs_in_match = []
        t1 = tuple(sorted(match.team1))
        t2 = tuple(sorted(match.team2))
        pairs_in_match.append(t1)
        pairs_in_match.append(t2)
        
        for pair in pairs_in_match:
            if pair in seen_pairs:
                # We found a repeat!
                # Check if there were still unused pairs available
                unused_pairs = all_possible_pairs - seen_pairs
                if unused_pairs:
                    print(f"Repeat found at match {i} for pair {pair}. Unused pairs remaining: {len(unused_pairs)}")
                    # This is the condition we want to avoid: repeating while unused pairs exist.
                else:
                    print(f"Repeat found at match {i} for pair {pair}. No unused pairs left (expected behavior).")
                
                repeats_found_at_index.append((i, pair))
            
            seen_pairs.add(pair)
            if pair in partnerships:
                partnerships[pair] += 1
            else:
                partnerships[pair] = 1

    print("\nTotal matches generated:", len(matches))
    if repeats_found_at_index:
        print(f"First repeat at match index {repeats_found_at_index[0][0]}")


if __name__ == "__main__":
    test_round_robin_partnership_variety()
