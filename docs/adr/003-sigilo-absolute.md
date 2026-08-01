# ADR-003: Sigilo absolute — no attack targeting, no exceptions

**Status:** Accepted  
**Date:** 2026-07-27

## Context

21 cards have "Sigilo: no puede ser atacado" or equivalent text. The ambiguity: does "cannot be attacked" mean (a) cannot be directly targeted, (b) cannot be hit by any attack including AoE/chain/secondary effects, or (c) something in between? The resolution affects every attack in the game and every future ability that references targeting.

## Decision

Sigilo is absolute. A card with Sigilo cannot be targeted by any attack, from any source, under any circumstances. This includes:

- Direct player attacks (click target → attack)
- Ability-forced attacks ("force target to attack X")
- Indirect/secondary attacks ("attack all adjacent cards")
- Chain attacks ("after destroying target, attack another")

**One bypass:** Guardaespaldas damage redirection. Redirection is not an attack — it's moved damage. If a Guardaespaldas redirects damage to a Sigilo card, the Sigilo card receives the damage. This is consistent: Sigilo blocks attack *targeting*, not damage *receipt*.

## Alternatives considered

1. **Partial Sigilo — direct targeting only (rejected)** — "Cannot be directly targeted" but vulnerable to AoE, chain, splash. Creates an "is this a direct attack?" classification problem for every new ability. Designers must remember to tag attacks as direct/indirect. Inevitably leads to bugs.

2. **Piercing — some attacks ignore Sigilo (rejected)** — A "piercing" keyword that bypasses Sigilo. Adds counterplay but also adds a counter-counterplay layer. If piercing exists, every attack must specify whether it pierces. Sigilo becomes a soft keyword that can be negated, undermining the 21 cards that depend on it.

3. **Sigilo tokens/charges (rejected)** — Sigilo blocks N attacks then breaks. Adds state tracking (charge counter per card). Complexity not justified for 21 cards.

4. **Absolute Sigilo (chosen)** — One rule, zero ambiguity. If a card says "cannot be attacked," it means it. The Guardaespaldas bypass is the single intentional exception, and it's justified by the semantic distinction between targeting and damage receipt.

## Consequences

- **UI**: Attack targeting must gray out Sigilo cards. Clicking them during target selection does nothing.
- **AI**: Bot target selection must skip Sigilo cards when scanning for isolated targets.
- **Design constraint**: Future cards that "force an attack" cannot force attacks on Sigilo cards. If a card text says "target opponent attacks your card," and the only valid target has Sigilo, the ability is blocked (no valid target = cannot activate, per Phase E decision 6).
- **Guardaespaldas interaction**: Guardaespaldas + Sigilo on the same board create an asymmetric defense: attacks target the Guardaespaldas, which redirects to Sigilo. This is intentional and creates a valid defensive strategy.
