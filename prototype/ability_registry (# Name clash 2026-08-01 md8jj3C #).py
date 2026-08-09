"""Unified ability registry for NFW.

Single source of truth for:
- Parsing passive abilities into Modifier objects
- Reporting implementation status for all abilities (active + passive)

When a new ability is added, register a pattern here. Status is derived automatically.
"""

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .modifier import Modifier
from .card import AbilityType


@dataclass
class AbilityPattern:
    """One entry in the ability registry.

    For passive abilities: try_parse returns a list of Modifier(s) on match, None on no match.
    For active abilities:  try_parse returns an empty list [] on match, None on no match.
                           (empty list = "matched, but active abilities produce no Modifiers")

    Attributes:
        name: human-readable identifier for debugging
        try_parse: (description_lower, ability, card_id) -> list[Modifier] | None
        is_active: True if this is an active ability pattern (status-only, no Modifiers)
        implemented: True if the effect is fully implemented
        is_partial: True if partially implemented (overrides to 'partial' status)
    """
    name: str
    try_parse: Callable[[str, 'Ability', int], Optional[list[Modifier]]]
    is_active: bool = False
    implemented: bool = True
    is_partial: bool = False


class AbilityRegistry:
    """Central registry of all known ability patterns.

    Usage:
        registry = AbilityRegistry()
        modifiers = registry.parse(ability, card)        # -> list[Modifier]
        status    = registry.status(ability)              # -> "implemented" | "partial" | "not_implemented"
    """

    def __init__(self):
        self._patterns: list[AbilityPattern] = []
        self._register_all()

    # ─── Public API ───

    def parse(self, ability: 'Ability', card: 'CardInstance') -> list[Modifier]:
        """Parse a passive ability into Modifier objects.

        Active abilities are skipped — they don't produce Modifiers.
        Returns empty list if no passive pattern matches.
        """
        desc = ability.description.lower()
        cid = card.card_id
        mods = []

        for pat in self._patterns:
            if pat.is_active:
                continue
            result = pat.try_parse(desc, ability, cid)
            if result is not None:
                mods.extend(result)

        return mods

    def status(self, ability: 'Ability') -> str:
        """Return implementation status for display in the decks modal.

        Returns 'implemented', 'partial', or 'not_implemented'.
        Derived from the same pattern list the parser uses — cannot drift.
        """
        desc = ability.description.lower()

        for pat in self._patterns:
            result = pat.try_parse(desc, ability, 0)  # card_id=0, not needed for status
            if result is not None:
                if pat.is_partial:
                    return "partial"
                if pat.implemented:
                    return "implemented"
                return "not_implemented"

        return "not_implemented"

    # ─── Pattern registration ───

    def _add(self, name: str, try_parse, is_active: bool = False,
             implemented: bool = True, is_partial: bool = False):
        self._patterns.append(AbilityPattern(
            name=name,
            try_parse=try_parse,
            is_active=is_active,
            implemented=implemented,
            is_partial=is_partial,
        ))

    def _register_all(self):
        """Register every known ability pattern.

        Organized by effect category (mirroring the original parser structure).
        Patterns are checked in registration order — first match wins for status.
        """
        # ═══════════════════════════════════════════════════════════════
        # Helpers
        # ═══════════════════════════════════════════════════════════════

        def _extract_condition(desc):
            """Extract positional condition from description text."""
            # Formation: "En triángulo/cuadrado/pentágono"
            for shape in ["triángulo", "triangulo", "cuadrado", "cuadrilátero",
                          "cuadrilatero", "pentágono", "pentagono"]:
                if f"en {shape}" in desc:
                    shape_clean = shape.replace("á", "a").replace("í", "i")
                    return {"type": "formation", "shape": shape_clean}
            # Layer: "Si está en L1/L2/L3" or "Mientras esté en L1/L2/L3"
            m = re.search(r'(?:si está|mientras esté|está)\s+en\s+[Ll](\d)', desc)
            if m:
                return {"type": "layer", "value": int(m.group(1))}
            # Frontier: "En frontera"
            if "en frontera" in desc:
                return {"type": "frontier"}
            # Links: "mientras tenga 1+ vínculos"
            m = re.search(r'(\d+)\+?\s*vínculo', desc)
            if m:
                return {"type": "links", "min": int(m.group(1))}
            return {}

        def _ability_params(ability):
            """Shared params for COLOR/FORMATION abilities."""
            return {
                "ability_type": ability.ability_type.name,
                "color_required": ability.color_required.value if ability.color_required else None,
                "formation_required": ability.formation_required,
            }

        # ═══════════════════════════════════════════════════════════════
        # ACTIVE abilities (status-only — executed by use_ability())
        # ═══════════════════════════════════════════════════════════════
        # Each pattern: if keyword in desc AND condition is True → matched.
        # try_parse returns [] (empty list = "active, matched, no Modifier").
        # Clear and redo properly
        self._patterns.clear()

        # --- Active: draw ---
        def _active_draw(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "roba" in desc and "control" not in desc and "vínculo" not in desc: return []
            return None
        self._add("active: roba (draw)", _active_draw, is_active=True)

        # --- Active: gain seals ---
        def _active_gain_seals(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "gana" in desc and any(w in desc for w in ["sello", "sellos"]): return []
            return None
        self._add("active: gana sello", _active_gain_seals, is_active=True)

        # --- Active: repair seals ---
        def _active_repair(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "repara" in desc and any(w in desc for w in ["sello", "sellos"]): return []
            return None
        self._add("active: repara sello", _active_repair, is_active=True)

        # --- Active: heal ---
        def _active_heal(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "cura" in desc and "hp" in desc: return []
            return None
        self._add("active: cura hp", _active_heal, is_active=True)

        # --- Active: ascend ---
        def _active_ascend(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "asciende" in desc: return []
            return None
        self._add("active: asciende", _active_ascend, is_active=True)

        # --- Active: self-destruct ---
        def _active_selfdestruct(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "destrúyete" in desc or "destruyete" in desc: return []
            return None
        self._add("active: destrúyete", _active_selfdestruct, is_active=True)

        # --- Active: enemy loses seals ---
        def _active_enemy_seal_loss(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "pierde" in desc and any(w in desc for w in ["sello", "sellos"]): return []
            return None
        self._add("active: pierde sello", _active_enemy_seal_loss, is_active=True)

        # --- Active: scry ---
        def _active_scry(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "mira" in desc and any(w in desc for w in ["carta", "cartas", "reserva", "tope"]): return []
            return None
        self._add("active: mira (scry)", _active_scry, is_active=True)

        # --- Active: discard ---
        def _active_discard(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "descarta" in desc and "roba" not in desc: return []
            return None
        self._add("active: descarta", _active_discard, is_active=True)

        # --- Active: swap (intercambia) ---
        def _active_swap(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "intercambia" in desc: return []
            return None
        self._add("active: intercambia", _active_swap, is_active=True)

        # --- Active: special link (ignorando/temporal/disuelve) ---
        def _active_special_link(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "vínculo" in desc and ("ignorando" in desc or "temporal" in desc or "disuelve" in desc): return []
            return None
        self._add("active: vínculo especial", _active_special_link, is_active=True)

        # --- Active: link armor (vinculo armadura) ---
        def _active_link_armor(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "vínculo" in desc and "armadura" in desc: return []
            return None
        self._add("active: vínculo armadura", _active_link_armor, is_active=True)

        # --- Active: break squad links ---
        def _active_break_squad(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "rompe" in desc and "vínculo" in desc and "escuadrón" in desc: return []
            return None
        self._add("active: rompe vínculo escuadrón", _active_break_squad, is_active=True)

        # --- Active: destroy link ---
        def _active_destroy_link(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "destruye" in desc and "vínculo" in desc: return []
            if "rompe" in desc and "vínculo" in desc and "escuadrón" not in desc: return []
            return None
        self._add("active: destruye/rompe vínculo", _active_destroy_link, is_active=True)

        # --- Active: move + link ---
        def _active_move_link(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "muévete" in desc and "meridiano" in desc: return []
            return None
        self._add("active: muévete meridiano", _active_move_link, is_active=True)

        # --- Active: squad damage buff ---
        def _active_squad_damage(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "escuadrón" in desc and ("daño" in desc or "daño base" in desc): return []
            return None
        self._add("active: escuadrón daño", _active_squad_damage, is_active=True)

        # --- Active: attach parasite ---
        def _active_attach(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "adjunta" in desc and "logistrón" in desc: return []
            return None
        self._add("active: adjunta logistrón", _active_attach, is_active=True)

        # --- Active: link cost free ---
        def _active_link_free(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "costos de vínculo" in desc: return []
            return None
        self._add("active: costos de vínculo", _active_link_free, is_active=True)

        # --- Active: change color ---
        def _active_change_color(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "cambia" in desc and "color" in desc and "escuadrón" not in desc: return []
            return None
        self._add("active: cambia color", _active_change_color, is_active=True)

        # --- Active: squad color ---
        def _active_squad_color(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "escuadrón se considera del color" in desc: return []
            return None
        self._add("active: escuadrón color", _active_squad_color, is_active=True)

        # --- Active: jump cell ---
        def _active_jump(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "salta" in desc and "celda libre" in desc: return []
            return None
        self._add("active: salta celda", _active_jump, is_active=True)

        # --- Active: teleport ---
        def _active_teleport(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "teletransporta" in desc: return []
            return None
        self._add("active: teletransporta", _active_teleport, is_active=True)

        # --- Active: node attack ---
        def _active_node_attack(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "ataca" in desc and "nodo" in desc: return []
            return None
        self._add("active: ataca nodo", _active_node_attack, is_active=True)

        # --- Active: fight ---
        def _active_fight(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "lucha" in desc and "daño" in desc: return []
            return None
        self._add("active: lucha", _active_fight, is_active=True)

        # --- Active: destroy ally + grimoire damage ---
        def _active_destroy_ally(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "destruye" in desc and "grimorio" in desc: return []
            return None
        self._add("active: destruye grimorio", _active_destroy_ally, is_active=True)

        # --- Active: discard then draw (Fase F) ---
        def _active_discard_draw(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "descarta" in desc and "roba" in desc: return []
            return None
        self._add("active: descarta+roba", _active_discard_draw, is_active=True)

        # --- Active: indestructible este turno (Fase F) ---
        def _active_indestructible(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "indestructible" in desc and "este turno" in desc: return []
            return None
        self._add("active: indestructible", _active_indestructible, is_active=True)

        # --- Active: enemy squad/HP damage (Fase F) ---
        def _active_lose_hp(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "pierden" in desc and "hp" in desc: return []
            return None
        self._add("active: pierden hp", _active_lose_hp, is_active=True)

        # --- Active: squad D buff (Fase F) ---
        def _active_squad_d_buff(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "ganan" in desc and "+" in desc and any(w in desc.split() for w in ['d', 'daño']): return []
            return None
        self._add("active: ganan +D escuadrón", _active_squad_d_buff, is_active=True)

        # --- Active: permanent HP buff (Fase F) ---
        def _active_perm_hp(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "ganan" in desc and "hp" in desc and "permanente" in desc: return []
            return None
        self._add("active: ganan hp permanente", _active_perm_hp, is_active=True)

        # --- Active: cannot attack (Fase G) ---
        def _active_cannot_attack(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "no pueden atacar" in desc: return []
            return None
        self._add("active: no pueden atacar", _active_cannot_attack, is_active=True)

        # --- Active: block formation (Fase G) ---
        def _active_block_formation(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "no reciben potenciamiento" in desc: return []
            return None
        self._add("active: no reciben potenciamiento", _active_block_formation, is_active=True)

        # --- Active: negate faction (Fase G) ---
        def _active_negate_faction(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "niega el efecto de facción" in desc: return []
            return None
        self._add("active: niega facción", _active_negate_faction, is_active=True)

        # --- Active: mass break links (Fase G) ---
        def _active_mass_break(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "rompe todos los vínculos enemigos" in desc: return []
            return None
        self._add("active: rompe todos vínculos", _active_mass_break, is_active=True)

        # --- Active: mass destroy logistrons (Fase G) ---
        def _active_mass_destroy(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "destruye todos los logistrones" in desc: return []
            return None
        self._add("active: destruye logistrones", _active_mass_destroy, is_active=True)

        # --- Active: mass link (Fase G) ---
        def _active_mass_link(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "conecta" in desc and "no vinculadas" in desc: return []
            return None
        self._add("active: conecta no vinculadas", _active_mass_link, is_active=True)

        # --- Active: grave play (Fase G) ---
        def _active_grave_play(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "jugar cartas de tu cementerio" in desc: return []
            return None
        self._add("active: jugar cementerio", _active_grave_play, is_active=True)

        # --- Active: swap D (Fase G) ---
        def _active_swap_d(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "intercambia d" in desc: return []
            return None
        self._add("active: intercambia D", _active_swap_d, is_active=True)

        # --- Active: swap HP squad (Fase G) ---
        def _active_swap_hp(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "intercambia hp" in desc and "escuadrón" in desc: return []
            return None
        self._add("active: intercambia HP escuadrón", _active_swap_hp, is_active=True)

        # --- Active: restore grimoire (Fase H) ---
        def _active_restore_grimoire(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "restaura tu grimorio" in desc and "30" in desc: return []
            return None
        self._add("active: restaura grimorio", _active_restore_grimoire, is_active=True)

        # --- Active: restore seals (Fase H) ---
        def _active_restore_seals(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "restaura" in desc and "sellos rotos" in desc: return []
            return None
        self._add("active: restaura sellos", _active_restore_seals, is_active=True)

        # --- Active: tutor (Fase H) ---
        def _active_tutor(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "busca" in desc and "reserva" in desc and "mano" in desc: return []
            return None
        self._add("active: busca reserva", _active_tutor, is_active=True)

        # --- Active: territory swap (Fase H) ---
        def _active_territory(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "cambia" in desc and "territorio" in desc: return []
            return None
        self._add("active: cambia territorio", _active_territory, is_active=True)

        # --- Active: temp meridian (Fase H) ---
        def _active_temp_meridian(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "meridiano temporal" in desc: return []
            return None
        self._add("active: meridiano temporal", _active_temp_meridian, is_active=True)

        # --- Active: clone (Fase I) ---
        def _active_clone(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "crea una copia" in desc: return []
            return None
        self._add("active: crea copia", _active_clone, is_active=True)

        # --- Active: copy ability (Fase I) ---
        def _active_copy_ability(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "copia una habilidad" in desc: return []
            return None
        self._add("active: copia habilidad", _active_copy_ability, is_active=True)

        # --- Active: negate effect (Fase I) ---
        def _active_negate(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "niega un efecto" in desc: return []
            return None
        self._add("active: niega efecto", _active_negate, is_active=True)

        # --- Active: force enemy attack (Fase I) ---
        def _active_force_attack(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "ataque a otro" in desc: return []
            return None
        self._add("active: ataque a otro", _active_force_attack, is_active=True)

        # --- Active: mind control (Fase I) ---
        def _active_mind_control(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "toma control" in desc and "escuadrón" in desc: return []
            return None
        self._add("active: toma control", _active_mind_control, is_active=True)

        # --- Active: +HP temp buff ---
        def _active_temp_hp(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "gana +" in desc and "hp" in desc: return []
            return None
        self._add("active: gana +HP", _active_temp_hp, is_active=True)

        # --- Active: +D temp buff ---
        def _active_temp_d(desc, ability, cid):
            if ability.trigger != "active": return None
        if ability.ability_type not in (AbilityType.ACTIVE, AbilityType.FORMATION, AbilityType.GENERAL): return None
            if "+" in desc and "d" in desc and "hp" not in desc: return []
            return None
        self._add("active: +D temp", _active_temp_d, is_active=True)

        # ═══════════════════════════════════════════════════════════════
        # START_OF_TURN passive patterns
        # ═══════════════════════════════════════════════════════════════

        def _sot_draw(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if ("roba" not in desc and "robo" not in desc) or "control" in desc or "vínculo" in desc: return None
            count = 1
            m = re.search(r'roba\s+(\d+)', desc)
            if m: count = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="start_of_turn", effect_type="draw", layer="self",
                    params={"count": count, **_ability_params(ability)})]
        self._add("sot: draw", _sot_draw)

        def _sot_scry(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if "mira" not in desc: return None
            count = 2
            m = re.search(r'mira\s+(\d+)', desc)
            if m: count = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="start_of_turn", effect_type="scry", layer="self",
                    params={"count": count, **_ability_params(ability)})]
        self._add("sot: scry", _sot_scry)

        def _sot_auto_ascend(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if "asciende" not in desc and "ascender" not in desc: return None
            return [Modifier(source_card_id=cid, hook="start_of_turn", effect_type="auto_ascend", layer="self",
                    params={"free": True, **_ability_params(ability)})]
        self._add("sot: auto_ascend", _sot_auto_ascend)

        def _sot_bonus_actions(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if "acción" not in desc and "accion" not in desc: return None
            bonus = 1
            m = re.search(r'\+(\d+)\s*acci', desc)
            if m: bonus = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="start_of_turn", effect_type="bonus_actions", layer="self",
                    params={"count": bonus, **_ability_params(ability)})]
        self._add("sot: bonus_actions", _sot_bonus_actions)

        def _sot_free_link(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if "vínculo" not in desc or "gratis" not in desc: return None
            return [Modifier(source_card_id=cid, hook="start_of_turn", effect_type="free_link", layer="self",
                    params={**_ability_params(ability)})]
        self._add("sot: free_link", _sot_free_link)

        # COLOR/FORMATION: start_of_turn
        def _sot_heal_all(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if ("curar" in desc or "cura" in desc): return []
            return None
        self._add("sot: curar (color/form)", _sot_heal_all, is_active=True)

        def _sot_gain_seal(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "gana" in desc and "sello" in desc: return []
            return None
        self._add("sot: gana sello (color/form)", _sot_gain_seal, is_active=True)

        def _sot_shield(desc, ability, cid):
            if ability.trigger != "start_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "escudo" in desc: return []
            return None
        self._add("sot: escudo (color/form)", _sot_shield, is_active=True)

        # ═══════════════════════════════════════════════════════════════
        # END_OF_TURN passive patterns
        # ═══════════════════════════════════════════════════════════════

        def _eot_recover_hp(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if "recupera" not in desc or "hp" not in desc: return None
            heal = 1
            m = re.search(r'recupera\s+(\d+)\s*hp', desc)
            if m: heal = int(m.group(1))
            scope = "squad" if "todas" in desc else "self"
            return [Modifier(source_card_id=cid, hook="end_of_turn", effect_type="recover_hp", layer="self",
                    params={"amount": heal, "scope": scope, **_ability_params(ability)})]
        self._add("eot: recover_hp", _eot_recover_hp)

        def _eot_recover_grave(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if "descarte" not in desc and "cementerio" not in desc: return None
            return [Modifier(source_card_id=cid, hook="end_of_turn", effect_type="recover_graveyard", layer="self",
                    params={**_ability_params(ability)})]
        self._add("eot: recover_graveyard", _eot_recover_grave)

        def _eot_break_link(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if "vínculo" not in desc: return None
            return [Modifier(source_card_id=cid, hook="end_of_turn", effect_type="break_enemy_link", layer="self",
                    params={"count": 1, **_ability_params(ability)})]
        self._add("eot: break_enemy_link", _eot_break_link)

        def _eot_bonus_seals(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if "sello" not in desc: return None
            bonus = 5
            m = re.search(r'\+(\d+)\s*sello', desc)
            if m: bonus = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="end_of_turn", effect_type="bonus_seals", layer="self",
                    params={"amount": bonus, **_ability_params(ability)})]
        self._add("eot: bonus_seals", _eot_bonus_seals)

        # COLOR/FORMATION: end_of_turn
        def _eot_color_seal(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "sello" in desc: return []
            return None
        self._add("eot: sello (color/form)", _eot_color_seal, is_active=True)

        def _eot_color_link(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "vínculo" in desc: return []
            return None
        self._add("eot: vínculo (color/form)", _eot_color_link, is_active=True)

        def _eot_color_autofobia(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "autofobia" in desc: return []
            return None
        self._add("eot: autofobia (color/form)", _eot_color_autofobia, is_active=True)

        def _eot_color_exact_link(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "exactamente" in desc and "vínculo" in desc: return []
            return None
        self._add("eot: exactamente vínculo (color/form)", _eot_color_exact_link, is_active=True)

        def _eot_color_roba_link(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "roba" in desc and "vínculo" in desc: return []
            return None
        self._add("eot: roba vínculo (color/form)", _eot_color_roba_link, is_active=True)

        def _eot_logistron_break(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "logistrón" in desc and "rompe" in desc: return []
            return None
        self._add("eot: logistrón rompe (color/form)", _eot_logistron_break, is_active=True)

        def _eot_node_break(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "nodo enemigo" in desc: return []
            return None
        self._add("eot: nodo enemigo (color/form)", _eot_node_break, is_active=True)

        def _eot_inflict_damage(desc, ability, cid):
            if ability.trigger != "end_of_turn": return None
            if ability.ability_type.name not in ("COLOR", "FORMATION"): return None
            if "inflige" in desc and "daño" in desc: return []
            return None
        self._add("eot: inflige daño (color/form)", _eot_inflict_damage, is_active=True)

        # ═══════════════════════════════════════════════════════════════
        # ON_KILL passive patterns
        # ═══════════════════════════════════════════════════════════════

        def _ok_gain_hp(desc, ability, cid):
            if ability.trigger != "on_kill": return None
            if "gana" not in desc or "hp" not in desc: return None
            hp_bonus = 1
            m = re.search(r'\+(\d+)\s*hp', desc)
            if m: hp_bonus = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_kill", effect_type="gain_hp_on_kill", layer="self",
                    params={"amount": hp_bonus})]
        self._add("on_kill: gain_hp", _ok_gain_hp)

        def _ok_enemy_seal_loss(desc, ability, cid):
            if ability.trigger != "on_kill": return None
            if "pierde" not in desc or "sello" not in desc: return None
            seal_loss = 2
            m = re.search(r'pierde\s+(\d+)\s+sello', desc)
            if m: seal_loss = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_kill", effect_type="enemy_seal_loss_on_kill", layer="self",
                    params={"amount": seal_loss})]
        self._add("on_kill: enemy_seal_loss", _ok_enemy_seal_loss)

        def _ok_draw(desc, ability, cid):
            if ability.trigger != "on_kill": return None
            if "roba" not in desc: return None
            return [Modifier(source_card_id=cid, hook="on_kill", effect_type="draw_on_kill", layer="self",
                    params={"count": 1})]
        self._add("on_kill: draw", _ok_draw)

        # ═══════════════════════════════════════════════════════════════
        # ON_ENTER passive patterns
        # ═══════════════════════════════════════════════════════════════

        def _oe_vanguardia(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "vanguardia" not in desc: return None
            m = re.search(r'[Ll](\d)', desc)
            layer = int(m.group(1)) if m else 2
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="vanguard_entry", layer="self",
                    params={"layer": layer})]
        self._add("on_enter: vanguardia", _oe_vanguardia)

        def _oe_linea_fuego(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "línea de fuego" not in desc and "linea de fuego" not in desc: return None
            m = re.search(r'[Ll](\d)', desc)
            layer = int(m.group(1)) if m else 3
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="vanguard_entry", layer="self",
                    params={"layer": layer})]
        self._add("on_enter: línea de fuego", _oe_linea_fuego)

        def _oe_draw(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if ("roba" not in desc and "robo" not in desc) or "control" in desc or "vínculo" in desc: return None
            count = 1
            m = re.search(r'roba\s+(\d+)', desc)
            if m: count = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="draw", layer="self",
                    params={"count": count})]
        self._add("on_enter: draw", _oe_draw)

        def _oe_scry(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "mira" not in desc and "scry" not in desc: return None
            count = 2
            m = re.search(r'(?:mira|scry)\s+(\d+)', desc)
            if m: count = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="scry", layer="self",
                    params={"count": count})]
        self._add("on_enter: scry", _oe_scry)

        def _oe_heal(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "hp" not in desc: return None
            if not any(w in desc for w in ["recupera", "gana", "+"]): return None
            amount = 1
            m = re.search(r'\+(\d+)\s*hp', desc) or re.search(r'recupera\s+(\d+)\s*hp', desc)
            if m: amount = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="heal_ally", layer="self",
                    params={"amount": amount})]
        self._add("on_enter: heal_ally", _oe_heal)

        def _oe_gain_seals(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if not any(w in desc for w in ["sello", "sellos"]): return None
            amount = 1
            m = re.search(r'\+(\d+)\s*sello', desc) or re.search(r'gana\s+(\d+)\s+sello', desc)
            if m: amount = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="gain_seals", layer="self",
                    params={"amount": amount})]
        self._add("on_enter: gain_seals", _oe_gain_seals)

        def _oe_move_self(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "muévete" not in desc and not ("mueve" in desc and "meridiano" in desc): return None
            dist = 1
            m = re.search(r'mu[eé]vete?\s+(\d+)\s+meridiano', desc)
            if m: dist = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="move_self", layer="self",
                    params={"distance": dist})]
        self._add("on_enter: move_self", _oe_move_self)

        def _oe_move_ally(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "mueve" not in desc or "carta" not in desc: return None
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="move_ally", layer="self",
                    params={"distance": 1})]
        self._add("on_enter: move_ally", _oe_move_ally)

        def _oe_ascend_ally(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "asciende" not in desc and "ascender" not in desc: return None
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="ascend_ally", layer="self",
                    params={"free": True})]
        self._add("on_enter: ascend_ally", _oe_ascend_ally)

        def _oe_break_link(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if not ("rompe" in desc or "romper" in desc) or "vínculo" not in desc: return None
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="break_link", layer="self",
                    params={"count": 1})]
        self._add("on_enter: break_link", _oe_break_link)

        def _oe_auto_link(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "vinc" not in desc or not ("adyacente" in desc or "sin costo" in desc): return None
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="auto_link", layer="self",
                    params={"free": True})]
        self._add("on_enter: auto_link", _oe_auto_link)

        def _oe_discard(desc, ability, cid):
            if ability.trigger != "on_enter": return None
            if "descarta" not in desc: return None
            count = 1
            m = re.search(r'descarta\s+(\d+)', desc)
            if m: count = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_enter", effect_type="discard", layer="self",
                    params={"count": count})]
        self._add("on_enter: discard", _oe_discard)

        # ═══════════════════════════════════════════════════════════════
        # ON_ATTACK passive patterns
        # ═══════════════════════════════════════════════════════════════

        def _oa_ignore_armor(desc, ability, cid):
            if ability.trigger != "on_attack": return None
            if "ignora" not in desc or not any(w in desc for w in ["armadura", "defensa"]): return None
            amount = 1
            m = re.search(r'ignora\s+(\d+)', desc)
            if m: amount = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_attack", effect_type="ignore_armor", layer="self",
                    params={"amount": amount})]
        self._add("on_attack: ignore_armor", _oa_ignore_armor)

        def _oa_double_damage(desc, ability, cid):
            if ability.trigger != "on_attack": return None
            if "duplicado" not in desc or "daño" not in desc: return None
            return [Modifier(source_card_id=cid, hook="on_attack", effect_type="double_damage", layer="self")]
        self._add("on_attack: double_damage", _oa_double_damage)

        def _oa_bonus_vs_nodes(desc, ability, cid):
            if ability.trigger != "on_attack": return None
            if "nodo" not in desc or not any(w in desc for w in ["+", "extra", "adicional"]): return None
            bonus = 2
            m = re.search(r'\+(\d+)', desc)
            if m: bonus = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_attack", effect_type="bonus_vs_nodes", layer="self",
                    params={"delta": bonus})]
        self._add("on_attack: bonus_vs_nodes", _oa_bonus_vs_nodes)

        def _oa_bonus_vs_high_hp(desc, ability, cid):
            if ability.trigger != "on_attack": return None
            if "hp" not in desc or ">=" not in desc: return None
            bonus = 1
            m = re.search(r'\+(\d+)\s*daño', desc)
            if m: bonus = int(m.group(1))
            hp_threshold = 5
            m2 = re.search(r'hp\s*>=\s*(\d+)', desc)
            if m2: hp_threshold = int(m2.group(1))
            return [Modifier(source_card_id=cid, hook="on_attack", effect_type="bonus_vs_high_hp", layer="self",
                    params={"delta": bonus, "hp_threshold": hp_threshold})]
        self._add("on_attack: bonus_vs_high_hp", _oa_bonus_vs_high_hp)

        def _oa_bonus_per_link(desc, ability, cid):
            if ability.trigger != "on_attack": return None
            if "vínculo" not in desc or not any(w in desc for w in ["+", "extra"]): return None
            max_bonus = 3
            m = re.search(r'máx\s*\+?(\d+)', desc) or re.search(r'max\s*\+?(\d+)', desc)
            if m: max_bonus = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_attack", effect_type="bonus_per_link", layer="self",
                    params={"max": max_bonus})]
        self._add("on_attack: bonus_per_link", _oa_bonus_per_link)

        def _oa_bonus_vs_grimoire(desc, ability, cid):
            if ability.trigger != "on_attack": return None
            if "grimorio" not in desc or not any(w in desc for w in ["+", "extra"]): return None
            bonus = 4
            m = re.search(r'\+(\d+)', desc)
            if m: bonus = int(m.group(1))
            return [Modifier(source_card_id=cid, hook="on_attack", effect_type="bonus_vs_grimoire", layer="self",
                    params={"delta": bonus})]
        self._add("on_attack: bonus_vs_grimoire", _oa_bonus_vs_grimoire)

        # ═══════════════════════════════════════════════════════════════
        # TRIGGER-AGNOSTIC patterns (fire regardless of ability.trigger)
        # ═══════════════════════════════════════════════════════════════

        # --- modify_squad ---

        def _ms_ignore_color(desc, ability, cid):
            if "no cuenta para la mayoría de color" not in desc: return None
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="ignore_color", layer="self",
                    params={"condition": cond} if cond else {})]
        self._add("modify_squad: ignore_color", _ms_ignore_color)

        def _ms_ignore_formation(desc, ability, cid):
            if "ignoran restricciones de formación" not in desc: return None
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="ignore_formation",
                    params={"formation": ability.formation_required or "any",
                            "color": ability.color_required.value if ability.color_required else "any"},
                    layer="squad")]
        self._add("modify_squad: ignore_formation", _ms_ignore_formation)

        def _ms_reduce_distance(desc, ability, cid):
            if "reducen" not in desc or "distancia" not in desc or "potenciamiento" not in desc: return None
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="reduce_potenciamiento_distance",
                    layer="network", params={"delta": -1})]
        self._add("modify_squad: reduce_potenciamiento_distance", _ms_reduce_distance)

        def _ms_ignore_polygon(desc, ability, cid):
            if "sin formar polígonos" not in desc or "vincularse" not in desc: return None
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="ignore_polygon_requirement",
                    layer="self")]
        self._add("modify_squad: ignore_polygon", _ms_ignore_polygon)

        def _ms_logistron_mult(desc, ability, cid):
            if "cuenta como" not in desc or "logistron" not in desc: return None
            try:
                m = re.search(r'cuenta como (\d+)', desc)
                count = int(m.group(1)) if m else 2
            except:
                count = 2
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="logistron_multiplier",
                    layer="self", params={"multiplier": count})]
        self._add("modify_squad: logistron_multiplier", _ms_logistron_mult)

        def _ms_formation_restrict(desc, ability, cid):
            if "no puede formar" in desc:
                shape = "triángulo" if "triángulo" in desc or "triangulo" in desc else "any"
                return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="formation_restriction",
                        layer="self", params={"cannot_form": shape})]
            if "solo puede formar" in desc:
                shape = "pentágono" if "pentágono" in desc or "pentagono" in desc else "any"
                return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="formation_restriction",
                        layer="self", params={"only_form": shape})]
            return None
        self._add("modify_squad: formation_restriction", _ms_formation_restrict)

        def _ms_caudillismo(desc, ability, cid):
            if "caudillismo" not in desc or "activos" not in desc: return None
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="caudillismo_always_active",
                    layer="network", params={"condition": cond} if cond else {})]
        self._add("modify_squad: caudillismo_always_active", _ms_caudillismo)

        def _ms_all_color_abilities(desc, ability, cid):
            if "todas las habilidades de color" not in desc or "activas" not in desc: return None
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="all_color_abilities_active",
                    layer="network", params={"condition": cond} if cond else {})]
        self._add("modify_squad: all_color_abilities_active", _ms_all_color_abilities)

        def _ms_all_colors(desc, ability, cid):
            if "cuenta como todos los colores" not in desc: return None
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="all_colors", layer="self")]
        self._add("modify_squad: all_colors", _ms_all_colors)

        def _ms_bonus_formation(desc, ability, cid):
            if "potenciamiento adicional" not in desc: return None
            bonus = 2
            m = re.search(r'\+(\d+)\s*de\s*potenciamiento', desc)
            if m: bonus = int(m.group(1))
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="bonus_formation_power",
                    layer="network", params={"bonus": bonus, "condition": cond} if cond else {"bonus": bonus})]
        self._add("modify_squad: bonus_formation_power", _ms_bonus_formation)

        def _ms_vitality_bonus(desc, ability, cid):
            if "gana" not in desc or "v" not in desc or "permanente" not in desc: return None
            m = re.search(r'\+(\d+)\s*v\b', desc)
            bonus = int(m.group(1)) if m else 1
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_squad", effect_type="vitality_bonus",
                    layer="network", params={"bonus": bonus, "condition": cond} if cond else {"bonus": bonus})]
        self._add("modify_squad: vitality_bonus", _ms_vitality_bonus)

        # --- modify_hp ---
        def _mh_hp_bonus(desc, ability, cid):
            if "gana" not in desc or "hp" not in desc or "permanente" not in desc: return None
            m = re.search(r'\+(\d+)\s*hp', desc)
            hp_bonus = int(m.group(1)) if m else 1
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_hp", effect_type="hp_bonus",
                    layer="network", params={"bonus": hp_bonus, "condition": cond} if cond else {"bonus": hp_bonus})]
        self._add("modify_hp: hp_bonus", _mh_hp_bonus)

        # --- before_attack ---
        def _ba_cannot_be_attacked(desc, ability, cid):
            if "sigilo" not in desc or "no puede ser atacado" not in desc: return None
            return [Modifier(source_card_id=cid, hook="before_attack", effect_type="cannot_be_attacked", layer="self")]
        self._add("before_attack: cannot_be_attacked (sigilo)", _ba_cannot_be_attacked)

        def _ba_sigilo_conditional(desc, ability, cid):
            cond = _extract_condition(desc)
            if not cond: return None
            if "sigilo" not in desc: return None
            return [Modifier(source_card_id=cid, hook="before_attack", effect_type="cannot_be_attacked",
                    layer="self", params={"condition": cond})]
        self._add("before_attack: sigilo conditional", _ba_sigilo_conditional)

        # --- modify_damage ---
        def _md_damage_bonus(desc, ability, cid):
            if "defensa" in desc: return None
            m = re.search(r'gana\s+\+(\d+)\s*[dD]\b', desc)
            if not m:
                m = re.search(r'\+(\d+)\s*[dD]\b', desc)
            if not m: return None
            if ability.trigger not in ("permanent",): return None
            delta = int(m.group(1))
            if "defensa" in desc[max(0, m.start()-20):m.end()+20]: return None
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_damage", effect_type="damage_bonus", layer="self",
                    params={"delta": delta, "condition": cond} if cond else {"delta": delta})]
        self._add("modify_damage: damage_bonus", _md_damage_bonus)

        def _md_damage_bonus_expanded(desc, ability, cid):
            m = re.search(r'(?:gana|ganan)\s+\+(\d+)\s*(?:al\s*)?(?:daño|d\b)', desc)
            if not m: return None
            if "defensa" in desc: return None
            delta = int(m.group(1))
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="modify_damage", effect_type="damage_bonus", layer="network",
                    params={"delta": delta, "condition": cond} if cond else {"delta": delta})]
        self._add("modify_damage: damage_bonus (expanded)", _md_damage_bonus_expanded)

        # --- grimoire_defense ---
        def _gd_max_seal_loss(desc, ability, cid):
            m = re.search(r'no pierde más de (\d+)', desc)
            if not m: return None
            cap = int(m.group(1))
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="grimoire_defense", effect_type="max_seal_loss", layer="self",
                    params={"max": cap, "condition": cond} if cond else {"max": cap})]
        self._add("grimoire_defense: max_seal_loss", _gd_max_seal_loss)

        def _gd_armor(desc, ability, cid):
            m = re.search(r'grimorio tiene \+(\d+) de defensa', desc)
            if not m: return None
            armor = int(m.group(1))
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="grimoire_defense", effect_type="grimoire_armor", layer="self",
                    params={"armor": armor, "condition": cond} if cond else {"armor": armor})]
        self._add("grimoire_defense: grimoire_armor", _gd_armor)

        def _gd_invulnerable(desc, ability, cid):
            if "grimorio invulnerable" not in desc: return None
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="grimoire_defense", effect_type="grimoire_invulnerable",
                    layer="self", params={"condition": cond} if cond else {})]
        self._add("grimoire_defense: invulnerable", _gd_invulnerable)

        # --- before_link ---
        def _bl_link_cost_zero(desc, ability, cid):
            if "vínculo gratis" in desc: return [Modifier(source_card_id=cid, hook="before_link", effect_type="link_cost_zero", layer="self")]
            if "vincular" in desc and "sin costo" in desc: return [Modifier(source_card_id=cid, hook="before_link", effect_type="link_cost_zero", layer="self")]
            if "vínculos no cuestan" in desc: return [Modifier(source_card_id=cid, hook="before_link", effect_type="link_cost_zero", layer="self")]
            if "cuesta 0 vincular" in desc: return [Modifier(source_card_id=cid, hook="before_link", effect_type="link_cost_zero", layer="self")]
            return None
        self._add("before_link: link_cost_zero", _bl_link_cost_zero)

        def _bl_link_cost_zero_expanded(desc, ability, cid):
            if ("vínculo" not in desc and "vinculo" not in desc): return None
            if not re.search(r'cuestan?\s+0\s+acciones', desc): return None
            return [Modifier(source_card_id=cid, hook="before_link", effect_type="link_cost_zero", layer="self")]
        self._add("before_link: link_cost_zero (expanded)", _bl_link_cost_zero_expanded)

        def _bl_cannot_link(desc, ability, cid):
            if "no puede vincularse" not in desc: return None
            return [Modifier(source_card_id=cid, hook="before_link", effect_type="cannot_link", layer="self")]
        self._add("before_link: cannot_link", _bl_cannot_link)

        def _bl_link_armor(desc, ability, cid):
            if "armadura" not in desc: return None
            if "vínculo" not in desc and "vinculo" not in desc: return None
            amount = 1
            m = re.search(r'\+(\d+)\s*(?:de\s*)?armadura', desc)
            if m: amount = int(m.group(1))
            scope = "own" if "~" in desc or "sus vínculos" in desc else "link"
            return [Modifier(source_card_id=cid, hook="before_link", effect_type="link_armor_bonus", layer="self",
                    params={"amount": amount, "scope": scope})]
        self._add("before_link: link_armor_bonus", _bl_link_armor)

        # --- after_link ---
        def _al_draw_on_link(desc, ability, cid):
            if ("al ser vinculado" not in desc and "al vincular" not in desc): return None
            if "roba" not in desc: return None
            return [Modifier(source_card_id=cid, hook="after_link", effect_type="draw_on_link", layer="self")]
        self._add("after_link: draw_on_link", _al_draw_on_link)

        # --- before_destroy ---
        def _bd_destroy_immunity(desc, ability, cid):
            if "inmune a destrucción" not in desc and "indestructible" not in desc: return None
            return [Modifier(source_card_id=cid, hook="before_destroy", effect_type="destroy_immunity", layer="self")]
        self._add("before_destroy: destroy_immunity", _bd_destroy_immunity)

        def _bd_link_protection(desc, ability, cid):
            if "vínculo" not in desc or "no pueden ser destruidos" not in desc: return None
            return [Modifier(source_card_id=cid, hook="before_destroy", effect_type="link_protection", layer="self")]
        self._add("before_destroy: link_protection", _bd_link_protection)

        # --- after_destroy ---
        def _ad_transfer_links(desc, ability, cid):
            if "transfiere" not in desc or "vínculo" not in desc: return None
            return [Modifier(source_card_id=cid, hook="after_destroy", effect_type="transfer_links", layer="self")]
        self._add("after_destroy: transfer_links", _ad_transfer_links)

        # --- on_ascend ---
        def _as_cannot_ascend(desc, ability, cid):
            if "no puede ascender" not in desc and "ni ascender" not in desc: return None
            return [Modifier(source_card_id=cid, hook="on_ascend", effect_type="cannot_ascend", layer="self")]
        self._add("on_ascend: cannot_ascend", _as_cannot_ascend)

        def _as_free_ascend(desc, ability, cid):
            if "ascensos" not in desc or "cuestan 0" not in desc: return None
            cond = _extract_condition(desc)
            return [Modifier(source_card_id=cid, hook="on_ascend", effect_type="free_ascend", layer="network",
                    params={"condition": cond} if cond else {})]
        self._add("on_ascend: free_ascend", _as_free_ascend)

        # --- on_move ---
        def _om_cannot_move(desc, ability, cid):
            if not ("no puede moverse" in desc or "no puede ser movido" in desc
                    or "ni ser movido" in desc or "ser movida" in desc): return None
            return [Modifier(source_card_id=cid, hook="on_move", effect_type="cannot_move", layer="self")]
        self._add("on_move: cannot_move", _om_cannot_move)

        # --- guardaespaldas ---
        def _gd_damage_redirect(desc, ability, cid):
            if "guardaespaldas" not in desc: return None
            if "grimorio" in desc:
                amount = 3
                m = re.search(r'hasta\s+(\d+)', desc)
                if m: amount = int(m.group(1))
                return [Modifier(source_card_id=cid, hook="grimoire_defense", effect_type="grimoire_damage_redirect",
                        layer="self", params={"max": amount})]
            else:
                color_filter = None
                for col in ["sellador", "político", "militar", "guerrillero", "naturaleza", "logistrón"]:
                    if col in desc: color_filter = col; break
                return [Modifier(source_card_id=cid, hook="modify_damage", effect_type="damage_redirect",
                        layer="self", params={"color": color_filter} if color_filter else {})]
        self._add("guardaespaldas: damage_redirect", _gd_damage_redirect)

        # --- before_play ---
        def _bp_cost_reduction(desc, ability, cid):
            if "meridiano" not in desc or "cuestan 0" not in desc: return None
            return [Modifier(source_card_id=cid, hook="before_play", effect_type="cost_reduction_meridian", layer="self")]
        self._add("before_play: cost_reduction_meridian", _bp_cost_reduction)

        # --- on_attack (color/form) always return implemented ---
        def _oa_color_always(desc, ability, cid):
            if ability.trigger != "on_attack": return None
            return []  # generic on_attack, always marked implemented
        self._add("on_attack: generic (color/form)", _oa_color_always, is_active=True)

        # --- Caudillismo on_ascend (status entry) ---
        def _as_caudillismo(desc, ability, cid):
            if ability.trigger != "on_ascend": return None
            if "caudillismo" in desc or "vínculo gratis" in desc: return []
            return None
        self._add("on_ascend: caudillismo (status)", _as_caudillismo, is_active=True)

        # --- Permanent status entries (match keyword packs from old status function) ---
        # These are already covered by the trigger-agnostic patterns above.
        # Adding explicit status entries for patterns that the parser doesn't handle
        # but the old status function marked as implemented.

        def _perm_global_d_buff(desc, ability, cid):
            if ability.trigger != "permanent": return None
            if "todas las cartas" in desc and "ganan" in desc:
                if "hp" in desc or "d" in desc: return []
            return None
        self._add("permanent: global buff", _perm_global_d_buff, is_active=True)

        def _perm_cannot_ascend_regen(desc, ability, cid):
            if ability.trigger != "permanent": return None
            if "no puede ascender" in desc and "regenera" in desc: return []
            return None
        self._add("permanent: cannot_ascend_regen", _perm_cannot_ascend_regen, is_active=True)

        print(f"[AbilityRegistry] Registered {len(self._patterns)} patterns")


# Singleton instance for the engine
_registry: Optional[AbilityRegistry] = None


def get_registry() -> AbilityRegistry:
    global _registry
    if _registry is None:
        _registry = AbilityRegistry()
    return _registry
