"""
Network Fantasy War — Deep Tournament Analysis
Head-to-head matrix, deck profiles, matchup details.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prototype.card import ALL_CARDS
from prototype.game import GameState
from prototype.decks import DECKS, DECK_NAMES
from prototype.simulate import SmartAI
from collections import defaultdict


def run_matchup(deck1_name: str, deck2_name: str, seed: int) -> dict:
    """Run a single game between two decks."""
    random.seed(seed)
    
    deck_p1 = DECKS[deck1_name][:]
    deck_p2 = DECKS[deck2_name][:]
    
    game = GameState(deck_p1, deck_p2)
    
    # Force formations
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
        
        sq_pos = [(1,3),(1,5),(2,3),(2,5)]
        for i,(l,m) in enumerate(sq_pos):
            game.board.place_card(player, candidates[i], l, m)
        sq = candidates[:4]
        for a,b in [(0,1),(1,3),(3,2),(2,0)]:
            game.network.add_link(sq[a], sq[b])
        
        pt_pos = [(1,9),(1,11),(2,12),(2,10),(2,8)]
        for i,(l,m) in enumerate(pt_pos):
            game.board.place_card(player, candidates[4+i], l, m)
        pt = candidates[4:9]
        for a,b in [(0,1),(1,2),(2,3),(3,4),(4,0)]:
            game.network.add_link(pt[a], pt[b])
        
        game.actions_remaining = 4
        game.start_attack_phase()
        game.exit_phase()
    
    ai_p1 = SmartAI(game, 0)
    ai_p2 = SmartAI(game, 1)
    
    for _ in range(40):
        if game.game_over:
            break
        player = game.active_player
        game.start_turn()
        game.entry_phase()
        if game.game_over:
            break
        ai = ai_p1 if player == 0 else ai_p2
        ai.take_turn()
    
    # Detailed stats
    cards_p1 = sum(1 for cid, c in game.all_cards.items() if c.position and c.owner == 0)
    cards_p2 = sum(1 for cid, c in game.all_cards.items() if c.position and c.owner == 1)
    links_p1 = sum(1 for cid, c in game.all_cards.items() if c.owner == 0 and game.network.link_count(c) > 0)
    links_p2 = sum(1 for cid, c in game.all_cards.items() if c.owner == 1 and game.network.link_count(c) > 0)
    
    all_squads = game.network.find_squads(game.all_cards)
    sq_types = {}
    for s in all_squads:
        t = s.squad_type
        sq_types[t] = sq_types.get(t, 0) + 1
    
    # Damage dealt (seals lost by opponent)
    dmg_by_p1 = 30 - game.seals[1]
    dmg_by_p2 = 30 - game.seals[0]
    
    return {
        "winner": game.winner,
        "turns": game.turn_number - 1,
        "seals_p1": game.seals[0],
        "seals_p2": game.seals[1],
        "dmg_p1": dmg_by_p1,
        "dmg_p2": dmg_by_p2,
        "cards_p1": cards_p1,
        "cards_p2": cards_p2,
        "links_p1": links_p1,
        "links_p2": links_p2,
        "squad_types": sq_types,
    }


# ═══════════════════════════════════════════════════════════
# DEEP ANALYSIS
# ═══════════════════════════════════════════════════════════

print("DEEP TOURNAMENT ANALYSIS")
print("=" * 70)

deck_names = list(DECKS.keys())

# Run 3 games per matchup for better stats
GAMES = 3
print(f"Running {len(deck_names)} decks × {len(deck_names)-1} matchups × {GAMES} games = {len(deck_names)*(len(deck_names)-1)//2*3} games...\n")

# Matrix: h2h[d1][d2] = (wins_d1, wins_d2, avg_turns, avg_seal_diff)
h2h = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
deck_totals = {d: {"w": 0, "l": 0, "turns": 0, "dmg_dealt": 0, "dmg_taken": 0, 
                    "cards": 0, "links": 0, "games": 0} for d in deck_names}

for i, d1 in enumerate(deck_names):
    for j, d2 in enumerate(deck_names):
        if i >= j:
            continue
        
        w1 = w2 = total_t = seal_sum = 0
        for g in range(GAMES):
            seed = (i * 1000 + j * 100 + g) * 7 + 1
            r = run_matchup(d1, d2, seed)
            
            if r["winner"] == 0:
                w1 += 1
                deck_totals[d1]["w"] += 1
                deck_totals[d2]["l"] += 1
            else:
                w2 += 1
                deck_totals[d2]["w"] += 1
                deck_totals[d1]["l"] += 1
            
            total_t += r["turns"]
            seal_sum += r["seals_p1"] - r["seals_p2"]
            
            deck_totals[d1]["turns"] += r["turns"]
            deck_totals[d2]["turns"] += r["turns"]
            deck_totals[d1]["dmg_dealt"] += r["dmg_p1"]
            deck_totals[d2]["dmg_dealt"] += r["dmg_p2"]
            deck_totals[d1]["dmg_taken"] += r["dmg_p2"]
            deck_totals[d2]["dmg_taken"] += r["dmg_p1"]
            deck_totals[d1]["cards"] += r["cards_p1"]
            deck_totals[d2]["cards"] += r["cards_p2"]
            deck_totals[d1]["links"] += r["links_p1"]
            deck_totals[d2]["links"] += r["links_p2"]
            deck_totals[d1]["games"] += 1
            deck_totals[d2]["games"] += 1
        
        h2h[d1][d2] = [w1, w2, total_t / GAMES, seal_sum / GAMES]

# ═══ HEAD-TO-HEAD MATRIX ═══
print("HEAD-TO-HEAD MATRIX")
print("(Reading row vs column: row deck's record against column deck)")
print()
header = f"{'':20s}"
for d in deck_names:
    header += f" {DECK_NAMES[d].split('(')[0].strip():12s}"
print(header)
print("-" * (20 + 13 * len(deck_names)))

for d1 in deck_names:
    row = f"{DECK_NAMES[d1].split('(')[0].strip():20s}"
    for d2 in deck_names:
        if d1 == d2:
            row += f" {'---':12s}"
        elif d1 in h2h and d2 in h2h[d1]:
            w1, w2, _, _ = h2h[d1][d2]
            row += f" {f'{w1}-{w2}':12s}"
        elif d2 in h2h and d1 in h2h[d2]:
            w2, w1, _, _ = h2h[d2][d1]
            row += f" {f'{w1}-{w2}':12s}"
        else:
            row += f" {'?':12s}"
    print(row)

# ═══ DECK PROFILES ═══
print(f"\n{'='*70}")
print("DECK PROFILES (averages per game)")
print(f"{'='*70}")
print(f"{'Deck':22s} {'W':>3} {'L':>3} {'Win%':>6} {'DmgDealt':>8} {'DmgTaken':>8} {'Cards':>5} {'Links':>5} {'Turns':>5}")
print("-" * 70)

profiles = []
for d in deck_names:
    t = deck_totals[d]
    g = t["games"]
    if g == 0:
        continue
    wp = t["w"] / g * 100
    dd = t["dmg_dealt"] / g
    dt = t["dmg_taken"] / g
    ca = t["cards"] / g
    li = t["links"] / g
    tu = t["turns"] / g
    profiles.append((d, t["w"], t["l"], wp, dd, dt, ca, li, tu))

profiles.sort(key=lambda x: -x[3])

for d, w, l, wp, dd, dt, ca, li, tu in profiles:
    name = DECK_NAMES[d].split("(")[0].strip()
    print(f"{name:22s} {w:3d} {l:3d} {wp:5.1f}% {dd:8.1f} {dt:8.1f} {ca:5.1f} {li:5.1f} {tu:5.1f}")

# ═══ KEY INSIGHTS ═══
print(f"\n{'='*70}")
print("KEY INSIGHTS")
print(f"{'='*70}")

# Best offense
best_off = max(profiles, key=lambda x: x[4])
print(f"  🗡️  Best offense: {DECK_NAMES[best_off[0]].split('(')[0].strip()} ({best_off[4]:.1f} dmg/game)")

# Best defense (lowest damage taken)
best_def = min(profiles, key=lambda x: x[5])
print(f"  🛡️  Best defense: {DECK_NAMES[best_def[0]].split('(')[0].strip()} ({best_def[5]:.1f} taken/game)")

# Most board presence
most_cards = max(profiles, key=lambda x: x[6])
print(f"  📊 Most cards: {DECK_NAMES[most_cards[0]].split('(')[0].strip()} ({most_cards[6]:.1f} cards/game)")

# Most linked
most_links = max(profiles, key=lambda x: x[7])
print(f"  🔗 Most linked: {DECK_NAMES[most_links[0]].split('(')[0].strip()} ({most_links[7]:.1f} linked/game)")

# Biggest blowout
biggest_diff = max(profiles, key=lambda x: x[4] - x[5])
print(f"  💥 Best dmg diff: {DECK_NAMES[biggest_diff[0]].split('(')[0].strip()} (+{biggest_diff[4]-biggest_diff[5]:.1f})")

# Closest matchup analysis
print(f"\n  Closest matchups (2-1 splits):")
for d1 in deck_names:
    for d2 in deck_names:
        if d1 >= d2:
            continue
        key = (d1, d2) if d1 in h2h and d2 in h2h[d1] else (d2, d1)
        d1_k, d2_k = key
        if d1_k in h2h and d2_k in h2h[d1_k]:
            w1, w2, _, _ = h2h[d1_k][d2_k]
            if (w1 == 2 and w2 == 1) or (w1 == 1 and w2 == 2):
                n1 = DECK_NAMES[d1_k].split("(")[0].strip()
                n2 = DECK_NAMES[d2_k].split("(")[0].strip()
                print(f"    {n1} vs {n2}: {w1}-{w2}")

print(f"\n✓ Analysis complete.")
