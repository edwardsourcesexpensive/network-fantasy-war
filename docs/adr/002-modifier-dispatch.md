# ADR-002: Modifier dispatch system for passive abilities

**Status:** Accepted  
**Date:** 2026-07-28

## Context

NFW has 423 passive/trigger abilities across 370 cards. The original implementation used ad-hoc `_resolve_ability()` with keyword matching — fragile, hard to extend, and impossible to reason about at scale. Phase E (the passive ability implementation push) needed an architecture that could handle 250+ pending passives without exponential complexity growth.

## Decision

A hook-based modifier dispatch system. The engine exposes 17 named hooks at key game events:

```
before_attack, after_attack, before_link, after_link, before_play,
before_destroy, after_destroy, modify_squad, modify_damage,
modify_actions, on_ascend, on_move, grimoire_defense,
start_of_turn, end_of_turn, on_kill, on_enter
```

Each card with passive/trigger abilities registers `Modifier` objects into `_modifiers[hook_name]` at play time. When the engine reaches a hook point, it dispatches by iterating all registered modifiers for that hook, applying conditions and effects.

Temp modifiers (single-turn, conditional) auto-cleanup at `exit_phase()` via `_unregister_temp_modifiers()`.

**Key design rules:**

- Adding a new hook requires three non-negotiable changes: (1) key in `_modifiers` init dict, (2) trigger name in `_register_modifiers` allowed list, (3) dispatch code at the engine point. Missing any = silent failure.
- `start_of_turn`/`end_of_turn`/`on_kill` migrated from ad-hoc to dispatch as pure refactor — zero stat change.
- `on_enter` activation (E8, 2026-07-28) added 22 new patterns, bumping implementation from 229 to 251 (+5%).
- Handler ordering in `use_ability()` is top-to-bottom with early return. Compound handlers (e.g., "gana sello + oponente pierde sellos") must check both effects in the first-matching branch.

## Alternatives considered

1. **Ad-hoc per-ability resolution (rejected)** — A single function with 250+ keyword-matching branches. Every new card ability requires a new if/elif. Ordering bugs compound silently. No way to test in isolation. This was the status quo pre-Phase E.

2. **Event bus / pub-sub (rejected)** — Full decoupling with event objects and subscribers. Overkill for a single-process Python game. Adds indirection without benefit — the engine IS the event source and the dispatch IS the handler.

3. **Scripted abilities (Lua/Python eval) (rejected)** — Embed ability logic in card data as executable strings. Too dangerous (code injection from card text), too hard to balance, and requires a sandbox.

4. **Hook-based dispatch (chosen)** — Each hook is a named list. Modifiers are data, not code. Conditions are declarative. Engine owns when dispatch happens; cards own what happens. Scales linearly: adding a new card with an existing trigger type is zero engine changes.

## Consequences

- **Current coverage**: 10/17 hooks implemented. Remaining: on_attack, on_defend, after_attack, before_play, modify_actions, conditional_draw, spy_infiltrate.
- **Regression risk**: The three-change requirement for new hooks is a footgun. Two verification scripts exist to catch missing registrations.
- **Performance**: Iterating `_modifiers[hook]` per trigger is O(n) in active modifiers. Acceptable for a card game with ~10-20 active cards per board.
- **Card design freedom**: Future cards can hook into any existing trigger without engine changes. A new card with `on_kill: draw 1` just registers a modifier — no code.
