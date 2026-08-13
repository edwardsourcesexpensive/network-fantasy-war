"""Combat Engine for NFW — extracted from GameState.attack() (Candidate 2).

Deep module owning all combat logic: damage calculation, defense calculation,
hook dispatch, and damage resolution.

GameState.attack() becomes a thin delegate.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .game import GameState
    from .card import CardInstance
    from .network import Squad

from .network import calculate_potenciamiento
from .card import Color
from .modifier import Modifier


@dataclass
class AttackResult:
    """Result of attack calculation (before resolution)."""
    total_damage: int
    ignore_armor: int
    double_damage: bool
    attacker: int
    defender: int
    attacking_squad: "Squad"  # the squad that executed the attack
    blocked: bool = False
    block_reason: Optional[str] = None


@dataclass
class DefenseResult:
    """Result of defense calculation."""
    defense: int
    armor: int
    def_pot: int


@dataclass
class CombatEngine:
    """Owns all combat calculations and resolution."""

    def validate_attack(self, game: GameState, attacking_squad: Squad) -> Optional[str]:
        """Check if attack is legal (phase, G1, already attacked)."""
        if game.phase != game.phase.ATTACK:
            return "No estás en la fase de ataque."

        # G1: squad containing "cannot attack this turn" card can't attack
        for cid in attacking_squad.members:
            c = game.all_cards.get(cid)
            if c is not None and getattr(c, "_cannot_attack", False):
                return f"{c.definition.name} no puede atacar este turno."

        # One-attack-per-squad rule (≥2 member overlap)
        member_set = set(attacking_squad.members)
        for prev_members in game._attacked_squads:
            if len(member_set & prev_members) >= 2:
                return "Este escuadrón ya atacó este turno."

        return None

    def apply_before_attack_hooks(self, game: GameState, attacking_squad: Squad,
                                   target: str, target_card_id: Optional[int]) -> Optional[str]:
        """Apply before_attack modifiers (sigilo, immunities)."""
        if target != "card" or not target_card_id:
            return None

        defender = 1 - game.active_player

        # Legacy sigilo check
        for mod in game.modifiers.get("before_attack"):
            source_card = game.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != defender:
                continue
            if mod.effect_type == "cannot_be_attacked":
                if mod.source_card_id == target_card_id or mod.layer == "squad":
                    squad_members = set()
                    for sq in game.get_player_squads(defender):
                        if mod.source_card_id in sq.members:
                            squad_members = sq.members
                            break
                    if mod.source_card_id == target_card_id or target_card_id in squad_members:
                        return f"{source_card.definition.name} tiene Sigilo: no puede ser atacado."

        # P1: permanent passive immunities
        immunity_err = game.modifiers.check_before_attack_immunity(
            game, target_card_id, attacking_squad)
        if immunity_err:
            return immunity_err

        return None

    def calculate_attack(self, game: GameState, attacking_squad: Squad,
                         target: str, target_card_id: Optional[int]) -> AttackResult:
        """Calculate total attack damage including all modifiers."""
        attacker = game.active_player
        defender = 1 - attacker

        # Base damage
        base = attacking_squad.base_damage
        all_squads = game.network.find_squads(game.all_cards)
        pot = calculate_potenciamiento(attacking_squad, all_squads, game.network, game.all_cards)

        # G2: enemy blocked formation bonus
        if game._block_enemy_formation:
            pot = 0

        # D bonus from squad members + faction bonuses
        extra = 0
        for cid in attacking_squad.members:
            card = game.all_cards.get(cid)
            if card:
                extra += card.definition.damage_bonus
                # Guerrero faction: +1 per node in L2/L3
                if attacking_squad.get_dominant_color(game._get_color_overrides()) == Color.GUERRERO:
                    if card.position and card.position[1] >= 2:
                        extra += 1
                # Naturaleza faction: +1 damage and +1 pot
                if attacking_squad.get_dominant_color(game._get_color_overrides()) == Color.NATURALEZA:
                    extra += 1
                    pot += 1

        # Guardián del Bosque (Naturaleza triangle): other cards give +2 instead of +1
        if attacking_squad.squad_type == "triangle" and attacking_squad.get_dominant_color(game._get_color_overrides()) == Color.NATURALEZA:
            for cid in attacking_squad.members:
                card = game.all_cards.get(cid)
                if card and "Guardián" in card.definition.name:
                    others = [c for c in attacking_squad.members if c != cid]
                    extra += len(others)
                    break

        total_damage = base + pot + extra

        # modify_damage hook: permanent +D modifiers
        for mod in game.modifiers.get("modify_damage"):
            source_card = game.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != attacker:
                continue
            if mod.effect_type == "damage_bonus":
                condition = mod.params.get("condition", {})
                if not game.modifiers.evaluate_condition(game, condition, source_card):
                    continue
                if mod.source_card_id in attacking_squad.members:
                    total_damage += mod.params.get("delta", 0)

        # on_attack hook: attack-triggered effects
        ignore_armor_total = 0
        double_damage = False
        for mod in game.modifiers.get("on_attack"):
            source_card = game.all_cards.get(mod.source_card_id)
            if not source_card or source_card.owner != attacker:
                continue
            if mod.source_card_id not in attacking_squad.members:
                continue
            condition = mod.params.get("condition", {})
            if condition and not game.modifiers.evaluate_condition(game, condition, source_card):
                continue
            if mod.effect_type == "ignore_armor":
                ignore_armor_total = max(ignore_armor_total, mod.params.get("amount", 1))
            elif mod.effect_type == "double_damage":
                double_damage = True
            elif mod.effect_type == "double_self_d":
                req = mod.params.get("requires_action", 0)
                if req:
                    if game.actions_remaining < req:
                        continue
                    game.actions_remaining -= req
                    game._log(f"  ⚡ {source_card.definition.name}: -{req} acción extra → D duplicado")
                total_damage += source_card.definition.damage_bonus
            elif mod.effect_type == "bonus_vs_nodes":
                if target == "card" and target_card_id:
                    target_card = game.all_cards.get(target_card_id)
                    if target_card:
                        total_damage += mod.params.get("delta", 2)
            elif mod.effect_type == "bonus_vs_high_hp":
                if target == "card" and target_card_id:
                    target_card = game.all_cards.get(target_card_id)
                    if target_card and target_card.current_hp >= mod.params.get("hp_threshold", 5):
                        total_damage += mod.params.get("delta", 1)
            elif mod.effect_type == "bonus_per_link":
                link_count = game.network.link_count(source_card)
                total_damage += min(link_count, mod.params.get("max", 3))
            elif mod.effect_type == "bonus_vs_grimoire":
                if target == "grimoire":
                    total_damage += mod.params.get("delta", 4)

        if double_damage:
            total_damage *= 2

        return AttackResult(
            total_damage=total_damage,
            ignore_armor=ignore_armor_total,
            double_damage=double_damage,
            attacker=attacker,
            defender=defender,
            attacking_squad=attacking_squad,
        )

    def calculate_defense(self, game: GameState, defending_squad: Optional[Squad],
                          ignore_armor: int) -> DefenseResult:
        """Calculate defense value including armor and modifiers."""
        if not defending_squad:
            return DefenseResult(defense=0, armor=0, def_pot=0)

        all_squads = game.network.find_squads(game.all_cards)
        def_pot = calculate_potenciamiento(defending_squad, all_squads, game.network, game.all_cards) // 2

        # Festivo: +2 armor to links
        armor = 0
        if defending_squad.get_dominant_color(game._get_color_overrides()) == Color.FESTIVO:
            armor = 2

        # Danzante makes links unbreakable (armor boost)
        for cid in defending_squad.members:
            card = game.all_cards.get(cid)
            if card and "Danzante" in card.definition.name:
                armor += 1
                break

        # Link armor from before_link modifiers
        for mod in game.modifiers.get("before_link"):
            if mod.effect_type == "link_armor_bonus":
                source_card = game.all_cards.get(mod.source_card_id)
                if source_card and source_card.card_id in defending_squad.members:
                    armor += mod.params.get("amount", 1)

        # P1: defense bonus from permanent passives (Ministro de Defensa)
        armor += game.modifiers.get_defense_bonus(game, defending_squad)

        defense = def_pot + armor

        # Apply ignore_armor from on_attack modifiers
        if ignore_armor > 0:
            old_defense = defense
            defense = max(0, defense - ignore_armor)
            game._log(f"  ⚡ Ignora {ignore_armor} armadura: {old_defense} → {defense}")

        return DefenseResult(defense=defense, armor=armor, def_pot=def_pot)

    def resolve_grimoire(self, game: GameState, attack: AttackResult,
                         net_damage: int) -> Optional[str]:
        """Resolve damage to grimoire. Returns cancel reason or None."""
        # P1: grimoire_defense hook (Arquitecta, Diplomática, Embajador, Piedra)
        net_damage, cancel_reason = game.modifiers.apply_grimoire_defense(
            game, attack.defender, net_damage, attack_type="normal")
        if cancel_reason:
            game._log(f"  🛡️ {cancel_reason}")
            return cancel_reason

        game.seals[attack.defender] -= net_damage
        game._log(f"  ¡{net_damage} sellos destruidos! Grimorio enemigo: {game.seals[attack.defender]}")

        if game.seals[attack.defender] <= 0:
            game._end_game(attack.attacker)

        return None

    def resolve_card(self, game: GameState, attack: AttackResult,
                     target_card_id: int, net_damage: int) -> None:
        """Resolve damage to a card."""
        target_card = game.all_cards.get(target_card_id)
        if not target_card:
            return

        target_card.current_hp -= net_damage
        game._log(f"  ¡{net_damage} daño a {target_card.definition.name}! (HP: {target_card.current_hp})")

        if target_card.current_hp <= 0:
            game._log(f"  {target_card.definition.name} DESTRUIDO.")
            # Find a killer from attacking squad
            killer_card = None
            for cid in attack.attacking_squad.members:
                kc = game.all_cards.get(cid)
                if kc:
                    killer_card = kc
                    break
            game._destroy_card(target_card, killer=killer_card)

    def execute(self, game: GameState, attacking_squad: Squad, target: str,
                defending_squad: Optional[Squad] = None,
                target_card_id: Optional[int] = None) -> Optional[str]:
        """Execute a full attack. Returns error string or None."""
        # 1. Validate
        err = self.validate_attack(game, attacking_squad)
        if err:
            return err

        # 2. Before-attack hooks
        err = self.apply_before_attack_hooks(game, attacking_squad, target, target_card_id)
        if err:
            return err

        # 3. Calculate attack
        attack = self.calculate_attack(game, attacking_squad, target, target_card_id)

        game._log(f"  ⚔️ Ataque: {attacking_squad.squad_type} "
                  f"(base={attacking_squad.base_damage} pot={attack.total_damage} extra=0) = {attack.total_damage}")

        # 4. Calculate defense
        defense = self.calculate_defense(game, defending_squad, attack.ignore_armor)
        if defending_squad:
            game._log(f"  🛡️ Defensa: {defending_squad.squad_type} "
                      f"(pot={defense.def_pot} armor={defense.armor}) = {defense.defense}")

        # 5. Net damage
        net_damage = max(0, attack.total_damage - defense.defense)
        game._log(f"  Daño neto: {attack.total_damage} - {defense.defense} = {net_damage}")

        # 6. Resolve
        if target == "grimoire":
            cancel = self.resolve_grimoire(game, attack, net_damage)
            if cancel:
                game._attacked_squads.add(frozenset(attacking_squad.members))
                return None
        elif target == "card" and target_card_id:
            self.resolve_card(game, attack, target_card_id, net_damage)

        # 7. Mark squad as attacked
        game._attacked_squads.add(frozenset(attacking_squad.members))
        return None
