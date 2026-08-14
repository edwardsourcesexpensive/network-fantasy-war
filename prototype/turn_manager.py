"""Turn and phase management extracted from GameState (Candidate 1).

Standalone functions that take `game: GameState` as first parameter.
Original methods in GameState become thin delegates.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game import GameState
from .enums import Phase
from .card import Color, CardInstance
from .network import calculate_potenciamiento


def start_turn(game: GameState) -> None:
    """Initialize a new turn for the active player."""
    game.phase = Phase.ENTRY
    game.actions_remaining = 4
    game._attacked_squads = set()
    game._spy_sabotage_used = set()
    game._block_enemy_formation = False
    game._grave_play = {0: False, 1: False}
    for _c in game.all_cards.values():
        if getattr(_c, "_cannot_attack", False):
            _c._cannot_attack = False
    game.log = []
    game._log(f"═══ TURNO {game.turn_number} — Jugador {game.active_player + 1} ═══")


def entry_phase(game: GameState, auto_resolve: bool = True) -> None:
    """Entry phase: trigger start-of-turn abilities + draw 2.

    auto_resolve=True (default): Político swap applies automatically via
    heuristics. auto_resolve=False: leaves `game.pending_politico_swap` set
    for the host to render a picker, then apply_politico_swap().
    """
    player = game.active_player
    game.pending_politico_swap = None
    squads = game.get_player_squads(player)

    game.modifiers.dispatch_squad_hook("start_of_turn", game)

    # Military faction: free ascension
    for squad in squads:
        if squad.get_dominant_color(game.modifiers.get_color_overrides(game)) == Color.MILITAR:
            for cid in squad.members:
                card = game.all_cards.get(cid)
                if card and card.owner == player and card.position:
                    _, layer, _ = card.position
                    if layer < 3 and card.position[0] != -1:
                        err = game.ascend(player, card, free=True)
                        if not err:
                            game._log(f"  Militar: ascenso gratis de {card.definition.name}")
                            break

    # Sabios: extra draw per sage squad
    extra_draws = 0
    for squad in squads:
        if squad.get_dominant_color(game.modifiers.get_color_overrides(game)) == Color.SABIO:
            extra_draws += 1

    # Draw 2 + extras
    total_draws = 2 + extra_draws
    drawn = 0
    for _ in range(total_draws):
        card = game._draw_card(player)
        if card:
            drawn += 1
        else:
            game.seals[player] -= 1
            game._log(f"  ¡Fatiga! -1 sello ({game.seals[player]} restantes)")
            if game.seals[player] <= 0:
                _end_game(game, 1 - player)
                return

    game._log(f"  Roba {drawn} carta(s). Mano: {len(game.hands[player])} | Sellos: {game.seals[player]}")
    game.phase = Phase.ACTIONS

    # Parasite damage
    for parasite_id, host_id in list(game._attached.items()):
        host = game.all_cards.get(host_id)
        if host and host.position and host.position[0] != -1:
            host.current_hp -= 1
            parasite = game.all_cards.get(parasite_id)
            pname = parasite.definition.name if parasite else "?"
            game._log(f"  🦠 {pname} drena 1 HP a {host.definition.name} ({host.current_hp}/{host.definition.hp})")
            if host.current_hp <= 0:
                game._log(f"  {host.definition.name} MUERE por parásito.")
                game._destroy_card(host)
                del game._attached[parasite_id]

    # Politicos: swap positions (start of turn, per squadron)
    politico_squads = sum(
        1 for s in squads
        if s.get_dominant_color(game.modifiers.get_color_overrides(game)) == Color.POLITICO
    )
    if politico_squads:
        if auto_resolve:
            resolve_politico_auto(game, player, politico_squads)
        else:
            pairs = politico_candidates(game, player)
            if pairs:
                game.pending_politico_swap = {"max": politico_squads, "pairs": pairs}


def start_attack_phase(game: GameState) -> None:
    """Transition to attack phase."""
    game.phase = Phase.ATTACK
    game._log(f"  >>> Fase de Ataque <<<")


def exit_phase(game: GameState, auto_resolve: bool = True) -> None:
    """Exit phase: purge, end-of-turn effects, discard, faction effects, switch player.

    auto_resolve=True (default): Saboteador/Monstruo effects apply automatically
    via heuristics (used by bots and the pre-UI path). auto_resolve=False:
    leaves `game.pending_faction_choices` set for the host to render pickers,
    then apply_faction_choices() + _finish_exit_phase().
    """
    player = game.active_player
    game.phase = Phase.EXIT
    game.pending_faction_choices = None

    # ─── 1. Purge isolated enemy nodes IN YOUR TERRITORY ───
    enemy = 1 - player
    for cid in list(game.all_cards.keys()):
        card = game.all_cards.get(cid)
        if (card and card.owner == enemy and card.position
                and card.position[0] == player  # only purge enemies IN your territory
                and card.position[0] != -1):
            if game.network.link_count(card) == 0:
                game._destroy_card(card)
                game._log(f"  Purga: {card.definition.name} aislado, destruido.")

    game.modifiers.dispatch_squad_hook("end_of_turn", game)

    # ─── 3. Discard to 5 (per §5.5 step 3) ───
    while len(game.hands[player]) > 5:
        discarded = game.hands[player].pop()
        game.discard_piles[player].append(discarded)
        game.seals[player] -= 1
        game._log(f"  Descarte: {discarded.definition.name}. -1 sello ({game.seals[player]})")
        if game.seals[player] <= 0:
            _end_game(game, 1 - player)
            return

    # ─── 4. Squad faction effects (per §5.5 step 4) ───
    squads = game.get_player_squads(player)
    for squad in squads:
        dom = squad.get_dominant_color(game.modifiers.get_color_overrides(game))
        if dom == Color.SELLADOR:
            game.seals[player] += 10
            game._log(f"  Escuadrón Sellador: +10 sellos ({game.seals[player]} total)")

        elif dom == Color.SABOTEADOR:
            game._log(f"  Escuadrón Saboteador: hasta 2 vínculos cortos enemigos por escuadrón")

        elif dom == Color.MONSTRUO:
            game._log(f"  Escuadrón Monstruo: puede remover 1 nodo enemigo (G < {_squad_attack(game, squad)})")

    if auto_resolve:
        resolve_faction_choices_auto(game, player)
        _finish_exit_phase(game)
    else:
        # Host renders pickers from the candidates, then calls
        # apply_faction_choices() + _finish_exit_phase(). Only pauses the
        # phase when there is something real to choose; otherwise complete
        # the exit normally (turn must still switch).
        choices = _collect_faction_choices(game, player)
        if choices["saboteador"]["links"] or choices["monstruo"]["nodes"]:
            game.pending_faction_choices = choices
        else:
            _finish_exit_phase(game)


def _finish_exit_phase(game: GameState) -> None:
    """Tail of exit_phase: fin log, temp-effect cleanup, switch player."""
    player = game.active_player
    game.pending_faction_choices = None

    game._log(f"  Fin del turno. Sellos J{player+1}: {game.seals[player]}")

    # Clear temporary HP buffs
    for mod in game.modifiers.get("end_of_turn"):
        if mod.is_temporary and mod.effect_type == "revert_hp_buff":
            card = game.all_cards.get(mod.source_card_id)
            if card:
                delta = mod.params.get("delta", 0)
                card.current_hp = max(0, card.current_hp - delta)
                card.current_hp = min(card.current_hp, card.definition.hp)

    # Dissolve temporary links
    for mod in game.modifiers.get("end_of_turn"):
        if mod.is_temporary and mod.effect_type == "dissolve_temp_link":
            pair = mod.params.get("pair")
            if pair:
                card_a = game.all_cards.get(pair[0])
                card_b = game.all_cards.get(pair[1])
                if card_a and card_b:
                    game.network.remove_link(card_a, card_b)

    # Clear state
    game._temp_colors = {}
    game.modifiers.cleanup()

    # Switch player
    game.active_player = 1 - game.active_player
    game.turn_number += 1


def _end_game(game: GameState, winner: int) -> None:
    """End the game with the given winner."""
    game.game_over = True
    game.winner = winner
    game._log(f"═══ ¡JUGADOR {winner + 1} HA GANADO! El grimorio enemigo ha sido destruido. ═══")


# ═══════════════════════════════════════════════════════════════
# Faction choice effects (audit #7: Saboteador / Monstruo / Político)
# ═══════════════════════════════════════════════════════════════

def _enemy_corta_links(game: GameState, player: int) -> list:
    """'Corta'-distance links inside the enemy network (both endpoints enemy)."""
    enemy = 1 - player
    links = []
    seen = set()
    for cid, neighbors in game.network.links.items():
        for nid in neighbors:
            pair = (cid, nid) if cid < nid else (nid, cid)
            if pair in seen:
                continue
            seen.add(pair)
            ca = game.all_cards.get(cid)
            cb = game.all_cards.get(nid)
            if not ca or not cb or ca.owner != enemy or cb.owner != enemy:
                continue
            if (not ca.position or not cb.position
                    or ca.position[0] == -1 or cb.position[0] == -1):
                continue  # frontier links have no spatial-distance category
            if game.board.spatial_distance(ca.position, cb.position) == "corta":
                links.append((cid, nid))
    return links


def _card_degree(game: GameState, cid: int) -> int:
    card = game.all_cards.get(cid)
    return len(game.network.get_links(card)) if card else 0


def _squad_attack(game: GameState, squad) -> int:
    """Efective attack of a squad: base damage + potenciamiento (mirrors combat.calculate_attack)."""
    all_squads = game.network.find_squads(game.all_cards)
    pot = calculate_potenciamiento(squad, all_squads, game.network, game.all_cards)
    return squad.base_damage + pot


def _monstruo_candidates(game: GameState, player: int, squad) -> list:
    """Enemy placed nodes with Grado < the squad's effective attack."""
    enemy = 1 - player
    attack = _squad_attack(game, squad)
    return [
        c.card_id for c in game.all_cards.values()
        if c.owner == enemy and c.position is not None
        and c.definition.grado < attack
    ]


def _break_link(game: GameState, cid: int, nid: int) -> None:
    ca = game.all_cards.get(cid)
    cb = game.all_cards.get(nid)
    if ca and cb:
        game.network.remove_link(ca, cb)
        game._log(f"  Saboteador: vínculo roto entre {ca.definition.name} y {cb.definition.name}")


def _destroy_enemy_node(game: GameState, cid: int) -> None:
    card = game.all_cards.get(cid)
    if card:
        game._destroy_card(card)
        game._log(f"  Monstruo: {card.definition.name} destruido (G {card.definition.grado})")


def _dom_color(game: GameState, squad) -> Color:
    return squad.get_dominant_color(game.modifiers.get_color_overrides(game))


def resolve_faction_choices_auto(game: GameState, player: int) -> None:
    """Auto Saboteador/Monstruo: break the most-connected corta enemy links,
    remove the most-connected valid enemy nodes. Up to 2 links per Saboteador
    squad, 1 node per Monstruo squad."""
    squads = game.get_player_squads(player)
    saboteador_squads = [s for s in squads if _dom_color(game, s) == Color.SABOTEADOR]
    monstruo_squads = [s for s in squads if _dom_color(game, s) == Color.MONSTRUO]

    if saboteador_squads:
        links = _enemy_corta_links(game, player)
        links.sort(key=lambda l: _card_degree(game, l[0]) + _card_degree(game, l[1]),
                   reverse=True)
        for cid, nid in links[: 2 * len(saboteador_squads)]:
            _break_link(game, cid, nid)

    for squad in monstruo_squads:
        candidates = _monstruo_candidates(game, player, squad)
        if candidates:
            target = max(candidates, key=lambda cid: _card_degree(game, cid))
            _destroy_enemy_node(game, target)


def _collect_faction_choices(game: GameState, player: int) -> dict:
    """Candidate lists for the interactive picker (auto_resolve=False path)."""
    squads = game.get_player_squads(player)
    saboteador_squads = [s for s in squads if _dom_color(game, s) == Color.SABOTEADOR]
    monstruo_squads = [s for s in squads if _dom_color(game, s) == Color.MONSTRUO]
    mon_damage = max((_squad_attack(game, s) for s in monstruo_squads), default=0)
    nodes = sorted({
        c.card_id for c in game.all_cards.values()
        if c.owner == 1 - player and c.position is not None
        and c.definition.grado < mon_damage
    })
    return {
        "saboteador": {
            "max": 2 * len(saboteador_squads),
            "links": _enemy_corta_links(game, player) if saboteador_squads else [],
        },
        "monstruo": {
            "max": len(monstruo_squads),
            "damage": mon_damage,
            "nodes": nodes,
        },
    }


def apply_faction_choices(game: GameState, player: int,
                          saboteador_links: list = None,
                          monstruo_nodes: list = None) -> None:
    """Apply the player's Saboteador/Monstruo picks, re-validated against the
    current state (a pick is dropped if it no longer qualifies)."""
    squads = game.get_player_squads(player)
    saboteador_squads = [s for s in squads if _dom_color(game, s) == Color.SABOTEADOR]
    monstruo_squads = [s for s in squads if _dom_color(game, s) == Color.MONSTRUO]
    sab_budget = 2 * len(saboteador_squads)
    mon_budget = len(monstruo_squads)
    mon_damage = max((_squad_attack(game, s) for s in monstruo_squads), default=0)
    enemy = 1 - player

    applied = 0
    for cid, nid in (saboteador_links or []):
        if applied >= sab_budget:
            break
        ca = game.all_cards.get(cid)
        cb = game.all_cards.get(nid)
        if not ca or not cb or ca.owner != enemy or cb.owner != enemy:
            continue
        if (not ca.position or not cb.position
                or ca.position[0] == -1 or cb.position[0] == -1):
            continue
        if game.board.spatial_distance(ca.position, cb.position) != "corta":
            continue
        game.network.remove_link(ca, cb)
        applied += 1
        game._log(f"  Saboteador: vínculo roto entre {ca.definition.name} y {cb.definition.name}")

    applied = 0
    for cid in (monstruo_nodes or []):
        if applied >= mon_budget:
            break
        card = game.all_cards.get(cid)
        if not card or card.owner != enemy or card.position is None:
            continue
        if card.definition.grado >= mon_damage:
            continue
        game._destroy_card(card)
        applied += 1
        game._log(f"  Monstruo: {card.definition.name} destruido (G {card.definition.grado})")

    game.pending_faction_choices = None


# ─── Político: position swap ───

def _swap_valid(game: GameState, a: CardInstance, b: CardInstance) -> bool:
    """A swap is valid when every link incident to a or b stays at a valid
    spatial distance (frontier links evaluate None → swap rejected, matching
    the move_card precedent of dissolving None-distance links).

    The a-b link itself is exempt: after the swap its endpoints occupy each
    other's positions, so its distance is unchanged (still valid)."""
    if a.card_id == b.card_id:
        return False

    def _ok(card: CardInstance, new_pos, partner: CardInstance) -> bool:
        for nid in game.network.get_links(card):
            if nid == partner.card_id:
                continue  # a-b distance is unchanged by the swap
            nb = game.all_cards.get(nid)
            if not nb or not nb.position:
                return False
            if game.board.spatial_distance(new_pos, nb.position) is None:
                return False
        return True

    return _ok(a, b.position, b) and _ok(b, a.position, a)


def politico_candidates(game: GameState, player: int) -> list:
    """Valid (a_id, b_id) swap pairs: own placed cards whose swap keeps all
    incident links at valid distance."""
    own = [
        c for c in game.all_cards.values()
        if c.owner == player and c.position and c.position[0] == player
    ]
    pairs = []
    for i in range(len(own)):
        for j in range(i + 1, len(own)):
            if _swap_valid(game, own[i], own[j]):
                pairs.append((own[i].card_id, own[j].card_id))
    return pairs


def _swap_score(game: GameState, a_id: int, b_id: int) -> int:
    """Same-color 'corta' neighbors gained minus lost by swapping a and b."""
    a = game.all_cards.get(a_id)
    b = game.all_cards.get(b_id)
    if not a or not b:
        return 0

    def _same_color_corta(card: CardInstance, pos) -> int:
        n = 0
        for nid in game.network.get_links(card):
            nb = game.all_cards.get(nid)
            if (nb and nb.position and nb.position[0] != -1
                    and nb.definition.color == card.definition.color
                    and game.board.spatial_distance(pos, nb.position) == "corta"):
                n += 1
        return n

    return (_same_color_corta(a, b.position) - _same_color_corta(a, a.position)
            + _same_color_corta(b, a.position) - _same_color_corta(b, b.position))


def apply_politico_swap(game: GameState, player: int, a_id: int, b_id: int) -> bool:
    """Validate and apply a Político position swap. Returns True if applied."""
    a = game.all_cards.get(a_id)
    b = game.all_cards.get(b_id)
    if not a or not b or a.owner != player or b.owner != player:
        return False
    if not a.position or not b.position or a.position[0] != player or b.position[0] != player:
        return False
    if a.card_id == b.card_id or not _swap_valid(game, a, b):
        return False
    game.board.swap_cards(a, b)
    game._log(f"  Político: {a.definition.name} ↔ {b.definition.name} (posiciones intercambiadas)")
    return True


def resolve_politico_auto(game: GameState, player: int, budget: int = 1) -> None:
    """Político auto: swap up to `budget` pairs that increase same-color 'corta'
    adjacency (best first, recomputed after each swap). Skips when none improves."""
    for _ in range(max(0, budget)):
        pairs = politico_candidates(game, player)
        best_pair = None
        best_score = 0
        for a_id, b_id in pairs:
            score = _swap_score(game, a_id, b_id)
            if score > best_score:
                best_score = score
                best_pair = (a_id, b_id)
        if best_pair is None:
            break
        apply_politico_swap(game, player, best_pair[0], best_pair[1])


def refresh_pending_politico(game: GameState) -> None:
    """Decrement the Político swap budget after an applied swap; recompute pairs
    against the new board (called by hosts between picker submissions)."""
    pending = getattr(game, "pending_politico_swap", None)
    if not pending:
        return
    pending["max"] -= 1
    if pending["max"] <= 0:
        game.pending_politico_swap = None
    else:
        pending["pairs"] = politico_candidates(game, game.active_player)
