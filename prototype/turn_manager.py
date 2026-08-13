"""Turn and phase management extracted from GameState (Candidate 1).

Standalone functions that take `game: GameState` as first parameter.
Original methods in GameState become thin delegates.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game import GameState
from .enums import Phase
from .card import Color


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


def entry_phase(game: GameState) -> None:
    """Entry phase: trigger start-of-turn abilities + draw 2."""
    player = game.active_player
    squads = game.network.find_squads(game.all_cards)

    game.modifiers.dispatch_squad_hook("start_of_turn", game)

    # Military faction: free ascension
    for squad in squads:
        if squad.get_dominant_color(game.modifiers.get_color_overrides(game)) == Color.MILITAR:
            for cid in squad.members:
                card = game.all_cards.get(cid)
                if card and card.owner == player and card.position:
                    _, layer, _ = card.position
                    if layer < 3 and card.position[0] != -1:
                        err = game.ascend(player, card)
                        if not err:
                            game.actions_remaining += 1
                            game._log(f"  Militar: ascenso gratis de {card.definition.name}")
                            break

    # Sabios: extra draw per sage squad
    extra_draws = 0
    for squad in squads:
        if squad.get_dominant_color(game.modifiers.get_color_overrides(game)) == Color.SABIO:
            extra_draws += 1
            for cid in squad.members:
                card = game.all_cards.get(cid)
                if card and card.owner == player and "Archivera" in card.definition.name:
                    extra_draws += 1
                    break

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

    # Politicos: swap positions
    for squad in squads:
        if squad.get_dominant_color(game.modifiers.get_color_overrides(game)) == Color.POLITICO:
            game._log(f"  [Político] Puedes intercambiar posiciones de 2 cartas por escuadrón.")


def start_attack_phase(game: GameState) -> None:
    """Transition to attack phase."""
    game.phase = Phase.ATTACK
    game._log(f"  >>> Fase de Ataque <<<")


def exit_phase(game: GameState) -> None:
    """Exit phase: purge isolated nodes, end-of-turn effects, discard, switch player."""
    player = game.active_player
    game.phase = Phase.EXIT
    squads = game.network.find_squads(game.all_cards)

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

    squads = game.network.find_squads(game.all_cards)

    game.modifiers.dispatch_squad_hook("end_of_turn", game)

    # Faction effects
    for squad in squads:
        dom = squad.get_dominant_color(game.modifiers.get_color_overrides(game))
        if dom == Color.SELLADOR:
            bonus = 10
            for cid in squad.members:
                card = game.all_cards.get(cid)
                if card and card.owner == player and "Abadesa" in card.definition.name:
                    bonus += 5
                    break
            game.seals[player] += bonus
            game._log(f"  Escuadrón Sellador: +{bonus} sellos ({game.seals[player]} total)")

        elif dom == Color.SABOTEADOR:
            break_count = 2
            for cid in squad.members:
                card = game.all_cards.get(cid)
                if card and card.owner == player and "Agente del Silencio" in card.definition.name:
                    break_count += 1
                    break
            game._log(f"  Escuadrón Saboteador: puedes romper {break_count} vínculos enemigos")

        elif dom == Color.MONSTRUO:
            game._log(f"  Escuadrón Monstruo: puedes remover 1 nodo enemigo (grado < {squad.base_damage})")

    # Discard to 5
    while len(game.hands[player]) > 5:
        discarded = game.hands[player].pop()
        game.discard_piles[player].append(discarded)
        game.seals[player] -= 1
        game._log(f"  Descarte: {discarded.definition.name}. -1 sello ({game.seals[player]})")
        if game.seals[player] <= 0:
            _end_game(game, 1 - player)
            return

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
