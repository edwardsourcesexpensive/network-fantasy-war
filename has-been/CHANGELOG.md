# Network Fantasy War — Changelog

---

## 2026-07-25 · Regla de entrada: Vanguardia & Línea de fuego

- **Nueva regla**: Toda carta debe entrar al campo de batalla en L1. Ya no se permite jugar directamente en L2 o L3.
- **Vanguardia**: habilidad pasiva (`on_enter`) que permite entrada directa en L2. ~31% de cartas con acceso a L2 la poseen (71 cartas).
- **Línea de fuego**: habilidad pasiva (`on_enter`) que permite entrada directa en L3. ~30% de cartas con acceso a L3 la poseen (37 cartas).
- Espías y logistrones exentos de la regla.
- UI: solo celdas L1 se marcan como jugables. IA ajustada para solo intentar capas válidas.
- `rules-reference.md` y PDF actualizados con la nueva regla.

---

## Session 1 — 2026-07-24 · Foundation

- [x] Read and analyzed original design doc (`Network Fantasy War.docx`)
- [x] Created formal rulebook (`rules-reference.md`, 17 sections)
- [x] Resolved 8 pending design issues:
  - Mulligan: accumulating seal cost
  - Deck-out: fatigue damage (1 seal per missed draw)
  - Espías: parasite mechanic (sabotage + intelligence)
  - Colors: 10 factions + 2 specials = 12
  - Ampliado with 0 internal nodes = basic
  - Link cap: V stat per card
  - Multi-attack: each squad attacks once/turn
  - Card play cost: always 1 action
- [x] Designed defense mechanic (defender squad, net damage)
- [x] Created skill `network-fantasy-war` v1.0

## Session 2 — 2026-07-24 · Mini-Set + Prototype

- [x] Designed 15-card mini-set (1 per faction + logistrones + spies)
- [x] Built Python prototype (`prototype/`):
  - `card.py`: Card data structures + mini-set
  - `board.py`: 3×15 battlefield, adjacency, distances
  - `network.py`: Links, initial squad detection
  - `game.py`: Turn flow, actions, combat
  - `cli.py`: Hotseat CLI for 2 players
- [x] Tested: card placement, linking, turn flow

## Session 3 — 2026-07-24 · Wave 2 + Mechanics

- [x] Designed 25 more cards (total 40, `cards-wave2.md`)
- [x] Rewrote squad detection: DFS cycle finding (line, triangle, square, pentagon)
- [x] Implemented spy mechanics (frontier, infiltration, sabotage)
- [x] Implemented active defense (defender chooses squad)
- [x] Built card ability trigger system
- [x] Improved CLI with full command set
- [x] Tested: triangles, squares, pentagons all working
- [x] Ran 3 automated games (40 cards)

## Session 4 — 2026-07-24 · Wave 3 + Smart AI

- [x] Designed 40 more cards (total 80, `cards-wave3.md`)
- [x] Built SmartAI with polygon-building strategy
- [x] Position scoring for triangle/squares
- [x] Ran 3 games: triangles forming (1-2 per game)
- [x] Skill updated to v2.0

## Session 5 — 2026-07-24 · Wave 4 + Square Demo

- [x] Designed 40 more cards (total 120, `cards-wave4.md`)
- [x] Demonstrated square formation manually
- [x] Forced squares in simulation: 1-2 squares per game
- [x] Games with squares: 7-10 turns (40% faster)
- [x] Skill updated to v3.0

## Session 6 — 2026-07-24 · Square Ampliado Fix + Decks 1-4

- [x] Designed 40 more cards (total 160, `cards-wave5.md`)
- [x] Fixed `square_ampliado` detection bug:
  - Root cause: 4-cycle search picked wrong perimeter
  - Fix: try all 4-cycles, pick one maximizing internal connections
- [x] Confirmed `pentagon_ampliado` working (dmg=6, emp=9)
- [x] Created 4 preconstructed decks:
  - Muro Inquebrantable (Sellador+Festivo)
  - Filo Carmesí (Guerrero+Militar)
  - Red de Sombras (Saboteador+Espía+Monstruo)
  - Colegio Arcano (Alquimista+Sabio+Naturaleza)
- [x] Skill updated to v4.1

## Session 7 — 2026-07-24 · Wave 6 + Pentagon Demo

- [x] Designed 40 more cards (total 200, `cards-wave6.md`)
- [x] Forced pentagons in simulation: 2 squares + 2 pentagons per game
- [x] All 7 polygon types confirmed working
- [x] Skill updated to v4.0 (then v4.1 after ampliado fix)

## Session 8 — 2026-07-24 · Wave 7 + Decks 5-8

- [x] Designed 100 more cards (total 300, `cards-wave7.md`)
- [x] Created 4 more preconstructed decks (`precon-decks-2.md`):
  - Asamblea Popular (Político+Incoloro)
  - Legión de Acero (Militar+Guerrero)
  - Jardín Salvaje (Naturaleza+Monstruo)
  - Consejo Arcano (Alquimista+Sabio)
- [x] All 300 cards integrated into `prototype/card.py`
- [x] Skill updated to v5.0

## Session 9 — 2026-07-24 · Deck Integration + Changelog

- [x] Created `prototype/decks.py`: 8 preconstructed decks with lookup API
- [x] Updated `prototype/cli.py`: deck selection menu at startup
- [x] Both players choose from 8 decks or random pool
- [x] Padded all decks to exactly 50 cards
- [x] Created `CHANGELOG.md` with full project history
- [x] Skill updated to v5.1

## Session 10 — 2026-07-24 · Wave 8 + Deck Sync + Final Audit

- [x] Designed 30 reinforcement cards (`cards-wave8.md`)
- [x] Updated Asamblea → v4 (D: 0.1→0.7), Consejo → v4 (D: 0.2→0.9)
- [x] Synced `precon-decks.md` with code v4 lists
- [x] Full audit: rules, code, 330 cards, 8 decks verified
- [x] Skill v5.3

## Session 11 — 2026-07-24 · Ascend Rule Fix

- [x] Clarified ascend rule in `rules-reference.md` §5.3: ascend respects `allowed_layers`
- [x] Implemented check in `game.py` `can_ascend`: blocks L2→L3 if not allowed
- [x] Updated `simulate.py` AI to check target layer before ascending
- [x] Rule: cards with `allowed_layers=[1,2]` cannot ascend to L3
- [x] Verified: L1-only → blocked, L1+L2 → L1→L2 ok, L2→L3 blocked

## Session 12 — 2026-07-24 · Waves 9-10 + Deck Integration

- [x] Designed 20 Wave 9 cards: anchored to L1/L2 (`cards-wave9.md`)
  - 8 L1-only, 8 L1+L2, 4 Logistrones anclados
- [x] Designed 20 Wave 10 cards: more L1/L2 for missing factions (`cards-wave10.md`)
  - Saboteadores, Festivos, Espías especiales, Incoloros
- [x] Added all 40 cards to `card.py` (total 370)
- [x] Updated all 8 decks to v5 with 2-6 anchored cards each
- [x] Tournament re-run: results stable (Filo 85.7%, Muro 71.4%, Jardín 71.4%)
- [x] Skill v5.5, Changelog updated

---

## Totals

| Metric | Count |
|---|---|
| Cards designed | 370 |
| Card waves | 10 |
| Preconstructed decks | 8 (v5) |
| Polygon types | 7 |
| Python files | 12 |
| Sessions logged | 12 |
| Deployable files | 11 |
