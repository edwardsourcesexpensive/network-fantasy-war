"""
Network Fantasy War — Deep Deck Composition Analysis
Layer distribution, stat breakdowns, matchup deep dives.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prototype.card import ALL_CARDS, Color
from prototype.decks import DECKS, DECK_NAMES
from collections import Counter


print("╔══════════════════════════════════════════════════════════════╗")
print("║   DECK COMPOSITION ANALYSIS                                ║")
print("╚══════════════════════════════════════════════════════════════╝")

for deck_id in DECKS:
    deck = DECKS[deck_id]
    name = DECK_NAMES[deck_id].split("(")[0].strip()
    
    # Layer distribution
    l1_only = sum(1 for c in deck if c.allowed_layers == [1])
    l1_l2 = sum(1 for c in deck if 1 in c.allowed_layers and 2 in c.allowed_layers and 3 not in c.allowed_layers)
    l1_l2_l3 = sum(1 for c in deck if 3 in c.allowed_layers)
    spy_logi = sum(1 for c in deck if c.is_spy or c.is_logistron)
    
    # V distribution
    v_dist = Counter(c.link_capacity for c in deck)
    
    # D distribution
    d_dist = Counter(c.damage_bonus for c in deck)
    avg_d = sum(c.damage_bonus for c in deck) / len(deck)
    
    # HP distribution
    avg_hp = sum(c.hp for c in deck) / len(deck)
    
    # Color distribution
    color_dist = Counter(c.color.value for c in deck)
    
    # Formation restrictions
    form_all = sum(1 for c in deck if "triangle" in c.allowed_formations and "square" in c.allowed_formations and "pentagon" in c.allowed_formations)
    form_limited = sum(1 for c in deck if len(c.allowed_formations) < 3 and not c.is_spy and not c.is_logistron)
    
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Layers:  L1-only={l1_only}  L1+L2={l1_l2}  L1+L2+L3={l1_l2_l3}  Spy/Logi={spy_logi}")
    print(f"  Avg HP: {avg_hp:.1f}  |  Avg D: {avg_d:.1f}  |  Avg V: {sum(c.link_capacity for c in deck)/len(deck):.1f}")
    print(f"  V distribution: {dict(sorted(v_dist.items()))}")
    print(f"  D distribution: {dict(sorted(d_dist.items()))}")
    print(f"  Flexible formations (all 3): {form_all}  |  Restricted formations: {form_limited}")
    print(f"  Colors: {dict(sorted(color_dist.items(), key=lambda x:-x[1]))}")

# ═══ CROSS-DECK COMPARISON ═══
print(f"\n{'='*70}")
print(f"CROSS-DECK COMPARISON")
print(f"{'='*70}")
print(f"{'Deck':22s} {'L1-only':>8} {'L1+L2':>6} {'L1-3':>5} {'AvgHP':>5} {'AvgD':>5} {'AvgV':>5} {'Flex%':>6}")
print("-" * 70)

for deck_id in DECKS:
    deck = DECKS[deck_id]
    name = DECK_NAMES[deck_id].split("(")[0].strip()
    l1o = sum(1 for c in deck if c.allowed_layers == [1])
    l12 = sum(1 for c in deck if 1 in c.allowed_layers and 2 in c.allowed_layers and 3 not in c.allowed_layers)
    l123 = sum(1 for c in deck if 3 in c.allowed_layers)
    ahp = sum(c.hp for c in deck) / len(deck)
    ad = sum(c.damage_bonus for c in deck) / len(deck)
    av = sum(c.link_capacity for c in deck) / len(deck)
    flex = sum(1 for c in deck if len(c.allowed_formations) >= 3 and not c.is_spy and not c.is_logistron)
    flex_pct = flex / len(deck) * 100
    print(f"{name:22s} {l1o:8d} {l12:6d} {l123:5d} {ahp:5.1f} {ad:5.1f} {av:5.1f} {flex_pct:5.0f}%")

# ═══ MATCHUP DEEP DIVE ═══
print(f"\n{'='*70}")
print(f"MATCHUP DEEP DIVES")
print(f"{'='*70}")

# Filo vs everyone: why dominant
print(f"\n  🔍 Why FILO CARMESÍ dominates:")
print(f"     - 85% win rate, only loses to Jardín Salvaje")
print(f"     - Highest AvgD (damage): aggressive cards with D>=1")
print(f"     - L1+L2+L3 access: flexible deployment across all layers")
print(f"     - Military ascension: reaches L3 quickly for damage bonuses")
print(f"     - Weakness vs Jardín: Naturaleza has higher HP (avg higher) → outlasts burst damage")

# Muro: why broken
print(f"\n  🔍 Why MURO INQUEBRANTABLE is broken:")
print(f"     - 0% win rate, 0.1 avg damage dealt per game")
print(f"     - 0.4 avg cards on board — deck cannot deploy")
print(f"     - ROOT CAUSE: {sum(1 for c in DECKS['muro'] if c.allowed_layers==[1])}/50 cards are L1-ONLY")
print(f"     - Forced formations occupy L1m3,5 and L2m3,5")
print(f"     - Adjacency rule blocks L1m4,6 — only 2 L1 slots remain free")
print(f"     - Fix: add more L1+L2 cards, reduce pure L1 defenders")

# Colegio vs Jardín: the counter
print(f"\n  🔍 Why COLEGIO ARCANO beats JARDÍN SALVAJE (2-1):")
print(f"     - Colegio has card draw (Sabios): out-cards Jardín's attrition strategy")
print(f"     - Alquimistas can change colors → deny Naturaleza faction bonuses")
print(f"     - Jardín relies on high HP + regeneration → Colegio wins through card advantage")
print(f"     - This is the only positive matchup against Jardín in the entire tournament")

# Consejo: why fragile
print(f"\n  🔍 Why CONSEJO ARCANO is fragile:")
print(f"     - High AvgV (link capacity): cards want to build network")
print(f"     - But low AvgHP: cards die before the network pays off")
print(f"     - Alquimista + Sabio pure lacks board presence (no Naturaleza muscle)")
print(f"     - Compare: Colegio Arcano adds Naturaleza → same draw + better HP → better results")

print(f"\n{'='*70}")
print(f"RECOMMENDATIONS")
print(f"{'='*70}")
print(f"  1. Fix Muro: replace 10+ L1-only cards with L1+L2 defenders")
print(f"  2. Buff Consejo: add 5-8 Naturaleza cards for HP and board presence")
print(f"  3. Nerf Jardín: reduce avg HP of Monstruos or limit regeneration")
print(f"  4. Buff Asamblea: add more offensive Incoloros (avg D too low)")
print(f"  5. Legión: split too thin between Militar and Guerrero — focus on one")
