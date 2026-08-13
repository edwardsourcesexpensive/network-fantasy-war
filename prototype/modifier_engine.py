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
            "permanent": [],
        }

    # ═══════════════════════════════════════════════════════════════
    # Registration
    # ═══════════════════════════════════════════════════════════════

    def register(self, game: GameState, card):
        """Parse a card's abilities into Modifier objects and register them."""
        for ability in card.definition.abilities:
            if ability.trigger not in ("permanent", "on_enter", "start_of_turn",
                                        "end_of_turn", "on_kill", "on_attack"):
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
            # Autofobia and similar self-targeting abilities don't require squad membership
            if not card_squad and mod.effect_type != "autofobia":
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
            # Evaluate positional/state condition (layer, formation shape, links, etc.)
            cond = params.get("condition")
            if cond and not self.evaluate_condition(game, cond, card):
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

        elif effect_type == "autofobia":
            # Autofobia: if card has no links at end of turn, it is destroyed
            if game.network.link_count(card) == 0:
                game._log(f"  {card.definition.name}: Autofobia — sin vínculos, se autodestruye")
                game._destroy_card(card)

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

    # ═══════════════════════════════════════════════════════════════
    # P1: Permanent passive effect handlers
    # ═══════════════════════════════════════════════════════════════

    def get_permanent_modifiers(self, hook_name: str) -> list[Modifier]:
        """Get permanent modifiers that route to a specific hook.
        
        Permanent abilities are registered with hook='permanent' but
        their effect_type determines which game system they interact with.
        This accessor lets dispatch sites query them by their target hook.
        """
        return [m for m in self._modifiers.get("permanent", []) 
                if m.params.get("target_hook") == hook_name]

    def has_permanent_effect(self, effect_type: str, card_id: int = None) -> bool:
        """Check if any permanent modifier with the given effect_type exists.
        
        If card_id is provided, only check modifiers from that card.
        """
        for mod in self._modifiers.get("permanent", []):
            if mod.effect_type != effect_type:
                continue
            if card_id is not None and mod.source_card_id != card_id:
                continue
            return True
        return False

    def get_permanent_effects(self, effect_type: str, card_id: int = None) -> list[Modifier]:
        """Get all permanent modifiers with the given effect_type."""
        results = []
        for mod in self._modifiers.get("permanent", []):
            if mod.effect_type != effect_type:
                continue
            if card_id is not None and mod.source_card_id != card_id:
                continue
            results.append(mod)
        return results

    def check_cannot_ascend(self, game: GameState, card) -> Optional[str]:
        """Check if a card cannot ascend due to permanent modifiers."""
        for mod in self._modifiers.get("on_ascend", []):
            if mod.source_card_id != card.card_id:
                continue
            if mod.effect_type == "cannot_ascend":
                return f"{card.definition.name} no puede ascender."
        return None

    def check_link_unbreakable(self, game: GameState, card_a, card_b) -> bool:
        """Check if a link is protected from being broken."""
        for mod in self._modifiers.get("before_link", []):
            if mod.effect_type != "link_unbreakable":
                continue
            # Check if either card is the source of this protection
            if mod.source_card_id in (card_a.card_id, card_b.card_id):
                return True
        return False

    def get_grimoire_defense_mods(self, game: GameState, defender: int) -> list[Modifier]:
        """Get all active grimoire_defense modifiers for a player."""
        results = []
        for mod in self._modifiers.get("grimoire_defense", []):
            source = game.all_cards.get(mod.source_card_id)
            if not source or source.owner != defender:
                continue
            if not source.position or source.position[0] == -1:
                continue
            results.append(mod)
        return results

    def apply_grimoire_defense(self, game: GameState, defender: int, 
                                net_damage: int, attack_type: str = "normal") -> tuple[int, Optional[str]]:
        """Apply grimoire_defense modifiers to reduce/cancel damage.
        
        Returns (modified_damage, cancel_reason).
        cancel_reason is None if attack proceeds, or a string if cancelled.
        """
        for mod in self.get_grimoire_defense_mods(game, defender):
            source = game.all_cards.get(mod.source_card_id)
            if not source:
                continue
                
            if mod.effect_type == "max_seal_loss":
                cap = mod.params.get("max", 999)
                if net_damage > cap:
                    game._log(f"  🛡️ {source.definition.name}: daño capado de {net_damage} a {cap}")
                    net_damage = cap
                    
            elif mod.effect_type == "pay_seal_cancel_attack":
                cost = mod.params.get("cost", 1)
                if game.seals[defender] >= cost:
                    game.seals[defender] -= cost
                    game._log(f"  🛡️ {source.definition.name}: paga {cost} sello(s), cancela ataque")
                    return 0, f"Ataque cancelado por {source.definition.name}"
                    
            elif mod.effect_type == "deny_attack_per_turn":
                # Track usage per turn
                used_key = f"_deny_attack_used_{mod.source_card_id}"
                if not getattr(game, used_key, False):
                    setattr(game, used_key, True)
                    game._log(f"  🛡️ {source.definition.name}: niega ataque")
                    return 0, f"Ataque negado por {source.definition.name}"
                    
            elif mod.effect_type == "cannot_lose":
                min_seals = mod.params.get("min_seals", 1)
                if game.seals[defender] - net_damage < min_seals:
                    net_damage = max(0, game.seals[defender] - min_seals)
                    game._log(f"  🛡️ {source.definition.name}: daño reducido a {net_damage} (no puede perder)")
                    
        return net_damage, None

    def check_before_attack_immunity(self, game: GameState, target_card_id: int, 
                                      attacker_squad=None) -> Optional[str]:
        """Check if a target is immune to attacks due to before_attack modifiers."""
        target = game.all_cards.get(target_card_id)
        if not target:
            return None
            
        for mod in self._modifiers.get("before_attack", []):
            source = game.all_cards.get(mod.source_card_id)
            if not source:
                continue
                
            # Sigilo: cannot be attacked
            if mod.effect_type == "sigilo_conditional":
                if mod.source_card_id == target_card_id:
                    cond = mod.params.get("condition", {})
                    if cond.get("type") == "no_links":
                        if game.network.link_count(target) == 0:
                            return f"{source.definition.name} tiene Sigilo: no puede ser atacado."
                            
            # Linked enemy cannot attack (Enredadera)
            if mod.effect_type == "linked_enemy_cannot_attack":
                if attacker_squad and mod.source_card_id in attacker_squad.members:
                    # Check if any enemy is linked to the Enredadera
                    for cid in attacker_squad.members:
                        c = game.all_cards.get(cid)
                        if c and game.network.has_link(c, source):
                            return f"{source.definition.name}: cartas vinculadas no pueden atacar."
                            
            # Cannot defend (Berserker)
            if mod.effect_type == "cannot_defend":
                if mod.source_card_id == target_card_id:
                    return f"{source.definition.name} no puede defender."
                    
        return None

    def apply_modify_damage(self, game: GameState, base_damage: int, 
                            attacker_squad, defender_squad=None) -> int:
        """Apply modify_damage modifiers to attack damage."""
        damage = base_damage
        
        for mod in self._modifiers.get("modify_damage", []):
            source = game.all_cards.get(mod.source_card_id)
            if not source:
                continue
                
            # Damage irreducible (Berserker)
            if mod.effect_type == "damage_irreducible":
                if attacker_squad and mod.source_card_id in attacker_squad.members:
                    game._log(f"  ⚔️ {source.definition.name}: daño irreducible")
                    # Mark that this damage cannot be reduced by defense
                    # The actual implementation is in game.py where defense is calculated
                    pass
                    
        return damage

    def check_destroy_immunity(self, game: GameState, card, destroyer=None) -> bool:
        """Check if a card is immune to destruction."""
        for mod in self._modifiers.get("before_destroy", []):
            if mod.effect_type == "destroy_immunity":
                if mod.source_card_id == card.card_id:
                    return True
            elif mod.effect_type == "destroy_immunity_type":
                if mod.source_card_id == card.card_id:
                    immune_to = mod.params.get("immune_to", "")
                    if destroyer and immune_to in destroyer.definition.name.lower():
                        return True
            elif mod.effect_type == "ability_target_immunity":
                if mod.source_card_id == card.card_id:
                    return True
            elif mod.effect_type == "ability_target_immunity_faction":
                if mod.source_card_id == card.card_id:
                    faction = mod.params.get("faction", "")
                    if destroyer and faction in destroyer.definition.color.value.lower():
                        return True
        return False

    def get_color_faction_mods(self, game: GameState, player: int) -> list[Modifier]:
        """Get all color_faction modifiers for a player."""
        results = []
        for mod in self._modifiers.get("color_faction", []):
            source = game.all_cards.get(mod.source_card_id)
            if source and source.owner == player:
                results.append(mod)
        return results

    def get_additional_factions(self, game: GameState, card) -> list[str]:
        """Get additional factions a card counts as (Carismático, Canalizador)."""
        factions = []
        for mod in self.get_color_faction_mods(game, card.owner):
            if mod.effect_type == "add_faction" and mod.layer == "network":
                # Applies to all cards in network
                factions.append(mod.params.get("faction", ""))
            elif mod.effect_type == "count_as_factions" and mod.source_card_id == card.card_id:
                factions.extend(mod.params.get("factions", []))
        return factions

    def get_defense_bonus(self, game: GameState, squad) -> int:
        """Get defense bonus from modify_squad modifiers."""
        bonus = 0
        for mod in self._modifiers.get("modify_squad", []):
            if mod.effect_type == "defense_bonus":
                if mod.source_card_id in squad.members:
                    bonus += mod.params.get("amount", 0)
        return bonus

    def get_linked_hp_bonus(self, game: GameState, card) -> int:
        """Get HP bonus from linked cards (Nodo Ancla)."""
        bonus = 0
        for mod in self._modifiers.get("modify_squad", []):
            if mod.effect_type == "linked_hp_bonus":
                # Check if card is linked to the source
                source = game.all_cards.get(mod.source_card_id)
                if source and game.network.has_link(card, source):
                    bonus += mod.params.get("amount", 0)
        return bonus

    # ═══════════════════════════════════════════════════════════════
    # P2: Medium-effort permanent passive effect handlers
    # ═══════════════════════════════════════════════════════════════

    def check_attack_override(self, game: GameState, card, context: str) -> Optional[str]:
        """Check attack overrides (multi-target, same-turn, unblockable, etc.)."""
        for mod in self._modifiers.get("before_attack", []):
            if mod.source_card_id != card.card_id:
                continue
            
            if mod.effect_type == "attack_in_actions_phase":
                if context == "actions_phase":
                    return None  # Allowed
                return f"{card.definition.name} solo puede atacar en Fase de Acciones."
                
            elif mod.effect_type == "attack_same_turn":
                # Check if card was played this turn
                if getattr(card, '_played_this_turn', False):
                    return None  # Allowed
                return f"{card.definition.name} no puede atacar el mismo turno que fue jugado."
                
        return None

    def check_unblockable(self, game: GameState, attacker, defender_squad) -> bool:
        """Check if attacker is unblockable by defender squad."""
        for mod in self._modifiers.get("before_attack", []):
            if mod.source_card_id != attacker.card_id:
                continue
            if mod.effect_type == "unblockable_by_v1":
                # Check if all defenders have V=1
                all_v1 = True
                for cid in defender_squad.members:
                    c = game.all_cards.get(cid)
                    if c and c.definition.hp > 1:  # V approximated by HP
                        all_v1 = False
                        break
                if all_v1:
                    return True
        return False

    def get_hand_limit(self, game: GameState, player: int) -> int:
        """Get max hand size for a player (default 7)."""
        for mod in self._modifiers.get("conditional_draw", []):
            source = game.all_cards.get(mod.source_card_id)
            if not source or source.owner != player:
                continue
            if mod.effect_type == "no_hand_limit":
                return 999
            elif mod.effect_type == "max_hand_size":
                return mod.params.get("max", 10)
        return 7

    def get_draw_count(self, game: GameState, player: int) -> int:
        """Get number of cards to draw at start of turn (default 2)."""
        for mod in self._modifiers.get("conditional_draw", []):
            source = game.all_cards.get(mod.source_card_id)
            if not source or source.owner != player:
                continue
            if mod.effect_type == "reveal_hand_draw":
                return mod.params.get("count", 3)
        return 2

    def check_play_override(self, game: GameState, player: int, card, 
                            source: str = "hand") -> tuple[int, Optional[str]]:
        """Check play cost overrides. Returns (cost, error)."""
        cost = 1  # Default cost
        
        for mod in self._modifiers.get("before_play", []):
            source_card = game.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != player:
                continue
            
            if mod.effect_type == "play_cost_zero":
                cost = 0
            elif mod.effect_type == "play_from_opponent_hand":
                if source == "opponent_hand":
                    cost = 1  # Can play from opponent hand
            elif mod.effect_type == "play_from_discard":
                if source == "discard":
                    cost = 1
            elif mod.effect_type == "play_from_graveyard_cost":
                if source == "graveyard":
                    cost = 1 + mod.params.get("extra_cost", 0)
            elif mod.effect_type == "play_layer_free":
                if card.position and card.position[1] == mod.params.get("layer", 1):
                    cost = 0
            elif mod.effect_type == "play_layer_discount":
                if card.position and card.position[1] == mod.params.get("layer", 1):
                    cost = max(0, cost - mod.params.get("discount", 0))
            elif mod.effect_type == "high_cost":
                cost = mod.params.get("cost", 1)
        
        return cost, None

    def check_lose_game_condition(self, game: GameState, card, event: str) -> bool:
        """Check if a card's death or action causes game loss."""
        for mod in self._modifiers.get("before_destroy", []):
            if mod.source_card_id != card.card_id:
                continue
            if mod.effect_type == "death_lose_game" and event == "death":
                return True
        return False

    def get_potenciamiento_mods(self, game: GameState, squad) -> dict:
        """Get potenciamiento modifiers for a squad."""
        result = {"multiplier": 1, "no_decay": False, "share": False}
        for mod in self._modifiers.get("modify_squad", []):
            if mod.source_card_id not in squad.members:
                continue
            if mod.effect_type == "double_potenciamiento":
                result["multiplier"] = 2
            elif mod.effect_type == "potenciamiento_no_decay":
                result["no_decay"] = True
            elif mod.effect_type == "share_potenciamiento":
                result["share"] = True
        return result

    def check_no_squad(self, game: GameState, card) -> bool:
        """Check if a card cannot form squads."""
        for mod in self._modifiers.get("modify_squad", []):
            if mod.source_card_id == card.card_id:
                if mod.effect_type in ("no_squad", "no_squad_destroy_adjacent", 
                                       "no_squad_destroy_allies"):
                    return True
        return False

    def get_layer_buffs(self, game: GameState, player: int, layer: int) -> dict:
        """Get buffs for cards in a specific layer."""
        result = {"hp": 0, "free_link": False}
        for mod in self._modifiers.get("modify_squad", []):
            if mod.effect_type == "layer_buff":
                if mod.params.get("layer") == layer:
                    result["hp"] += mod.params.get("hp", 0)
                    result["free_link"] = True
        return result

    # ═══════════════════════════════════════════════════════════════
    # P3: Spy/parasite effect handlers
    # ═══════════════════════════════════════════════════════════════

    def get_spy_mods(self, game: GameState, card) -> list[Modifier]:
        """Get all spy_infiltrate modifiers for a card."""
        return [m for m in self._modifiers.get("spy_infiltrate", [])
                if m.source_card_id == card.card_id]

    def has_spy_effect(self, game: GameState, card, effect_type: str) -> bool:
        """Check if a spy card has a specific effect."""
        for mod in self.get_spy_mods(game, card):
            if mod.effect_type == effect_type:
                return True
        return False

    def can_infiltrate(self, game: GameState, card) -> Optional[str]:
        """Check if a spy can infiltrate (not blocked by Centinela)."""
        if not card.definition.is_spy:
            return "No es un espía."
        
        # Check if enemy has Centinela de la Puerta in L1
        enemy = 1 - card.owner
        for mod in self._modifiers.get("spy_infiltrate", []):
            if mod.effect_type == "block_enemy_infiltrate":
                source = game.all_cards.get(mod.source_card_id)
                if source and source.owner == enemy:
                    if source.position and source.position[1] == 1:
                        return f"{source.definition.name} bloquea infiltración."
        return None

    def get_infiltrate_layer(self, game: GameState, card) -> list[int]:
        """Get allowed infiltration layers for a spy (default [3])."""
        for mod in self.get_spy_mods(game, card):
            if mod.effect_type == "infiltrate_low_layer":
                return mod.params.get("layers", [1, 2])
        return [3]

    def can_return_to_frontier(self, game: GameState, card) -> bool:
        """Check if a spy can return to frontier."""
        for mod in self.get_spy_mods(game, card):
            if mod.effect_type in ("infiltrate_return", "infiltrate_unlimited"):
                return True
        return False

    def get_infiltrate_cost(self, game: GameState, card) -> int:
        """Get infiltration cost (default 1 action)."""
        for mod in self.get_spy_mods(game, card):
            if mod.effect_type == "infiltrate_return":
                return mod.params.get("cost", 1)
        return 1

    def on_spy_infiltrate(self, game: GameState, card, target_layer: int = 3):
        """Execute post-infiltration effects."""
        for mod in self.get_spy_mods(game, card):
            if mod.effect_type == "parasite_sabotage_intel":
                # Sombra Infiltrada: attach to a Logistron if possible
                enemy = 1 - card.owner
                for cid, c in game.all_cards.items():
                    if c.owner == enemy and c.definition.is_logistron and c.position:
                        game._attached[card.card_id] = cid
                        game._log(f"  {card.definition.name}: parasitando {c.definition.name}")
                        break
                        
            elif mod.effect_type == "block_squad_attack_grimoire":
                # Agente Durmiente: mark a squad as unable to attack grimoire
                game._log(f"  {card.definition.name}: escuadrón marcado (no ataca grimorio)")
                
            elif mod.effect_type == "poison_node":
                # Envenenador: attach to a node, poison it
                enemy = 1 - card.owner
                for cid, c in game.all_cards.items():
                    if c.owner == enemy and c.position and not c.definition.is_spy:
                        game._attached[card.card_id] = cid
                        game._log(f"  {card.definition.name}: envenenando {c.definition.name}")
                        break
                        
            elif mod.effect_type == "infiltrate_unlimited":
                # Agente Triple: steal a seal
                enemy = 1 - card.owner
                steal = mod.params.get("steal_seal", 1)
                if game.seals[enemy] >= steal:
                    game.seals[enemy] -= steal
                    game.seals[card.owner] += steal
                    game._log(f"  {card.definition.name}: roba {steal} sello ({game.seals[card.owner]})")

    def check_spy_turn_effects(self, game: GameState, player: int):
        """Check turn-based spy effects (Dormido, Topo Paciente)."""
        for spy_id in list(game.spies_infiltrated[player]):
            spy = game.all_cards.get(spy_id)
            if not spy:
                continue
                
            for mod in self.get_spy_mods(game, spy):
                if mod.effect_type == "delayed_destroy_links":
                    turns = mod.params.get("turns", 2)
                    # Track infiltration turn
                    key = f"_infiltrate_turn_{spy_id}"
                    if not hasattr(game, key):
                        setattr(game, key, game.turn_number)
                    elif game.turn_number - getattr(game, key) >= turns:
                        # Destroy all links of the host squad
                        host_id = game._attached.get(spy_id)
                        if host_id:
                            host = game.all_cards.get(host_id)
                            if host:
                                for linked_id in list(game.network.get_links(host)):
                                    linked = game.all_cards.get(linked_id)
                                    if linked:
                                        game.network.remove_link(host, linked)
                                        game._log(f"  {spy.definition.name}: destruye vínculo {host.definition.name} <-> {linked.definition.name}")
                        # Remove the tracker
                        delattr(game, key)
                        
                elif mod.effect_type == "delayed_destroy_grimoire":
                    turns = mod.params.get("turns", 3)
                    min_spies = mod.params.get("min_spies", 5)
                    key = f"_infiltrate_turn_{spy_id}"
                    if not hasattr(game, key):
                        setattr(game, key, game.turn_number)
                    elif game.turn_number - getattr(game, key) >= turns:
                        if len(game.spies_infiltrated[player]) >= min_spies:
                            enemy = 1 - player
                            game.seals[enemy] = 0
                            game._log(f"  {spy.definition.name}: ¡DESTRUYE GRIMORIO ENEMIGO!")
                            game._end_game(player)
                        delattr(game, key)

    def get_spy_v_bonus(self, game: GameState, player: int) -> int:
        """Get V bonus for spies (Red de Inteligencia)."""
        bonus = 0
        for mod in self._modifiers.get("spy_infiltrate", []):
            if mod.effect_type == "spy_buff_reveal":
                source = game.all_cards.get(mod.source_card_id)
                if source and source.owner == player:
                    bonus += mod.params.get("v_bonus", 1)
        return bonus

    def can_spy_attack_grimoire(self, game: GameState, spy_card) -> bool:
        """Check if a spy's host squad is blocked from attacking grimoire."""
        host_id = game._attached.get(spy_card.card_id)
        if not host_id:
            return True
        
        for mod in self._modifiers.get("spy_infiltrate", []):
            if mod.effect_type == "block_squad_attack_grimoire":
                if mod.source_card_id == spy_card.card_id:
                    return False
        return True
