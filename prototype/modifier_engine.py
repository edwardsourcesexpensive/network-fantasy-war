"""Modifier Engine extracted from GameState (grilling Candidate 1).

ADR-002's hook-based dispatch system, consolidated into a single dataclass.
Owns the _modifiers dict and all registration/dispatch/cleanup/condition logic.
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .game import GameState
    from .card import CardInstance
    from .network import Squad
from .card import Color
from .modifier import Modifier
from .ability_registry import get_registry
from .enums import Phase


class ModifierEngine:
    """Owns the modifier lifecycle: register → dispatch → cleanup.

    Usage:
        game.modifiers.register(card)
        game.modifiers.dispatch_card_hook("on_enter", game, card, player=player)
        game.modifiers.dispatch_squad_hook("start_of_turn", game)
        game.modifiers.cleanup()
    """

    def __init__(self):
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

    # ═══════════════════════════════════════════════════════════════
    # Registration
    # ═══════════════════════════════════════════════════════════════

    def register(self, game: GameState, card):
        """Parse a card's abilities into Modifier objects and register them."""
        for ability in card.definition.abilities:
            if ability.trigger not in ("permanent", "on_enter", "start_of_turn",
                                        "end_of_turn", "on_kill"):
                continue
            modifiers = get_registry().parse(ability, card)
            for mod in modifiers:
                if mod.hook in self._modifiers:
                    self._modifiers[mod.hook].append(mod)
                    game._log(f"  [mod] {card.definition.name}: +{mod.effect_type} on {mod.hook}")

    def unregister(self, game: GameState, card_id: int):
        """Remove all modifiers belonging to a card (when it leaves the board)."""
        for hook_name, hook_list in self._modifiers.items():
            before = len(hook_list)
            hook_list[:] = [m for m in hook_list if m.source_card_id != card_id]
            removed = before - len(hook_list)
            if removed:
                game._log(f"  [mod] card#{card_id}: -{removed} modifiers from {hook_name}")

    def register_temp(self, mod: Modifier):
        """Register a temporary modifier (cleaned in cleanup())."""
        mod.is_temporary = True
        if mod.hook in self._modifiers:
            self._modifiers[mod.hook].append(mod)

    def cleanup(self):
        """Remove all temporary modifiers (called in exit_phase)."""
        for hook_list in self._modifiers.values():
            hook_list[:] = [m for m in hook_list if not m.is_temporary]

    # ═══════════════════════════════════════════════════════════════
    # Color helpers
    # ═══════════════════════════════════════════════════════════════

    def get_color_overrides(self, game: GameState) -> dict[int, Color]:
        """Merge _temp_colors with modifier-based color overrides."""
        overrides = dict(game._temp_colors)
        for mod in self._modifiers.get("modify_squad", []):
            if mod.effect_type == "color_override":
                overrides[mod.source_card_id] = mod.params["color"]
        return overrides

    def get_effective_squad_color(self, game: GameState, card, squad) -> Optional[Color]:
        """Get the effective squad color for COLOR ability checks.

        If the squad contains at least one Alquimista, each card uses its own
        printed color instead of the squad's dominant color (§9.3).
        """
        for cid in squad.members:
            member = game.all_cards.get(cid)
            if member and member.definition.color == Color.ALQUIMISTA:
                return card.definition.color
        return squad.get_dominant_color(self.get_color_overrides(game))

    # ═══════════════════════════════════════════════════════════════
    # Condition evaluation
    # ═══════════════════════════════════════════════════════════════

    def evaluate_condition(self, game: GameState, condition: dict, source) -> bool:
        """Evaluate a modifier condition against current game state."""
        if not condition:
            return True

        ctype = condition.get("type")

        if ctype == "layer":
            if not source.position or source.position[0] == -1:
                return False
            return source.position[1] == condition.get("value", 1)

        if ctype == "frontier":
            return source.position and source.position[0] == -1

        if ctype == "formation":
            shape = condition.get("shape", "triangle")
            squads = game.get_player_squads(source.owner)
            for sq in squads:
                if source.card_id in sq.members and sq.squad_type.replace("_ampliado", "") == shape:
                    return True
            return False

        if ctype == "links":
            count = game.network.link_count(source)
            return count >= condition.get("min", 1)

        if ctype == "damaged_this_turn":
            return getattr(source, '_damaged_this_turn', False)

        if ctype == "once_per_game":
            used = condition.get("used_set", set())
            return source.card_id not in used

        return True

    # ═══════════════════════════════════════════════════════════════
    # Dispatch: card-aware hooks
    # ═══════════════════════════════════════════════════════════════

    def dispatch_card_hook(self, hook_name: str, game: GameState,
                           card, **context) -> Optional[str]:
        """Dispatch a card-specific hook (on_enter, on_ascend, on_move, before/after_link).

        Returns None (success) or an error string if the hook blocks the action.
        """
        for mod in self._modifiers.get(hook_name, []):
            # Most card hooks filter by source_card_id
            if mod.source_card_id != card.card_id:
                continue

            if hook_name == "on_enter":
                if mod.effect_type == "vanguard_entry":
                    continue  # declarative, handled by placement
                self._apply_on_enter(game, mod, card, context.get("player", card.owner))

            elif hook_name == "on_ascend":
                if mod.effect_type == "cannot_ascend":
                    return f"{card.definition.name} no puede ascender."

            elif hook_name == "on_move":
                if mod.effect_type == "cannot_move":
                    return f"{card.definition.name} no puede ser movido."

            elif hook_name == "before_link":
                source_card = game.all_cards.get(mod.source_card_id)
                if not source_card:
                    continue
                if mod.effect_type == "link_cost_zero":
                    pass  # handled in link_cards
                if mod.effect_type == "cannot_link":
                    if mod.source_card_id in (card.card_id, context.get("other_id", -1)):
                        return f"{source_card.definition.name} no puede vincularse."

            elif hook_name == "after_link":
                source_card = game.all_cards.get(mod.source_card_id)
                if not source_card or source_card.owner != context.get("player"):
                    continue
                if mod.source_card_id not in (card.card_id, context.get("other_id", -1)):
                    continue
                if mod.effect_type == "draw_on_link":
                    extra = game._draw_card(context.get("player", card.owner))
                    if extra:
                        game._log(f"  {source_card.definition.name}: +1 robo por vínculo")

            elif hook_name == "after_play":
                source_card = game.all_cards.get(mod.source_card_id)
                if not source_card or source_card.owner != context.get("player", card.owner):
                    continue
                if mod.effect_type == "draw_on_play" and mod.source_card_id != card.card_id:
                    pass  # Reserved

            elif hook_name == "before_destroy":
                if mod.effect_type == "destroy_immunity":
                    return "immune"

            elif hook_name == "after_destroy":
                pass  # handled by _destroy_card

            else:
                # Generic: try _apply_trigger_modifier
                self._apply_trigger_modifier(game, mod, card,
                                             context.get("squad"),
                                             context.get("all_squads", []))

        return None

    # ═══════════════════════════════════════════════════════════════
    # Dispatch: squad-aware hooks (start_of_turn, end_of_turn, on_kill)
    # ═══════════════════════════════════════════════════════════════

    def dispatch_squad_hook(self, hook_name: str, game: GameState):
        """Dispatch start_of_turn or end_of_turn modifiers.

        Iterates all modifiers for the hook, finds the source card's squad,
        checks color/formation requirements, and applies the effect.
        """
        player = game.active_player
        squads = game.network.find_squads(game.all_cards)

        for mod in self._modifiers.get(hook_name, []):
            if mod.is_temporary:
                continue
            card = game.all_cards.get(mod.source_card_id)
            if not card or card.owner != player or not card.position or card.position[0] == -1:
                continue
            card_squad = None
            for sq in squads:
                if card.card_id in sq.members:
                    card_squad = sq
                    break
            if not card_squad:
                continue
            params = mod.params
            if params.get("ability_type") == "COLOR":
                req_color = params.get("color_required")
                if req_color and self.get_effective_squad_color(game, card, card_squad).value != req_color:
                    continue
            if params.get("ability_type") == "FORMATION":
                req_form = params.get("formation_required")
                if req_form and card_squad.squad_type.replace("_ampliado", "") != req_form:
                    continue
            self._apply_trigger_modifier(game, mod, card, card_squad, squads)

    # ═══════════════════════════════════════════════════════════════
    # Convenience accessors (for dispatch sites that need raw iteration)
    # ═══════════════════════════════════════════════════════════════

    def get(self, hook_name: str) -> list[Modifier]:
        """Get all modifiers registered for a hook (for raw iteration)."""
        return self._modifiers.get(hook_name, [])

    def apply_modify_squad(self, game: GameState, source_card, result_squads):
        """Apply modify_squad modifiers (ignore_color, etc.) to a squad list."""
        for mod in self._modifiers.get("modify_squad", []):
            if mod.effect_type == "ignore_color":
                if not source_card or source_card.owner != game.active_player:
                    continue
                for squad in result_squads:
                    if mod.source_card_id in squad.members:
                        squad.ignored_color_cards.add(mod.source_card_id)
                        break

    # ═══════════════════════════════════════════════════════════════
    # Application: trigger effects
    # ═══════════════════════════════════════════════════════════════

    def _apply_trigger_modifier(self, game: GameState, mod: Modifier, card,
                                 squad, all_squads: list):
        """Execute a start_of_turn, end_of_turn, or on_kill modifier effect."""
        effect_type = mod.effect_type
        params = mod.params
        player = card.owner

        if effect_type == "draw":
            count = params.get("count", 1)
            total = 0
            for _ in range(count):
                drawn = game._draw_card(player)
                if drawn:
                    total += 1
            game._log(f"  {card.definition.name}: +{total} robo(s)")

        elif effect_type == "scry":
            count = params.get("count", 2)
            top_cards = game.decks[player][-count:] if len(game.decks[player]) >= count else game.decks[player][:]
            names = [c.definition.name for c in reversed(top_cards)]
            game._log(f"  {card.definition.name}: mira top {len(names)}: {', '.join(names)}")

        elif effect_type == "auto_ascend":
            target = card
            for cid in squad.members:
                c = game.all_cards.get(cid)
                if c and c.position and c.position[1] < 3 and c.position[0] != -1:
                    target = c
                    break
            err = game.ascend(player, target, free=True)
            if not err:
                game._log(f"  {card.definition.name}: asciende {target.definition.name} sin costo")

        elif effect_type == "bonus_actions":
            bonus = params.get("count", 1)
            game.actions_remaining += bonus
            game._log(f"  {card.definition.name}: +{bonus} acción(es) ({game.actions_remaining})")

        elif effect_type == "free_link":
            members = [game.all_cards.get(cid) for cid in squad.members
                      if game.all_cards.get(cid) and game.all_cards[cid].owner == player]
            linked = False
            for i, ca in enumerate(members):
                for cb in members[i+1:]:
                    if ca and cb and not game.network.has_link(ca, cb) and game.network.can_link(ca) and game.network.can_link(cb):
                        game.network.add_link(ca, cb)
                        game._log(f"  {card.definition.name}: vínculo gratis {ca.definition.name} <-> {cb.definition.name}")
                        linked = True
                        break
                if linked:
                    break

        elif effect_type == "recover_hp":
            amount = params.get("amount", 1)
            if params.get("scope") == "squad":
                for cid in squad.members:
                    c = game.all_cards.get(cid)
                    if c and c.owner == player:
                        c.current_hp = min(c.current_hp + amount, c.definition.hp)
                game._log(f"  {card.definition.name}: +{amount} HP a todo el escuadrón")
            else:
                card.current_hp = min(card.current_hp + amount, card.definition.hp)
                game._log(f"  {card.definition.name}: recupera {amount} HP ({card.current_hp}/{card.definition.hp})")

        elif effect_type == "recover_graveyard":
            if game.discard_piles[player]:
                recovered = game.discard_piles[player].pop()
                game.hands[player].append(recovered)
                game._log(f"  {card.definition.name}: recupera {recovered.definition.name} del cementerio")

        elif effect_type == "break_enemy_link":
            game._log(f"  {card.definition.name}: +{params.get('count', 1)} vínculo enemigo destruible")

        elif effect_type == "bonus_seals":
            amount = params.get("amount", 5)
            game.seals[player] += amount
            game._log(f"  {card.definition.name}: +{amount} sellos ({game.seals[player]})")

    def _apply_on_enter(self, game: GameState, mod: Modifier, card, player: int):
        """Execute an on_enter modifier effect when a card is played."""
        effect_type = mod.effect_type
        params = mod.params

        if effect_type == "draw":
            count = params.get("count", 1)
            total = 0
            for _ in range(count):
                drawn = game._draw_card(player)
                if drawn:
                    total += 1
            game._log(f"  {card.definition.name} (on_enter): +{total} robo(s)")

        elif effect_type == "scry":
            count = params.get("count", 2)
            top_cards = game.decks[player][-count:] if len(game.decks[player]) >= count else game.decks[player][:]
            names = [c.definition.name for c in reversed(top_cards)]
            game._log(f"  {card.definition.name} (on_enter): mira top {len(names)}: {', '.join(names)}")

        elif effect_type == "heal_ally":
            amount = params.get("amount", 1)
            card.current_hp = min(card.current_hp + amount, card.definition.hp)
            game._log(f"  {card.definition.name} (on_enter): +{amount} HP ({card.current_hp}/{card.definition.hp})")

        elif effect_type == "gain_seals":
            amount = params.get("amount", 1)
            game.seals[player] += amount
            game._log(f"  {card.definition.name} (on_enter): +{amount} sellos ({game.seals[player]})")

        elif effect_type == "move_self":
            dist = params.get("distance", 1)
            if card.position:
                p, layer, meridian = card.position
                for direction in [1, -1]:
                    new_m = meridian + direction * dist
                    li = layer - 1
                    if 0 <= new_m < 15 and game.board.cells[p][li][new_m] is None:
                        game.board.cells[p][li][meridian] = None
                        game.board.cells[p][li][new_m] = card.card_id
                        card.position = (p, layer, new_m)
                        game._log(f"  {card.definition.name} (on_enter): se mueve a L{layer}:{new_m}")
                        break

        elif effect_type == "move_ally":
            game._log(f"  {card.definition.name} (on_enter): mueve carta aliada (pendiente selección UI)")

        elif effect_type == "ascend_ally":
            for cid in list(game.all_cards.keys()):
                ally = game.all_cards.get(cid)
                if (ally and ally.owner == player and ally.card_id != card.card_id
                        and ally.position and ally.position[1] < 3 and ally.position[0] != -1):
                    err = game.ascend(player, ally, free=True)
                    if not err:
                        game._log(f"  {card.definition.name} (on_enter): asciende {ally.definition.name} gratis")
                        break

        elif effect_type == "break_link":
            count = params.get("count", 1)
            enemy = 1 - player
            broken = 0
            for cid in list(game.all_cards.keys()):
                if broken >= count:
                    break
                enemy_card = game.all_cards.get(cid)
                if not enemy_card or enemy_card.owner != enemy or not enemy_card.position:
                    continue
                for linked_id in list(game.network.links.get(cid, set())):
                    if broken >= count:
                        break
                    linked = game.all_cards.get(linked_id)
                    if linked:
                        game.network.remove_link(enemy_card, linked)
                        broken += 1
                        game._log(f"  {card.definition.name} (on_enter): rompe vínculo {enemy_card.definition.name} <-> {linked.definition.name}")
                        break

        elif effect_type == "auto_link":
            if card.position:
                p, layer, meridian = card.position
                for dm in [-2, -1, 1, 2]:
                    for dl in [-1, 0, 1]:
                        check_m = meridian + dm
                        check_l = layer + dl
                        if 0 <= check_m < 15 and 1 <= check_l <= 3:
                            li = check_l - 1
                            neighbor_cid = game.board.cells[p][li][check_m]
                            if neighbor_cid and game.network.can_link(card):
                                neighbor = game.all_cards.get(neighbor_cid)
                                if neighbor:
                                    dist = game.board.spatial_distance(card.position, neighbor.position)
                                    if dist:
                                        game.network.add_link(card, neighbor)
                                        game._log(f"  {card.definition.name} (on_enter): vínculo gratis con {neighbor.definition.name}")
                                        return

        elif effect_type == "discard":
            count = params.get("count", 1)
            discarded = []
            for _ in range(count):
                if game.hands[player]:
                    dc = game.hands[player].pop()
                    game.discard_piles[player].append(dc)
                    discarded.append(dc.definition.name)
            game._log(f"  {card.definition.name} (on_enter): descarta {', '.join(discarded) if discarded else '(mano vacía)'}")
