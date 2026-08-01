# ADR-004: Same-layer adjacent cards (dh=1) cannot link

**Status:** Accepted  
**Date:** 2026-07-27

## Context

The board uses axial coordinates (layer, meridian). During development, the same spatial distance that governs placement also governs linking. Two cards at the same layer, 1 meridian apart (dh=1, dv=0) are visually adjacent — and players intuitively try to link them. The engine rejects these links. This is the single most common pitfall in NFW development and gameplay.

## Decision

`spatial_distance(dv=0, dh=1)` returns `None` (invalid). The complete same-layer distance table:

| dh | Result |
|---|---|
| 0 | Invalid (same cell) |
| 1 | Invalid (adjacent, cannot link) |
| 2 | "corta" |
| 3 | "media" |
| ≥4 | Invalid (too far) |

Only dh=2 and dh=3 are valid for same-layer links. Cross-layer links (dv=1) have wider tolerance: dh≤1 is "corta", dh=2 is "media", dh=3 is "larga".

This is enforced at the engine level in `board.spatial_distance()` and `board._can_place_horizontal()`. Both placement and linking respect the same geometry.

## Alternatives considered

1. **Allow dh=1 links (rejected)** — Would allow every adjacent card to link trivially. With 15 meridians and 3 layers, players could form chains instantly without spatial thinking. Squads would be too easy: any three cards in a row auto-form a line. Eliminates the core spatial puzzle.

2. **Allow dh=1 but with penalty (rejected)** — dh=1 links are valid but don't count toward squad formation. Adds a special case: "some links form squads, some don't." Confusing to players, complicated to implement.

3. **Allow dh=1 only for Logistrones (rejected)** — Logistrones are already exempt from formation rules and linking cost. Giving them dh=1 access would make them universal connectors, trivializing squad formation when Logistrones are in play.

4. **dh=2 minimum (chosen)** — Forces deliberate positioning. Cards must be placed with ≥2 meridians between them to form same-layer links. Cross-layer linking at dh≤1 creates the Vanguardia bridge pattern (ADR-001). The spatial constraint IS the game.

## Consequences

- **Vanguardia bridge is the workaround**: To form same-turn triangles, play a Vanguardia card at L2 between two L1 cards spaced dh=2 apart. This is the only geometrically valid way to form a triangle in one turn. See ADR-001.
- **Bot placement scoring**: Bot must score positions by dh=2 proximity, not dh≤1. Early bot implementations had `links=0` because dh=1 placement scoring silently produced invalid link attempts. Fixed by scoring only dh=2 positions.
- **UI**: The UI must not prevent clicking adjacent cards (players should be allowed to try), but the error must be visible in the game log. Silent rejection without feedback was a recurring bug.
- **Design constraint**: Cards with V=1 cannot form triangles (need V≥2 for all three nodes in a 3-cycle). This makes link capacity a critical stat beyond just "how many links can this card make."
- **Grado system interacts**: Monstruos faction effect benefits cards at L1. The dh=2 constraint means Monstruos cards must either stay at L1 with deliberate spacing or ascend, risking isolation.
