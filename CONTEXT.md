# CONTEXT.md — Network Fantasy War

Domain glossary. No implementation details. Updated lazily as terms resolve.

## Core Concepts

- **Card (Carta)**: A unit with HP, damage bonus (D), link capacity (V), color/faction, allowed layers, formations, and abilities. 370 card definitions in `prototype/card.py`.
- **Grimoire (Grimorio)**: Each player's life total. Represented as seals. When seals reach 0, that player loses.
- **Layer (Capa)**: Vertical position on the board. L1 (front), L2 (middle), L3 (back). Movement between layers is ascension.
- **Meridian (Meridiano)**: Horizontal position on the board (0–14). Cards are placed at (layer, meridian) coordinates.
- **Board (Tablero)**: 3-layer × 15-meridian grid per player. Each player has their own territory.
- **Deck (Mazo)**: 50 cards. 8 prebuilt decks with faction distributions.
- **Grado**: Card tier (1–3). Auto-computed from allowed layers: G1 = max layer 1, G2 = max layer 2, G3 = max layer 3. Logistrones and spies are always G3. Used by Monstruos faction effect (can remove enemy cards with grado less than squad damage).

## Spatial Rules

- **Link (Vínculo)**: Connection between two cards. Requires valid spatial distance. Consumes 1 link capacity (V) per endpoint. Formed during ACTIONS phase.
- **Spatial distance**: Same layer: dh=2 is "corta", dh=3 is "media". dh=0, dh=1, dh≥4 are invalid. Cross-layer (dv=1): dh≤1 is "corta", dh=2 is "media", dh=3 is "larga". Two-layer gap (dv=2): dh=1 is "larga".
- **Same-layer adjacent (dh=1) is invalid**: Two cards 1 meridian apart on the same layer cannot link. Minimum same-layer distance is dh=2. See ADR-004.
- **Squad (Escuadrón)**: A polygon formed by linked cards belonging to the same player. Cross-owner links (spy infiltration, frontier↔L3) do not fuse squads across players. A card belongs to at most one squad — membership is exclusive. Types: line, triangle, square, pentagon. Higher polygons grant higher damage multipliers.
- **Potenciamiento**: Damage bonus from friendly-alive squad overlap, respecting live color overrides. Multiplier depends on polygon type (line=1, triangle=2, square=3, pentagon=4). Overlap means counting friendly squads whose members intersect with the attacking squad.

## Card Entry

- **L1-only entry**: Cards enter at L1 by default. No exceptions unless the card has Vanguardia or Línea de Fuego. See ADR-001.
- **Vanguardia**: Passive ability. Card may enter directly at L2.
- **Línea de Fuego**: Passive ability. Card may enter directly at L3 (also grants L2).
- **Spies (Espías)**: Exempt from layer restrictions. Enter at the frontier.
- **Logistrones**: Exempt from layer and formation restrictions. Cannot form polygons.

## Factions (Colores)

Saboteador, Espía, Monstruo, Militar, Guerrero, Sellador, Festivo, Político, Incoloro, Naturaleza, Alquimista, Sabio, Logistrón.

- **Color change**: A card's printed color is temporarily replaced (e.g., by an active ability). All effects — faction triggers, potenciamiento, targeting — see the new color. Cleared at end of turn.
- **Color exclusion**: A card's printed color is ignored when tallying squad dominant color (e.g., Incoloro cards). The card retains its printed color for all other purposes.

## Abilities

- **Active ability**: Costs [N] actions to activate. Marked with `[1]` or `[2]` in card text.
- **Passive ability**: Always active. No action cost.
- **Trigger**: Event-driven passive (on_enter, on_kill, start_of_turn, end_of_turn, on_attack, on_ascend, permanent). Dispatched via modifier system. See ADR-002.
- **Sigilo**: Absolute. Card cannot be targeted by attacks. Damage redirection (Guardaespaldas) bypasses. See ADR-003.

### Trigger types

| Trigger | Meaning |
|---|---|
| `on_enter` | When the card is played onto the board |
| `start_of_turn` | At the beginning of the card owner's turn |
| `end_of_turn` | At the end of the card owner's turn |
| `on_kill` | When this card destroys an enemy card |
| `on_attack` | When this card attacks |
| `on_ascend` | When this card ascends to a higher layer |
| `permanent` | Always active while the card is on the board |
