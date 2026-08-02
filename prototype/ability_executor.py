"""Ability execution extracted from GameState (Candidate 1).

Standalone functions that take `game: GameState` as first parameter.
Original methods in GameState become thin delegates.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import re

if TYPE_CHECKING:
    from .game import GameState
from .card import CardInstance, Color as CardColor
from .modifier import Modifier
from .enums import Phase
from . import turn_manager


def can_use_ability(game: GameState, player: int, card: CardInstance,
                    ability_index: int = 0, reactive: bool = False) -> Optional[str]:
        if player != game.active_player and not reactive:
            return "No es tu turno."
        if game.phase != Phase.ACTIONS and not reactive:
            return "No estás en la fase de acciones."
        if not card.position or card.position[0] == -1:
            return "La carta no está en el tablero."

        active_abilities = [a for a in card.definition.abilities
                           if a.ability_type.name == 'ACTIVE']
        if ability_index < 0 or ability_index >= len(active_abilities):
            return "Habilidad no encontrada."
        ability = active_abilities[ability_index]

        cost = ability.action_cost
        if game.actions_remaining < cost:
            return f"Necesitas {cost} acciones (tienes {game.actions_remaining})."
        return None



def use_ability(game: GameState, player: int, card: CardInstance,
                ability_index: int = 0, targets: dict = None) -> Optional[str]:
    """Activate an active ability on a card.

    Supported effects (keyword matching on description):
    - Draw, gain/repair seals, heal HP, ascend, self-destruct, temp buffs,
      scry/peek, discard, swap, link effects, attack, fight, destroy,
      parasite, squad buffs, movement, color change, and more.
    """
    targets = targets or {}
    active_abilities_pre = [a for a in card.definition.abilities
                            if a.ability_type.name == 'ACTIVE']
    ability_pre = (active_abilities_pre[ability_index]
                   if 0 <= ability_index < len(active_abilities_pre) else None)
    desc_lower_pre = ability_pre.description.lower() if ability_pre else ""
    # Reactive "instant" abilities (e.g. Árbitro del Juego) may fire during
    # the OPPONENT's turn to negate an effect as it resolves.
    is_reactive = "niega un efecto" in desc_lower_pre

    err = can_use_ability(game, player, card, ability_index, reactive=is_reactive)
    if err:
        return err

    active_abilities = [a for a in card.definition.abilities
                       if a.ability_type.name == 'ACTIVE']
    ability = active_abilities[ability_index]
    desc = ability.description
    desc_lower = desc.lower()
    cost = ability.action_cost

    # -- Helper: find a card by target_id --
    def get_target_card(key: str = "target_id") -> Optional[CardInstance]:
        tid = targets.get(key)
        if tid is not None:
            return game.all_cards.get(tid)
        return None

        try:
            # ─── Discard then draw (checked BEFORE generic draw so the ───
            # ─── discard half isn't swallowed by an early return) ───
            if "descarta" in desc_lower and "roba" in desc_lower:
                import re
                dc_match = re.search(r'descarta\s+(\d+)', desc_lower)
                discard_count = int(dc_match.group(1)) if dc_match else 1
                dr_match = re.search(r'roba\s+(\d+)', desc_lower)
                draw_count = int(dr_match.group(1)) if dr_match else 1
                for _ in range(min(discard_count, len(game.hands[player]))):
                    if game.hands[player]:
                        game.discard_piles[player].append(game.hands[player].pop())
                for _ in range(draw_count):
                    game._draw_card(player)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: descarta {discard_count}, roba {draw_count}")
                return None

            # ─── Draw effects ───
            if "roba" in desc_lower and "control" not in desc_lower and "vínculo" not in desc_lower:
                # Count draws mentioned in description
                import re
                draw_count = 1
                match = re.search(r'roba\s+(\d+)', desc_lower)
                if match:
                    draw_count = int(match.group(1))
                total_drawn = 0
                for _ in range(draw_count):
                    drawn = game._draw_card(player)
                    if drawn:
                        total_drawn += 1
                    else:
                        game.seals[player] -= 1
                        game._log(f"  ¡Fatiga! -1 sello ({game.seals[player]})")
                        if game.seals[player] <= 0:
                            game._end_game(1 - player)
                # Check for "gana N sello" in the same ability
                gain_match = re.search(r'(?:tú\s+)?ganas?\s+(\d+)\s+sello', desc_lower)
                if gain_match:
                    gain = int(gain_match.group(1))
                    game.seals[player] += gain
                game.actions_remaining -= cost
                if gain_match:
                    game._log(f"  {card.definition.name}: usa habilidad → roba {total_drawn} carta(s), gana {gain} sello")
                else:
                    game._log(f"  {card.definition.name}: usa habilidad → roba {total_drawn} carta(s)")
                return None

            # ─── Gain seals ───
            if "gana" in desc_lower and any(w in desc_lower for w in ["sello", "sellos"]):
                import re
                seal_count = 1
                match = re.search(r'gana\s+(\d+)\s+sello', desc_lower)
                if match:
                    seal_count = int(match.group(1))
                game.seals[player] += seal_count
                # Also check for "pierde N sello" in the same ability
                lose_match = re.search(r'pierde\s+(\d+)\s+sello', desc_lower)
                if lose_match:
                    lose = int(lose_match.group(1))
                    enemy = 1 - player
                    game.seals[enemy] = max(0, game.seals[enemy] - lose)
                game.actions_remaining -= cost
                if lose_match:
                    game._log(f"  {card.definition.name}: usa habilidad → +{seal_count} sellos, enemigo -{lose} sellos ({game.seals[player]} / {game.seals[enemy]})")
                else:
                    game._log(f"  {card.definition.name}: usa habilidad → +{seal_count} sellos ({game.seals[player]})")
                return None

            # ─── Repair seals ───
            if "repara" in desc_lower and any(w in desc_lower for w in ["sello", "sellos"]):
                import re
                seal_count = 1
                match = re.search(r'repara\s+(\d+)\s+sello', desc_lower)
                if match:
                    seal_count = int(match.group(1))
                game.seals[player] += seal_count
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: usa habilidad → repara {seal_count} sellos ({game.seals[player]})")
                return None

            # ─── Heal HP ───
            if "cura" in desc_lower and "hp" in desc_lower:
                import re
                heal_amount = 2
                match = re.search(r'cura\s+(\d+)\s*hp', desc_lower)
                if match:
                    heal_amount = int(match.group(1))
                target_card = get_target_card("target_id") or card
                target_card.current_hp = min(target_card.current_hp + heal_amount,
                                            target_card.definition.hp)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: usa habilidad → cura {heal_amount} HP a {target_card.definition.name} ({target_card.current_hp}/{target_card.definition.hp})")
                return None

            # ─── Ascend ───
            if "asciende" in desc_lower or "asciende" in desc:
                # Check if card can ascend (position valid)
                if not card.position or card.position[0] == -1:
                    return "La carta no está en posición de ascender."
                p, layer, meridian = card.position
                if layer >= 3:
                    return "Ya está en la capa máxima."
                new_layer = layer + 1
                new_li = new_layer - 1

                # Check destination is free
                if game.board.cells[p][new_li][meridian] is not None:
                    return "Celda de destino ocupada."

                # Move the card up one layer (bypass allowed_layers check)
                old_li = layer - 1
                game.board.cells[p][old_li][meridian] = None
                game.board.cells[p][new_li][meridian] = card.card_id
                card.position = (p, new_layer, meridian)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: usa habilidad → asciende a L{new_layer}")
                return None

            # ─── Self-destruct ───
            if "destrúyete" in desc_lower or "destruyete" in desc_lower:
                name = card.definition.name
                seal_boost = 0
                if "grimorio gana" in desc_lower:
                    import re
                    seal_boost = 5
                    match = re.search(r'gana\s+(\d+)\s+sello', desc_lower)
                    if match:
                        seal_boost = int(match.group(1))
                    game.seals[player] += seal_boost
                game._destroy_card(card)
                game.actions_remaining -= cost
                game._log(f"  {name}: se autodestruye. Grimorio +{seal_boost} sellos")
                return None

            # ─── Opponent loses seals ───
            if "pierde" in desc_lower and any(w in desc_lower for w in ["sello", "sellos"]) and "hp" not in desc_lower:
                import re
                seal_count = 2
                match = re.search(r'pierde\s+(\d+)\s+sello', desc_lower)
                if match:
                    seal_count = int(match.group(1))
                enemy = 1 - player
                game.seals[enemy] = max(0, game.seals[enemy] - seal_count)
                # Also check for "Tú ganas N sello/s" in the same ability
                gain_match = re.search(r'(?:tú\s+)?ganas?\s+(\d+)\s+sello', desc_lower)
                if gain_match:
                    gain = int(gain_match.group(1))
                    game.seals[player] += gain
                    game._log(f"  {card.definition.name}: usa habilidad → enemigo pierde {seal_count} sellos, tú ganas {gain} sello ({game.seals[enemy]} / {game.seals[player]})")
                else:
                    game._log(f"  {card.definition.name}: usa habilidad → enemigo pierde {seal_count} sellos ({game.seals[enemy]})")
                game.actions_remaining -= cost
                if game.seals[enemy] <= 0:
                    game._end_game(player)
                return None

            # ─── Temporary +HP buff ───
            if any(w in desc_lower for w in ["gana +", "gana +"]) and "hp" in desc_lower:
                import re
                hp_bonus = 1
                match = re.search(r'\+(\d+)\s*hp', desc_lower)
                if match:
                    hp_bonus = int(match.group(1))
                target_card = get_target_card("target_id") or card
                target_card.current_hp += hp_bonus
                game.modifiers.register_temp(Modifier(
                    source_card_id=target_card.card_id, hook="end_of_turn",
                    effect_type="revert_hp_buff", layer="self",
                    params={"delta": hp_bonus}))
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: usa habilidad → {target_card.definition.name} +{hp_bonus} HP temporal")
                return None

            # ─── Temporary +D buff ───
            if any(w in desc_lower for w in ["+", "+"]) and "d" in desc_lower and "hp" not in desc_lower:
                # Skip if squad-wide (handled below)
                if "ganan" in desc_lower or "escuadrón" in desc_lower:
                    pass  # handled by Temp D buff squad-wide
                else:
                    import re
                    d_bonus = 1
                    match = re.search(r'\+(\d+)\s*d', desc_lower)
                    if match:
                        d_bonus = int(match.group(1))
                    target_card = get_target_card("target_id") or card
                    game.modifiers.register_temp(Modifier(
                        source_card_id=target_card.card_id, hook="modify_damage",
                        effect_type="damage_bonus", layer="self",
                        params={"delta": d_bonus}))
                    game.actions_remaining -= cost
                    game._log(f"  {card.definition.name}: usa habilidad → {target_card.definition.name} +{d_bonus} D temporal")
                    return None

            # ─── Scry / peek ───
            if "mira" in desc_lower and any(w in desc_lower for w in ["carta", "cartas", "reserva", "tope"]):
                import re
                count = 3
                match = re.search(r'mira\s+(\d+)', desc_lower)
                if match:
                    count = int(match.group(1))
                # Reveal top N cards to the log
                top_cards = game.decks[player][-count:] if len(game.decks[player]) >= count else game.decks[player][:]
                names = [c.definition.name for c in reversed(top_cards)]
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: usa habilidad → mira top {len(names)}: {', '.join(names)}")
                return None

            # ─── Discard ───
            if "descarta" in desc_lower:
                import re
                discard_count = 1
                match = re.search(r'descarta\s+(\d+)', desc_lower)
                if match:
                    discard_count = int(match.group(1))
                # Discard from player's hand
                discarded = []
                for _ in range(discard_count):
                    if game.hands[player]:
                        dc = game.hands[player].pop()
                        game.discard_piles[player].append(dc)
                        discarded.append(dc.definition.name)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: usa habilidad → descarta: {', '.join(discarded) if discarded else '(mano vacía)'}")
                return None

            # ─── Swap positions ───
            if "intercambia" in desc_lower and any(w in desc_lower for w in ["posición", "posiciones"]):
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para intercambiar."
                if card.card_id == target_card.card_id:
                    return "No puedes intercambiar una carta consigo misma."
                # Check same territory restriction on some abilities
                if "tu territorio" in desc_lower and target_card.owner != player:
                    return "Solo puedes intercambiar con cartas en tu territorio."
                if "aliada" in desc_lower and target_card.owner != player:
                    return "Solo puedes intercambiar con cartas aliadas."
                game.board.swap_cards(card, target_card)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia posición con {target_card.definition.name}")
                return None

            # ─── Swap layers ───
            if "intercambia" in desc_lower and "capa" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para intercambiar capas."
                if target_card.owner != player:
                    return "Solo puedes intercambiar capas con cartas propias."
                p, l_a, m_a = card.position
                _, l_b, m_b = target_card.position
                if m_a != m_b:
                    return "Las cartas deben estar en el mismo meridiano."
                game.board.swap_cards(card, target_card)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia capas con {target_card.definition.name}")
                return None

            # ─── Swap HP ───
            if "intercambia" in desc_lower and "hp" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para intercambiar HP."
                hp_a = card.current_hp
                hp_b = target_card.current_hp
                card.current_hp = min(hp_b, card.definition.hp)
                target_card.current_hp = min(hp_a, target_card.definition.hp)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia HP con {target_card.definition.name}")
                return None

            # ─── Swap colors ───
            if "intercambia" in desc_lower and "color" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para intercambiar colores."
                color_a = game._get_color_overrides().get(card.card_id, card.definition.color)
                color_b = game._get_color_overrides().get(target_card.card_id, target_card.definition.color)
                game._temp_colors[card.card_id] = color_b
                game._temp_colors[target_card.card_id] = color_a
                # Also register as temp modifiers
                from .card import Color as C
                game.modifiers.register_temp(Modifier(
                    source_card_id=card.card_id, hook="modify_squad",
                    effect_type="color_override", params={"color": color_b}, layer="self"))
                game.modifiers.register_temp(Modifier(
                    source_card_id=target_card.card_id, hook="modify_squad",
                    effect_type="color_override", params={"color": color_a}, layer="self"))
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia colores con {target_card.definition.name}")
                return None

            # ─── Swap hand with deck ───
            if "intercambia" in desc_lower and "mano" in desc_lower and "reserva" in desc_lower:
                if not game.hands[player]:
                    return "No tienes cartas en la mano."
                if not game.decks[player]:
                    return "No quedan cartas en la reserva."
                hand_card = game.hands[player].pop()
                deck_card = game.decks[player].pop()
                game.hands[player].append(deck_card)
                game.decks[player].append(hand_card)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia {hand_card.definition.name} de la mano con reserva")
                return None

            # ─── Swap hand with graveyard ───
            if "intercambia" in desc_lower and "mano" in desc_lower and "cementerio" in desc_lower:
                if not game.hands[player]:
                    return "No tienes cartas en la mano."
                if not game.discard_piles[player]:
                    return "No hay cartas en el cementerio."
                hand_card = game.hands[player].pop()
                grave_card = game.discard_piles[player].pop()
                game.hands[player].append(grave_card)
                game.discard_piles[player].append(hand_card)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia {hand_card.definition.name} de mano con cementerio")
                return None

            # ─── Create link ignoring distance ───
            if "vínculo" in desc_lower and "ignorando" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para vincular."
                err = game.link_cards(player, card, target_card, bypass_distance=True)
                if err:
                    return err
                # link_cards already deducts actions; refund since we already charge cost
                game.actions_remaining += 1  # link_cards deducted 1, we charge 'cost'
                game.actions_remaining -= cost
                return None

            # ─── Temp link (disuelve al final del turno) ───
            if "vínculo" in desc_lower and ("temporal" in desc_lower or "disuelve" in desc_lower):
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para vínculo temporal."
                err = game.link_cards(player, card, target_card, bypass_distance=True, is_temp=True)
                if err:
                    return err
                game.actions_remaining += 1
                game.actions_remaining -= cost
                return None

            # ─── Break all squad links ───
            if "rompe" in desc_lower and "vínculo" in desc_lower and "escuadrón" in desc_lower:
                enemy = 1 - player
                squads = game.get_player_squads(enemy)
                if not squads:
                    return "El enemigo no tiene escuadrones."
                # Target first squad (or use target_squad_idx from targets)
                squad_idx = targets.get("squad_index", 0)
                if squad_idx >= len(squads):
                    return "Escuadrón no encontrado."
                squad = squads[squad_idx]
                game.network.break_all_squad_links(squad)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: rompe vínculos de escuadrón enemigo ({squad.squad_type})")
                return None

            # ─── Destroy specific link (skip mass-break "todos los vínculos") ───
            if (("destruye" in desc_lower or "rompe" in desc_lower) and "vínculo" in desc_lower
                    and "escuadrón" not in desc_lower and "todos los vínculos" not in desc_lower):
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona las dos cartas del vínculo a destruir."
                if not game.network.has_link(card, target_card):
                    return "Esas cartas no están vinculadas."
                game.network.remove_link(card, target_card)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: destruye vínculo con {target_card.definition.name}")
                return None

            # ─── Link armor reduction ───
            if "vínculo" in desc_lower and "armadura" in desc_lower:
                enemy = 1 - player
                squads = game.get_player_squads(enemy)
                if not squads:
                    return "El enemigo no tiene escuadrones."
                squad_idx = targets.get("squad_index", 0)
                if squad_idx >= len(squads):
                    return "Escuadrón no encontrado."
                squad = squads[squad_idx]
                for cid in squad.members:
                    for neighbor in list(game.network.links.get(cid, set())):
                        key = tuple(sorted((cid, neighbor)))
                        game.network.link_armor[key] = max(0, game.network.link_armor.get(key, 0) - 1)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: -1 armadura a vínculos del escuadrón enemigo")
                return None

            # ─── Link cost free this turn ───
            if "costos de vínculo" in desc_lower:
                # Register temp global modifier instead of _link_cost_free flag
                game.modifiers.register_temp(Modifier(
                    source_card_id=card.card_id, hook="before_link",
                    effect_type="link_cost_zero", layer="global"))
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: costos de vínculo = 0 hasta final del turno")
                return None

            # ─── Change card color ───
            if "cambia" in desc_lower and "color" in desc_lower and "intercambia" not in desc_lower:
                target_card = get_target_card("target_id") or card
                # Determine target color (from ability text or default)
                new_color_str = None
                from prototype.card import Color as CardColor
                for color in CardColor:
                    if color.value.lower() in desc_lower:
                        new_color_str = color
                        break
                if not new_color_str:
                    # Generic "cambia el color" — default to player's choice (just pick Incoloro)
                    new_color_str = CardColor.INCOLORO
                game._temp_colors[target_card.card_id] = new_color_str
                # Also register as temp modifier
                game.modifiers.register_temp(Modifier(
                    source_card_id=target_card.card_id, hook="modify_squad",
                    effect_type="color_override", params={"color": new_color_str}, layer="self"))
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: cambia color de {target_card.definition.name} a {new_color_str.value}")
                return None

            # ─── Squad color override ───
            if "escuadrón se considera del color" in desc_lower:
                enemy = 1 - player
                squads = game.get_player_squads(player) or game.get_player_squads(enemy)
                # Apply color to all members of target squad
                squad_idx = targets.get("squad_index", 0)
                if squad_idx >= len(squads):
                    return "Escuadrón no encontrado."
                from prototype.card import Color as CardColor
                new_color = CardColor.INCOLORO
                for color in CardColor:
                    if color.value.lower() in desc_lower:
                        new_color = color
                        break
                for cid in squads[squad_idx].members:
                    game._temp_colors[cid] = new_color
                    # Also register as temp modifier
                    game.modifiers.register_temp(Modifier(
                        source_card_id=cid, hook="modify_squad",
                        effect_type="color_override", params={"color": new_color}, layer="self"))
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: escuadrón se considera {new_color.value}")
                return None

            # ─── Jump to free cell ───
            if "salta" in desc_lower and "celda libre" in desc_lower:
                p, layer, meridian = card.position
                # Find a free cell in any layer
                placed = False
                for li in range(3):
                    for m in range(15):
                        if game.board.cells[p][li][m] is None:
                            old_li = layer - 1
                            game.board.cells[p][old_li][meridian] = None
                            game.board.cells[p][li][m] = card.card_id
                            card.position = (p, li + 1, m)
                            placed = True
                            break
                    if placed:
                        break
                if not placed:
                    return "No hay celdas libres en tu territorio."
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: salta a L{card.position[1]}:{card.position[2]}")
                return None

            # ─── Teleport ally L1↔L2 ───
            if "teletransporta" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una carta aliada para teletransportar."
                if target_card.owner != player:
                    return "Solo puedes teletransportar aliados."
                if not target_card.position or target_card.position[0] == -1:
                    return "Carta sin posición válida."
                tp, t_layer, t_m = target_card.position
                if t_layer not in (1, 2):
                    return "Solo puedes teletransportar entre L1 y L2."
                new_layer = 2 if t_layer == 1 else 1
                new_li = new_layer - 1
                if game.board.cells[tp][new_li][t_m] is not None:
                    return "Celda de destino ocupada."
                old_li = t_layer - 1
                game.board.cells[tp][old_li][t_m] = None
                game.board.cells[tp][new_li][t_m] = target_card.card_id
                target_card.position = (tp, new_layer, t_m)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: teletransporta {target_card.definition.name} a L{new_layer}")
                return None

            # ─── Attack enemy node directly ───
            if "ataca" in desc_lower and "nodo" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona un nodo enemigo para atacar."
                if target_card.owner == player:
                    return "No puedes atacar tus propias cartas."
                dmg = card.definition.damage_bonus
                target_card.current_hp -= dmg
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: ataca {target_card.definition.name} por {dmg} daño (HP: {target_card.current_hp})")
                if target_card.current_hp <= 0:
                    game._log(f"  {target_card.definition.name} DESTRUIDO.")
                    game._destroy_card(target_card)
                return None

            # ─── Fight (both take 2 damage) ───
            if "lucha" in desc_lower and "daño" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona un nodo enemigo para luchar."
                card.current_hp -= 2
                target_card.current_hp -= 2
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: lucha con {target_card.definition.name} — ambos reciben 2 daño")
                if card.current_hp <= 0:
                    game._log(f"  {card.definition.name} DESTRUIDO en combate.")
                    game._destroy_card(card, killer=target_card)
                if target_card.current_hp <= 0:
                    game._log(f"  {target_card.definition.name} DESTRUIDO en combate.")
                    game._destroy_card(target_card, killer=card)
                return None

            # ─── Destroy ally + damage grimoire ───
            if "destruye" in desc_lower and "grimorio" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona un aliado para destruir."
                if target_card.owner != player:
                    return "Debes destruir un aliado."
                import re
                dmg = 5
                match = re.search(r'inflige\s+(\d+)\s+de\s+daño', desc_lower)
                if match:
                    dmg = int(match.group(1))
                enemy = 1 - player
                game._destroy_card(target_card)
                game.seals[enemy] -= dmg
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: destruye a {target_card.definition.name}, {dmg} daño al grimorio enemigo")
                if game.seals[enemy] <= 0:
                    game._end_game(player)
                return None

            # ─── Attach parasite to enemy Logistron ───
            if "adjunta" in desc_lower and "logistrón" in desc_lower:
                if card.card_id in game._attached:
                    host = game.all_cards.get(game._attached[card.card_id])
                    host_name = host.definition.name if host else "?"
                    return f"Ya está adjuntado a {host_name}."
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona un Logistrón enemigo."
                if target_card.owner == player:
                    return "Debe ser un Logistrón enemigo."
                if not target_card.definition.is_logistron:
                    return f"{target_card.definition.name} no es un Logistrón."
                game._attached[card.card_id] = target_card.card_id
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: se adjunta a {target_card.definition.name}")
                return None
            if "escuadrón" in desc_lower and ("daño" in desc_lower or "daño base" in desc_lower):
                squads = game.get_player_squads(player)
                if not squads:
                    return "No tienes escuadrones."
                squad_idx = targets.get("squad_index", 0)
                if squad_idx >= len(squads):
                    return "Escuadrón no encontrado."
                squad = squads[squad_idx]
                import re
                bonus = 1
                m = re.search(r'\+(\d+)', desc_lower)
                if m:
                    bonus = int(m.group(1))
                key = frozenset(squad.members)
                # Register temp modifier for each squad member instead of dict
                for cid in squad.members:
                    game.modifiers.register_temp(Modifier(
                        source_card_id=cid, hook="modify_damage",
                        effect_type="damage_bonus", layer="squad",
                        params={"delta": bonus}))
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: +{bonus} daño base al escuadrón {squad.squad_type}")
                return None

            # ─── Move 1 meridian + conditional Nature link ───
            if "muévete" in desc_lower and "meridiano" in desc_lower:
                p, layer, meridian = card.position
                direction = targets.get("direction", 1)  # 1=right, -1=left
                import re
                m = re.search(r'muévete\s+(-?\d+)', desc_lower)
                if m:
                    direction = int(m.group(1))
                new_m = meridian + direction
                li = layer - 1
                if new_m < 0 or new_m >= 15:
                    return "Fuera del tablero."
                if game.board.cells[p][li][new_m] is not None:
                    return "Celda ocupada."

                # Move
                game.board.cells[p][li][meridian] = None
                game.board.cells[p][li][new_m] = card.card_id
                card.position = (p, layer, new_m)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: se mueve a L{layer}:{new_m}")

                # Check for adjacent Naturaleza for free link
                if "naturaleza" in desc_lower and "vínculo gratis" in desc_lower:
                    color_naturaleza = Color.NATURALEZA
                    # Scan same-layer at dh=2
                    for check_m in [new_m - 2, new_m + 2]:
                        if 0 <= check_m < 15:
                            neighbor_cid = game.board.cells[p][li][check_m]
                            if neighbor_cid:
                                neighbor = game.all_cards.get(neighbor_cid)
                                if neighbor and neighbor.definition.color == color_naturaleza:
                                    if game.network.can_link(card) and game.network.can_link(neighbor):
                                        game.network.add_link(card, neighbor)
                                        game._log(f"  {card.definition.name}: vínculo gratis con {neighbor.definition.name} (Naturaleza)")
                                        break
                    # Also scan cross-layer dv=1, dh<=1
                    linked = False
                    for dl in [-1, 1]:
                        if linked: break
                        check_li = li + dl
                        if 0 <= check_li < 3:
                            for check_m in [new_m - 1, new_m, new_m + 1]:
                                if 0 <= check_m < 15:
                                    neighbor_cid = game.board.cells[p][check_li][check_m]
                                    if neighbor_cid:
                                        neighbor = game.all_cards.get(neighbor_cid)
                                        if neighbor and neighbor.definition.color == color_naturaleza:
                                            if game.network.can_link(card) and game.network.can_link(neighbor):
                                                game.network.add_link(card, neighbor)
                                                game._log(f"  {card.definition.name}: vínculo gratis cross-layer con {neighbor.definition.name}")
                                                linked = True
                                                break
                return None

            # ─── (Discard-then-draw moved up, before generic draw) ───

            # ─── Temp D buff squad-wide ───
            if ("ganan" in desc_lower or "gana" in desc_lower) and "+" in desc and "d" in desc_lower:
                d_match = re.search(r'\+(\d+)\s*(d|daño)', desc_lower)
                delta = int(d_match.group(1)) if d_match else 1
                if "este turno" in desc_lower:
                    squad = game._squad_of(card.card_id)
                    if squad:
                        for cid in squad.members:
                            mem = game.all_cards.get(cid)
                            if mem and mem.owner == player:
                                game.modifiers.register_temp(Modifier(
                                    source_card_id=cid, hook="modify_damage",
                                    effect_type="damage_bonus", layer="self",
                                    params={"delta": delta}))
                    game.actions_remaining -= cost
                    game._log(f"  {card.definition.name}: escuadrón +{delta} D este turno")
                    return None

            # ─── Temp indestructible ───
            if "indestructible" in desc_lower and "este turno" in desc_lower:
                for cid_list in game.board.cells[player]:
                    for cid in cid_list:
                        if cid is not None:
                            game.modifiers.register_temp(Modifier(
                                source_card_id=cid, hook="before_destroy",
                                effect_type="destroy_immunity", layer="self",
                                params={"duration": "turn"}))
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: cartas aliadas indestructibles este turno")
                return None

            # ─── Permanent +HP buff ───
            if "ganan" in desc_lower and "hp" in desc_lower and "permanente" in desc_lower:
                hp_match = re.search(r'\+(\d+)\s*hp', desc_lower)
                hp_bonus = int(hp_match.group(1)) if hp_match else 2
                for cid_list in game.board.cells[player]:
                    for cid in cid_list:
                        if cid is not None:
                            mem = game.all_cards.get(cid)
                            if mem:
                                mem.current_hp += hp_bonus
                                mem.definition.hp += hp_bonus
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: cartas aliadas +{hp_bonus} HP permanente")
                return None

            # ─── Damage enemy squad ───
            if "pierden" in desc_lower and "hp" in desc_lower:
                hp_match = re.search(r'pierden?\s+(\d+)\s*hp', desc_lower)
                dmg = int(hp_match.group(1)) if hp_match else 1
                target_card = get_target_card("target_id")
                if target_card:
                    squad = game._squad_of(target_card.card_id)
                    if squad:
                        for cid in list(squad.members):
                            mem = game.all_cards.get(cid)
                            if mem:
                                mem.current_hp -= dmg
                                game._log(f"  {mem.definition.name}: -{dmg} HP ({mem.current_hp}/{mem.definition.hp})")
                                if mem.current_hp <= 0:
                                    game._destroy_card(mem)
                game.actions_remaining -= cost
                return None

            # ─── Damage specific card type ───
            if "pierden" in desc_lower and "logistron" in desc_lower:
                hp_match = re.search(r'pierden?\s+(\d+)\s*hp', desc_lower)
                dmg = int(hp_match.group(1)) if hp_match else 2
                enemy = 1 - player
                for cid_list in game.board.cells[enemy]:
                    for cid in cid_list:
                        if cid is not None:
                            mem = game.all_cards.get(cid)
                            if mem and "Logistrón" in mem.definition.name:
                                mem.current_hp -= dmg
                                game._log(f"  {mem.definition.name}: -{dmg} HP ({mem.current_hp}/{mem.definition.hp})")
                                if mem.current_hp <= 0:
                                    game._destroy_card(mem)
                game.actions_remaining -= cost
                return None

            # ─── G1: Cannot attack this turn ───
            if "no pueden atacar" in desc_lower and "este turno" in desc_lower:
                enemy = 1 - player
                # Flag ALL enemy cards (board + elsewhere); attack() checks the flag
                for ec in game.all_cards.values():
                    if ec.owner == enemy:
                        ec._cannot_attack = True
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: cartas enemigas no pueden atacar este turno")
                return None

            # ─── G2: Block enemy formation bonus ───
            if "no reciben potenciamiento" in desc_lower and "este turno" in desc_lower:
                game._block_enemy_formation = True
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: escuadrones enemigos no reciben potenciamiento")
                return None

            # ─── G3: Negate faction effect ───
            if "niega el efecto de facción" in desc_lower:
                target_card = get_target_card("target_id")
                if target_card:
                    target_card._faction_disabled = True
                    game.actions_remaining -= cost
                    game._log(f"  {card.definition.name}: niega efecto de facción de {target_card.definition.name}")
                    return None

            # ─── G4: Break all enemy links ───
            if "rompe todos los vínculos enemigos" in desc_lower:
                enemy = 1 - player
                broken = 0
                # Links live in Network.links (dict[int, set[int]]) keyed by card_id
                # and remove_link takes CardInstance objects — iterate enemy cards
                # that actually have links.
                for cid in list(game.network.links.keys()):
                    card_obj = game.all_cards.get(cid)
                    if not card_obj or card_obj.owner != enemy:
                        continue
                    for neighbor_id in list(game.network.links.get(cid, set())):
                        neighbor = game.all_cards.get(neighbor_id)
                        if neighbor is not None:
                            game.network.remove_link(card_obj, neighbor)
                            broken += 1
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: rompe {broken} vínculos enemigos")
                return None

            # ─── G5: Destroy all enemy Logistrones ───
            if "destruye todos los logistrones" in desc_lower:
                enemy = 1 - player
                for cid_list in game.board.cells[enemy]:
                    for cid in cid_list:
                        if cid is not None:
                            mem = game.all_cards.get(cid)
                            if mem and "Logistrón" in mem.definition.name:
                                game._destroy_card(mem)
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: destruye todos los Logistrones enemigos")
                return None

            # ─── G6: Mass free link ───
            if "conecta" in desc_lower and "no vinculadas" in desc_lower and "vínculos gratis" in desc_lower:
                linked = 0
                mine = [c for c in game.all_cards.values() if c.owner == player]
                for i, card_obj in enumerate(mine):
                    for card2 in mine[i+1:]:
                        if (game.network.can_link(card_obj) and game.network.can_link(card2)
                                and not game.network.has_link(card_obj, card2)):
                            game.network.add_link(card_obj, card2)
                            linked += 1
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: conecta {linked} cartas con vínculos gratis")
                return None

            # ─── G7: Play from graveyard this turn ───
            if "jugar cartas de tu cementerio" in desc_lower:
                game._grave_play[player] = True
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: puede jugar cartas de cementerio este turno")
                return None

            # ─── G8: Swap D with enemy ───
            if "intercambia d" in desc_lower and "enemig" in desc_lower:
                enemy = 1 - player
                for cid_list in game.board.cells[player]:
                    for cid in cid_list:
                        if cid is not None:
                            ally = game.all_cards.get(cid)
                            if ally:
                                enemy_cid = game.board.cells[enemy][0][ally.position[2]] if ally.position else None
                                if enemy_cid:
                                    enemy_card = game.all_cards.get(enemy_cid)
                                    if enemy_card:
                                        ally.definition.damage, enemy_card.definition.damage = enemy_card.definition.damage, ally.definition.damage
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia D con enemigo")
                return None

            # ─── G9: Swap squad HP with defender ───
            if "intercambia hp" in desc_lower and "escuadrón" in desc_lower:
                target_card = get_target_card("target_id")
                if target_card:
                    my_squad = game._squad_of(card.card_id)
                    enemy_squad = game._squad_of(target_card.card_id)
                    if my_squad and enemy_squad:
                        my_hps = {}
                        for cid in my_squad.members:
                            mem = game.all_cards.get(cid)
                            if mem:
                                my_hps[cid] = mem.current_hp
                        for cid in enemy_squad.members:
                            mem = game.all_cards.get(cid)
                            if mem:
                                enemy_hp = mem.current_hp
                                # Get corresponding ally at same position
                                if mem.position:
                                    ally_cid = game.board.cells[player][mem.position[1]-1][mem.position[2]]
                                    if ally_cid and ally_cid in my_hps:
                                        mem.current_hp = my_hps[ally_cid]
                                        game.all_cards[ally_cid].current_hp = enemy_hp
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: intercambia HP de escuadrones")
                return None

            # ─── H1: Restore grimorio to 30 ───
            if "restaura tu grimorio" in desc_lower and "30" in desc:
                game.seals[player] = 30
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: grimorio restaurado a 30 sellos")
                return None

            # ─── H2: Restore broken seals ───
            if "restaura" in desc_lower and "sellos rotos" in desc_lower:
                broken = 30 - game.seals[player]
                game.seals[player] = 30
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: restaura {broken} sellos rotos")
                return None

            # ─── H3: Tutor (search deck) ───
            if "busca" in desc_lower and "reserva" in desc_lower and "mano" in desc_lower:
                if game.decks[player]:
                    # Simple: pick top non-spy card
                    for i, dc in enumerate(game.decks[player]):
                        if not dc.definition.is_spy:
                            chosen = game.decks[player].pop(i)
                            game.hands[player].append(chosen)
                            game._log(f"  {card.definition.name}: busca {chosen.definition.name} de la reserva")
                            break
                    else:
                        game._log(f"  {card.definition.name}: reserva solo tiene espías (sin efecto)")
                game.actions_remaining -= cost
                return None

            # ─── H4: Swap territory ───
            if "cambiar de territorio" in desc_lower or ("cambia" in desc_lower and "territorio" in desc_lower):
                # Toggle: 0 (North) ↔ 1 (South) for this player
                if hasattr(self, '_territory'):
                    game._territory[player] = 1 - game._territory.get(player, 0)
                else:
                    game._territory = {0: 0, 1: 0}
                    game._territory[player] = 1
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: cambia de territorio → {'Sur' if game._territory.get(player,0) else 'Norte'}")
                return None

            # ─── H5: Add temporal meridian ───
            if "meridiano temporal" in desc_lower:
                game._temp_meridians = getattr(self, '_temp_meridians', 0) + 1
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: +1 meridiano temporal (total: {game._temp_meridians})")
                return None

            # ─── I1: Magnum Opus — clone card ───
            if "crea una copia" in desc_lower or ("copia" in desc_lower and "carta" in desc_lower):
                target_card = get_target_card("target_id")
                if target_card:
                    new_id = max(game.all_cards.keys()) + 1 if game.all_cards else 10000
                    clone = target_card.clone(new_id, player)
                    game.all_cards[new_id] = clone
                    # Place in first free cell
                    placed = False
                    for li in range(3):
                        for m in range(15):
                            if game.board.cells[player][li][m] is None:
                                game.board.cells[player][li][m] = new_id
                                clone.position = (player, li+1, m)
                                placed = True
                                break
                        if placed:
                            break
                    if placed:
                        game._log(f"  {card.definition.name}: crea copia de {target_card.definition.name} en L{clone.position[1]}")
                    else:
                        game._log(f"  {card.definition.name}: no hay espacio para la copia")
                game.actions_remaining -= cost
                return None

            # ─── I2: Falsificador de Órdenes — force enemy attack ───
            if "ataque a otro" in desc_lower and "enemig" in desc_lower:
                enemy = 1 - player
                target_card = get_target_card("target_id")
                if target_card:
                    attacker_squad = game._squad_of(target_card.card_id)
                    if attacker_squad:
                        # Pick another enemy squad as target (find_squads → list)
                        for squad2 in game.network.find_squads(game.all_cards):
                            if squad2 is attacker_squad:
                                continue
                            # enemy squad (majority owner == enemy)
                            owners = [game.all_cards[m].owner for m in squad2.members if game.all_cards.get(m)]
                            if owners and owners.count(enemy) > len(owners) // 2:
                                # Force attack: attacker squad damages defender squad
                                atk_dmg = sum(game.all_cards[cid].definition.damage_bonus for cid in attacker_squad.members if game.all_cards.get(cid))
                                for cid in squad2.members:
                                    mem = game.all_cards.get(cid)
                                    if mem:
                                        mem.current_hp -= max(1, atk_dmg)
                                        game._log(f"  {mem.definition.name}: -{max(1,atk_dmg)} HP (ataque forzado)")
                                game._log(f"  {card.definition.name}: escuadrón enemigo ataca a otro escuadrón enemigo")
                                break
                game.actions_remaining -= cost
                return None

            # ─── I3: Árbitro del Juego — negate next effect ───
            if "niega un efecto" in desc_lower and "active" in desc_lower:
                game._negate_next = True
                game.actions_remaining -= cost
                game._log(f"  {card.definition.name}: próximo efecto enemigo será negado")
                return None

            # ─── I4: Polinizadora — copy ally ability ───
            if "copia una habilidad" in desc_lower:
                target_card = get_target_card("target_id")
                if target_card and target_card.owner == player:
                    if target_card.definition.abilities:
                        # Copy first non-on_enter ability
                        for ab in target_card.definition.abilities:
                            if ab.trigger != "on_enter":
                                # Register as temp modifier that re-applies the effect
                                game.modifiers.register_temp(Modifier(
                                    source_card_id=card.card_id, hook="start_of_turn",
                                    effect_type="copied_ability", layer="self",
                                    params={"desc": ab.description, "source": target_card.definition.name}))
                                game._log(f"  {card.definition.name}: copia habilidad de {target_card.definition.name}: {ab.description[:40]}")
                                break
                game.actions_remaining -= cost
                return None

            # ─── I5: Titiritero — mind control enemy squad ───
            if "toma control" in desc_lower and "escuadrón" in desc_lower:
                target_card = get_target_card("target_id")
                if target_card and target_card.owner != player:
                    # find_squads returns a list — locate the squad containing the target
                    squad = None
                    for sq in game.network.find_squads(game.all_cards):
                        if target_card.card_id in sq.members:
                            squad = sq
                            break
                    if squad:
                        for cid in list(squad.members):
                            mem = game.all_cards.get(cid)
                            if mem:
                                old_owner = mem.owner
                                # Move to player cells; if no free cell at this meridian,
                                # DON'T steal the card (it would vanish from the board).
                                placed = False
                                if mem.position:
                                    p, li_old, m = mem.position
                                    for li_new in range(3):
                                        if game.board.cells[player][li_new][m] is None:
                                            placed = True
                                            break
                                if not placed:
                                    game._log(f"  {mem.definition.name}: sin celda libre en meridiano {m}, no puede ser robada")
                                    continue
                                game._mind_controlled[cid] = old_owner
                                mem.owner = player
                                # Break enemy links (Network.links, CardInstance objects)
                                for nb_id in list(game.network.links.get(cid, set())):
                                    nb = game.all_cards.get(nb_id)
                                    if nb is not None:
                                        game.network.remove_link(mem, nb)
                                # Move to player cells
                                if mem.position:
                                    p, li_old, m = mem.position
                                    game.board.cells[old_owner][li_old-1][m] = None
                                    game.board.cells[player][li_new][m] = cid
                                    mem.position = (player, li_new+1, m)
                        game._log(f"  {card.definition.name}: toma control del escuadrón de {target_card.definition.name}")
                game.actions_remaining -= cost
                return None

            # ─── Fallback: ability not yet implemented ───
            return None

        except Exception as e:
            # Safety net: log error, refund actions, don't crash
            game._log(f"  ⚠ Error en habilidad de {card.definition.name}: {str(e)}")
            return f"Error al ejecutar habilidad: {str(e)}"



def _squad_of(game: GameState, card_id: int):
    """Return the squad containing card_id, or None."""
    for sq in game.network.find_squads(game.all_cards):
        if card_id in sq.members:
            return sq
    return None
