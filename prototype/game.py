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


@dataclass
class Modifier:
    """A passive modifier registered by a card on the board.

    When a card with permanent/on_enter abilities enters the board, its
    abilities are parsed into Modifier objects and registered under the
    relevant hooks. When the card leaves the board, its modifiers are
    removed.

    Attributes:
        source_card_id: which card created this modifier
        hook: which hook does this fire on (e.g. 'modify_squad')
        effect_type: what kind of effect (e.g. 'color_override', 'ignore_color')
        params: effect-specific parameters
        layer: scope — 'self', 'squad', 'network', 'global'
        priority: lower fires first (default 100)
        is_temporary: if True, cleaned in exit_phase (for temp buffs/colors)
    """
    source_card_id: int
    hook: str
    effect_type: str
    params: dict = field(default_factory=dict)
    layer: str = "self"
    priority: int = 100
    is_temporary: bool = False


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

    # ─── ACTIVE / FORMATION / GENERAL abilities (use_ability handles these) ───
    if trigger == "active" and atype in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL):
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
            ("rompe", "vínculo" in desc and "escuadrón" not in desc),    # destroy specific link (alias)
            ("muévete", "meridiano" in desc),                            # move + conditional link
            ("escuadrón", "daño" in desc or "daño base" in desc),       # squad damage buff
            ("adjunta", "logistrón" in desc),                            # attach parasite
            ("costos de vínculo", True),                                 # link cost free
            ("cambia", "color" in desc),                                 # change color
            ("escuadrón se considera del color", True),                  # squad color
            ("salta", "celda libre" in desc),                            # jump to free cell
            ("teletransporta", True),                                    # teleport ally
            ("ataca", "nodo" in desc),                                   # direct node attack
            ("lucha", "daño" in desc),                                   # fight
            ("destruye", "grimorio" in desc),                            # destroy ally + damage
            # Fase F additions
            ("descarta", "roba" in desc),                               # discard then draw
            ("indestructible", "este turno" in desc),                   # temp indestructible
            ("pierden", "hp" in desc),                                  # damage enemy squad/type
            ("ganan", "+" in desc and any(w in desc.split() for w in ['d', 'daño'])),  # squad-wide D buff
            ("ganan", "hp" in desc and "permanente" in desc),           # permanent HP buff
            # Phase G additions
            ("no pueden atacar", True),                                 # cannot attack
            ("no reciben potenciamiento", True),                         # block formation
            ("niega el efecto de facción", True),                       # negate faction
            ("rompe todos los vínculos enemigos", True),                 # mass break links
            ("destruye todos los logistrones", True),                   # mass destroy type
            ("conecta", "no vinculadas" in desc and "vínculos gratis" in desc),  # mass link
            ("jugar cartas de tu cementerio", True),                    # grave play
            ("intercambia d", "enemig" in desc),                        # swap D
            ("intercambia hp", "escuadrón" in desc),                    # swap squad HP
            # Phase H additions
            ("restaura tu grimorio", "30" in desc),
            ("restaura", "sellos rotos" in desc),
            ("busca", "reserva" in desc and "mano" in desc),
            ("cambia", "territorio" in desc),
            ("meridiano temporal", True),
            # Phase I additions
            ("crea una copia", True),
            ("copia una habilidad", True),
            ("niega un efecto", True),
            ("ataque a otro", "enemig" in desc),
            ("toma control", "escuadrón" in desc),
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

    # ─── PASSIVE abilities (modifier system handles these) ───
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
        if "restaura" in desc and "armadura" in desc:
            return "partial"
        if "descarte" in desc or "cementerio" in desc:
            return "implemented"
        if "sello" in desc:
            return "implemented"
        return "not_implemented"

    if trigger == "on_enter":
        # Vanguardia / Línea de fuego: checked in play_card()
        if "vanguardia" in desc or "línea de fuego" in desc:
            return "implemented"
        # New on_enter patterns via modifier system
        if ("roba" in desc or "robo" in desc) and "control" not in desc:
            return "implemented"
        if "mira" in desc or "scry" in desc:
            return "implemented"
        if "hp" in desc and any(w in desc for w in ["recupera", "gana", "+"]):
            return "implemented"
        if any(w in desc for w in ["sello", "sellos"]):
            return "implemented"
        if "muévete" in desc or ("mueve" in desc and "meridiano" in desc):
            return "implemented"
        if "mueve" in desc and "carta" in desc:
            return "implemented"
        if "asciende" in desc or "ascender" in desc:
            return "implemented"
        if ("rompe" in desc or "romper" in desc) and "vínculo" in desc:
            return "implemented"
        if "vinc" in desc and ("adyacente" in desc or "sin costo" in desc):
            return "implemented"
        if "descarta" in desc:
            return "implemented"
        if "armadura" in desc and "vínculo" in desc:
            return "implemented"
        if "vínculo" in desc and ("gana" in desc or "+" in desc):
            return "implemented"
        return "not_implemented"

    if trigger == "active":
        # New patterns added in Fase F
        if "descarta" in desc.lower() and "roba" in desc.lower():
            return "implemented"
        if "indestructible" in desc.lower() and "este turno" in desc.lower():
            return "implemented"
        if "ganan" in desc.lower() and "hp" in desc.lower() and "permanente" in desc.lower():
            return "implemented"
        if "pierden" in desc.lower() and "hp" in desc.lower():
            return "implemented"
        if "ganan" in desc.lower() and "+" in desc and "d" in desc.lower() and "este turno" in desc.lower():
            return "implemented"
        # Existing patterns
        # (draw, self-destruct, seals, heal, ascend, scry, discard, swap, etc.)
        # handled via keyword matching in use_ability()
        return "not_implemented"

    if trigger == "on_ascend":
        # Caudillismo: auto-link in ascend()
        if "caudillismo" in desc.lower() or "vínculo gratis" in desc.lower():
            return "implemented"
        # Cannot ascend
        if "no puede ascender" in desc.lower() or "ni ascender" in desc.lower():
            return "implemented"
        return "not_implemented"

    if trigger == "permanent":
        # All patterns handled by modifier parser
        implemented_perm_kw = [
            # Original patterns
            ("reticencia", True),
            ("sigilo", True),
            ("no puede ser atacado", True),
            ("no cuenta para la mayoría de color", True),
            ("ignoran restricciones de formación", True),
            ("reducen", "distancia" in desc.lower() and "potenciamiento" in desc.lower()),
            ("sin formar polígonos", "vincularse" in desc.lower()),
            ("cuenta como", "logistron" in desc.lower()),
            # Damage / HP
            ("gana +", any(w in desc.split() for w in ['d', 'D', 'daño'])),
            ("+", any(w in desc for w in [" d ", " D ", " D.", " D,", "daño"]) and "defensa" not in desc.lower()),
            ("gana", "hp" in desc.lower() and "permanente" in desc.lower()),
            ("gana", "+" in desc and "v" in desc.lower() and "permanente" in desc.lower()),
            # Grimoire
            ("grimorio tiene", "defensa" in desc.lower()),
            ("no pierde más de", True),
            ("grimorio invulnerable", True),
            ("inmune a destrucción", True),
            ("indestructible", True),
            # Links
            ("transfiere", "vínculo" in desc.lower()),
            ("vínculo gratis", True),
            ("cuesta 0 vincular", True),
            ("vínculos no cuestan", True),
            ("no puede vincularse", True),
            ("armadura", any(w in desc.lower() for w in ["vínculo", "vinculo"])),
            ("vínculos", "no pueden ser destruidos" in desc.lower()),
            ("al ser vinculado", "roba" in desc.lower()),
            ("al vincular", "roba" in desc.lower()),
            # Movement
            ("no puede ascender", True),
            ("ni ascender", True),
            ("no puede moverse", True),
            ("no puede ser movido", True),
            # Guards
            ("guardaespaldas", True),
            ("redirige", "daño" in desc.lower()),
            # Bonus formation / color
            ("caudillismo", "activos" in desc.lower()),
            ("todas las habilidades de color", True),
            ("potenciamiento adicional", True),
            ("solo puede formar", True),
            ("no puede formar", True),
            # Cost reduction
            ("cuestan 0 acciones", True),
            ("cuesta 0", "vincular" in desc.lower()),
            # Phase K additions (parser handles, status must match)
            ("vanguardia", True),
            ("línea de fuego", True),
            ("ganan +", "d" in desc.split() or "daño" in desc.lower()),
            ("gana +1 v", "permanente" in desc.lower()),
            ("gana +2 hp", True),
            ("todas las cartas", "ganan" in desc.lower() and ("hp" in desc.lower() or "d" in desc.lower())),
            ("no puede ascender", "regenera" in desc.lower()),
        ]
        for kw, cond in implemented_perm_kw:
            if kw in desc.lower() and cond:
                return "implemented"
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
            # Parser handles: recover_hp, recover_graveyard, break_enemy_link, bonus_seals
            implemented_eot_kw = [
                ("sello", True),
                ("vínculo", True),
                ("recupera", "hp" in desc),
                ("descarte", True),
                ("cementerio", True),
                ("restaura", True),
                ("inflige", "daño" in desc),
                ("rompe", "vínculo" in desc),
                # Phase K
                ("autofobia", True),
                ("exactamente", "vínculo" in desc),
                ("roba", "vínculo" in desc),
                ("logistrón", "rompe" in desc),
                ("nodo enemigo", "rompe" in desc),
            ]
            for kw, cond in implemented_eot_kw:
                if kw in desc.lower() and cond:
                    return "implemented"
            return "not_implemented"
        if trigger == "start_of_turn":
            # Parser handles: draw, scry, auto_ascend, bonus_actions, free_link
            implemented_sot_kw = [
                ("roba", True),
                ("mira", True),
                ("asciende", True),
                ("acción", True),
                ("vínculo", "gratis" in desc),
                ("curar", True),
                ("cura", True),
                ("gana", "sello" in desc),
                ("escudo", True),
            ]
            for kw, cond in implemented_sot_kw:
                if kw in desc.lower() and cond:
                    return "implemented"
            return "not_implemented"
        if trigger == "on_attack":
            return "implemented"  # Color checks in attack()
        if trigger == "permanent":
            # All effect types handled by modifier parser
            implemented_perm_kw = [
                # Core
                ("armadura", any(w in desc.lower() for w in ["vínculo", "vinculo"])),
                ("festivo", True),
                # Damage / stat bonuses
                ("gana", "+" in desc and any(w in desc.split() for w in ['d', 'D', 'daño'])),
                ("+", any(w in desc for w in [" d ", " D ", " D.", " D,", "daño"])),
                # Grimoire protection
                ("no pierde más de", True),
                ("grimorio tiene", "defensa" in desc.lower()),
                ("inmune", True),
                ("indestructible", True),
                ("invulnerable", True),
                # Links
                ("vínculo", "no pueden ser destruidos" in desc.lower() or "no puede ser destruido" in desc.lower()),
                ("vínculo", "gratis" in desc.lower() or "sin costo" in desc.lower()),
                ("vínculo", "no cuestan" in desc.lower()),
                ("no puede vincularse", True),
                # HP / stats permanent
                ("gana", "hp" in desc.lower() and "permanente" in desc.lower()),
                ("gana", "+" in desc and "v" in desc.lower() and "permanente" in desc.lower()),
                # Color / formation
                ("caudillismo", "activos" in desc.lower()),
                ("todas las habilidades de color", True),
                ("no cuenta para", True),
                ("ignoran restricciones", True),
                ("reducen", "distancia" in desc.lower()),
                ("sin formar polígonos", True),
                ("cuenta como", "logistron" in desc.lower()),
                # Movement / ascension
                ("no puede ascender", True),
                ("ni ascender", True),
                ("no puede moverse", True),
                ("no puede ser movido", True),
                # Guards / redirects
                ("guardaespaldas", True),
                ("redirige", "daño" in desc.lower()),
                # Cost reduction
                ("cuesta 0", "vincular" in desc.lower()),
                ("cuesta 0 vincular", True),
                ("vincularse cuesta 0", True),
                ("cuestan 0 acciones", True),
                # Bonus formation
                ("potenciamiento adicional", True),
                ("solo puede formar", True),
                ("no puede formar", True),
            ]
            for kw, cond in implemented_perm_kw:
                if kw in desc.lower() and cond:
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

        # Phase G flags
        self._block_enemy_formation: bool = False
        self._grave_play: dict[int, bool] = {0: False, 1: False}

        # Phase I infrastructure
        self.effect_stack: list[dict] = []  # [{source, target, effect_type, params}]
        self._mind_controlled: dict[int, int] = {}  # card_id -> original_owner
        self._negate_next: bool = False  # Árbitro del Juego

        # Attacked squads this turn
        self._attacked_squads: set[int] = set()  # squad hashes

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
        self._modifiers: dict[str, list[Modifier]] = {
            "modify_squad": [],
            "modify_damage": [],
            "before_attack": [],
            "after_attack": [],
            "grimoire_defense": [],
            "before_link": [],
            "after_link": [],
            "before_play": [],
            "after_play": [],
            "before_destroy": [],
            "after_destroy": [],
            "on_ascend": [],
            "on_move": [],
            "modify_actions": [],
            "conditional_draw": [],
            "spy_infiltrate": [],
            "color_faction": [],
            "start_of_turn": [],
            "end_of_turn": [],
            "on_kill": [],
            "on_enter": [],
            "on_attack": [],
        }

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
        """Merge _temp_colors with modifier-based color overrides.

        Modifiers with effect_type='color_override' on hook='modify_squad'
        provide permanent color changes; _temp_colors handles temporary
        color swaps from active abilities.
        """
        overrides = dict(self._temp_colors)
        for mod in self._modifiers.get("modify_squad", []):
            if mod.effect_type == "color_override":
                overrides[mod.source_card_id] = mod.params["color"]
        return overrides

    def _get_effective_squad_color(self, card: CardInstance, squad: "Squad") -> Optional[Color]:
        """Get the effective squad color for COLOR ability checks.
        
        If the squad contains at least one Alquimista, each card uses its own
        printed color instead of the squad's dominant color (§9.3 armonización v1.3).
        Otherwise, uses the squad's actual dominant color.
        """
        has_alchemist = any(
            self.all_cards[cid].definition.color == Color.ALQUIMISTA
            for cid in squad.members if cid in self.all_cards
        )
        if has_alchemist:
            return card.definition.color
        return squad.get_dominant_color(self._get_color_overrides())

    def _register_temp_modifier(self, mod: Modifier):
        """Register a temporary modifier (cleaned in exit_phase)."""
        mod.is_temporary = True
        if mod.hook in self._modifiers:
            self._modifiers[mod.hook].append(mod)

    def _unregister_temp_modifiers(self):
        """Remove all temporary modifiers (called in exit_phase)."""
        for hook_list in self._modifiers.values():
            hook_list[:] = [m for m in hook_list if not m.is_temporary]

    def _evaluate_condition(self, condition: dict, source: CardInstance) -> bool:
        """Evaluate a modifier condition against current game state.

        Supported conditions:
          - positional: {"type": "layer", "value": 1..3}
          - positional: {"type": "frontier"}
          - formation: {"type": "formation", "shape": "triangle"|"square"|"pentagon"}
          - network: {"type": "links", "min": N}
          - state: {"type": "damaged_this_turn"}
          - turn: {"type": "once_per_game", "used_set": set()}
        Returns True if condition is met or if no condition is set.
        """
        if not condition:
            return True

        ctype = condition.get("type")

        # ─── Positional: layer ───
        if ctype == "layer":
            if not source.position or source.position[0] == -1:
                return False
            return source.position[1] == condition.get("value", 1)

        # ─── Positional: frontier ───
        if ctype == "frontier":
            return source.position and source.position[0] == -1

        # ─── Formation ───
        if ctype == "formation":
            shape = condition.get("shape", "triangle")
            squads = self.get_player_squads(source.owner)
            for sq in squads:
                if source.card_id in sq.members and sq.squad_type.replace("_ampliado", "") == shape:
                    return True
            return False

        # ─── Network: link count ───
        if ctype == "links":
            count = self.network.link_count(source)
            min_links = condition.get("min", 1)
            return count >= min_links

        # ─── State ───
        if ctype == "damaged_this_turn":
            return getattr(source, '_damaged_this_turn', False)

        # ─── Turn ───
        if ctype == "once_per_game":
            used = condition.get("used_set", set())
            return source.card_id not in used

        # Unknown condition type — assume met
        return True

    # ═══════════════════════════════════════════════════════════════
    # Modifier Engine
    # ═══════════════════════════════════════════════════════════════

    def _register_modifiers(self, card: CardInstance):
        """Parse a card's abilities into Modifier objects and register them."""
        for ability in card.definition.abilities:
            if ability.trigger not in ("permanent", "on_enter", "start_of_turn", "end_of_turn", "on_kill"):
                continue
            modifiers = self._parse_ability_to_modifiers(ability, card)
            for mod in modifiers:
                if mod.hook in self._modifiers:
                    self._modifiers[mod.hook].append(mod)
                    self._log(f"  [mod] {card.definition.name}: +{mod.effect_type} on {mod.hook}")

    def _unregister_modifiers(self, card_id: int):
        """Remove all modifiers belonging to a card (when it leaves the board)."""
        for hook_name, hook_list in self._modifiers.items():
            before = len(hook_list)
            hook_list[:] = [m for m in hook_list if m.source_card_id != card_id]
            removed = before - len(hook_list)
            if removed:
                self._log(f"  [mod] card#{card_id}: -{removed} modifiers from {hook_name}")

    def _parse_ability_to_modifiers(self, ability: Ability, card: CardInstance) -> list[Modifier]:
        """Convert an ability description into zero or more Modifier objects.

        This is the central registry of known passive effects. Each pattern
        match produces one or more Modifier objects keyed to the right hook.
        """
        desc = ability.description.lower()
        cid = card.card_id
        mods = []

        # ─── Extract conditions from description ───
        condition = {}
        # Formation: "En triángulo/cuadrado/pentágono"
        import re as _re2
        for shape in ["triángulo", "triangulo", "cuadrado", "cuadrilátero", "cuadrilatero", "pentágono", "pentagono"]:
            if f"en {shape}" in desc:
                shape_clean = shape.replace("á", "a").replace("í", "i")
                condition = {"type": "formation", "shape": shape_clean}
                break
        # Layer: "Si está en L1/L2/L3" or "Mientras esté en L1/L2/L3"
        layer_match = _re2.search(r'(?:si está|mientras esté|está)\s+en\s+[Ll](\d)', desc)
        if layer_match:
            condition = {"type": "layer", "value": int(layer_match.group(1))}
        # Frontier: "En frontera"
        if "en frontera" in desc:
            condition = {"type": "frontier"}
        # Links: "mientras tenga 1+ vínculos"
        link_match = _re2.search(r'(\d+)\+?\s*vínculo', desc)
        if link_match:
            condition = {"type": "links", "min": int(link_match.group(1))}

        # ─── modify_squad effects ───
        # "Incoloro: no cuenta para la mayoría de color de ningún escuadrón"
        if "no cuenta para la mayoría de color" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="modify_squad",
                effect_type="ignore_color",
                layer="self",
                params={"condition": condition} if condition else {},
            ))

        # "En cuadrado Guerrero: los Guerreros ignoran restricciones de formación"
        if "ignoran restricciones de formación" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="modify_squad",
                effect_type="ignore_formation",
                params={
                    "formation": ability.formation_required or "any",
                    "color": ability.color_required.value if ability.color_required else "any",
                },
                layer="squad",
            ))

        # "Escuadrones conectados reducen en 1 la distancia de red para potenciamiento"
        if "reducen" in desc and "distancia" in desc and "potenciamiento" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="modify_squad",
                effect_type="reduce_potenciamiento_distance",
                layer="network",
                params={"delta": -1},
            ))

        # "En frontera: puede vincularse con L3 enemigo y propio sin formar polígonos"
        if "sin formar polígonos" in desc and "vincularse" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="modify_squad",
                effect_type="ignore_polygon_requirement",
                layer="self",
            ))

        # "Cuenta como 2 logistrones para efectos que los mencionen"
        if "cuenta como" in desc and "logistron" in desc:
            try:
                import re
                m = re.search(r'cuenta como (\d+)', desc)
                count = int(m.group(1)) if m else 2
            except:
                count = 2
            mods.append(Modifier(
                source_card_id=cid,
                hook="modify_squad",
                effect_type="logistron_multiplier",
                layer="self",
                params={"multiplier": count},
            ))

        # ─── before_attack effects ───
        # "Sigilo: ~ no puede ser atacado"
        if "sigilo" in desc and "no puede ser atacado" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="before_attack",
                effect_type="cannot_be_attacked",
                layer="self",
            ))

        # ─── modify_damage effects ───
        # "+N D" or "gana +N D" (permanent damage bonus, not "de defensa")
        import re as _re
        d_match = _re.search(r'gana\s+\+(\d+)\s*[dD]\b', desc)
        if not d_match:
            d_match = _re.search(r'\+(\d+)\s*[dD]\b', desc)
        if d_match and ability.trigger in ("permanent",):
            delta = int(d_match.group(1))
            # Exclude false matches like "+5 de defensa" — ensure it's about damage
            if "defensa" not in desc[max(0, d_match.start()-20):d_match.end()+20]:
                mods.append(Modifier(
                    source_card_id=cid,
                    hook="modify_damage",
                    effect_type="damage_bonus",
                    layer="self",
                    params={"delta": delta, "condition": condition} if condition else {"delta": delta},
                ))

        # ─── grimoire_defense effects ───
        # "grimorio no pierde más de N sellos por ataque"
        seal_match = _re.search(r'no pierde más de (\d+)', desc)
        if seal_match:
            cap = int(seal_match.group(1))
            mods.append(Modifier(
                source_card_id=cid,
                hook="grimoire_defense",
                effect_type="max_seal_loss",
                layer="self",
                params={"max": cap, "condition": condition} if condition else {"max": cap},
            ))

        # "grimorio tiene +N de defensa contra ataques directos"
        def_match = _re.search(r'grimorio tiene \+(\d+) de defensa', desc)
        if def_match:
            armor = int(def_match.group(1))
            mods.append(Modifier(
                source_card_id=cid,
                hook="grimoire_defense",
                effect_type="grimoire_armor",
                layer="self",
                params={"armor": armor, "condition": condition} if condition else {"armor": armor},
            ))

        # ─── before_link effects ───
        # "vínculo(s) gratis" or "vincularse cuesta 0" → cost zero for this card
        if ("vínculo gratis" in desc or "vincular" in desc and "sin costo" in desc
                or "vínculos no cuestan" in desc or "cuesta 0 vincular" in desc):
            mods.append(Modifier(
                source_card_id=cid,
                hook="before_link",
                effect_type="link_cost_zero",
                layer="self",
            ))

        # ─── after_link effects ───
        # "Al ser vinculado/a/X: roba" → draw on link
        if ("al ser vinculado" in desc or "al vincular" in desc) and "roba" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="after_link",
                effect_type="draw_on_link",
                layer="self",
            ))

        # ─── before_destroy effects ───
        # "Inmune a destrucción" / "indestructible"
        if "inmune a destrucción" in desc or "indestructible" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="before_destroy",
                effect_type="destroy_immunity",
                layer="self",
            ))

        # ─── after_destroy effects ───
        # "Al destruirse: transfiere vínculos" 
        if "transfiere" in desc and "vínculo" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="after_destroy",
                effect_type="transfer_links",
                layer="self",
            ))

        # ─── on_ascend effects ───
        # "No puede ascender" / "ni ascender"
        if "no puede ascender" in desc or "ni ascender" in desc:
            mods.append(Modifier(
                source_card_id=cid,
                hook="on_ascend",
                effect_type="cannot_ascend",
                layer="self",
            ))

        # ─── on_move effects ───
        # "No puede moverse" / "no puede ser movido" / "ni ser movido"
        if ("no puede moverse" in desc or "no puede ser movido" in desc
                or "ni ser movido" in desc or "ser movida" in desc):
            mods.append(Modifier(
                source_card_id=cid,
                hook="on_move",
                effect_type="cannot_move",
                layer="self",
            ))

        # ─── start_of_turn effects ───
        if ability.trigger == "start_of_turn":
            # Draw: "Roba 1 carta"
            if ("roba" in desc or "robo" in desc) and "control" not in desc and "vínculo" not in desc:
                count = 1
                m = _re2.search(r'roba\s+(\d+)', desc)
                if m:
                    count = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="start_of_turn",
                    effect_type="draw", layer="self",
                    params={"count": count, "ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))
            # Scry: "Mira las 3 primeras cartas"
            elif "mira" in desc:
                count = 2
                m = _re2.search(r'mira\s+(\d+)', desc)
                if m:
                    count = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="start_of_turn",
                    effect_type="scry", layer="self",
                    params={"count": count, "ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))
            # Auto-ascend: "asciende ~ a L2"
            elif "asciende" in desc or "ascender" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="start_of_turn",
                    effect_type="auto_ascend", layer="self",
                    params={"free": True, "ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))
            # Bonus actions: "+1 acción"
            elif "acción" in desc or "accion" in desc:
                bonus = 1
                m = _re2.search(r'\+(\d+)\s*acci', desc)
                if m:
                    bonus = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="start_of_turn",
                    effect_type="bonus_actions", layer="self",
                    params={"count": bonus, "ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))
            # Free link: "vínculo gratis"
            elif "vínculo" in desc and "gratis" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="start_of_turn",
                    effect_type="free_link", layer="self",
                    params={"ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))

        # ─── end_of_turn effects ───
        if ability.trigger == "end_of_turn":
            # Recover HP: "recupera N HP"
            if "recupera" in desc and "hp" in desc:
                heal = 1
                m = _re2.search(r'recupera\s+(\d+)\s*hp', desc)
                if m:
                    heal = int(m.group(1))
                scope = "squad" if "todas" in desc else "self"
                mods.append(Modifier(
                    source_card_id=cid, hook="end_of_turn",
                    effect_type="recover_hp", layer="self",
                    params={"amount": heal, "scope": scope, "ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))
            # Recover from graveyard
            elif "descarte" in desc or "cementerio" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="end_of_turn",
                    effect_type="recover_graveyard", layer="self",
                    params={"ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))
            # Break enemy link
            elif "vínculo" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="end_of_turn",
                    effect_type="break_enemy_link", layer="self",
                    params={"count": 1, "ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))
            # Bonus seals
            elif "sello" in desc:
                bonus = 5
                m = _re2.search(r'\+(\d+)\s*sello', desc)
                if m:
                    bonus = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="end_of_turn",
                    effect_type="bonus_seals", layer="self",
                    params={"amount": bonus, "ability_type": ability.ability_type.name,
                            "color_required": ability.color_required.value if ability.color_required else None,
                            "formation_required": ability.formation_required},
                ))

        # ─── on_kill effects ───
        if ability.trigger == "on_kill":
            # Gain HP on kill: "gana +N HP"
            if "gana" in desc and "hp" in desc:
                hp_bonus = 1
                m = _re2.search(r'\+(\d+)\s*hp', desc)
                if m:
                    hp_bonus = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_kill",
                    effect_type="gain_hp_on_kill", layer="self",
                    params={"amount": hp_bonus},
                ))
            # Enemy loses seals on kill: "pierde N sellos"
            elif "pierde" in desc and "sello" in desc:
                seal_loss = 2
                m = _re2.search(r'pierde\s+(\d+)\s+sello', desc)
                if m:
                    seal_loss = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_kill",
                    effect_type="enemy_seal_loss_on_kill", layer="self",
                    params={"amount": seal_loss},
                ))
            # Draw on kill: "roba"
            elif "roba" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="on_kill",
                    effect_type="draw_on_kill", layer="self",
                    params={"count": 1},
                ))

        # ─── on_enter effects ───
        if ability.trigger == "on_enter":
            # Draw: "Al entrar: roba N"
            if ("roba" in desc or "robo" in desc) and "control" not in desc and "vínculo" not in desc:
                count = 1
                m = _re2.search(r'roba\s+(\d+)', desc)
                if m:
                    count = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="draw", layer="self",
                    params={"count": count},
                ))
            # Scry: "Al entrar: scry N" / "mira N cartas"
            elif "mira" in desc or "scry" in desc:
                count = 2
                m = _re2.search(r'(?:mira|scry)\s+(\d+)', desc)
                if m:
                    count = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="scry", layer="self",
                    params={"count": count},
                ))
            # Heal: "+N HP a una carta aliada" / "recupera N HP"
            elif ("hp" in desc and any(w in desc for w in ["recupera", "gana", "+"])):
                amount = 1
                m = _re2.search(r'\+(\d+)\s*hp', desc) or _re2.search(r'recupera\s+(\d+)\s*hp', desc)
                if m:
                    amount = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="heal_ally", layer="self",
                    params={"amount": amount},
                ))
            # Gain seals: "+N sello" / "gana N sello"
            elif any(w in desc for w in ["sello", "sellos"]):
                amount = 1
                m = _re2.search(r'\+(\d+)\s*sello', desc) or _re2.search(r'gana\s+(\d+)\s+sello', desc)
                if m:
                    amount = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="gain_seals", layer="self",
                    params={"amount": amount},
                ))
            # Move self: "muévete N meridiano"
            elif "muévete" in desc or "mueve" in desc and "meridiano" in desc:
                dist = 1
                m = _re2.search(r'mu[eé]vete?\s+(\d+)\s+meridiano', desc)
                if m:
                    dist = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="move_self", layer="self",
                    params={"distance": dist},
                ))
            # Move ally: "mueve N carta propia"
            elif "mueve" in desc and "carta" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="move_ally", layer="self",
                    params={"distance": 1},
                ))
            # Ascend ally: "asciende a L2 sin costo"
            elif "asciende" in desc or "ascender" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="ascend_ally", layer="self",
                    params={"free": True},
                ))
            # Break link: "rompe N vínculo"
            elif ("rompe" in desc or "romper" in desc) and "vínculo" in desc:
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="break_link", layer="self",
                    params={"count": 1},
                ))
            # Link immediately: "vincúlala con 1 carta adyacente sin costo"
            elif "vinc" in desc and ("adyacente" in desc or "sin costo" in desc):
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="auto_link", layer="self",
                    params={"free": True},
                ))
            # Discard: "descarta N"
            elif "descarta" in desc:
                count = 1
                m = _re2.search(r'descarta\s+(\d+)', desc)
                if m:
                    count = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_enter",
                    effect_type="discard", layer="self",
                    params={"count": count},
                ))

        # ─── on_attack effects ───
        if ability.trigger == "on_attack":
            # Ignore armor: "ignora N de armadura/defensa"
            if "ignora" in desc and any(w in desc for w in ["armadura", "defensa"]):
                amount = 1
                m = _re2.search(r'ignora\s+(\d+)', desc)
                if m:
                    amount = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_attack",
                    effect_type="ignore_armor", layer="self",
                    params={"amount": amount},
                ))
            # Double damage: "daño duplicado" / "daño base duplicado"
            elif "duplicado" in desc and ("daño" in desc or "daño" in desc):
                mods.append(Modifier(
                    source_card_id=cid, hook="on_attack",
                    effect_type="double_damage", layer="self",
                    params={},
                ))
            # Bonus vs nodes/structures: "+N daño a nodos"
            elif "nodo" in desc and any(w in desc for w in ["+", "extra", "adicional"]):
                bonus = 2
                m = _re2.search(r'\+(\d+)', desc)
                if m:
                    bonus = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_attack",
                    effect_type="bonus_vs_nodes", layer="self",
                    params={"delta": bonus},
                ))
            # Bonus vs high HP: "+N daño contra cartas con HP >= X"
            elif "hp" in desc and ">=" in desc:
                bonus = 1
                m = _re2.search(r'\+(\d+)\s*daño', desc)
                if m:
                    bonus = int(m.group(1))
                hp_threshold = 5
                m2 = _re2.search(r'hp\s*>=\s*(\d+)', desc)
                if m2:
                    hp_threshold = int(m2.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_attack",
                    effect_type="bonus_vs_high_hp", layer="self",
                    params={"delta": bonus, "hp_threshold": hp_threshold},
                ))
            # Bonus per link: "+1 daño por cada vínculo"
            elif "vínculo" in desc and any(w in desc for w in ["+", "extra"]):
                max_bonus = 3
                m = _re2.search(r'máx\s*\+?(\d+)', desc) or _re2.search(r'max\s*\+?(\d+)', desc)
                if m:
                    max_bonus = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_attack",
                    effect_type="bonus_per_link", layer="self",
                    params={"max": max_bonus},
                ))
            # Bonus vs grimoires: "+N daño contra grimorios"
            elif "grimorio" in desc and any(w in desc for w in ["+", "extra"]):
                bonus = 4
                m = _re2.search(r'\+(\d+)', desc)
                if m:
                    bonus = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="on_attack",
                    effect_type="bonus_vs_grimoire", layer="self",
                    params={"delta": bonus},
                ))

        # ─── Additional permanent/on_enter patterns ───
        # Cannot link: "No puede vincularse"
        if "no puede vincularse" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="before_link",
                effect_type="cannot_link", layer="self",
                params={},
            ))
        # Link armor: "vínculo(s) tienen/ganan +N de armadura"
        if "armadura" in desc and ("vínculo" in desc or "vinculo" in desc):
            amount = 1
            m = _re2.search(r'\+(\d+)\s*(?:de\s*)?armadura', desc)
            if m:
                amount = int(m.group(1))
            scope = "own" if "~" in desc or "sus vínculos" in desc else "link"
            mods.append(Modifier(
                source_card_id=cid, hook="before_link",
                effect_type="link_armor_bonus", layer="self",
                params={"amount": amount, "scope": scope},
            ))


        # ─── Phase K: new parser patterns ───

        # Vanguardia / Línea de fuego: on_enter at higher layer
        if "vanguardia" in desc:
            layer_match = _re2.search(r'[Ll](\d)', desc)
            target_layer = int(layer_match.group(1)) if layer_match else 2
            mods.append(Modifier(
                source_card_id=cid, hook="on_enter",
                effect_type="vanguard_entry", layer="self",
                params={"layer": target_layer},
            ))
        if "línea de fuego" in desc or "linea de fuego" in desc:
            layer_match = _re2.search(r'[Ll](\d)', desc)
            target_layer = int(layer_match.group(1)) if layer_match else 3
            mods.append(Modifier(
                source_card_id=cid, hook="on_enter",
                effect_type="vanguard_entry", layer="self",
                params={"layer": target_layer},
            ))

        # Cannot form / only form specific polygons
        if "no puede formar" in desc:
            shape = "triángulo" if "triángulo" in desc or "triangulo" in desc else "any"
            mods.append(Modifier(
                source_card_id=cid, hook="modify_squad",
                effect_type="formation_restriction", layer="self",
                params={"cannot_form": shape},
            ))
        if "solo puede formar" in desc:
            shape = "pentágono" if "pentágono" in desc or "pentagono" in desc else "any"
            mods.append(Modifier(
                source_card_id=cid, hook="modify_squad",
                effect_type="formation_restriction", layer="self",
                params={"only_form": shape},
            ))

        # Grimoire invulnerable
        if "grimorio invulnerable" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="grimoire_defense",
                effect_type="grimoire_invulnerable", layer="self",
                params={"condition": condition} if condition else {},
            ))

        # Caudillismo always active
        if "caudillismo" in desc and "activos" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="modify_squad",
                effect_type="caudillismo_always_active", layer="network",
                params={"condition": condition} if condition else {},
            ))

        # All color abilities active
        if "todas las habilidades de color" in desc and "activas" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="modify_squad",
                effect_type="all_color_abilities_active", layer="network",
                params={"condition": condition} if condition else {},
            ))

        # Count as all colors
        if "cuenta como todos los colores" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="modify_squad",
                effect_type="all_colors", layer="self",
            ))

        # Free ascension
        if "ascensos" in desc and "cuestan 0" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="on_ascend",
                effect_type="free_ascend", layer="network",
                params={"condition": condition} if condition else {},
            ))

        # Guardaespaldas: redirect damage
        if "guardaespaldas" in desc:
            if "grimorio" in desc:
                amount = 3
                m = _re2.search(r'hasta\s+(\d+)', desc)
                if m:
                    amount = int(m.group(1))
                mods.append(Modifier(
                    source_card_id=cid, hook="grimoire_defense",
                    effect_type="grimoire_damage_redirect", layer="self",
                    params={"max": amount},
                ))
            else:
                color_filter = None
                for col in ["sellador", "político", "militar", "guerrillero", "naturaleza", "logistrón"]:
                    if col in desc:
                        color_filter = col
                        break
                mods.append(Modifier(
                    source_card_id=cid, hook="modify_damage",
                    effect_type="damage_redirect", layer="self",
                    params={"color": color_filter} if color_filter else {},
                ))

        # Bonus formation power
        if "potenciamiento adicional" in desc:
            bonus = 2
            m = _re2.search(r'\+(\d+)\s*de\s*potenciamiento', desc)
            if m:
                bonus = int(m.group(1))
            mods.append(Modifier(
                source_card_id=cid, hook="modify_squad",
                effect_type="bonus_formation_power", layer="network",
                params={"bonus": bonus, "condition": condition} if condition else {"bonus": bonus},
            ))

        # Vitality bonus (V)
        if "gana" in desc and "v" in desc and "permanente" in desc:
            v_match = _re2.search(r'\+(\d+)\s*v', desc.lower())
            bonus = int(v_match.group(1)) if v_match else 1
            mods.append(Modifier(
                source_card_id=cid, hook="modify_squad",
                effect_type="vitality_bonus", layer="network",
                params={"bonus": bonus, "condition": condition} if condition else {"bonus": bonus},
            ))

        # HP bonus (permanent)
        if "gana" in desc and "hp" in desc and "permanente" in desc:
            hp_match = _re2.search(r'\+(\d+)\s*hp', desc)
            hp_bonus = int(hp_match.group(1)) if hp_match else 1
            mods.append(Modifier(
                source_card_id=cid, hook="modify_hp",
                effect_type="hp_bonus", layer="network",
                params={"bonus": hp_bonus, "condition": condition} if condition else {"bonus": hp_bonus},
            ))

        # Link protection
        if "vínculo" in desc and "no pueden ser destruidos" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="before_destroy",
                effect_type="link_protection", layer="self",
            ))

        # Sigilo with condition
        if "sigilo" in desc and condition:
            if not any(m.effect_type == "cannot_be_attacked" for m in mods):
                mods.append(Modifier(
                    source_card_id=cid, hook="before_attack",
                    effect_type="cannot_be_attacked", layer="self",
                    params={"condition": condition},
                ))

        # Expanded damage regex: "gana +N al daño" / "ganan +N daño base"
        if not any(m.effect_type == "damage_bonus" for m in mods):
            d_match2 = _re2.search(r'(?:gana|ganan)\s+\+(\d+)\s*(?:al\s*)?(?:daño|d)', desc.lower())
            if d_match2:
                delta = int(d_match2.group(1))
                if "defensa" not in desc:
                    mods.append(Modifier(
                        source_card_id=cid, hook="modify_damage",
                        effect_type="damage_bonus", layer="network",
                        params={"delta": delta, "condition": condition} if condition else {"delta": delta},
                    ))

        # Expanded link_cost_zero: "vínculo(s) ... cuestan 0 acciones"
        if not any(m.effect_type == "link_cost_zero" for m in mods):
            if ("vínculo" in desc or "vinculo" in desc) and _re2.search(r'cuestan?\s+0\s+acciones', desc.lower()):
                mods.append(Modifier(
                    source_card_id=cid, hook="before_link",
                    effect_type="link_cost_zero", layer="self",
                ))

        # Cost reduction: "cartas jugadas en el mismo meridiano cuestan 0"
        if "meridiano" in desc and "cuestan 0" in desc:
            mods.append(Modifier(
                source_card_id=cid, hook="before_play",
                effect_type="cost_reduction_meridian", layer="self",
            ))

        return mods

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
        for mod in self._modifiers.get("on_enter", []):
            if mod.source_card_id == card.card_id:
                if mod.effect_type == "vanguard_entry":
                    # Positional entry is already enforced/validated by the
                    # layer checks in play_card(); the modifier is declarative
                    # only, so don't no-op-dispatch it through _apply_on_enter.
                    continue
                self._apply_on_enter(mod, card, player)

        # ─── after_play hook ───
        for mod in self._modifiers.get("after_play", []):
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
        for mod in self._modifiers.get("on_ascend", []):
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
        err = self.can_ascend(player, card, free=free)
        if err:
            return err

        if card.definition.is_spy:
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

        # ─── on_move hook ───
        for mod in self._modifiers.get("on_move", []):
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
        """Check if a card can use an active ability.

        reactive=True (Árbitro del Juego-style "instant" negate) bypasses the
        active-player / ACTIONS-phase restrictions so it can fire on the
        opponent's turn in response to an enemy effect.
        """
        if player != self.active_player and not reactive:
            return "No es tu turno."
        if self.phase != Phase.ACTIONS and not reactive:
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
        active_abilities_pre = [a for a in card.definition.abilities
                                if a.ability_type.name == 'ACTIVE']
        ability_pre = (active_abilities_pre[ability_index]
                       if 0 <= ability_index < len(active_abilities_pre) else None)
        desc_lower_pre = ability_pre.description.lower() if ability_pre else ""
        # Reactive "instant" abilities (e.g. Árbitro del Juego) may fire during
        # the OPPONENT's turn to negate an effect as it resolves.
        is_reactive = "niega un efecto" in desc_lower_pre

        err = self.can_use_ability(player, card, ability_index, reactive=is_reactive)
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
            # ─── Discard then draw (checked BEFORE generic draw so the ───
            # ─── discard half isn't swallowed by an early return) ───
            if "descarta" in desc_lower and "roba" in desc_lower:
                import re
                dc_match = re.search(r'descarta\s+(\d+)', desc_lower)
                discard_count = int(dc_match.group(1)) if dc_match else 1
                dr_match = re.search(r'roba\s+(\d+)', desc_lower)
                draw_count = int(dr_match.group(1)) if dr_match else 1
                for _ in range(min(discard_count, len(self.hands[player]))):
                    if self.hands[player]:
                        self.discard_piles[player].append(self.hands[player].pop())
                for _ in range(draw_count):
                    self._draw_card(player)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: descarta {discard_count}, roba {draw_count}")
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
                    drawn = self._draw_card(player)
                    if drawn:
                        total_drawn += 1
                    else:
                        self.seals[player] -= 1
                        self._log(f"  ¡Fatiga! -1 sello ({self.seals[player]})")
                        if self.seals[player] <= 0:
                            self._end_game(1 - player)
                # Check for "gana N sello" in the same ability
                gain_match = re.search(r'(?:tú\s+)?ganas?\s+(\d+)\s+sello', desc_lower)
                if gain_match:
                    gain = int(gain_match.group(1))
                    self.seals[player] += gain
                self.actions_remaining -= cost
                if gain_match:
                    self._log(f"  {card.definition.name}: usa habilidad → roba {total_drawn} carta(s), gana {gain} sello")
                else:
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
                # Also check for "pierde N sello" in the same ability
                lose_match = re.search(r'pierde\s+(\d+)\s+sello', desc_lower)
                if lose_match:
                    lose = int(lose_match.group(1))
                    enemy = 1 - player
                    self.seals[enemy] = max(0, self.seals[enemy] - lose)
                self.actions_remaining -= cost
                if lose_match:
                    self._log(f"  {card.definition.name}: usa habilidad → +{seal_count} sellos, enemigo -{lose} sellos ({self.seals[player]} / {self.seals[enemy]})")
                else:
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
            if "pierde" in desc_lower and any(w in desc_lower for w in ["sello", "sellos"]) and "hp" not in desc_lower:
                import re
                seal_count = 2
                match = re.search(r'pierde\s+(\d+)\s+sello', desc_lower)
                if match:
                    seal_count = int(match.group(1))
                enemy = 1 - player
                self.seals[enemy] = max(0, self.seals[enemy] - seal_count)
                # Also check for "Tú ganas N sello/s" in the same ability
                gain_match = re.search(r'(?:tú\s+)?ganas?\s+(\d+)\s+sello', desc_lower)
                if gain_match:
                    gain = int(gain_match.group(1))
                    self.seals[player] += gain
                    self._log(f"  {card.definition.name}: usa habilidad → enemigo pierde {seal_count} sellos, tú ganas {gain} sello ({self.seals[enemy]} / {self.seals[player]})")
                else:
                    self._log(f"  {card.definition.name}: usa habilidad → enemigo pierde {seal_count} sellos ({self.seals[enemy]})")
                self.actions_remaining -= cost
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
                target_card.current_hp += hp_bonus
                self._register_temp_modifier(Modifier(
                    source_card_id=target_card.card_id, hook="end_of_turn",
                    effect_type="revert_hp_buff", layer="self",
                    params={"delta": hp_bonus}))
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: usa habilidad → {target_card.definition.name} +{hp_bonus} HP temporal")
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
                    self._register_temp_modifier(Modifier(
                        source_card_id=target_card.card_id, hook="modify_damage",
                        effect_type="damage_bonus", layer="self",
                        params={"delta": d_bonus}))
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
                color_a = self._get_color_overrides().get(card.card_id, card.definition.color)
                color_b = self._get_color_overrides().get(target_card.card_id, target_card.definition.color)
                self._temp_colors[card.card_id] = color_b
                self._temp_colors[target_card.card_id] = color_a
                # Also register as temp modifiers
                from .card import Color as C
                self._register_temp_modifier(Modifier(
                    source_card_id=card.card_id, hook="modify_squad",
                    effect_type="color_override", params={"color": color_b}, layer="self"))
                self._register_temp_modifier(Modifier(
                    source_card_id=target_card.card_id, hook="modify_squad",
                    effect_type="color_override", params={"color": color_a}, layer="self"))
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

            # ─── Destroy specific link (skip mass-break "todos los vínculos") ───
            if (("destruye" in desc_lower or "rompe" in desc_lower) and "vínculo" in desc_lower
                    and "escuadrón" not in desc_lower and "todos los vínculos" not in desc_lower):
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
            if "costos de vínculo" in desc_lower:
                # Register temp global modifier instead of _link_cost_free flag
                self._register_temp_modifier(Modifier(
                    source_card_id=card.card_id, hook="before_link",
                    effect_type="link_cost_zero", layer="global"))
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
                # Also register as temp modifier
                self._register_temp_modifier(Modifier(
                    source_card_id=target_card.card_id, hook="modify_squad",
                    effect_type="color_override", params={"color": new_color_str}, layer="self"))
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
                    # Also register as temp modifier
                    self._register_temp_modifier(Modifier(
                        source_card_id=cid, hook="modify_squad",
                        effect_type="color_override", params={"color": new_color}, layer="self"))
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

            # ─── Attach parasite to enemy Logistron ───
            if "adjunta" in desc_lower and "logistrón" in desc_lower:
                if card.card_id in self._attached:
                    host = self.all_cards.get(self._attached[card.card_id])
                    host_name = host.definition.name if host else "?"
                    return f"Ya está adjuntado a {host_name}."
                target_card = get_target_card("target_id")
                if not target_card:
                    return "Selecciona un Logistrón enemigo."
                if target_card.owner == player:
                    return "Debe ser un Logistrón enemigo."
                if not target_card.definition.is_logistron:
                    return f"{target_card.definition.name} no es un Logistrón."
                self._attached[card.card_id] = target_card.card_id
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: se adjunta a {target_card.definition.name}")
                return None
            if "escuadrón" in desc_lower and ("daño" in desc_lower or "daño base" in desc_lower):
                squads = self.get_player_squads(player)
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
                    self._register_temp_modifier(Modifier(
                        source_card_id=cid, hook="modify_damage",
                        effect_type="damage_bonus", layer="squad",
                        params={"delta": bonus}))
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: +{bonus} daño base al escuadrón {squad.squad_type}")
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
                if self.board.cells[p][li][new_m] is not None:
                    return "Celda ocupada."

                # Move
                self.board.cells[p][li][meridian] = None
                self.board.cells[p][li][new_m] = card.card_id
                card.position = (p, layer, new_m)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: se mueve a L{layer}:{new_m}")

                # Check for adjacent Naturaleza for free link
                if "naturaleza" in desc_lower and "vínculo gratis" in desc_lower:
                    color_naturaleza = Color.NATURALEZA
                    # Scan same-layer at dh=2
                    for check_m in [new_m - 2, new_m + 2]:
                        if 0 <= check_m < 15:
                            neighbor_cid = self.board.cells[p][li][check_m]
                            if neighbor_cid:
                                neighbor = self.all_cards.get(neighbor_cid)
                                if neighbor and neighbor.definition.color == color_naturaleza:
                                    if self.network.can_link(card) and self.network.can_link(neighbor):
                                        self.network.add_link(card, neighbor)
                                        self._log(f"  {card.definition.name}: vínculo gratis con {neighbor.definition.name} (Naturaleza)")
                                        break
                    # Also scan cross-layer dv=1, dh<=1
                    linked = False
                    for dl in [-1, 1]:
                        if linked: break
                        check_li = li + dl
                        if 0 <= check_li < 3:
                            for check_m in [new_m - 1, new_m, new_m + 1]:
                                if 0 <= check_m < 15:
                                    neighbor_cid = self.board.cells[p][check_li][check_m]
                                    if neighbor_cid:
                                        neighbor = self.all_cards.get(neighbor_cid)
                                        if neighbor and neighbor.definition.color == color_naturaleza:
                                            if self.network.can_link(card) and self.network.can_link(neighbor):
                                                self.network.add_link(card, neighbor)
                                                self._log(f"  {card.definition.name}: vínculo gratis cross-layer con {neighbor.definition.name}")
                                                linked = True
                                                break
                return None

            # ─── (Discard-then-draw moved up, before generic draw) ───

            # ─── Temp D buff squad-wide ───
            if ("ganan" in desc_lower or "gana" in desc_lower) and "+" in desc and "d" in desc_lower:
                d_match = re.search(r'\+(\d+)\s*(d|daño)', desc_lower)
                delta = int(d_match.group(1)) if d_match else 1
                if "este turno" in desc_lower:
                    squad = self._squad_of(card.card_id)
                    if squad:
                        for cid in squad.members:
                            mem = self.all_cards.get(cid)
                            if mem and mem.owner == player:
                                self._register_temp_modifier(Modifier(
                                    source_card_id=cid, hook="modify_damage",
                                    effect_type="damage_bonus", layer="self",
                                    params={"delta": delta}))
                    self.actions_remaining -= cost
                    self._log(f"  {card.definition.name}: escuadrón +{delta} D este turno")
                    return None

            # ─── Temp indestructible ───
            if "indestructible" in desc_lower and "este turno" in desc_lower:
                for cid_list in self.board.cells[player]:
                    for cid in cid_list:
                        if cid is not None:
                            self._register_temp_modifier(Modifier(
                                source_card_id=cid, hook="before_destroy",
                                effect_type="destroy_immunity", layer="self",
                                params={"duration": "turn"}))
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: cartas aliadas indestructibles este turno")
                return None

            # ─── Permanent +HP buff ───
            if "ganan" in desc_lower and "hp" in desc_lower and "permanente" in desc_lower:
                hp_match = re.search(r'\+(\d+)\s*hp', desc_lower)
                hp_bonus = int(hp_match.group(1)) if hp_match else 2
                for cid_list in self.board.cells[player]:
                    for cid in cid_list:
                        if cid is not None:
                            mem = self.all_cards.get(cid)
                            if mem:
                                mem.current_hp += hp_bonus
                                mem.definition.hp += hp_bonus
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: cartas aliadas +{hp_bonus} HP permanente")
                return None

            # ─── Damage enemy squad ───
            if "pierden" in desc_lower and "hp" in desc_lower:
                hp_match = re.search(r'pierden?\s+(\d+)\s*hp', desc_lower)
                dmg = int(hp_match.group(1)) if hp_match else 1
                target_card = get_target_card("target_id")
                if target_card:
                    squad = self._squad_of(target_card.card_id)
                    if squad:
                        for cid in list(squad.members):
                            mem = self.all_cards.get(cid)
                            if mem:
                                mem.current_hp -= dmg
                                self._log(f"  {mem.definition.name}: -{dmg} HP ({mem.current_hp}/{mem.definition.hp})")
                                if mem.current_hp <= 0:
                                    self._destroy_card(mem)
                self.actions_remaining -= cost
                return None

            # ─── Damage specific card type ───
            if "pierden" in desc_lower and "logistron" in desc_lower:
                hp_match = re.search(r'pierden?\s+(\d+)\s*hp', desc_lower)
                dmg = int(hp_match.group(1)) if hp_match else 2
                enemy = 1 - player
                for cid_list in self.board.cells[enemy]:
                    for cid in cid_list:
                        if cid is not None:
                            mem = self.all_cards.get(cid)
                            if mem and "Logistrón" in mem.definition.name:
                                mem.current_hp -= dmg
                                self._log(f"  {mem.definition.name}: -{dmg} HP ({mem.current_hp}/{mem.definition.hp})")
                                if mem.current_hp <= 0:
                                    self._destroy_card(mem)
                self.actions_remaining -= cost
                return None

            # ─── G1: Cannot attack this turn ───
            if "no pueden atacar" in desc_lower and "este turno" in desc_lower:
                enemy = 1 - player
                # Flag ALL enemy cards (board + elsewhere); attack() checks the flag
                for ec in self.all_cards.values():
                    if ec.owner == enemy:
                        ec._cannot_attack = True
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: cartas enemigas no pueden atacar este turno")
                return None

            # ─── G2: Block enemy formation bonus ───
            if "no reciben potenciamiento" in desc_lower and "este turno" in desc_lower:
                self._block_enemy_formation = True
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: escuadrones enemigos no reciben potenciamiento")
                return None

            # ─── G3: Negate faction effect ───
            if "niega el efecto de facción" in desc_lower:
                target_card = get_target_card("target_id")
                if target_card:
                    target_card._faction_disabled = True
                    self.actions_remaining -= cost
                    self._log(f"  {card.definition.name}: niega efecto de facción de {target_card.definition.name}")
                    return None

            # ─── G4: Break all enemy links ───
            if "rompe todos los vínculos enemigos" in desc_lower:
                enemy = 1 - player
                broken = 0
                # Links live in Network.links (dict[int, set[int]]) keyed by card_id
                # and remove_link takes CardInstance objects — iterate enemy cards
                # that actually have links.
                for cid in list(self.network.links.keys()):
                    card_obj = self.all_cards.get(cid)
                    if not card_obj or card_obj.owner != enemy:
                        continue
                    for neighbor_id in list(self.network.links.get(cid, set())):
                        neighbor = self.all_cards.get(neighbor_id)
                        if neighbor is not None:
                            self.network.remove_link(card_obj, neighbor)
                            broken += 1
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: rompe {broken} vínculos enemigos")
                return None

            # ─── G5: Destroy all enemy Logistrones ───
            if "destruye todos los logistrones" in desc_lower:
                enemy = 1 - player
                for cid_list in self.board.cells[enemy]:
                    for cid in cid_list:
                        if cid is not None:
                            mem = self.all_cards.get(cid)
                            if mem and "Logistrón" in mem.definition.name:
                                self._destroy_card(mem)
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: destruye todos los Logistrones enemigos")
                return None

            # ─── G6: Mass free link ───
            if "conecta" in desc_lower and "no vinculadas" in desc_lower and "vínculos gratis" in desc_lower:
                linked = 0
                mine = [c for c in self.all_cards.values() if c.owner == player]
                for i, card_obj in enumerate(mine):
                    for card2 in mine[i+1:]:
                        if (self.network.can_link(card_obj) and self.network.can_link(card2)
                                and not self.network.has_link(card_obj, card2)):
                            self.network.add_link(card_obj, card2)
                            linked += 1
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: conecta {linked} cartas con vínculos gratis")
                return None

            # ─── G7: Play from graveyard this turn ───
            if "jugar cartas de tu cementerio" in desc_lower:
                self._grave_play[player] = True
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: puede jugar cartas de cementerio este turno")
                return None

            # ─── G8: Swap D with enemy ───
            if "intercambia d" in desc_lower and "enemig" in desc_lower:
                enemy = 1 - player
                for cid_list in self.board.cells[player]:
                    for cid in cid_list:
                        if cid is not None:
                            ally = self.all_cards.get(cid)
                            if ally:
                                enemy_cid = self.board.cells[enemy][0][ally.position[2]] if ally.position else None
                                if enemy_cid:
                                    enemy_card = self.all_cards.get(enemy_cid)
                                    if enemy_card:
                                        ally.definition.damage, enemy_card.definition.damage = enemy_card.definition.damage, ally.definition.damage
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia D con enemigo")
                return None

            # ─── G9: Swap squad HP with defender ───
            if "intercambia hp" in desc_lower and "escuadrón" in desc_lower:
                target_card = get_target_card("target_id")
                if target_card:
                    my_squad = self._squad_of(card.card_id)
                    enemy_squad = self._squad_of(target_card.card_id)
                    if my_squad and enemy_squad:
                        my_hps = {}
                        for cid in my_squad.members:
                            mem = self.all_cards.get(cid)
                            if mem:
                                my_hps[cid] = mem.current_hp
                        for cid in enemy_squad.members:
                            mem = self.all_cards.get(cid)
                            if mem:
                                enemy_hp = mem.current_hp
                                # Get corresponding ally at same position
                                if mem.position:
                                    ally_cid = self.board.cells[player][mem.position[1]-1][mem.position[2]]
                                    if ally_cid and ally_cid in my_hps:
                                        mem.current_hp = my_hps[ally_cid]
                                        self.all_cards[ally_cid].current_hp = enemy_hp
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: intercambia HP de escuadrones")
                return None

            # ─── H1: Restore grimorio to 30 ───
            if "restaura tu grimorio" in desc_lower and "30" in desc:
                self.seals[player] = 30
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: grimorio restaurado a 30 sellos")
                return None

            # ─── H2: Restore broken seals ───
            if "restaura" in desc_lower and "sellos rotos" in desc_lower:
                broken = 30 - self.seals[player]
                self.seals[player] = 30
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: restaura {broken} sellos rotos")
                return None

            # ─── H3: Tutor (search deck) ───
            if "busca" in desc_lower and "reserva" in desc_lower and "mano" in desc_lower:
                if self.decks[player]:
                    # Simple: pick top non-spy card
                    for i, dc in enumerate(self.decks[player]):
                        if not dc.definition.is_spy:
                            chosen = self.decks[player].pop(i)
                            self.hands[player].append(chosen)
                            self._log(f"  {card.definition.name}: busca {chosen.definition.name} de la reserva")
                            break
                    else:
                        self._log(f"  {card.definition.name}: reserva solo tiene espías (sin efecto)")
                self.actions_remaining -= cost
                return None

            # ─── H4: Swap territory ───
            if "cambiar de territorio" in desc_lower or ("cambia" in desc_lower and "territorio" in desc_lower):
                # Toggle: 0 (North) ↔ 1 (South) for this player
                if hasattr(self, '_territory'):
                    self._territory[player] = 1 - self._territory.get(player, 0)
                else:
                    self._territory = {0: 0, 1: 0}
                    self._territory[player] = 1
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: cambia de territorio → {'Sur' if self._territory.get(player,0) else 'Norte'}")
                return None

            # ─── H5: Add temporal meridian ───
            if "meridiano temporal" in desc_lower:
                self._temp_meridians = getattr(self, '_temp_meridians', 0) + 1
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: +1 meridiano temporal (total: {self._temp_meridians})")
                return None

            # ─── I1: Magnum Opus — clone card ───
            if "crea una copia" in desc_lower or ("copia" in desc_lower and "carta" in desc_lower):
                target_card = get_target_card("target_id")
                if target_card:
                    new_id = max(self.all_cards.keys()) + 1 if self.all_cards else 10000
                    clone = target_card.clone(new_id, player)
                    self.all_cards[new_id] = clone
                    # Place in first free cell
                    placed = False
                    for li in range(3):
                        for m in range(15):
                            if self.board.cells[player][li][m] is None:
                                self.board.cells[player][li][m] = new_id
                                clone.position = (player, li+1, m)
                                placed = True
                                break
                        if placed:
                            break
                    if placed:
                        self._log(f"  {card.definition.name}: crea copia de {target_card.definition.name} en L{clone.position[1]}")
                    else:
                        self._log(f"  {card.definition.name}: no hay espacio para la copia")
                self.actions_remaining -= cost
                return None

            # ─── I2: Falsificador de Órdenes — force enemy attack ───
            if "ataque a otro" in desc_lower and "enemig" in desc_lower:
                enemy = 1 - player
                target_card = get_target_card("target_id")
                if target_card:
                    attacker_squad = self._squad_of(target_card.card_id)
                    if attacker_squad:
                        # Pick another enemy squad as target (find_squads → list)
                        for squad2 in self.network.find_squads(self.all_cards):
                            if squad2 is attacker_squad:
                                continue
                            # enemy squad (majority owner == enemy)
                            owners = [self.all_cards[m].owner for m in squad2.members if self.all_cards.get(m)]
                            if owners and owners.count(enemy) > len(owners) // 2:
                                # Force attack: attacker squad damages defender squad
                                atk_dmg = sum(self.all_cards[cid].definition.damage_bonus for cid in attacker_squad.members if self.all_cards.get(cid))
                                for cid in squad2.members:
                                    mem = self.all_cards.get(cid)
                                    if mem:
                                        mem.current_hp -= max(1, atk_dmg)
                                        self._log(f"  {mem.definition.name}: -{max(1,atk_dmg)} HP (ataque forzado)")
                                self._log(f"  {card.definition.name}: escuadrón enemigo ataca a otro escuadrón enemigo")
                                break
                self.actions_remaining -= cost
                return None

            # ─── I3: Árbitro del Juego — negate next effect ───
            if "niega un efecto" in desc_lower and "active" in desc_lower:
                self._negate_next = True
                self.actions_remaining -= cost
                self._log(f"  {card.definition.name}: próximo efecto enemigo será negado")
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
                                self._register_temp_modifier(Modifier(
                                    source_card_id=card.card_id, hook="start_of_turn",
                                    effect_type="copied_ability", layer="self",
                                    params={"desc": ab.description, "source": target_card.definition.name}))
                                self._log(f"  {card.definition.name}: copia habilidad de {target_card.definition.name}: {ab.description[:40]}")
                                break
                self.actions_remaining -= cost
                return None

            # ─── I5: Titiritero — mind control enemy squad ───
            if "toma control" in desc_lower and "escuadrón" in desc_lower:
                target_card = get_target_card("target_id")
                if target_card and target_card.owner != player:
                    # find_squads returns a list — locate the squad containing the target
                    squad = None
                    for sq in self.network.find_squads(self.all_cards):
                        if target_card.card_id in sq.members:
                            squad = sq
                            break
                    if squad:
                        for cid in list(squad.members):
                            mem = self.all_cards.get(cid)
                            if mem:
                                old_owner = mem.owner
                                # Move to player cells; if no free cell at this meridian,
                                # DON'T steal the card (it would vanish from the board).
                                placed = False
                                if mem.position:
                                    p, li_old, m = mem.position
                                    for li_new in range(3):
                                        if self.board.cells[player][li_new][m] is None:
                                            placed = True
                                            break
                                if not placed:
                                    self._log(f"  {mem.definition.name}: sin celda libre en meridiano {m}, no puede ser robada")
                                    continue
                                self._mind_controlled[cid] = old_owner
                                mem.owner = player
                                # Break enemy links (Network.links, CardInstance objects)
                                for nb_id in list(self.network.links.get(cid, set())):
                                    nb = self.all_cards.get(nb_id)
                                    if nb is not None:
                                        self.network.remove_link(mem, nb)
                                # Move to player cells
                                if mem.position:
                                    p, li_old, m = mem.position
                                    self.board.cells[old_owner][li_old-1][m] = None
                                    self.board.cells[player][li_new][m] = cid
                                    mem.position = (player, li_new+1, m)
                        self._log(f"  {card.definition.name}: toma control del escuadrón de {target_card.definition.name}")
                self.actions_remaining -= cost
                return None

            # ─── Fallback: ability not yet implemented ───
            return None

        except Exception as e:
            # Safety net: log error, refund actions, don't crash
            self._log(f"  ⚠ Error en habilidad de {card.definition.name}: {str(e)}")
            return f"Error al ejecutar habilidad: {str(e)}"

    def _squad_of(self, card_id: int) -> Optional["Squad"]:
        """Return the squad (from find_squads) containing card_id, or None.

        find_squads() returns a list of fresh Squad objects, so callers can't use
        .get(card_id) — this is the canonical lookup.
        """
        for sq in self.network.find_squads(self.all_cards):
            if card_id in sq.members:
                return sq
        return None

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
        for mod in self._modifiers.get("before_link", []):
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
        for mod in self._modifiers.get("before_link", []):
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

        self.network.add_link(card_a, card_b)

        # ─── after_link hook ───
        # On-link triggers from permanent modifiers
        for mod in self._modifiers.get("after_link", []):
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
        self.phase = Phase.ENTRY
        self.actions_remaining = 4
        self._attacked_squads = set()
        self._spy_sabotage_used = set()
        # Reset "este turno" ability flags (G1/G2/G7) and per-card G1 marks
        self._block_enemy_formation = False
        self._grave_play = {0: False, 1: False}
        for _c in self.all_cards.values():
            if getattr(_c, "_cannot_attack", False):
                _c._cannot_attack = False
        self.log = []
        self._log(f"═══ TURNO {self.turn_number} — Jugador {self.active_player + 1} ═══")

    def entry_phase(self):
        """Entry phase: trigger start-of-turn abilities + draw 2."""
        player = self.active_player
        squads = self.network.find_squads(self.all_cards)

        # ─── Dispatch start_of_turn modifiers ───
        for mod in self._modifiers.get("start_of_turn", []):
            card = self.all_cards.get(mod.source_card_id)
            if not card or card.owner != player or not card.position or card.position[0] == -1:
                continue
            # Find which squad this card belongs to
            card_squad = None
            for sq in squads:
                if card.card_id in sq.members:
                    card_squad = sq
                    break
            if not card_squad:
                continue
            # Check COLOR/FORMATION requirements
            params = mod.params
            if params.get("ability_type") == "COLOR":
                req_color = params.get("color_required")
                if req_color and self._get_effective_squad_color(card, card_squad).value != req_color:
                    continue
            if params.get("ability_type") == "FORMATION":
                req_form = params.get("formation_required")
                if req_form and card_squad.squad_type.replace("_ampliado", "") != req_form:
                    continue
            # Execute effect
            self._apply_trigger_modifier(mod, card, card_squad, squads)

        # Military faction: free ascension
        for squad in squads:
            if squad.get_dominant_color(self._get_color_overrides()) == Color.MILITAR:
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
            if squad.get_dominant_color(self._get_color_overrides()) == Color.SABIO:
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
        # Parasite damage: deal 1 HP to all parasitized hosts
        for parasite_id, host_id in list(self._attached.items()):
            host = self.all_cards.get(host_id)
            if host and host.position and host.position[0] != -1:
                host.current_hp -= 1
                parasite = self.all_cards.get(parasite_id)
                pname = parasite.definition.name if parasite else "?"
                self._log(f"  🦠 {pname} drena 1 HP a {host.definition.name} ({host.current_hp}/{host.definition.hp})")
                if host.current_hp <= 0:
                    self._log(f"  {host.definition.name} MUERE por parásito.")
                    self._destroy_card(host)
                    # Parasite is freed
                    del self._attached[parasite_id]
        # Politicos: swap positions
        for squad in squads:
            if squad.get_dominant_color(self._get_color_overrides()) == Color.POLITICO:
                self._log(f"  [Político] Puedes intercambiar posiciones de 2 cartas por escuadrón.")

    def start_attack_phase(self):
        self.phase = Phase.ATTACK
        self._log(f"  >>> Fase de Ataque <<<")

    def exit_phase(self):
        player = self.active_player
        self.phase = Phase.EXIT
        squads = self.network.find_squads(self.all_cards)

        # ─── 1. Purge isolated enemy nodes (before end_of_turn, per §5.5) ───
        enemy = 1 - player
        for cid in list(self.all_cards.keys()):
            card = self.all_cards.get(cid)
            if card and card.owner == enemy and card.position and card.position[0] != -1:
                if self.network.link_count(card) == 0 and not card.definition.is_spy:
                    self._destroy_card(card)
                    self._log(f"  Purga: {card.definition.name} aislado, destruido.")

        # Recalculate squads after purge (connectivity may have changed)
        squads = self.network.find_squads(self.all_cards)

        # ─── 2. Dispatch end_of_turn modifiers (incl. Autofobia) ───
        for mod in self._modifiers.get("end_of_turn", []):
            card = self.all_cards.get(mod.source_card_id)
            if not card or card.owner != player or not card.position or card.position[0] == -1:
                continue
            # Find which squad this card belongs to
            card_squad = None
            for sq in squads:
                if card.card_id in sq.members:
                    card_squad = sq
                    break
            if not card_squad:
                continue
            # Check COLOR/FORMATION requirements
            params = mod.params
            if params.get("ability_type") == "COLOR":
                req_color = params.get("color_required")
                if req_color and self._get_effective_squad_color(card, card_squad).value != req_color:
                    continue
            if params.get("ability_type") == "FORMATION":
                req_form = params.get("formation_required")
                if req_form and card_squad.squad_type.replace("_ampliado", "") != req_form:
                    continue
            # Execute effect
            self._apply_trigger_modifier(mod, card, card_squad, squads)

        # Faction effects at end of turn
        for squad in squads:
            dom = squad.get_dominant_color(self._get_color_overrides())
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

        self._log(f"  Fin del turno. Sellos J{player+1}: {self.seals[player]}")

        # Clear temporary HP buffs (revert before modifier cleanup)
        for mod in self._modifiers.get("end_of_turn", []):
            if mod.is_temporary and mod.effect_type == "revert_hp_buff":
                card = self.all_cards.get(mod.source_card_id)
                if card:
                    delta = mod.params.get("delta", 0)
                    card.current_hp = max(0, card.current_hp - delta)
                    card.current_hp = min(card.current_hp, card.definition.hp)

        # Dissolve temporary links (before modifier cleanup)
        for mod in self._modifiers.get("end_of_turn", []):
            if mod.is_temporary and mod.effect_type == "dissolve_temp_link":
                pair = mod.params.get("pair")
                if pair:
                    card_a = self.all_cards.get(pair[0])
                    card_b = self.all_cards.get(pair[1])
                    if card_a and card_b:
                        self.network.remove_link(card_a, card_b)

        # Clear temporary colors
        self._temp_colors = {}

        # Clear temporary modifiers
        self._unregister_temp_modifiers()

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

        # ─── Apply modify_squad modifiers ───
        for mod in self._modifiers.get("modify_squad", []):
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

        # Check if squad already attacked
        squad_hash = hash(frozenset(attacking_squad.members))
        if squad_hash in self._attacked_squads:
            return "Este escuadrón ya atacó este turno."

        attacker = self.active_player
        defender = 1 - attacker

        # ─── before_attack hook ───
        # Cards with sigilo block attacks on themselves; guardaespaldas redirect
        if target == "card" and target_card_id:
            for mod in self._modifiers.get("before_attack", []):
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
        for mod in self._modifiers.get("modify_damage", []):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != attacker:
                continue
            if mod.effect_type == "damage_bonus":
                # Check condition + squad membership
                condition = mod.params.get("condition", {})
                if not self._evaluate_condition(condition, source_card):
                    continue
                if mod.source_card_id in attacking_squad.members:
                    total_damage += mod.params.get("delta", 0)

        # ─── on_attack hook ───
        # Attack-triggered effects (ignore_armor, double_damage, conditional bonuses)
        ignore_armor_total = 0
        double_damage = False
        for mod in self._modifiers.get("on_attack", []):
            source_card = self.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != attacker:
                continue
            if mod.source_card_id not in attacking_squad.members:
                continue
            condition = mod.params.get("condition", {})
            if condition and not self._evaluate_condition(condition, source_card):
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
            for mod in self._modifiers.get("before_link", []):
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
            # Cap max seal loss, apply grimoire armor
            for mod in self._modifiers.get("grimoire_defense", []):
                source_card = self.all_cards.get(mod.source_card_id)
                if not source_card or source_card.owner != defender:
                    continue
                if mod.effect_type == "max_seal_loss":
                    cap = mod.params.get("max", 999)
                    if net_damage > cap:
                        self._log(f"  🛡️ {source_card.definition.name}: daño capado de {net_damage} a {cap}")
                        net_damage = cap
                elif mod.effect_type == "grimoire_armor":
                    armor_val = mod.params.get("armor", 0)
                    net_damage = max(0, net_damage - armor_val)
                    self._log(f"  🛡️ {source_card.definition.name}: +{armor_val} armadura al grimorio")

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

    # ═══════════════════════════════════════════════════════════════
    # Trigger Modifier Dispatch
    # ═══════════════════════════════════════════════════════════════

    def _apply_trigger_modifier(self, mod: Modifier, card: CardInstance,
                                 squad: Squad, all_squads: list[Squad]):
        """Execute a start_of_turn or end_of_turn modifier effect."""
        effect_type = mod.effect_type
        params = mod.params
        player = card.owner

        if effect_type == "draw":
            count = params.get("count", 1)
            total = 0
            for _ in range(count):
                drawn = self._draw_card(player)
                if drawn:
                    total += 1
            self._log(f"  {card.definition.name}: +{total} robo(s)")

        elif effect_type == "scry":
            count = params.get("count", 2)
            top_cards = self.decks[player][-count:] if len(self.decks[player]) >= count else self.decks[player][:]
            names = [c.definition.name for c in reversed(top_cards)]
            self._log(f"  {card.definition.name}: mira top {len(names)}: {', '.join(names)}")

        elif effect_type == "auto_ascend":
            target = card
            for cid in squad.members:
                c = self.all_cards.get(cid)
                if c and c.position and c.position[1] < 3 and c.position[0] != -1:
                    target = c
                    break
            err = self.ascend(player, target, free=True)
            if not err:
                self._log(f"  {card.definition.name}: asciende {target.definition.name} sin costo")

        elif effect_type == "bonus_actions":
            bonus = params.get("count", 1)
            self.actions_remaining += bonus
            self._log(f"  {card.definition.name}: +{bonus} acción(es) ({self.actions_remaining})")

        elif effect_type == "free_link":
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

        elif effect_type == "recover_hp":
            amount = params.get("amount", 1)
            if params.get("scope") == "squad":
                for cid in squad.members:
                    c = self.all_cards.get(cid)
                    if c and c.owner == player:
                        c.current_hp = min(c.current_hp + amount, c.definition.hp)
                self._log(f"  {card.definition.name}: +{amount} HP a todo el escuadrón")
            else:
                card.current_hp = min(card.current_hp + amount, card.definition.hp)
                self._log(f"  {card.definition.name}: recupera {amount} HP ({card.current_hp}/{card.definition.hp})")

        elif effect_type == "recover_graveyard":
            if self.discard_piles[player]:
                recovered = self.discard_piles[player].pop()
                self.hands[player].append(recovered)
                self._log(f"  {card.definition.name}: recupera {recovered.definition.name} del cementerio")

        elif effect_type == "break_enemy_link":
            self._log(f"  {card.definition.name}: +{params.get('count', 1)} vínculo enemigo destruible")

        elif effect_type == "bonus_seals":
            amount = params.get("amount", 5)
            self.seals[player] += amount
            self._log(f"  {card.definition.name}: +{amount} sellos ({self.seals[player]})")

    def _apply_on_enter(self, mod: Modifier, card: CardInstance, player: int):
        """Execute an on_enter modifier effect when a card is played."""
        effect_type = mod.effect_type
        params = mod.params

        if effect_type == "draw":
            count = params.get("count", 1)
            total = 0
            for _ in range(count):
                drawn = self._draw_card(player)
                if drawn:
                    total += 1
            self._log(f"  {card.definition.name} (on_enter): +{total} robo(s)")

        elif effect_type == "scry":
            count = params.get("count", 2)
            top_cards = self.decks[player][-count:] if len(self.decks[player]) >= count else self.decks[player][:]
            names = [c.definition.name for c in reversed(top_cards)]
            self._log(f"  {card.definition.name} (on_enter): mira top {len(names)}: {', '.join(names)}")

        elif effect_type == "heal_ally":
            amount = params.get("amount", 1)
            # Heal any allied card (or self by default)
            card.current_hp = min(card.current_hp + amount, card.definition.hp)
            self._log(f"  {card.definition.name} (on_enter): +{amount} HP ({card.current_hp}/{card.definition.hp})")

        elif effect_type == "gain_seals":
            amount = params.get("amount", 1)
            self.seals[player] += amount
            self._log(f"  {card.definition.name} (on_enter): +{amount} sellos ({self.seals[player]})")

        elif effect_type == "move_self":
            dist = params.get("distance", 1)
            # Move card horizontally by dist meridians
            if card.position:
                p, layer, meridian = card.position
                for direction in [1, -1]:  # try right first, then left
                    new_m = meridian + direction * dist
                    li = layer - 1
                    if 0 <= new_m < 15 and self.board.cells[p][li][new_m] is None:
                        self.board.cells[p][li][meridian] = None
                        self.board.cells[p][li][new_m] = card.card_id
                        card.position = (p, layer, new_m)
                        self._log(f"  {card.definition.name} (on_enter): se mueve a L{layer}:{new_m}")
                        break

        elif effect_type == "move_ally":
            self._log(f"  {card.definition.name} (on_enter): mueve carta aliada (pendiente selección UI)")

        elif effect_type == "ascend_ally":
            # Find another allied card to ascend for free
            for cid in list(self.all_cards.keys()):
                ally = self.all_cards.get(cid)
                if (ally and ally.owner == player and ally.card_id != card.card_id
                        and ally.position and ally.position[1] < 3 and ally.position[0] != -1):
                    err = self.ascend(player, ally, free=True)
                    if not err:
                        self._log(f"  {card.definition.name} (on_enter): asciende {ally.definition.name} gratis")
                        break

        elif effect_type == "break_link":
            # Break an enemy link at short distance
            count = params.get("count", 1)
            enemy = 1 - player
            broken = 0
            for cid in list(self.all_cards.keys()):
                if broken >= count:
                    break
                enemy_card = self.all_cards.get(cid)
                if not enemy_card or enemy_card.owner != enemy or not enemy_card.position:
                    continue
                for linked_id in list(self.network.links.get(cid, set())):
                    if broken >= count:
                        break
                    linked = self.all_cards.get(linked_id)
                    if linked:
                        self.network.remove_link(enemy_card, linked)
                        broken += 1
                        self._log(f"  {card.definition.name} (on_enter): rompe vínculo {enemy_card.definition.name} <-> {linked.definition.name}")
                        break

        elif effect_type == "auto_link":
            # Link this card to an adjacent allied card
            if card.position:
                p, layer, meridian = card.position
                for dm in [-2, -1, 1, 2]:
                    for dl in [-1, 0, 1]:
                        check_m = meridian + dm
                        check_l = layer + dl
                        if 0 <= check_m < 15 and 1 <= check_l <= 3:
                            li = check_l - 1
                            neighbor_cid = self.board.cells[p][li][check_m]
                            if neighbor_cid and self.network.can_link(card):
                                neighbor = self.all_cards.get(neighbor_cid)
                                if neighbor:
                                    dist = self.board.spatial_distance(card.position, neighbor.position)
                                    if dist:
                                        self.network.add_link(card, neighbor)
                                        self._log(f"  {card.definition.name} (on_enter): vínculo gratis con {neighbor.definition.name}")
                                        return

        elif effect_type == "discard":
            count = params.get("count", 1)
            discarded = []
            for _ in range(count):
                if self.hands[player]:
                    dc = self.hands[player].pop()
                    self.discard_piles[player].append(dc)
                    discarded.append(dc.definition.name)
            self._log(f"  {card.definition.name} (on_enter): descarta {', '.join(discarded) if discarded else '(mano vacía)'}")

    # ═══════════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════════

    def _destroy_card(self, card: CardInstance, killer: Optional[CardInstance] = None):
        # ─── before_destroy hook ───
        for mod in self._modifiers.get("before_destroy", []):
            if mod.source_card_id == card.card_id and mod.effect_type == "destroy_immunity":
                source = self.all_cards.get(mod.source_card_id)
                name = source.definition.name if source else f"#{mod.source_card_id}"
                self._log(f"  🛡️ {name} es inmune a destrucción.")
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
            for mod in self._modifiers.get("on_kill", []):
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
        for mod in self._modifiers.get("after_destroy", []):
            if mod.effect_type == "transfer_links":
                target = self.all_cards.get(mod.source_card_id)
                if not target or not target.position:
                    continue
                # Link target to cards that were linked to the destroyed card
                # (links already removed, but we can re-link to the target)
                self._log(f"  {target.definition.name}: hereda vínculos de {card.definition.name}")

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
            dom = s.get_dominant_color(self._get_color_overrides())
            color_str = dom.value if dom else "incoloro"
            print(f"  [{i}] {s.squad_type} | color: {color_str} | daño base: {s.base_damage} | potenciamiento: {s.empowerment}")
            print(f"      Miembros: {', '.join(names)}")

    def show_log(self):
        if self.log:
            print("\n  ── Eventos ──")
            for entry in self.log:
                print(f"  {entry}")
