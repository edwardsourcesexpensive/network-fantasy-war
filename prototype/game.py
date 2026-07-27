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


def ability_implementation_status(ability: Ability) -> str:
    """Return implementation status for a card ability.
    
    Returns one of:
      - "implemented": fully functional
      - "partial": partially implemented (e.g., logged but no mechanical effect)
      - "not_implemented": description only, no code
    """
    desc = ability.description.lower()
    atype = ability.ability_type
    trigger = ability.trigger

    # ─── ACTIVE abilities (use_ability handles these) ───
    if atype == AbilityType.ACTIVE and ability.action_cost > 0:
        # Keyword-matched effects in use_ability()
        implemented_kw = [
            ("roba", "control" not in desc and "vínculo" not in desc),  # draw
            ("gana", any(w in desc for w in ["sello", "sellos"])),      # gain seals
            ("repara", any(w in desc for w in ["sello", "sellos"])),    # repair seals
            ("cura", "hp" in desc),                                      # heal
            ("asciende", True),                                          # ascend
            ("destrúyete", True) or ("destruyete", True),                # self-destruct
            ("pierde", any(w in desc for w in ["sello", "sellos"])),    # enemy loses seals
            ("mira", any(w in desc for w in ["carta", "cartas", "reserva", "tope"])),  # scry
            ("descarta", True),                                          # discard
            # Phase B additions
            ("intercambia", True),                                       # swap (position, layer, HP, color, hand)
            ("vínculo", "ignorando" in desc or "temporal" in desc or "disuelve" in desc),  # special links
            ("vínculo", "armadura" in desc),                             # link armor reduction
            ("rompe", "vínculo" in desc and "escuadrón" in desc),        # break squad links
            ("destruye", "vínculo" in desc),                             # destroy specific link
            ("costos de vínculo", True),                                 # link cost free
            ("cambia", "color" in desc),                                 # change color
            ("escuadrón se considera del color", True),                  # squad color
            ("salta", "celda libre" in desc),                            # jump to free cell
            ("teletransporta", True),                                    # teleport ally
            ("ataca", "nodo" in desc),                                   # direct node attack
            ("lucha", "daño" in desc),                                   # fight
            ("destruye", "grimorio" in desc),                            # destroy ally + damage
        ]
        for kw, cond in implemented_kw:
            if kw in desc and cond:
                return "implemented"
        
        # +HP or +D temp buff
        if any(w in desc for w in ["gana +", "gana +"]) and "hp" in desc:
            return "implemented"
        if "+" in desc and "d" in desc and "hp" not in desc:
            return "implemented"

        # Fallthrough: active but not keyword-matched
        return "not_implemented"

    # ─── PASSIVE abilities (_resolve_ability handles these) ───
    if trigger == "start_of_turn":
        if "roba" in desc or "robo" in desc:
            return "implemented"
        if "mira" in desc:
            return "implemented"
        if "asciende" in desc or "ascender" in desc:
            return "implemented"
        if "acción" in desc or "accion" in desc:
            return "implemented"
        if "vínculo" in desc and "gratis" in desc:
            return "implemented"
        return "not_implemented"

    if trigger == "end_of_turn":
        if "recupera" in desc and "hp" in desc:
            return "implemented"
        if "vínculo" in desc:
            return "partial"
        if "sello" in desc:
            return "implemented"
        return "not_implemented"

    if trigger == "on_enter":
        # Vanguardia / Línea de fuego: checked in play_card()
        if "vanguardia" in desc or "línea de fuego" in desc:
            return "implemented"
        return "not_implemented"

    if trigger == "on_ascend":
        # Caudillismo: auto-link in ascend()
        if "caudillismo" in desc.lower() or "vínculo gratis" in desc.lower():
            return "implemented"
        return "not_implemented"

    if trigger == "permanent":
        # Reticencia: checked in can_link()
        if "reticencia" in desc.lower():
            return "implemented"
        # Sigilo: not implemented
        if "sigilo" in desc.lower():
            return "not_implemented"
        return "not_implemented"

    if trigger == "on_attack":
        # Guerrero +1 per L2/L3: checked in attack()
        # Naturaleza units: checked in attack()
        # Guardián del Bosque: checked in attack()
        # Engendro del Vacío: checked in attack()
        return "implemented"  # Most on_attack are checked inline in attack()

    if trigger == "on_kill":
        if "gana" in desc and "hp" in desc:
            return "implemented"
        if "pierde" in desc and "sello" in desc:
            return "implemented"
        if "roba" in desc:
            return "implemented"
        return "not_implemented"

    # COLOR/FORMATION abilities — same trigger keywords as GENERIC above
    if atype == AbilityType.COLOR or atype == AbilityType.FORMATION:
        if trigger == "end_of_turn":
            if "sellador" in desc.lower() or "sello" in desc:
                return "implemented"
            if "saboteador" in desc.lower() or "vínculo" in desc:
                return "partial"
            if "monstruo" in desc.lower():
                return "partial"
            if "recupera" in desc and "hp" in desc:
                return "implemented"
            if "restaura" in desc and "armadura" in desc:
                return "partial"  # armor restore not fully implemented
            return "not_implemented"
        if trigger == "start_of_turn":
            if "roba" in desc or "robo" in desc:
                return "implemented"
            if "acción" in desc or "accion" in desc:
                return "implemented"
            if "asciende" in desc or "ascender" in desc:
                return "implemented"
            if "vínculo" in desc and "gratis" in desc:
                return "implemented"
            return "not_implemented"
        if trigger == "on_attack":
            return "implemented"  # Color checks in attack()
        if trigger == "permanent":
            if "armadura" in desc.lower() or "festivo" in desc.lower():
                return "implemented"
            return "not_implemented"
        return "not_implemented"

    # Default
    return "not_implemented"


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

        # Temporary buffs applied this turn (cleared in exit_phase)
        # {card_id: [{"attr": "d", "delta": 2}, ...]}
        self._temp_buffs: dict[int, list[dict]] = {}

        # Temporary color overrides (cleared in exit_phase)
        # {card_id: Color}
        self._temp_colors: dict[int, Color] = {}

        # Temporary links that dissolve at end of turn
        # set of (card_id, card_id) tuples
        self._temp_links: set[tuple] = set()

        # Global flag: link costs are 0 this turn
        self._link_cost_free: bool = False

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
            # New rule: cards must enter at L1 by default
            # Vanguardia: allows direct entry at L2
            # Línea de fuego: allows direct entry at L3
            # Spies are exempt (they go to frontier)
            has_vanguardia = any("Vanguardia" in a.description for a in card.definition.abilities)
            has_linea_de_fuego = any("Línea de fuego" in a.description for a in card.definition.abilities)
            
            if layer == 2 and not has_vanguardia and not has_linea_de_fuego:
                return f"{card.definition.name} no puede entrar directamente en L2 (requiere Vanguardia)."
            if layer == 3 and not has_linea_de_fuego:
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
        self.hands[player].pop(hand_index)
        self.actions_remaining -= 1

        # Trigger Vanguardia ability
        if any(a.trigger == "on_enter" and "Vanguardia" in a.description
               for a in card.definition.abilities):
            # Vanguardia: enters directly in L2 — already handled by selection
            pass

        self._log(f"J{player+1} juega {card.definition.name} en L{layer}:{meridian}.")
        return None

    def can_ascend(self, player: int, card: CardInstance, free: bool = False) -> Optional[str]:
        if not free:
            if player != self.active_player:
                return "No es tu turno."
            if self.phase != Phase.ACTIONS:
                return "No estás en la fase de acciones."
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
        err = self.can_ascend(player, card, free=free)
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
        if not free:
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
                        ability_index: int = 0) -> Optional[str]:
        """Check if a card can use an active ability."""
        if player != self.active_player:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS:
            return "No estás en la fase de acciones."
        if not card.position or card.position[0] == -1:
            return "La carta no está en el tablero."

        active_abilities = [a for a in card.definition.abilities
                           if a.ability_type.name == 'ACTIVE']
        if ability_index < 0 or ability_index >= len(active_abilities):
            return "Habilidad no encontrada."
        ability = active_abilities[ability_index]

        cost = ability.action_cost
        if self.actions_remaining < cost:
            return f"Necesitas {cost} acciones (tienes {self.actions_remaining})."
        return None

    def use_ability(self, player: int, card: CardInstance,
                    ability_index: int = 0, targets: dict = None) -> Optional[str]:
        """Activate an active ability on a card.

        Supported effects (keyword matching on description):
        - "roba N carta(s)": draw cards
        - "gana N sello(s)": gain seals
        - "cura N HP": heal a card
        - "repara N sello(s)": repair seals
        - "asciende": ascend the card (reuse existing logic)
        - "Destrúyete": self-destruct + effect
        - "+N HP": temporary HP buff
        - "+N D": temporary damage buff
        - "pierde N sello(s)": enemy loses seals
        - "mira": peek at deck/hand (info-only, logged)
        - "descarta": discard effects
        """
        targets = targets or {}
        err = self.can_use_ability(player, card, ability_index)
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
                return self.all_cards.get(tid)
            return None

        try:
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
                    drawn = self._draw_card(player)
                    if drawn:
                        total_drawn += 1
                    else:
                        self.seals[player] -= 1
                        self._log(f"  ¡Fatiga! -1 sello ({self.seals[player]})")
                        if self.seals[player] <= 0:
                            self._end_game(1 - player)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → roba {total_drawn} carta(s)")
                return None

            # ─── Gain seals ───
            if "gana" in desc_lower and any(w in desc_lower for w in ["sello", "sellos"]):
                import re
                seal_count = 1
                match = re.search(r'gana\s+(\d+)\s+sello', desc_lower)
                if match:
                    seal_count = int(match.group(1))
                self.seals[player] += seal_count
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → +{seal_count} sellos ({self.seals[player]})")
                return None

            # ─── Repair seals ───
            if "repara" in desc_lower and any(w in desc_lower for w in ["sello", "sellos"]):
                import re
                seal_count = 1
                match = re.search(r'repara\s+(\d+)\s+sello', desc_lower)
                if match:
                    seal_count = int(match.group(1))
                self.seals[player] += seal_count
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → repara {seal_count} sellos ({self.seals[player]})")
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
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → cura {heal_amount} HP a {target_card.definition.name} ({target_card.current_hp}/{target_card.definition.hp})")
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
                if self.board.cells[p][new_li][meridian] is not None:
                    return "Celda de destino ocupada."

                # Move the card up one layer (bypass allowed_layers check)
                old_li = layer - 1
                self.board.cells[p][old_li][meridian] = None
                self.board.cells[p][new_li][meridian] = card.card_id
                card.position = (p, new_layer, meridian)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → asciende a L{new_layer}")
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
                    self.seals[player] += seal_boost
                self._destroy_card(card)
                self.actions_remaining -= cost
                self._log(f"  {name}: se autodestruye. Grimorio +{seal_boost} sellos")
                return None

            # ─── Opponent loses seals ───
            if "pierde" in desc_lower and any(w in desc_lower for w in ["sello", "sellos"]):
                import re
                seal_count = 2
                match = re.search(r'pierde\s+(\d+)\s+sello', desc_lower)
                if match:
                    seal_count = int(match.group(1))
                enemy = 1 - player
                self.seals[enemy] = max(0, self.seals[enemy] - seal_count)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → enemigo pierde {seal_count} sellos ({self.seals[enemy]})")
                if self.seals[enemy] <= 0:
                    self._end_game(player)
                return None

            # ─── Temporary +HP buff ───
            if any(w in desc_lower for w in ["gana +", "gana +"]) and "hp" in desc_lower:
                import re
                hp_bonus = 1
                match = re.search(r'\+(\d+)\s*hp', desc_lower)
                if match:
                    hp_bonus = int(match.group(1))
                target_card = get_target_card("target_id") or card
                self._temp_buffs.setdefault(target_card.card_id, []).append(
                    {"attr": "hp", "delta": hp_bonus}
                )
                target_card.current_hp += hp_bonus
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → {target_card.definition.name} +{hp_bonus} HP temporal")
                return None

            # ─── Temporary +D buff ───
            if any(w in desc_lower for w in ["+", "+"]) and "d" in desc_lower and "hp" not in desc_lower:
                import re
                d_bonus = 1
                match = re.search(r'\+(\d+)\s*d', desc_lower)
                if match:
                    d_bonus = int(match.group(1))
                target_card = get_target_card("target_id") or card
                self._temp_buffs.setdefault(target_card.card_id, []).append(
                    {"attr": "d", "delta": d_bonus}
                )
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → {target_card.definition.name} +{d_bonus} D temporal")
                return None

            # ─── Scry / peek ───
            if "mira" in desc_lower and any(w in desc_lower for w in ["carta", "cartas", "reserva", "tope"]):
                import re
                count = 3
                match = re.search(r'mira\s+(\d+)', desc_lower)
                if match:
                    count = int(match.group(1))
                # Reveal top N cards to the log
                top_cards = self.decks[player][-count:] if len(self.decks[player]) >= count else self.decks[player][:]
                names = [c.definition.name for c in reversed(top_cards)]
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → mira top {len(names)}: {', '.join(names)}")
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
                    if self.hands[player]:
                        dc = self.hands[player].pop()
                        self.discard_piles[player].append(dc)
                        discarded.append(dc.definition.name)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → descarta: {', '.join(discarded) if discarded else '(mano vacía)'}")
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
                self.board.swap_cards(card, target_card)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia posición con {target_card.definition.name}")
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
                self.board.swap_cards(card, target_card)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia capas con {target_card.definition.name}")
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
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia HP con {target_card.definition.name}")
                return None

            # ─── Swap colors ───
            if "intercambia" in desc_lower and "color" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para intercambiar colores."
                color_a = self._temp_colors.get(card.card_id, card.definition.color)
                color_b = self._temp_colors.get(target_card.card_id, target_card.definition.color)
                self._temp_colors[card.card_id] = color_b
                self._temp_colors[target_card.card_id] = color_a
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia colores con {target_card.definition.name}")
                return None

            # ─── Swap hand with deck ───
            if "intercambia" in desc_lower and "mano" in desc_lower and "reserva" in desc_lower:
                if not self.hands[player]:
                    return "No tienes cartas en la mano."
                if not self.decks[player]:
                    return "No quedan cartas en la reserva."
                hand_card = self.hands[player].pop()
                deck_card = self.decks[player].pop()
                self.hands[player].append(deck_card)
                self.decks[player].append(hand_card)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia {hand_card.definition.name} de la mano con reserva")
                return None

            # ─── Swap hand with graveyard ───
            if "intercambia" in desc_lower and "mano" in desc_lower and "cementerio" in desc_lower:
                if not self.hands[player]:
                    return "No tienes cartas en la mano."
                if not self.discard_piles[player]:
                    return "No hay cartas en el cementerio."
                hand_card = self.hands[player].pop()
                grave_card = self.discard_piles[player].pop()
                self.hands[player].append(grave_card)
                self.discard_piles[player].append(hand_card)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia {hand_card.definition.name} de mano con cementerio")
                return None

            # ─── Create link ignoring distance ───
            if "vínculo" in desc_lower and "ignorando" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para vincular."
                err = self.link_cards(player, card, target_card, bypass_distance=True)
                if err:
                    return err
                # link_cards already deducts actions; refund since we already charge cost
                self.actions_remaining += 1  # link_cards deducted 1, we charge 'cost'
                self.actions_remaining -= cost
                return None

            # ─── Temp link (disuelve al final del turno) ───
            if "vínculo" in desc_lower and ("temporal" in desc_lower or "disuelve" in desc_lower):
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona una segunda carta para vínculo temporal."
                err = self.link_cards(player, card, target_card, bypass_distance=True, is_temp=True)
                if err:
                    return err
                self.actions_remaining += 1
                self.actions_remaining -= cost
                return None

            # ─── Break all squad links ───
            if "rompe" in desc_lower and "vínculo" in desc_lower and "escuadrón" in desc_lower:
                enemy = 1 - player
                squads = self.get_player_squads(enemy)
                if not squads:
                    return "El enemigo no tiene escuadrones."
                # Target first squad (or use target_squad_idx from targets)
                squad_idx = targets.get("squad_index", 0)
                if squad_idx >= len(squads):
                    return "Escuadrón no encontrado."
                squad = squads[squad_idx]
                self.network.break_all_squad_links(squad)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: rompe vínculos de escuadrón enemigo ({squad.squad_type})")
                return None

            # ─── Destroy specific link ───
            if "destruye" in desc_lower and "vínculo" in desc_lower and "escuadrón" not in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona las dos cartas del vínculo a destruir."
                if not self.network.has_link(card, target_card):
                    return "Esas cartas no están vinculadas."
                self.network.remove_link(card, target_card)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: destruye vínculo con {target_card.definition.name}")
                return None

            # ─── Link armor reduction ───
            if "vínculo" in desc_lower and "armadura" in desc_lower:
                enemy = 1 - player
                squads = self.get_player_squads(enemy)
                if not squads:
                    return "El enemigo no tiene escuadrones."
                squad_idx = targets.get("squad_index", 0)
                if squad_idx >= len(squads):
                    return "Escuadrón no encontrado."
                squad = squads[squad_idx]
                for cid in squad.members:
                    for neighbor in list(self.network.links.get(cid, set())):
                        key = tuple(sorted((cid, neighbor)))
                        self.network.link_armor[key] = max(0, self.network.link_armor.get(key, 0) - 1)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: -1 armadura a vínculos del escuadrón enemigo")
                return None

            # ─── Link cost free this turn ───
            if "costos de vínculo" in desc_lower or "costos de vínculo" in desc_lower:
                self._link_cost_free = True
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: costos de vínculo = 0 hasta final del turno")
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
                self._temp_colors[target_card.card_id] = new_color_str
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: cambia color de {target_card.definition.name} a {new_color_str.value}")
                return None

            # ─── Squad color override ───
            if "escuadrón se considera del color" in desc_lower:
                enemy = 1 - player
                squads = self.get_player_squads(player) or self.get_player_squads(enemy)
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
                    self._temp_colors[cid] = new_color
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: escuadrón se considera {new_color.value}")
                return None

            # ─── Jump to free cell ───
            if "salta" in desc_lower and "celda libre" in desc_lower:
                p, layer, meridian = card.position
                # Find a free cell in any layer
                placed = False
                for li in range(3):
                    for m in range(15):
                        if self.board.cells[p][li][m] is None:
                            old_li = layer - 1
                            self.board.cells[p][old_li][meridian] = None
                            self.board.cells[p][li][m] = card.card_id
                            card.position = (p, li + 1, m)
                            placed = True
                            break
                    if placed:
                        break
                if not placed:
                    return "No hay celdas libres en tu territorio."
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: salta a L{card.position[1]}:{card.position[2]}")
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
                if self.board.cells[tp][new_li][t_m] is not None:
                    return "Celda de destino ocupada."
                old_li = t_layer - 1
                self.board.cells[tp][old_li][t_m] = None
                self.board.cells[tp][new_li][t_m] = target_card.card_id
                target_card.position = (tp, new_layer, t_m)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: teletransporta {target_card.definition.name} a L{new_layer}")
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
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: ataca {target_card.definition.name} por {dmg} daño (HP: {target_card.current_hp})")
                if target_card.current_hp <= 0:
                    self._log(f"  {target_card.definition.name} DESTRUIDO.")
                    self._destroy_card(target_card)
                return None

            # ─── Fight (both take 2 damage) ───
            if "lucha" in desc_lower and "daño" in desc_lower:
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona un nodo enemigo para luchar."
                card.current_hp -= 2
                target_card.current_hp -= 2
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: lucha con {target_card.definition.name} — ambos reciben 2 daño")
                if card.current_hp <= 0:
                    self._log(f"  {card.definition.name} DESTRUIDO en combate.")
                    self._destroy_card(card, killer=target_card)
                if target_card.current_hp <= 0:
                    self._log(f"  {target_card.definition.name} DESTRUIDO en combate.")
                    self._destroy_card(target_card, killer=card)
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
                self._destroy_card(target_card)
                self.seals[enemy] -= dmg
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: destruye a {target_card.definition.name}, {dmg} daño al grimorio enemigo")
                if self.seals[enemy] <= 0:
                    self._end_game(player)
                return None

            # ─── Fallback: ability not yet implemented ───
            self.actions_remaining -= cost
            self._log(f"  {card.definition.name}: usa habilidad ({desc[:50]}...) — efecto no implementado")
            return None

        except Exception as e:
            # Safety net: log error, refund actions, don't crash
            self._log(f"  ⚠ Error en habilidad de {card.definition.name}: {str(e)}")
            return f"Error al ejecutar habilidad: {str(e)}"

    def get_temp_buff_bonus(self, card_id: int) -> int:
        """Get temporary D bonus from active buffs for attack calculations."""
        buffs = self._temp_buffs.get(card_id, [])
        return sum(b["delta"] for b in buffs if b["attr"] == "d")

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
                pass
        if b_is_frontier_spy and not a_is_frontier_spy:
            if card_a.owner != player:
                pass

        # Normal distance check
        if not bypass_distance and not a_is_frontier_spy and not b_is_frontier_spy:
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

    def link_cards(self, player: int, card_a: CardInstance, card_b: CardInstance,
                   bypass_distance: bool = False, is_temp: bool = False) -> Optional[str]:
        err = self.can_link(player, card_a, card_b, bypass_distance=bypass_distance)
        if err:
            return err

        if bypass_distance or (card_a.definition.is_spy and card_a.position and card_a.position[0] == -1):
            cost = 1
        else:
            dist = self.board.spatial_distance(card_a.position, card_b.position)
            if dist:
                cost = {"corta": 1, "media": 1, "larga": 3}[dist]
                if dist == "media" and card_a.definition.color != card_b.definition.color:
                    cost = 2
            else:
                cost = 1

        if card_a.definition.is_logistron or card_b.definition.is_logistron:
            cost = 1
        
        # Check global link cost free flag
        if self._link_cost_free:
            cost = 0

        self.network.add_link(card_a, card_b)
        self.actions_remaining -= cost
        
        if is_temp:
            pair = tuple(sorted((card_a.card_id, card_b.card_id)))
            self._temp_links.add(pair)
        
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
            if squad.get_dominant_color(self._temp_colors) == Color.MILITAR:
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
            if squad.get_dominant_color(self._temp_colors) == Color.SABIO:
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
            if squad.get_dominant_color(self._temp_colors) == Color.POLITICO:
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
            dom = squad.get_dominant_color(self._temp_colors)
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

        # Clear temporary buffs
        for cid, buffs in self._temp_buffs.items():
            card = self.all_cards.get(cid)
            if card:
                for b in buffs:
                    if b["attr"] == "hp":
                        card.current_hp = max(0, card.current_hp - b["delta"])
                        card.current_hp = min(card.current_hp, card.definition.hp)
        self._temp_buffs = {}

        # Clear temporary colors
        self._temp_colors = {}

        # Dissolve temporary links
        for a, b in list(self._temp_links):
            card_a = self.all_cards.get(a)
            card_b = self.all_cards.get(b)
            if card_a and card_b:
                self.network.remove_link(card_a, card_b)
        self._temp_links = set()

        # Reset link cost free flag
        self._link_cost_free = False

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
                # Temp buff D bonus
                extra += self.get_temp_buff_bonus(card.card_id)
                # Guerrero faction: +1 per node in L2/L3
                if attacking_squad.get_dominant_color(self._temp_colors) == Color.GUERRERO:
                    if card.position and card.position[1] >= 2:
                        extra += 1
                # Naturaleza faction: units give +1 damage and +1 pot
                if attacking_squad.get_dominant_color(self._temp_colors) == Color.NATURALEZA:
                    extra += 1
                    pot += 1

        # Check for Guardián del Bosque (Naturaleza triangle)
        if attacking_squad.squad_type == "triangle" and attacking_squad.get_dominant_color(self._temp_colors) == Color.NATURALEZA:
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
            if defending_squad.get_dominant_color(self._temp_colors) == Color.FESTIVO:
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
                    # Find a killer from attacking squad
                    killer_card = None
                    for cid in attacking_squad.members:
                        kc = self.all_cards.get(cid)
                        if kc:
                            killer_card = kc
                            break
                    self._destroy_card(target_card, killer=killer_card)

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
        """Try to resolve a card ability (passive triggers only)."""
        # Check conditions
        if ability.ability_type == AbilityType.COLOR:
            if squad.get_dominant_color(self._temp_colors) != ability.color_required:
                return
        if ability.ability_type == AbilityType.FORMATION:
            if squad.squad_type.replace("_ampliado", "") != ability.formation_required:
                return

        desc = ability.description.lower()
        player = card.owner

        # Execute based on trigger
        if ability.trigger == "start_of_turn":
            # ─── Draw ───
            if "roba" in desc or "robo" in desc:
                count = 1
                import re
                m = re.search(r'roba\s+(\d+)', desc)
                if m:
                    count = int(m.group(1))
                for _ in range(count):
                    extra = self._draw_card(player)
                    if extra:
                        self._log(f"  {card.definition.name}: +1 robo")
                # Also handle "+1 robo extra" pattern
                if "extra" in desc and count == 1:
                    pass  # already drawn above

            # ─── Scry / peek ───
            elif "mira" in desc:
                import re
                count = 2
                m = re.search(r'mira\s+(\d+)', desc)
                if m:
                    count = int(m.group(1))
                top_cards = self.decks[player][-count:] if len(self.decks[player]) >= count else self.decks[player][:]
                names = [c.definition.name for c in reversed(top_cards)]
                self._log(f"  {card.definition.name}: mira top {len(names)}: {', '.join(names)}")

            # ─── Auto-ascend ───
            elif "asciende" in desc or "ascender" in desc:
                # Find a card to ascend in the same squad (or self)
                target = card
                for cid in squad.members:
                    c = self.all_cards.get(cid)
                    if c and c.position and c.position[1] < 3 and c.position[0] != -1:
                        target = c
                        break
                err = self.ascend(player, target, free=True)
                if not err:
                    self._log(f"  {card.definition.name}: asciende {target.definition.name} sin costo")

            # ─── +1 acción ───
            elif "acción" in desc or "accion" in desc:
                bonus = 1
                import re
                m = re.search(r'\+(\d+)\s*acci', desc)
                if m:
                    bonus = int(m.group(1))
                self.actions_remaining += bonus
                self._log(f"  {card.definition.name}: +{bonus} acción(es) ({self.actions_remaining})")

            # ─── Free link ───
            elif "vínculo" in desc and "gratis" in desc:
                # Auto-link two cards in squad
                members = [self.all_cards.get(cid) for cid in squad.members
                          if self.all_cards.get(cid) and self.all_cards[cid].owner == player]
                linked = False
                for i, ca in enumerate(members):
                    for cb in members[i+1:]:
                        if ca and cb and not self.network.has_link(ca, cb) and self.network.can_link(ca) and self.network.can_link(cb):
                            self.network.add_link(ca, cb)
                            self._log(f"  {card.definition.name}: vínculo gratis {ca.definition.name} <-> {cb.definition.name}")
                            linked = True
                            break
                    if linked:
                        break

        elif ability.trigger == "end_of_turn":
            # ─── Heal self / ally ───
            if "recupera" in desc and "hp" in desc:
                import re
                heal = 1
                m = re.search(r'recupera\s+(\d+)\s*hp', desc)
                if m:
                    heal = int(m.group(1))
                # "a todas las cartas de tu red" or "a todas las cartas de tu escuadrón"
                if "todas" in desc:
                    for cid in squad.members:
                        c = self.all_cards.get(cid)
                        if c and c.owner == player:
                            c.current_hp = min(c.current_hp + heal, c.definition.hp)
                    self._log(f"  {card.definition.name}: +{heal} HP a todo el escuadrón")
                else:
                    card.current_hp = min(card.current_hp + heal, card.definition.hp)
                    self._log(f"  {card.definition.name}: recupera {heal} HP ({card.current_hp}/{card.definition.hp})")

            # ─── Vínculo enemigo destruible ───
            elif "vínculo" in desc:
                self._log(f"  {card.definition.name}: +1 vínculo enemigo destruible")

            # ─── Sellos adicionales (individual cards) ───
            elif "sello" in desc:
                import re
                bonus = 5
                m = re.search(r'\+(\d+)\s*sello', desc)
                if m:
                    bonus = int(m.group(1))
                self.seals[player] += bonus
                self._log(f"  {card.definition.name}: +{bonus} sellos ({self.seals[player]})")

        elif ability.trigger == "on_kill":
            # ─── Gain HP on kill ───
            if "gana" in desc and "hp" in desc:
                import re
                hp_bonus = 1
                m = re.search(r'\+(\d+)\s*hp', desc)
                if m:
                    hp_bonus = int(m.group(1))
                card.current_hp += hp_bonus
                self._log(f"  {card.definition.name}: +{hp_bonus} HP por destrucción ({card.current_hp})")

            # ─── Enemy loses seals on kill ───
            elif "pierde" in desc and "sello" in desc:
                import re
                seal_loss = 2
                m = re.search(r'pierde\s+(\d+)\s+sello', desc)
                if m:
                    seal_loss = int(m.group(1))
                enemy = 1 - player
                self.seals[enemy] = max(0, self.seals[enemy] - seal_loss)
                self._log(f"  {card.definition.name}: enemigo pierde {seal_loss} sellos ({self.seals[enemy]})")
                if self.seals[enemy] <= 0:
                    self._end_game(player)

            # ─── Draw on kill ───
            elif "roba" in desc:
                extra = self._draw_card(player)
                if extra:
                    self._log(f"  {card.definition.name}: +1 robo por destrucción")

    def _destroy_card(self, card: CardInstance, killer: Optional[CardInstance] = None):
        self.network.remove_all_links(card)
        self.board.remove_card(card)
        # Remove from spy tracking
        for p in [0, 1]:
            if card.card_id in self.spies_infiltrated[p]:
                self.spies_infiltrated[p].remove(card.card_id)
        self.discard_piles[card.owner].append(card)

        # Trigger on_kill abilities for the killer
        if killer:
            squads = self.network.find_squads(self.all_cards)
            for squad in squads:
                if killer.card_id in squad.members:
                    for cid in squad.members:
                        c = self.all_cards.get(cid)
                        if not c or c.owner != killer.owner:
                            continue
                        for ability in c.definition.abilities:
                            if ability.trigger == "on_kill":
                                self._resolve_ability(ability, c, squad, squads)
                    break

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
            dom = s.get_dominant_color(self._temp_colors)
            color_str = dom.value if dom else "incoloro"
            print(f"  [{i}] {s.squad_type} | color: {color_str} | daño base: {s.base_damage} | potenciamiento: {s.empowerment}")
            print(f"      Miembros: {', '.join(names)}")

    def show_log(self):
        if self.log:
            print("\n  ── Eventos ──")
            for entry in self.log:
                print(f"  {entry}")
