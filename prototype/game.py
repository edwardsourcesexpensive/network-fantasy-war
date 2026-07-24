"""
Network Fantasy War - Digital Prototype
Game state: complete turn management, combat, spy mechanics, ability triggers.
"""
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from .card import CardInstance, CardDef, Color, Ability, AbilityType
from .board import Board
from .network import Network, Squad, calculate_potenciamiento


class Phase(Enum):
    ENTRY = "entry"
    ACTIONS = "actions"
    ATTACK = "attack"
    EXIT = "exit"


class GameState:
    """Complete state of a Network Fantasy War match."""

    def __init__(self, decklist_player0: list[CardDef], decklist_player1: list[CardDef]):
        self.board = Board()
        self.network = Network()

        self.decks: list[list[CardInstance]] = [[], []]
        self.hands: list[list[CardInstance]] = [[], []]
        self.discard_piles: list[list[CardInstance]] = [[], []]
        self.seals: list[int] = [30, 30]
        self.all_cards: dict[int, CardInstance] = {}

        self.active_player: int = 0
        self.phase: Phase = Phase.ENTRY
        self.actions_remaining: int = 4
        self.turn_number: int = 1
        self.game_over: bool = False
        self.winner: Optional[int] = None

        # Spy state
        self.spies_infiltrated: dict[int, list[int]] = {0: [], 1: []}  # player -> [card_ids in enemy territory]

        # Attacked squads this turn
        self._attacked_squads: set[int] = set()  # squad hashes

        # Event log for UI
        self.log: list[str] = []

        self._build_deck(0, decklist_player0)
        self._build_deck(1, decklist_player1)

        for _ in range(5):
            self._draw_card(0)
            self._draw_card(1)

    def _build_deck(self, player: int, card_defs: list[CardDef]):
        deck = []
        for cdef in card_defs:
            deck.append(cdef)
        random.shuffle(deck)
        for i, cdef in enumerate(deck):
            instance = CardInstance(
                card_id=i + (player * 1000),
                definition=cdef,
                current_hp=cdef.hp,
                owner=player
            )
            self.decks[player].append(instance)
            self.all_cards[instance.card_id] = instance

    def _draw_card(self, player: int) -> Optional[CardInstance]:
        if not self.decks[player]:
            return None
        card = self.decks[player].pop()
        self.hands[player].append(card)
        return card

    def _log(self, msg: str):
        self.log.append(msg)

    # ═══════════════════════════════════════════════════════════════
    # Actions
    # ═══════════════════════════════════════════════════════════════

    def can_play_card(self, player: int, hand_index: int) -> Optional[str]:
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if self.actions_remaining < 1:
            return "No te quedan acciones."
        if hand_index < 0 or hand_index >= len(self.hands[player]):
            return "Índice de mano inválido."
        return None

    def play_card(self, player: int, hand_index: int, layer: int, meridian: int) -> Optional[str]:
        err = self.can_play_card(player, hand_index)
        if err:
            return err

        card = self.hands[player][hand_index]

        # Spy: play on frontier
        if card.definition.is_spy:
            self.board.place_spy_frontier(card)
            self.hands[player].pop(hand_index)
            self.actions_remaining -= 1
            self._log(f"J{player+1} juega {card.definition.name} en la FRONTERA.")
            return None

        if not card.definition.is_logistron:
            if layer not in card.definition.allowed_layers:
                return f"{card.definition.name} no puede jugarse en L{layer}."

        li = layer - 1
        if self.board.cells[player][li][meridian] is not None:
            return "Celda ya ocupada."
        if meridian > 0 and self.board.cells[player][li][meridian - 1] is not None:
            return "Celda bloqueada (adyacente ocupada)."
        if meridian < 14 and self.board.cells[player][li][meridian + 1] is not None:
            return "Celda bloqueada (adyacente ocupada)."

        self.board.place_card(player, card, layer, meridian)
        self.hands[player].pop(hand_index)
        self.actions_remaining -= 1

        # Trigger Vanguardia ability
        if any(a.trigger == "on_enter" and "Vanguardia" in a.description
               for a in card.definition.abilities):
            # Vanguardia: enters directly in L2 — already handled by selection
            pass

        self._log(f"J{player+1} juega {card.definition.name} en L{layer}:{meridian}.")
        return None

    def can_ascend(self, player: int, card: CardInstance) -> Optional[str]:
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if not card.position or card.position[0] == -1:
            # Spy infiltration
            if card.definition.is_spy and self.actions_remaining >= 1:
                return None
            return "Esa carta no está en posición de ascender."
        _, layer, meridian = card.position
        if layer >= 3:
            return "Esa carta no está en posición de ascender."
        new_layer = layer + 1
        if new_layer not in card.definition.allowed_layers:
            return f"{card.definition.name} solo puede estar en L{card.definition.allowed_layers}."
        cost = 1 if layer == 1 else 2
        if self.actions_remaining < cost:
            return f"Necesitas {cost} acciones (tienes {self.actions_remaining})."
        new_li = layer  # L1->L2: layer goes from 1 to 2, index from 0 to 1
        if self.board.cells[player][new_li][meridian] is not None:
            return "Celda de destino ocupada."
        return None

    def ascend(self, player: int, card: CardInstance) -> Optional[str]:
        err = self.can_ascend(player, card)
        if err:
            return err

        if card.definition.is_spy:
            # Infiltrate spy into enemy territory
            self.spies_infiltrated[player].append(card.card_id)
            self.board.frontier_cards.remove(card.card_id)
            enemy = 1 - player
            # Place spy in enemy L3, any free meridian
            m = self.board.find_empty_meridian(enemy, 3)
            if m is None:
                self.board.place_spy_frontier(card)
                return "No hay espacio en territorio enemigo para infiltrar."
            self.board.place_card(enemy, card, 3, m)
            card.owner = player  # Still owned by original player
            self.actions_remaining -= 1
            self._log(f"¡{card.definition.name} se infiltra en territorio enemigo! L3:{m}")
            return None

        _, layer, meridian = card.position
        cost = 1 if layer == 1 else 2
        old_li = layer - 1
        new_layer = layer + 1
        new_li = new_layer - 1

        self.board.cells[player][old_li][meridian] = None
        self.board.cells[player][new_li][meridian] = card.card_id
        card.position = (player, new_layer, meridian)
        self.actions_remaining -= cost

        # Caudillismo trigger
        if new_layer == 3:
            if any(a.trigger == "on_ascend" for a in card.definition.abilities):
                # Auto-link to a node in L2
                for m2 in range(15):
                    neighbor_cid = self.board.cells[player][1][m2]  # L2 index = 1
                    if neighbor_cid and self.network.can_link(card):
                        neighbor = self.all_cards[neighbor_cid]
                        dist = self.board.spatial_distance(card.position, neighbor.position)
                        if dist:
                            self.network.add_link(card, neighbor)
                            self._log(f"  Caudillismo: vínculo gratis con {neighbor.definition.name}")
                            break

        self._log(f"J{player+1} asciende {card.definition.name} a L{new_layer}.")
        return None

    def can_link(self, player: int, card_a: CardInstance, card_b: CardInstance) -> Optional[str]:
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if card_a.card_id == card_b.card_id:
            return "No puedes vincular una carta consigo misma."
        if self.network.has_link(card_a, card_b):
            return "Ya están vinculadas."
        if not self.network.can_link(card_a):
            return f"{card_a.definition.name} sin capacidad (V={card_a.definition.link_capacity})."
        if not self.network.can_link(card_b):
            return f"{card_b.definition.name} sin capacidad (V={card_b.definition.link_capacity})."

        # Reticencia check
        for card, other in [(card_a, card_b), (card_b, card_a)]:
            for ability in card.definition.abilities:
                if "Reticencia" in ability.description:
                    # Simplified: check if other's color is mentioned
                    if other.definition.color.value.lower() in ability.description.lower():
                        return f"{card.definition.name} es reticente a {other.definition.color.value}."

        # Special: spy on frontier linking to enemy L3
        a_is_frontier_spy = (card_a.definition.is_spy and card_a.position and card_a.position[0] == -1)
        b_is_frontier_spy = (card_b.definition.is_spy and card_b.position and card_b.position[0] == -1)
        if a_is_frontier_spy and not b_is_frontier_spy:
            if card_b.owner != player:
                # Spy linking to enemy — allowed for Eco de la Frontera
                pass
        if b_is_frontier_spy and not a_is_frontier_spy:
            if card_a.owner != player:
                pass

        # Normal distance check
        if not a_is_frontier_spy and not b_is_frontier_spy:
            dist = self.board.spatial_distance(card_a.position, card_b.position)
            if dist is None:
                return "Distancia espacial inválida para vínculo."

            cost = {"corta": 1, "media": 1, "larga": 3}.get(dist, 999)
            if dist == "media" and card_a.definition.color != card_b.definition.color:
                cost = 2
            if card_a.definition.is_logistron or card_b.definition.is_logistron:
                cost = 1
            if self.actions_remaining < cost:
                return f"Necesitas {cost} acciones (tienes {self.actions_remaining})."

        return None

    def link_cards(self, player: int, card_a: CardInstance, card_b: CardInstance) -> Optional[str]:
        err = self.can_link(player, card_a, card_b)
        if err:
            return err

        dist = self.board.spatial_distance(card_a.position, card_b.position)
        if dist:
            cost = {"corta": 1, "media": 1, "larga": 3}[dist]
            if dist == "media" and card_a.definition.color != card_b.definition.color:
                cost = 2
        else:
            cost = 1  # spy links

        if card_a.definition.is_logistron or card_b.definition.is_logistron:
            cost = 1

        self.network.add_link(card_a, card_b)
        self.actions_remaining -= cost
        self._log(f"J{player+1} vincula {card_a.definition.name} <-> {card_b.definition.name}.")
        return None

    # ═══════════════════════════════════════════════════════════════
    # Turn Flow
    # ═══════════════════════════════════════════════════════════════

    def start_turn(self):
        self.phase = Phase.ENTRY
        self.actions_remaining = 4
        self._attacked_squads = set()
        self.log = []
        self._log(f"═══ TURNO {self.turn_number} — Jugador {self.active_player + 1} ═══")

    def entry_phase(self):
        """Entry phase: trigger start-of-turn abilities + draw 2."""
        player = self.active_player
        squads = self.network.find_squads(self.all_cards)

        # Trigger start-of-turn abilities
        for squad in squads:
            for cid in squad.members:
                card = self.all_cards.get(cid)
                if not card or card.owner != player:
                    continue
                for ability in card.definition.abilities:
                    if ability.trigger == "start_of_turn":
                        self._resolve_ability(ability, card, squad, squads)

        # Military faction: free ascension
        for squad in squads:
            if squad.dominant_color == Color.MILITAR:
                # Find a card to ascend
                for cid in squad.members:
                    card = self.all_cards.get(cid)
                    if card and card.owner == player and card.position:
                        _, layer, _ = card.position
                        if layer < 3 and card.position[0] != -1:
                            err = self.ascend(player, card)
                            if not err:
                                self.actions_remaining += 1  # refund the action
                                self._log(f"  Militar: ascenso gratis de {card.definition.name}")
                                break

        # Sabios: extra draw per sage squad
        extra_draws = 0
        for squad in squads:
            if squad.dominant_color == Color.SABIO:
                extra_draws += 1
                # Archivera bonus
                for cid in squad.members:
                    card = self.all_cards.get(cid)
                    if card and card.owner == player and "Archivera" in card.definition.name:
                        extra_draws += 1
                        break

        # Draw 2 + extras
        total_draws = 2 + extra_draws
        drawn = 0
        for _ in range(total_draws):
            card = self._draw_card(player)
            if card:
                drawn += 1
            else:
                self.seals[player] -= 1
                self._log(f"  ¡Fatiga! -1 sello ({self.seals[player]} restantes)")
                if self.seals[player] <= 0:
                    self._end_game(1 - player)
                    return

        self._log(f"  Roba {drawn} carta(s). Mano: {len(self.hands[player])} | Sellos: {self.seals[player]}")
        self.phase = Phase.ACTIONS
        # Politicos: swap positions
        for squad in squads:
            if squad.dominant_color == Color.POLITICO:
                self._log(f"  [Político] Puedes intercambiar posiciones de 2 cartas por escuadrón.")

    def start_attack_phase(self):
        self.phase = Phase.ATTACK
        self._log(f"  >>> Fase de Ataque <<<")

    def exit_phase(self):
        player = self.active_player
        self.phase = Phase.EXIT
        squads = self.network.find_squads(self.all_cards)

        # End of turn triggers
        for squad in squads:
            for cid in squad.members:
                card = self.all_cards.get(cid)
                if not card or card.owner != player:
                    continue
                for ability in card.definition.abilities:
                    if ability.trigger == "end_of_turn":
                        self._resolve_ability(ability, card, squad, squads)

        # Faction effects at end of turn
        for squad in squads:
            dom = squad.dominant_color
            if dom == Color.SELLADOR:
                bonus = 10
                # Abadesa bonus
                for cid in squad.members:
                    card = self.all_cards.get(cid)
                    if card and card.owner == player and "Abadesa" in card.definition.name:
                        bonus += 5
                        break
                self.seals[player] += bonus
                self._log(f"  Escuadrón Sellador: +{bonus} sellos ({self.seals[player]} total)")

            elif dom == Color.SABOTEADOR:
                break_count = 2
                for cid in squad.members:
                    card = self.all_cards.get(cid)
                    if card and card.owner == player and "Agente del Silencio" in card.definition.name:
                        break_count += 1
                        break
                self._log(f"  Escuadrón Saboteador: puedes romper {break_count} vínculos enemigos")

            elif dom == Color.MONSTRUO:
                self._log(f"  Escuadrón Monstruo: puedes remover 1 nodo enemigo (grado < {squad.base_damage})")

        # Discard to 5
        while len(self.hands[player]) > 5:
            discarded = self.hands[player].pop()
            self.discard_piles[player].append(discarded)
            self.seals[player] -= 1
            self._log(f"  Descarte: {discarded.definition.name}. -1 sello ({self.seals[player]})")
            if self.seals[player] <= 0:
                self._end_game(1 - player)
                return

        # Purge isolated enemy nodes
        enemy = 1 - player
        for cid in list(self.all_cards.keys()):
            card = self.all_cards.get(cid)
            if card and card.owner == enemy and card.position and card.position[0] != -1:
                if self.network.link_count(card) == 0 and not card.definition.is_spy:
                    self._destroy_card(card)
                    self._log(f"  Purga: {card.definition.name} aislado, destruido.")

        self._log(f"  Fin del turno. Sellos J{player+1}: {self.seals[player]}")

        # Switch player
        self.active_player = 1 - self.active_player
        self.turn_number += 1

    # ═══════════════════════════════════════════════════════════════
    # Combat
    # ═══════════════════════════════════════════════════════════════

    def get_player_squads(self, player: int) -> list[Squad]:
        """Get squads belonging to a player (majority of members are theirs)."""
        squads = self.network.find_squads(self.all_cards)
        result = []
        for squad in squads:
            own = sum(1 for cid in squad.members
                      if self.all_cards.get(cid) and self.all_cards[cid].owner == player)
            if own > len(squad.members) / 2:
                result.append(squad)
        return result

    def attack(self, attacking_squad: Squad, target: str,
               defending_squad: Optional[Squad] = None,
               target_card_id: Optional[int] = None) -> Optional[str]:
        """
        Execute an attack.
        target: "grimoire" or "card"
        defending_squad: if provided, defender blocks with this squad
        """
        if self.phase != Phase.ATTACK:
            return "No estás en la fase de ataque."

        # Check if squad already attacked
        squad_hash = hash(frozenset(attacking_squad.members))
        if squad_hash in self._attacked_squads:
            return "Este escuadrón ya atacó este turno."

        attacker = self.active_player
        defender = 1 - attacker

        # Calculate attack damage
        base = attacking_squad.base_damage
        all_squads = self.network.find_squads(self.all_cards)
        pot = calculate_potenciamiento(attacking_squad, all_squads, self.network, self.all_cards)

        # D bonus from squad members
        extra = 0
        for cid in attacking_squad.members:
            card = self.all_cards.get(cid)
            if card:
                extra += card.definition.damage_bonus
                # Guerrero faction: +1 per node in L2/L3
                if attacking_squad.dominant_color == Color.GUERRERO:
                    if card.position and card.position[1] >= 2:
                        extra += 1
                # Naturaleza faction: units give +1 damage and +1 pot
                if attacking_squad.dominant_color == Color.NATURALEZA:
                    extra += 1
                    pot += 1

        # Check for Guardián del Bosque (Naturaleza triangle)
        if attacking_squad.squad_type == "triangle" and attacking_squad.dominant_color == Color.NATURALEZA:
            for cid in attacking_squad.members:
                card = self.all_cards.get(cid)
                if card and "Guardián" in card.definition.name:
                    # Other cards give +2 instead of +1
                    others = [c for c in attacking_squad.members if c != cid]
                    extra += len(others)  # already counted above, but this doubles it
                    break

        total_damage = base + pot + extra

        self._log(f"  ⚔️ Ataque: {attacking_squad.squad_type} (base={base} pot={pot} extra={extra}) = {total_damage}")

        # Defense
        defense = 0
        if defending_squad:
            # Calculate defensive potenciamiento (simplified: half of offensive)
            def_pot = calculate_potenciamiento(defending_squad, all_squads, self.network, self.all_cards) // 2
            # Festivo: +2 armor to links
            armor = 0
            if defending_squad.dominant_color == Color.FESTIVO:
                armor = 2
            # Danzante makes links unbreakable (armor boost)
            for cid in defending_squad.members:
                card = self.all_cards.get(cid)
                if card and "Danzante" in card.definition.name:
                    armor += 1
                    break
            defense = def_pot + armor
            self._log(f"  🛡️ Defensa: {defending_squad.squad_type} (pot={def_pot} armor={armor}) = {defense}")

        net_damage = max(0, total_damage - defense)
        self._log(f"  Daño neto: {total_damage} - {defense} = {net_damage}")

        if target == "grimoire":
            self.seals[defender] -= net_damage
            self._log(f"  ¡{net_damage} sellos destruidos! Grimorio enemigo: {self.seals[defender]}")
            if self.seals[defender] <= 0:
                self._end_game(attacker)
        elif target == "card" and target_card_id:
            target_card = self.all_cards.get(target_card_id)
            if target_card:
                target_card.current_hp -= net_damage
                self._log(f"  ¡{net_damage} daño a {target_card.definition.name}! (HP: {target_card.current_hp})")
                if target_card.current_hp <= 0:
                    self._log(f"  {target_card.definition.name} DESTRUIDO.")
                    self._destroy_card(target_card)
                    # Engendro del Vacío: gains HP on kill
                    for cid in attacking_squad.members:
                        card = self.all_cards.get(cid)
                        if card and "Engendro" in card.definition.name:
                            card.current_hp += 1
                            self._log(f"  Engendro del Vacío gana +1 HP ({card.current_hp})")

        self._attacked_squads.add(squad_hash)
        return None

    # ═══════════════════════════════════════════════════════════════
    # Spy actions
    # ═══════════════════════════════════════════════════════════════

    def spy_sabotage(self, player: int, spy_card: CardInstance) -> Optional[str]:
        """Use a spy to break a link in the enemy squad it's parasitizing."""
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if self.actions_remaining < 1:
            return "No te quedan acciones."
        if spy_card.card_id not in self.spies_infiltrated[player]:
            return "Ese espía no está infiltrado."

        # For now, just break a random link of a card the spy is linked to
        links = self.network.get_links(spy_card)
        if not links:
            return "El espía no tiene vínculos que sabotear."

        # Break the first non-spy link
        for neighbor_id in links:
            neighbor = self.all_cards.get(neighbor_id)
            if neighbor and not neighbor.definition.is_spy:
                self.network.remove_link(spy_card, neighbor)
                self.actions_remaining -= 1
                self._log(f"  Sabotaje: {spy_card.definition.name} rompe vínculo con {neighbor.definition.name}")
                return None

        return "No hay vínculos válidos para sabotear."

    def spy_intelligence(self, opponent_hand: list[CardInstance]) -> Optional[CardInstance]:
        """Reveal a random card from opponent's hand (spy intelligence)."""
        if not opponent_hand:
            return None
        return random.choice(opponent_hand)

    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════

    def _resolve_ability(self, ability: Ability, card: CardInstance,
                         squad: Squad, all_squads: list[Squad]):
        """Try to resolve a card ability."""
        # Check conditions
        if ability.ability_type == AbilityType.COLOR:
            if squad.dominant_color != ability.color_required:
                return
        if ability.ability_type == AbilityType.FORMATION:
            if squad.squad_type.replace("_ampliado", "") != ability.formation_required:
                return

        # Execute based on trigger
        if ability.trigger == "start_of_turn":
            if "roba" in ability.description.lower():
                extra = self._draw_card(card.owner)
                if extra:
                    self._log(f"  {card.definition.name}: +1 robo")
        elif ability.trigger == "end_of_turn":
            if "vínculo" in ability.description.lower():
                self._log(f"  {card.definition.name}: +1 vínculo enemigo destruible")

    def _destroy_card(self, card: CardInstance):
        self.network.remove_all_links(card)
        self.board.remove_card(card)
        # Remove from spy tracking
        for p in [0, 1]:
            if card.card_id in self.spies_infiltrated[p]:
                self.spies_infiltrated[p].remove(card.card_id)
        self.discard_piles[card.owner].append(card)

    def _end_game(self, winner: int):
        self.game_over = True
        self.winner = winner
        self._log(f"═══ ¡JUGADOR {winner + 1} HA GANADO! El grimorio enemigo ha sido destruido. ═══")

    # ═══════════════════════════════════════════════════════════════
    # Display
    # ═══════════════════════════════════════════════════════════════

    def display_board(self):
        print(f"\n  ┌─── TABLERO ───────────────────────────────────────────────")
        print(f"  │ Sellos J1: {self.seals[0]:>3}  │  Mano J1: {len(self.hands[0]):>2}  │  Deck J1: {len(self.decks[0]):>2}")
        print(f"  │ Sellos J2: {self.seals[1]:>3}  │  Mano J2: {len(self.hands[1]):>2}  │  Deck J2: {len(self.decks[1]):>2}")
        print(f"  │")

        # J2 territory (top): L1, L2, L3
        for layer_idx in [0, 1, 2]:
            layer = layer_idx + 1
            row = f"  │ J2 L{layer}: "
            for m in range(15):
                cid = self.board.cells[1][layer_idx][m]
                if cid:
                    card = self.all_cards[cid]
                    owner_mark = "*" if card.owner == 0 else " "
                    row += f"[{owner_mark}{card.definition.name[:3]:3s}]"
                else:
                    row += "[    ]"
            print(row)

        # Frontier
        frontier_str = ""
        if self.board.frontier_cards:
            spy_names = [self.all_cards[cid].definition.name[:10]
                        for cid in self.board.frontier_cards]
            frontier_str = f"  Espías: {', '.join(spy_names)}"
        print(f"  │ ═══════════ FRONTERA {frontier_str}")

        # J1 territory (bottom): L3, L2, L1
        for layer_idx in [2, 1, 0]:
            layer = layer_idx + 1
            row = f"  │ J1 L{layer}: "
            for m in range(15):
                cid = self.board.cells[0][layer_idx][m]
                if cid:
                    card = self.all_cards[cid]
                    owner_mark = "*" if card.owner == 1 else " "
                    row += f"[{owner_mark}{card.definition.name[:3]:3s}]"
                else:
                    row += "[    ]"
            print(row)

        print(f"  └─── Acciones: {self.actions_remaining} | Fase: {self.phase.value} | Turno: {self.turn_number} ───┘")

    def display_hand(self, player: int = None):
        if player is None:
            player = self.active_player
        print(f"\n  Mano del Jugador {player + 1}:")
        for i, card in enumerate(self.hands[player]):
            defn = card.definition
            layers = ','.join(f'L{l}' for l in defn.allowed_layers) if defn.allowed_layers else "FRONT"
            forms = ','.join(defn.allowed_formations) if defn.allowed_formations else "—"
            spy_tag = " [ESPÍA]" if defn.is_spy else ""
            logi_tag = " [LOGIS]" if defn.is_logistron else ""
            print(f"  [{i}] {defn.name:30s} | {defn.color.value:12s} | HP:{defn.hp} D:{defn.damage_bonus} V:{defn.link_capacity} | L:{layers:8s} | F:{forms}{spy_tag}{logi_tag}")

    def display_squads(self, player: int = None):
        if player is None:
            player = self.active_player
        squads = self.get_player_squads(player)
        print(f"\n  Escuadrones del Jugador {player + 1}:")
        if not squads:
            print("    (ninguno)")
            return
        for i, s in enumerate(squads):
            names = [self.all_cards[cid].definition.name for cid in s.members if self.all_cards.get(cid)]
            dom = s.dominant_color
            color_str = dom.value if dom else "incoloro"
            print(f"  [{i}] {s.squad_type} | color: {color_str} | daño base: {s.base_damage} | potenciamiento: {s.empowerment}")
            print(f"      Miembros: {', '.join(names)}")

    def show_log(self):
        if self.log:
            print("\n  ── Eventos ──")
            for entry in self.log:
                print(f"  {entry}")
