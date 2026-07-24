"""
Network Fantasy War — Deck Tournament
Round-robin: all 8 decks face each other. 3 games per matchup.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prototype.card import ALL_CARDS, Color, CardDef
from prototype.game import GameState, Phase
from prototype.decks import DECKS, DECK_NAMES
from prototype.simulate import SmartAI, simulate_game


def run_matchup(deck1_name: str, deck2_name: str, seed: int) -> dict:
    """Run a single game between two decks. Returns result dict."""
    random.seed(seed)
    
    deck_p1 = DECKS[deck1_name][:]
    deck_p2 = DECKS[deck2_name][:]
    
    game = GameState(deck_p1, deck_p2)
    
    # Force squares + pentagons for both
    for player in [0, 1]:
        game.active_player = player
        game.start_turn()
        game.entry_phase()
        
        candidates = []
        for source in [game.hands[player], game.decks[player]]:
            for c in source:
                if c.definition.link_capacity >= 2 \
                   and not c.definition.is_spy \
                   and not c.definition.is_logistron \
                   and 1 in c.definition.allowed_layers \
                   and 2 in c.definition.allowed_layers \
                   and c not in candidates:
                    candidates.append(c)
                    if len(candidates) >= 9:
                        break
            if len(candidates) >= 9:
                break
        
        if len(candidates) < 9:
            continue
        
        for c in candidates:
            if c in game.hands[player]:
                game.hands[player].remove(c)
            elif c in game.decks[player]:
                game.decks[player].remove(c)
        
        # Square
        sq_pos = [(1,3),(1,5),(2,3),(2,5)]
        for i,(l,m) in enumerate(sq_pos):
            game.board.place_card(player, candidates[i], l, m)
        sq = candidates[:4]
        for a,b in [(0,1),(1,3),(3,2),(2,0)]:
            game.network.add_link(sq[a], sq[b])
        
        # Pentagon
        pt_pos = [(1,9),(1,11),(2,12),(2,10),(2,8)]
        for i,(l,m) in enumerate(pt_pos):
            game.board.place_card(player, candidates[4+i], l, m)
        pt = candidates[4:9]
        for a,b in [(0,1),(1,2),(2,3),(3,4),(4,0)]:
            game.network.add_link(pt[a], pt[b])
        
        game.actions_remaining = 4
        game.start_attack_phase()
        game.exit_phase()
    
    # AI play
    ai_p1 = SmartAI(game, 0)
    ai_p2 = SmartAI(game, 1)
    
    max_turns = 40
    for _ in range(max_turns):
        if game.game_over:
            break
        player = game.active_player
        game.start_turn()
        game.entry_phase()
        if game.game_over:
            break
        ai = ai_p1 if player == 0 else ai_p2
        ai.take_turn()
    
    winner = game.winner
    turns = game.turn_number - 1
    
    # Count squads
    all_squads = game.network.find_squads(game.all_cards)
    sq_types = {}
    for s in all_squads:
        t = s.squad_type
        sq_types[t] = sq_types.get(t, 0) + 1
    
    return {
        "winner": winner,
        "turns": turns,
        "seals_p1": game.seals[0],
        "seals_p2": game.seals[1],
        "squad_types": sq_types,
        "deck1": deck1_name,
        "deck2": deck2_name,
    }


# ═══════════════════════════════════════════════════════════
# TOURNAMENT
# ═══════════════════════════════════════════════════════════

print("╔══════════════════════════════════════════════════════════════╗")
print("║   NETWORK FANTASY WAR — Tournament                         ║")
print("║   8 decks · round-robin · 3 games per matchup              ║")
print("╚══════════════════════════════════════════════════════════════╝")

deck_names = list(DECKS.keys())
GAMES_PER_MATCHUP = 1  # Quick tournament

# Results matrix
wins = {d: 0 for d in deck_names}
losses = {d: 0 for d in deck_names}
total_turns = {d: 0 for d in deck_names}
games_played = {d: 0 for d in deck_names}
seal_diff = {d: 0 for d in deck_names}

all_results = []

for i, d1 in enumerate(deck_names):
    for j, d2 in enumerate(deck_names):
        if i > j:
            continue  # Only play each pair once (or mirror matches)
        if i == j:
            continue  # Skip mirror for now
        
        matchup_wins = {d1: 0, d2: 0}
        
        for g in range(GAMES_PER_MATCHUP):
            seed = (i * 100 + j * 10 + g) * 7 + 1
            result = run_matchup(d1, d2, seed)
            all_results.append(result)
            
            winner_name = d1 if result["winner"] == 0 else d2
            loser_name = d2 if result["winner"] == 0 else d1
            
            wins[winner_name] += 1
            losses[loser_name] += 1
            games_played[d1] += 1
            games_played[d2] += 1
            total_turns[d1] += result["turns"]
            total_turns[d2] += result["turns"]
            
            if result["winner"] == 0:
                seal_diff[d1] += result["seals_p1"] - result["seals_p2"]
                seal_diff[d2] += result["seals_p2"] - result["seals_p1"]
            else:
                seal_diff[d1] += result["seals_p1"] - result["seals_p2"]
                seal_diff[d2] += result["seals_p2"] - result["seals_p1"]
            
            matchup_wins[winner_name] += 1
        
        # Print matchup result
        d1_short = DECK_NAMES[d1].split("(")[0].strip()
        d2_short = DECK_NAMES[d2].split("(")[0].strip()
        print(f"  {d1_short:25s} vs {d2_short:25s}  →  {matchup_wins[d1]}-{matchup_wins[d2]}")

# ═══ STANDINGS ═══
print(f"\n{'='*70}")
print(f"STANDINGS")
print(f"{'='*70}")
print(f"{'Deck':30s} {'W':>3} {'L':>3} {'Win%':>6} {'AvgT':>5} {'SealΔ':>6}")
print(f"{'-'*60}")

# Sort by win%
standings = []
for d in deck_names:
    w = wins[d]
    l = losses[d]
    gp = games_played[d]
    if gp == 0:
        continue
    win_pct = w / gp * 100
    avg_t = total_turns[d] / gp
    sd = seal_diff[d] / gp
    standings.append((d, w, l, win_pct, avg_t, sd))

standings.sort(key=lambda x: (-x[3], -x[5]))  # Win% then seal diff

for d, w, l, wp, at, sd in standings:
    name = DECK_NAMES[d].split("(")[0].strip()
    print(f"{name:30s} {w:3d} {l:3d} {wp:5.1f}% {at:5.1f} {sd:+6.1f}")

# ═══ SQUAD TYPE DISTRIBUTION ═══
print(f"\n{'='*70}")
print(f"SQUAD TYPES SEEN")
print(f"{'='*70}")
all_squad_types = {}
for r in all_results:
    for t, count in r["squad_types"].items():
        all_squad_types[t] = all_squad_types.get(t, 0) + count
for t in ["line", "triangle", "square", "square_ampliado", "pentagon", "pentagon_ampliado"]:
    if t in all_squad_types:
        print(f"  {t:20s}: {all_squad_types[t]:4d}")
