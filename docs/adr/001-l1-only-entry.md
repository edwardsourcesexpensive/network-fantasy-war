# ADR-001: L1-only card entry with ability-based exceptions

**Status:** Accepted  
**Date:** 2026-07-27

## Context

The board has three layers (L1/L2/L3). The engine supports placing cards at any layer, but allowing unrestricted entry creates balance problems: high-value cards could be placed at L3 immediately, making them hard to reach and attack. A restriction was needed.

## Decision

All cards enter at L1 by default. Two passive abilities grant exceptions:

- **Vanguardia**: Allows direct placement at L2 (~31% of L2-capable cards)
- **Línea de Fuego**: Allows direct placement at L3, also grants L2 (~30% of L3-capable cards)

These abilities are distributed across the 370-card pool using `random.seed(42)` for reproducibility. Engine enforces the restriction in `play_card()`: attempting L2 without Vanguardia or Línea de Fuego returns an error; L3 requires Línea de Fuego.

Spies and Logistrones are exempt: Spies enter at the frontier, Logistrones have no layer restriction.

## Alternatives considered

1. **Open entry (any card any layer)** — Rejected. Would allow players to stack L3 immediately with high-HP cards, making the game static. No strategic tension around positioning.

2. **Phase-based unlock (L2 unlocks at turn 3, L3 at turn 5)** — Rejected. Adds a clock mechanic unrelated to card design. Would require UI to track unlock state. Players can't plan around their own deck's capabilities.

3. **Mana/payment system (pay seals to enter higher layers)** — Rejected. Adds a second resource system on top of actions. Complexity not justified for a TCG that already has action economy and link capacity as limiting factors.

4. **Ability-based exceptions (chosen)** — Ability text lives on the card, visible to both players from hand. Distribution via fixed seed means the meta is stable. Creates strategic decisions: do you play your Vanguardia card now at L2, or save it?

## Consequences

- **Forced cross-layer building**: Same-layer links require dh≥2 spacing. Players must use L1→L2 ascension or Vanguardia bridge to form triangles. This shapes the entire spatial game.
- **~20% triangle rate for AI**: The bot forms triangles in ~20% of turns using Vanguardia bridge geometry (L1:m, L2:m+1, L1:m+2).
- **Card design constraint**: Future cards must declare `allowed_layers` realistically. A card with `allowed_layers=[1,2,3]` still only enters at L1 unless it has the right ability.
- **Geometric constraint**: Ascending a card from L1:m+2 to L2:m+2 breaks same-layer spacing (dh=2 pair becomes dv=1,dh=0 which is invalid). The Vanguardia bridge is the only geometrically valid way to form same-turn triangles.
