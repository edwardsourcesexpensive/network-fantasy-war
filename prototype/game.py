"""
Network Fantasy War - Digital Prototype
Game state: complete turn management, combat, spy mechanics, ability triggers.
"""
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from .card import CardInstance, CardDef, Color, Ability, AbilityType
from .enums import Phase
from .board import Board
from .network import Network, Squad, calculate_potenciamiento
from .modifier import Modifier
from .modifier_engine import ModifierEngine
from .ability_registry import get_registry
from . import turn_manager
from . import ability_executor



# Backward-compatible alias for code that imports from game.py
def ability_implementation_status(ability: Ability) -> str:
    """Return implementation status for a card ability.
    
    Delegates to the unified AbilityRegistry. Kept as a backward-compatible
    alias for webui apps that import from game.py.
    """
    return get_registry().status(ability)


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

        # Phase G flags
        self._block_enemy_formation: bool = False
        self._grave_play: dict[int, bool] = {0: False, 1: False}

        # Phase I infrastructure
        self.effect_stack: list[dict] = []  # [{source, target, effect_type, params}]
        self._mind_controlled: dict[int, int] = {}  # card_id -> original_owner
        self._negate_next: bool = False  # Árbitro del Juego

        # Attacked squads this turn
        self._attacked_squads: set = set()  # frozensets of squad member-id sets

        # Spy sabotage tracking (once per spy per turn)
        self._spy_sabotage_used: set[int] = set()

        # Temporary color overrides (cleared in exit_phase)
        # {card_id: Color}
        self._temp_colors: dict[int, Color] = {}

        # Global flag: link costs are 0 this turn
        self._link_cost_free: bool = False

        # Temporary squad damage buffs (cleared in exit_phase)
        # {frozenset(members): +N damage}
        self._temp_squad_buffs: dict[frozenset, int] = {}

        # Parasite attachments: {parasite_card_id: host_card_id}
        self._attached: dict[int, int] = {}

        # Modifier engine: hook → list of active Modifier objects
        # Permanent modifiers registered when cards enter the board,
        # unregistered when they leave. Temp modifiers from active abilities
        # are registered with is_temporary=True and cleaned in exit_phase.
        self.modifiers = ModifierEngine()

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
                owner=player
            )
            instance.current_hp = cdef.hp
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

    def _get_color_overrides(self) -> dict[int, Color]:
        return self.modifiers.get_color_overrides(self)

    def _get_effective_squad_color(self, card: CardInstance, squad: "Squad") -> Optional[Color]:
        return self.modifiers.get_effective_squad_color(self, card, squad)

    def _register_temp_modifier(self, mod: Modifier):
        self.modifiers.register_temp(mod)

    def _unregister_temp_modifiers(self):
        self.modifiers.cleanup()

    def _evaluate_condition(self, condition: dict, source: CardInstance) -> bool:
        return self.modifiers.evaluate_condition(self, condition, source)

    # ═══════════════════════════════════════════════════════════════
    # Modifier Engine
    # ═══════════════════════════════════════════════════════════════

    def _register_modifiers(self, card: CardInstance):
        self.modifiers.register(self, card)

    def _unregister_modifiers(self, card_id: int):
        self.modifiers.unregister(self, card_id)



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
        from_graveyard = False
        return self._place_card_from(player, card, layer, meridian, self.hands[player], hand_index, from_graveyard)

    def play_from_graveyard(self, player: int, grave_index: int, layer: int, meridian: int) -> Optional[str]:
        """G7: play a card directly from the discard pile while _grave_play is set."""
        if not self._grave_play.get(player, False):
            return "No puedes jugar cartas del cementerio ahora."
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if grave_index < 0 or grave_index >= len(self.discard_piles[player]):
            return "Carta no encontrada en el cementerio."
        if self.actions_remaining < 1:
            return f"Necesitas 1 acciones (tienes {self.actions_remaining})."
        card = self.discard_piles[player][grave_index]
        return self._place_card_from(player, card, layer, meridian, self.discard_piles[player], grave_index, True)

    def _place_card_from(self, player: int, card: CardInstance, layer: int, meridian: int,
                         source: list, index: int, from_graveyard: bool) -> Optional[str]:

        # Spy: play on frontier
        if card.definition.is_spy:
            self.board.place_spy_frontier(card)
            source.pop(index)
            self.actions_remaining -= 1
            self._log(f"J{player+1} juega {card.definition.name} en la FRONTERA.")
            return None

        if not card.definition.is_logistron:
            # New rule: cards must enter at L1 by default
            # Vanguardia: allows direct entry at L2
            # Línea de fuego: allows direct entry at L3
            # Spies are exempt (they go to frontier)
            has_vanguardia = any("Vanguardia" in a.description for a in card.definition.abilities)
            has_linea_de_fuego = any("Línea de fuego" in a.description for a in card.definition.abilities)
            
            if layer == 2 and not (has_vanguardia or has_linea_de_fuego):
                return f"{card.definition.name} no puede entrar directamente en L2 (requiere Vanguardia)."
            # Línea de fuego grants L3; some Vanguardia cards also grant L3 per
            # their card text (e.g. "Vanguardia: entra en L3").
            vanguard_grants_l3 = any(
                "Vanguardia" in a.description and "l3" in a.description.lower()
                for a in card.definition.abilities)
            if layer == 3 and not (has_linea_de_fuego or vanguard_grants_l3):
                return f"{card.definition.name} no puede entrar directamente en L3 (requiere Línea de fuego)."
            
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
        source.pop(index)

        # Register permanent/on_enter modifiers
        self._register_modifiers(card)

        # ─── Dispatch on_enter modifiers ───
        for mod in self.modifiers.get("on_enter"):
            if mod.source_card_id == card.card_id:
                if mod.effect_type == "vanguard_entry":
                    # Positional entry is already enforced/validated by the
                    # layer checks in play_card(); the modifier is declarative
                    # only, so don't no-op-dispatch it through _apply_on_enter.
                    continue
                self.modifiers.dispatch_card_hook("on_enter", self, card, player=player)

        # ─── after_play hook ───
        for mod in self.modifiers.get("after_play"):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != player:
                continue
            if mod.effect_type == "draw_on_play" and mod.source_card_id != card.card_id:
                # Another card triggers draw when something is played
                pass  # Reserved for future patterns

        self.actions_remaining -= 1

        # Trigger Vanguardia ability
        if any(a.trigger == "on_enter" and "Vanguardia" in a.description
               for a in card.definition.abilities):
            # Vanguardia: enters directly in L2 — already handled by selection
            pass

        src = "cementerio" if from_graveyard else "mano"
        self._log(f"J{player+1} juega {card.definition.name} en L{layer}:{meridian} (desde {src}).")
        return None

    def can_ascend(self, player: int, card: CardInstance, free: bool = False) -> Optional[str]:
        if not free:
            if player != self.active_player:
                return "No es tu turno."
            if self.phase != Phase.ACTIONS:
                return "No estás en la fase de acciones."

        # ─── on_ascend hook ───
        for mod in self.modifiers.get("on_ascend"):
            if mod.source_card_id == card.card_id and mod.effect_type == "cannot_ascend":
                return f"{card.definition.name} no puede ascender."

        if not card.position or card.position[0] == -1:
            if card.definition.is_spy and self.actions_remaining >= 1:
                return None
            return "Esa carta no está en posición de ascender."
        _, layer, meridian = card.position
        if layer >= 3:
            return "Esa carta no está en posición de ascender."
        new_layer = layer + 1
        if new_layer not in card.definition.allowed_layers:
            return f"{card.definition.name} solo puede estar en L{card.definition.allowed_layers}."
        if not free:
            cost = 1 if layer == 1 else 2
            if self.actions_remaining < cost:
                return f"Necesitas {cost} acciones (tienes {self.actions_remaining})."
        new_li = layer
        if self.board.cells[player][new_li][meridian] is not None:
            return "Celda de destino ocupada."
        return None

    def ascend(self, player: int, card: CardInstance, free: bool = False) -> Optional[str]:
        # P1: Check permanent cannot_ascend modifiers
        ascend_err = self.modifiers.check_cannot_ascend(self, card)
        if ascend_err:
            return ascend_err
        
        err = self.can_ascend(player, card, free=free)
        if err:
            return err

        if card.definition.is_spy:
            # P3: Check if infiltration is blocked
            infiltrate_err = self.modifiers.can_infiltrate(self, card)
            if infiltrate_err:
                return infiltrate_err
            
            # P3: Get allowed infiltration layers
            allowed_layers = self.modifiers.get_infiltrate_layer(self, card)
            
            # Disuelve vínculos con unidades propias antes de infiltrarse
            for neighbor_id in list(self.network.get_links(card)):
                neighbor = self.all_cards.get(neighbor_id)
                if neighbor and neighbor.owner == player and neighbor.position and neighbor.position[0] != -1:
                    self.network.remove_link(card, neighbor)
                    self._log(f"  Vínculo espía disuelto: {card.definition.name} ⟷ {neighbor.definition.name}")
            # Infiltrate spy into enemy territory
            self.spies_infiltrated[player].append(card.card_id)
            self.board.frontier_cards.remove(card.card_id)
            enemy = 1 - player
            # P3: Try allowed layers (default L3, Espía de Trinchera can go L1/L2)
            placed = False
            for target_layer in allowed_layers:
                m = self.board.find_empty_meridian(enemy, target_layer)
                if m is not None:
                    self.board.place_card(enemy, card, target_layer, m)
                    placed = True
                    break
            if not placed:
                self.board.place_spy_frontier(card)
                return "No hay espacio en territorio enemigo para infiltrar."
            card.owner = player  # Still owned by original player
            self.actions_remaining -= 1
            self._log(f"¡{card.definition.name} se infiltra en territorio enemigo! L{card.position[1]}:{card.position[2]}")
            
            # P3: Post-infiltration effects
            self.modifiers.on_spy_infiltrate(self, card, card.position[1])
            
            return None

        _, layer, meridian = card.position
        cost = 1 if layer == 1 else 2
        old_li = layer - 1
        new_layer = layer + 1
        new_li = new_layer - 1

        self.board.cells[player][old_li][meridian] = None
        self.board.cells[player][new_li][meridian] = card.card_id
        card.position = (player, new_layer, meridian)
        if not free:
            self.actions_remaining -= cost

        # Caudillismo trigger
        if new_layer == 3:
            if any(a.trigger == "on_ascend" for a in card.definition.abilities):
                # Auto-link to a VALID node in L2: both ends need capacity, and
                # distance must be corta/media (not "larga" — every other link
                # path enforces distance, the free caudillismo link does too).
                for m2 in range(15):
                    neighbor_cid = self.board.cells[player][1][m2]  # L2 index = 1
                    if not neighbor_cid:
                        continue
                    neighbor = self.all_cards.get(neighbor_cid)
                    if neighbor is None:
                        continue
                    if not (self.network.can_link(card) and self.network.can_link(neighbor)):
                        continue  # over-capacity — try the next candidate
                    dist = self.board.spatial_distance(card.position, neighbor.position)
                    if dist in ("corta", "media"):
                        self.network.add_link(card, neighbor)
                        self._log(f"  Caudillismo: vínculo gratis con {neighbor.definition.name} ({dist})")
                        break

        self._log(f"J{player+1} asciende {card.definition.name} a L{new_layer}.")
        return None

    def move_card(self, player: int, card: CardInstance, direction: int) -> Optional[str]:
        """
        Move a card horizontally (free action, 0 cost).
        direction: -1 (left) or +1 (right) in meridians.
        Links that exceed valid distance after move are dissolved.
        """
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if not card.position:
            return "Carta sin posición."
        if direction not in (-1, 1):
            return "Dirección inválida."

        # ─── on_move hook ───
        for mod in self.modifiers.get("on_move"):
            if mod.source_card_id == card.card_id and mod.effect_type == "cannot_move":
                return f"{card.definition.name} no puede ser movido."

        p, layer, meridian = card.position
        new_m = meridian + direction
        li = layer - 1

        if new_m < 0 or new_m >= 15:
            return "Fuera del tablero."
        if self.board.cells[p][li][new_m] is not None:
            return "Celda ocupada."

        # Move the card
        self.board.cells[p][li][meridian] = None
        self.board.cells[p][li][new_m] = card.card_id
        card.position = (p, layer, new_m)

        # Break links that exceed valid distance
        broken = []
        for neighbor_id in list(self.network.links.get(card.card_id, set())):
            neighbor = self.all_cards.get(neighbor_id)
            if neighbor and neighbor.position:
                dist = self.board.spatial_distance(card.position, neighbor.position)
                if dist is None:
                    self.network.remove_link(card, neighbor)
                    broken.append(neighbor.definition.name)

        self._log(f"J{player+1} mueve {card.definition.name} a L{layer}:{new_m}.")
        if broken:
            self._log(f"  Vínculos rotos: {', '.join(broken)}")
        return None

    # ═══════════════════════════════════════════════════════════════
    # Active Abilities
    # ═══════════════════════════════════════════════════════════════

    def can_use_ability(self, player: int, card: CardInstance,
                        ability_index: int = 0, reactive: bool = False) -> Optional[str]:
        return ability_executor.can_use_ability(self, player, card, ability_index, reactive)

    def use_ability(self, player: int, card: CardInstance,
                    ability_index: int = 0, targets: dict = None) -> Optional[str]:
        return ability_executor.use_ability(self, player, card, ability_index, targets)

    def _squad_of(self, card_id: int) -> Optional["Squad"]:
        return ability_executor._squad_of(self, card_id)

    def can_link(self, player: int, card_a: CardInstance, card_b: CardInstance,
                 bypass_distance: bool = False) -> Optional[str]:
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

        # Parasite block: host cannot create new links
        if card_a.card_id in self._attached.values():
            return f"{card_a.definition.name} está parasitado, no puede crear vínculos."
        if card_b.card_id in self._attached.values():
            return f"{card_b.definition.name} está parasitado, no puede crear vínculos."

        # Reticencia check
        for card, other in [(card_a, card_b), (card_b, card_a)]:
            for ability in card.definition.abilities:
                if "Reticencia" in ability.description:
                    # Simplified: check if other's color is mentioned
                    if other.definition.color.value.lower() in ability.description.lower():
                        return f"{card.definition.name} es reticente a {other.definition.color.value}."

        # Frontier / distance check
        a_on_frontier = card_a.position and card_a.position[0] == -1
        b_on_frontier = card_b.position and card_b.position[0] == -1
        
        if not bypass_distance and not (a_on_frontier and b_on_frontier):
            # Frontier ↔ enemy L3: special case, cost = 4
            is_frontier_l3 = False
            if a_on_frontier and not b_on_frontier and card_b.owner != player:
                is_frontier_l3 = True
            elif b_on_frontier and not a_on_frontier and card_a.owner != player:
                is_frontier_l3 = True
            
            if is_frontier_l3:
                cost = 4
            else:
                dist = self.board.spatial_distance(card_a.position, card_b.position)
                if dist is None:
                    return "Distancia espacial inválida para vínculo."
                cost = {"corta": 1, "media": 1, "larga": 3}.get(dist, 999)
                if dist == "media" and card_a.definition.color != card_b.definition.color:
                    cost = 2
            
            # Logistron always costs 1 (prevails over frontier-L3 and all others)
            if card_a.definition.is_logistron or card_b.definition.is_logistron:
                cost = 1
            
            if self.actions_remaining < cost:
                return f"Necesitas {cost} acciones (tienes {self.actions_remaining})."

        # ─── before_link hook ───
        # Modifiers can block or modify link validation
        for mod in self.modifiers.get("before_link"):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card:
                continue
            if mod.effect_type == "link_cost_zero":
                # Handled in link_cards — reduces cost to 0
                pass
            if mod.effect_type == "cannot_link":
                if mod.source_card_id in (card_a.card_id, card_b.card_id):
                    return f"{source_card.definition.name} no puede vincularse."

        return None

    def link_cards(self, player: int, card_a: CardInstance, card_b: CardInstance,
                   bypass_distance: bool = False, is_temp: bool = False) -> Optional[str]:
        err = self.can_link(player, card_a, card_b, bypass_distance=bypass_distance)
        if err:
            return err

        a_on_frontier = card_a.position and card_a.position[0] == -1
        b_on_frontier = card_b.position and card_b.position[0] == -1
        
        if bypass_distance or (a_on_frontier and b_on_frontier):
            cost = 1
        else:
            # Frontier ↔ enemy L3: cost = 4
            is_frontier_l3 = False
            if a_on_frontier and not b_on_frontier and card_b.owner != player:
                is_frontier_l3 = True
            elif b_on_frontier and not a_on_frontier and card_a.owner != player:
                is_frontier_l3 = True
            
            if is_frontier_l3:
                cost = 4
            else:
                dist = self.board.spatial_distance(card_a.position, card_b.position)
                if dist:
                    cost = {"corta": 1, "media": 1, "larga": 3}[dist]
                    if dist == "media" and card_a.definition.color != card_b.definition.color:
                        cost = 2
                else:
                    cost = 1

        # Logistron always costs 1 (prevails over all)
        if card_a.definition.is_logistron or card_b.definition.is_logistron:
            cost = 1
        
        # Check before_link modifiers for cost_zero
        for mod in self.modifiers.get("before_link"):
            if mod.effect_type == "link_cost_zero":
                if mod.layer == "global":
                    cost = 0
                    self._log(f"  Vínculo sin costo (efecto global)")
                    break
                source_card = self.all_cards.get(mod.source_card_id)
                if source_card and source_card.owner == player:
                    if mod.source_card_id in (card_a.card_id, card_b.card_id):
                        cost = 0
                        self._log(f"  {source_card.definition.name}: vínculo sin costo")

        # Guard: never let the action ledger go negative (bypass/free-link
        # paths previously skipped the affordability check and could push it
        # below zero). If cost was waived to 0 this is a no-op.
        if cost > 0 and self.actions_remaining < cost:
            return f"Necesitas {cost} acciones (tienes {self.actions_remaining})."

        # P1: Check if link is unbreakable
        if self.modifiers.check_link_unbreakable(self, card_a, card_b):
            self._log(f"  🔒 Vínculo protegido: no puede ser roto")
        
        self.network.add_link(card_a, card_b)

        # ─── after_link hook ───
        # On-link triggers from permanent modifiers
        for mod in self.modifiers.get("after_link"):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != player:
                continue
            # Check if source card is involved in this link
            if mod.source_card_id not in (card_a.card_id, card_b.card_id):
                continue
            if mod.effect_type == "draw_on_link":
                extra = self._draw_card(player)
                if extra:
                    self._log(f"  {source_card.definition.name}: +1 robo por vínculo")

        self.actions_remaining -= cost
        
        if is_temp:
            pair = tuple(sorted((card_a.card_id, card_b.card_id)))
            self._register_temp_modifier(Modifier(
                source_card_id=card_a.card_id, hook="end_of_turn",
                effect_type="dissolve_temp_link", layer="self",
                params={"pair": pair}))
        
        self._log(f"J{player+1} vincula {card_a.definition.name} <-> {card_b.definition.name}.")
        return None

    # ═══════════════════════════════════════════════════════════════
    # Turn Flow
    # ═══════════════════════════════════════════════════════════════

    def start_turn(self):
        turn_manager.start_turn(self)

    def entry_phase(self):
        """Entry phase: trigger start-of-turn abilities + draw 2."""
        turn_manager.entry_phase(self)

    def start_attack_phase(self):
        turn_manager.start_attack_phase(self)

    def exit_phase(self):
        # P3: Check spy turn effects before cleanup
        self.modifiers.check_spy_turn_effects(self, self.active_player)
        turn_manager.exit_phase(self)

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

        # ─── Apply modify_squad modifiers ───
        for mod in self.modifiers.get("modify_squad"):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != player:
                continue

            if mod.effect_type == "ignore_color":
                # Find squad containing the source card and mark it as color-ignored
                for squad in result:
                    if mod.source_card_id in squad.members:
                        squad.ignored_color_cards.add(mod.source_card_id)
                        break

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

        # G1: a squad containing a card flagged "cannot attack this turn" can't attack
        for cid in attacking_squad.members:
            c = self.all_cards.get(cid)
            if c is not None and getattr(c, "_cannot_attack", False):
                return f"{c.definition.name} no puede atacar este turno."

        # Check if squad already attacked. A squad counts as "the same one that
        # already attacked" if it shares ≥2 members with any squad that attacked
        # this turn — so toggling ONE link (add/drop a member) can't reset the
        # one-attack-per-squad rule by changing the frozenset hash.
        member_set = set(attacking_squad.members)
        for prev_members in self._attacked_squads:
            if len(member_set & prev_members) >= 2:
                return "Este escuadrón ya atacó este turno."

        attacker = self.active_player
        defender = 1 - attacker

        # ─── before_attack hook ───
        # Cards with sigilo block attacks on themselves; guardaespaldas redirect
        if target == "card" and target_card_id:
            for mod in self.modifiers.get("before_attack"):
                source_card = self.all_cards.get(mod.source_card_id)
                if not source_card or source_card.owner != defender:
                    continue
                if mod.effect_type == "cannot_be_attacked":
                    if mod.source_card_id == target_card_id or mod.layer == "squad":
                        # Check if any squad member is the protected one
                        squad_members = set()
                        for sq in self.get_player_squads(defender):
                            if mod.source_card_id in sq.members:
                                squad_members = sq.members
                                break
                        if mod.source_card_id == target_card_id or target_card_id in squad_members:
                            return f"{source_card.definition.name} tiene Sigilo: no puede ser atacado."
            
            # P1: Additional before_attack immunities from permanent passives
            immunity_err = self.modifiers.check_before_attack_immunity(
                self, target_card_id, attacking_squad)
            if immunity_err:
                return immunity_err

        # Calculate attack damage
        base = attacking_squad.base_damage
        all_squads = self.network.find_squads(self.all_cards)
        pot = calculate_potenciamiento(attacking_squad, all_squads, self.network, self.all_cards)
        # G2: enemy blocked their formation bonus this turn → no potenciamiento
        if self._block_enemy_formation:
            pot = 0

        # D bonus from squad members
        extra = 0
        for cid in attacking_squad.members:
            card = self.all_cards.get(cid)
            if card:
                extra += card.definition.damage_bonus
                # Temp D buffs now handled by modify_damage modifier hook
                # Guerrero faction: +1 per node in L2/L3
                if attacking_squad.get_dominant_color(self._get_color_overrides()) == Color.GUERRERO:
                    if card.position and card.position[1] >= 2:
                        extra += 1
                # Naturaleza faction: units give +1 damage and +1 pot
                if attacking_squad.get_dominant_color(self._get_color_overrides()) == Color.NATURALEZA:
                    extra += 1
                    pot += 1

        # Check for Guardián del Bosque (Naturaleza triangle)
        if attacking_squad.squad_type == "triangle" and attacking_squad.get_dominant_color(self._get_color_overrides()) == Color.NATURALEZA:
            for cid in attacking_squad.members:
                card = self.all_cards.get(cid)
                if card and "Guardián" in card.definition.name:
                    # Other cards give +2 instead of +1
                    others = [c for c in attacking_squad.members if c != cid]
                    extra += len(others)  # already counted above, but this doubles it
                    break

        total_damage = base + pot + extra

        # ─── modify_damage hook ───
        # Permanent +D modifiers (e.g., "+1 D mientras esté en L2")
        for mod in self.modifiers.get("modify_damage"):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != attacker:
                continue
            if mod.effect_type == "damage_bonus":
                # Check condition + squad membership
                condition = mod.params.get("condition", {})
                if not self.modifiers.evaluate_condition(self, condition, source_card):
                    continue
                if mod.source_card_id in attacking_squad.members:
                    total_damage += mod.params.get("delta", 0)

        # ─── on_attack hook ───
        # Attack-triggered effects (ignore_armor, double_damage, conditional bonuses)
        ignore_armor_total = 0
        double_damage = False
        for mod in self.modifiers.get("on_attack"):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != attacker:
                continue
            if mod.source_card_id not in attacking_squad.members:
                continue
            condition = mod.params.get("condition", {})
            if condition and not self.modifiers.evaluate_condition(self, condition, source_card):
                continue
            if mod.effect_type == "ignore_armor":
                ignore_armor_total = max(ignore_armor_total, mod.params.get("amount", 1))
            elif mod.effect_type == "double_damage":
                double_damage = True
            elif mod.effect_type == "bonus_vs_nodes":
                if target == "card" and target_card_id:
                    target_card = self.all_cards.get(target_card_id)
                    if target_card:
                        total_damage += mod.params.get("delta", 2)
            elif mod.effect_type == "bonus_vs_high_hp":
                if target == "card" and target_card_id:
                    target_card = self.all_cards.get(target_card_id)
                    if target_card and target_card.current_hp >= mod.params.get("hp_threshold", 5):
                        total_damage += mod.params.get("delta", 1)
            elif mod.effect_type == "bonus_per_link":
                link_count = self.network.link_count(source_card)
                total_damage += min(link_count, mod.params.get("max", 3))
            elif mod.effect_type == "bonus_vs_grimoire":
                if target == "grimoire":
                    total_damage += mod.params.get("delta", 4)
        if double_damage:
            total_damage *= 2

        self._log(f"  ⚔️ Ataque: {attacking_squad.squad_type} (base={base} pot={pot} extra={extra}) = {total_damage}")

        # Defense
        defense = 0
        if defending_squad:
            # Calculate defensive potenciamiento (simplified: half of offensive)
            def_pot = calculate_potenciamiento(defending_squad, all_squads, self.network, self.all_cards) // 2
            # Festivo: +2 armor to links
            armor = 0
            if defending_squad.get_dominant_color(self._get_color_overrides()) == Color.FESTIVO:
                armor = 2
            # Danzante makes links unbreakable (armor boost)
            for cid in defending_squad.members:
                card = self.all_cards.get(cid)
                if card and "Danzante" in card.definition.name:
                    armor += 1
                    break
            # Link armor from before_link modifiers
            for mod in self.modifiers.get("before_link"):
                if mod.effect_type == "link_armor_bonus":
                    source_card = self.all_cards.get(mod.source_card_id)
                    if source_card and source_card.card_id in defending_squad.members:
                        armor += mod.params.get("amount", 1)
            defense = def_pot + armor
            # Apply ignore_armor from on_attack modifiers
            if ignore_armor_total > 0:
                old_defense = defense
                defense = max(0, defense - ignore_armor_total)
                self._log(f"  ⚡ Ignora {ignore_armor_total} armadura: {old_defense} → {defense}")
            self._log(f"  🛡️ Defensa: {defending_squad.squad_type} (pot={def_pot} armor={armor}) = {defense}")

        net_damage = max(0, total_damage - defense)
        self._log(f"  Daño neto: {total_damage} - {defense} = {net_damage}")

        if target == "grimoire":
            # ─── grimoire_defense hook ───
            # Use ModifierEngine's unified grimoire defense (handles P1 permanent passives)
            net_damage, cancel_reason = self.modifiers.apply_grimoire_defense(
                self, defender, net_damage, attack_type="normal")
            if cancel_reason:
                self._log(f"  🛡️ {cancel_reason}")
                self._attacked_squads.add(frozenset(member_set))
                return None

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
                    # Find a killer from attacking squad
                    killer_card = None
                    for cid in attacking_squad.members:
                        kc = self.all_cards.get(cid)
                        if kc:
                            killer_card = kc
                            break
                    self._destroy_card(target_card, killer=killer_card)

        self._attacked_squads.add(frozenset(member_set))
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
        if spy_card.card_id in self._spy_sabotage_used:
            return "Este espía ya usó sabotaje este turno."

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
                self._spy_sabotage_used.add(spy_card.card_id)
                self._log(f"  Sabotaje: {spy_card.definition.name} rompe vínculo con {neighbor.definition.name}")
                return None

        return "No hay vínculos válidos para sabotear."

    def spy_intelligence(self, opponent_hand: list[CardInstance]) -> Optional[CardInstance]:
        """Reveal a random card from opponent's hand (spy intelligence)."""
        if not opponent_hand:
            return None
        return random.choice(opponent_hand)

    def spy_return(self, player: int, spy_card: CardInstance) -> Optional[str]:
        """Return an infiltrated spy to the frontier."""
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if spy_card.card_id not in self.spies_infiltrated[player]:
            return "Ese espía no está infiltrado."
        
        # Check if spy can return (Maestro de Espías, Agente Triple)
        if not self.modifiers.can_return_to_frontier(self, spy_card):
            return "Este espía no puede regresar a la frontera."
        
        cost = self.modifiers.get_infiltrate_cost(self, spy_card)
        if self.actions_remaining < cost:
            return f"Necesitas {cost} acciones (tienes {self.actions_remaining})."
        
        # Remove from enemy territory
        enemy = 1 - player
        if spy_card.position and spy_card.position[0] == enemy:
            self.board.remove_card(spy_card)
        
        # Remove from infiltrated list
        self.spies_infiltrated[player].remove(spy_card.card_id)
        
        # Remove any attachments
        if spy_card.card_id in self._attached:
            del self._attached[spy_card.card_id]
        
        # Place on frontier
        self.board.place_spy_frontier(spy_card)
        self.actions_remaining -= cost
        self._log(f"J{player+1} regresa {spy_card.definition.name} a la frontera.")
        return None

    # ═══════════════════════════════════════════════════════════════
    # Trigger Modifier Dispatch
    # ═══════════════════════════════════════════════════════════════


    def _destroy_card(self, card: CardInstance, killer: Optional[CardInstance] = None):
        # ─── before_destroy hook ───
        for mod in self.modifiers.get("before_destroy"):
            if mod.source_card_id == card.card_id and mod.effect_type == "destroy_immunity":
                source = self.all_cards.get(mod.source_card_id)
                name = source.definition.name if source else f"#{mod.source_card_id}"
                self._log(f"  🛡️ {name} es inmune a destrucción.")
                return  # Card survives
        
        # P1: Additional destroy immunities from permanent passives
        if self.modifiers.check_destroy_immunity(self, card, destroyer=killer):
            self._log(f"  🛡️ {card.definition.name} es inmune a destrucción.")
            return  # Card survives

        self.network.remove_all_links(card)
        self.board.remove_card(card)

        # Unregister all modifiers from this card
        self._unregister_modifiers(card.card_id)

        # Remove from spy tracking
        for p in [0, 1]:
            if card.card_id in self.spies_infiltrated[p]:
                self.spies_infiltrated[p].remove(card.card_id)
        self.discard_piles[card.owner].append(card)

        # Clean up attachments: if this card was a host, free parasites
        freed = [pid for pid, hid in self._attached.items() if hid == card.card_id]
        for pid in freed:
            del self._attached[pid]
        # If this card was a parasite, remove attachment
        if card.card_id in self._attached:
            del self._attached[card.card_id]

        # ─── Dispatch on_kill modifiers for the killer ───
        if killer:
            squads = self.network.find_squads(self.all_cards)
            for mod in self.modifiers.get("on_kill"):
                c = self.all_cards.get(mod.source_card_id)
                if not c or c.owner != killer.owner or not c.position or c.position[0] == -1:
                    continue
                # Find the killer's squad
                killer_squad = None
                for sq in squads:
                    if killer.card_id in sq.members and c.card_id in sq.members:
                        killer_squad = sq
                        break
                if not killer_squad:
                    continue
                # Execute the on_kill effect
                effect_type = mod.effect_type
                player = killer.owner
                if effect_type == "gain_hp_on_kill":
                    c.current_hp += mod.params.get("amount", 1)
                    self._log(f"  {c.definition.name}: +{mod.params.get('amount', 1)} HP por destrucción ({c.current_hp})")
                elif effect_type == "enemy_seal_loss_on_kill":
                    enemy = 1 - player
                    amount = mod.params.get("amount", 2)
                    self.seals[enemy] = max(0, self.seals[enemy] - amount)
                    self._log(f"  {c.definition.name}: enemigo pierde {amount} sellos ({self.seals[enemy]})")
                    if self.seals[enemy] <= 0:
                        self._end_game(player)
                elif effect_type == "draw_on_kill":
                    extra = self._draw_card(player)
                    if extra:
                        self._log(f"  {c.definition.name}: +1 robo por destrucción")

        # ─── after_destroy hook ───
        # Transfer links from destroyed card to another
        for mod in self.modifiers.get("after_destroy"):
            if mod.effect_type == "transfer_links":
                target = self.all_cards.get(mod.source_card_id)
                if not target or not target.position:
                    continue
                # Link target to cards that were linked to the destroyed card
                # (links already removed, but we can re-link to the target)
                self._log(f"  {target.definition.name}: hereda vínculos de {card.definition.name}")

    def _end_game(self, winner: int):
        turn_manager._end_game(self, winner)

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
            dom = s.get_dominant_color(self._get_color_overrides())
            color_str = dom.value if dom else "incoloro"
            print(f"  [{i}] {s.squad_type} | color: {color_str} | daño base: {s.base_damage} | potenciamiento: {s.empowerment}")
            print(f"      Miembros: {', '.join(names)}")

    def show_log(self):
        if self.log:
            print("\n  ── Eventos ──")
            for entry in self.log:
                print(f"  {entry}")
