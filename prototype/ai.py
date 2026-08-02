"""Bot AI for Network Fantasy War — single-player and multiplayer share one implementation.

Extracted from webui/app.py and webui/multiplayer/app.py (Candidate 3).
Uses the MP bot's smarter logic as default — SP gets the upgrade for free.

Boundary: BotPlayer produces decisions (which cards to play, where to link, which
squads attack what). The HOST (SP/MP app.py) owns the I/O — SocketIO emits,
JSON responses, animation sleeps, and the interactive defense queue loop.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable

from .card import CardInstance, CardDef
from .game import GameState
from .enums import Phase


@dataclass
class AttackIntent:
    """A single attack the bot wants to execute. The host sets it as pending_attack."""
    squad_type: str
    squad_damage: int
    members_ids: list[int]
    members_names: list[str]
    squad_color: str
    target: str          # 'grimoire' or 'card'
    target_id: Optional[int] = None


@dataclass
class BotTurnResult:
    """What the bot did in one turn. The host uses this to drive the UI."""
    cards_played: int = 0
    links_formed: int = 0
    attacks: list[AttackIntent] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


class BotPlayer:
    """Stateless bot that plays a single turn of NFW.

    Usage per turn:
        result = bot.take_turn(game, player_id, on_log=...)
        # Host sets room['bot_attacks'] = result.attacks
        # Host pops one attack → pending_attack → sends to frontend
        # After all attacks resolved:
        bot.end_turn(game, player_id)
    """

    def take_turn(
        self,
        game: GameState,
        player: int,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> BotTurnResult:
        """Execute a full bot turn: play cards → link → build attack queue.

        Does NOT start/end phases — the host must have game in the right state
        (start_turn + entry_phase already called) before calling this.

        Returns BotTurnResult with attacks ready for the interactive defense loop.
        """
        result = BotTurnResult()

        def log(msg: str):
            result.logs.append(msg)
            if on_log:
                on_log(msg)

        # ─── Phase 1: Enter actions ───
        game.phase = Phase.ACTIONS
        game.actions_remaining = 10
        log("IA comienza su turno (10 acciones)")

        # ─── Phase 2: Play cards ───
        result.cards_played = self._play_cards(game, player, log)

        if result.cards_played == 0:
            log("IA no pudo jugar cartas")

        # ─── Phase 3: Vanguardia bridge ───
        if result.cards_played >= 2 and game.actions_remaining >= 1:
            self._vanguardia_bridge(game, player, log, result)

        # ─── Phase 4: Ascension ───
        self._use_ascension(game, player, log)

        # ─── Phase 5: Horizontal movement ───
        self._horizontal_move(game, player, log)

        # ─── Phase 6: Smart linking ───
        result.links_formed = self._link_cards(game, player, log)

        if result.links_formed == 0 and result.cards_played > 0:
            log("IA no pudo vincular cartas")

        # ─── Phase 7: Build attack queue ───
        squads = game.get_player_squads(player)
        log(f"IA tiene {len(squads)} escuadron(es)")

        if squads:
            game.start_attack_phase()
            result.attacks = self._build_attacks(game, player, squads, log)

        return result

    # ═══════════════════════════════════════════════════════════════
    # Internal: Play cards
    # ═══════════════════════════════════════════════════════════════

    def _play_cards(self, game: GameState, player: int, log) -> int:
        """Play up to 4 cards with smart positioning. Returns count played."""
        hand = game.hands[player]
        if not hand:
            return 0

        # Sort by link capacity desc, damage desc (VG cards deprioritized for bridge)
        hand_with_idx = [(i, hand[i]) for i in range(len(hand))]

        def _sort_key(item):
            _idx, c = item
            has_vg = any("Vanguardia" in a.description for a in c.definition.abilities)
            vg_penalty = -10 if has_vg else 0
            return (vg_penalty, c.definition.link_capacity, c.definition.damage_bonus)

        hand_sorted = sorted(hand_with_idx, key=_sort_key, reverse=True)

        cards_played = 0
        for _orig_idx, card in hand_sorted:
            if cards_played >= 4 or game.actions_remaining < 1:
                break
            if not game.hands[player]:
                break

            # Find card in current hand (indices shift after plays)
            current_idx = None
            for i, hc in enumerate(game.hands[player]):
                if hc.card_id == card.card_id:
                    current_idx = i
                    break
            if current_idx is None:
                continue

            # Spy handling
            if card.definition.is_spy:
                played = self._play_spy(game, player, current_idx, card, log)
                if played:
                    cards_played += 1
                continue

            # Determine valid entry layers
            valid_layers = self._valid_layers(card)

            # Try to play near existing cards for squad formation
            bot_pos = self._get_positions(game, player)
            best_pos = self._find_best_position(game, player, valid_layers, bot_pos)

            layer, m, _ = best_pos if best_pos else (None, None, None)
            if layer is None:
                # Fallback: first valid layer with empty slot
                for li_0 in range(3):
                    lyr = li_0 + 1
                    if lyr not in valid_layers:
                        continue
                    fm = game.board.find_empty_meridian(player, lyr)
                    if fm is not None:
                        layer, m = lyr, fm
                        break
                if layer is None:
                    continue

            err = game.play_card(player, current_idx, layer, m)
            if err is None:
                log(f"IA juega {card.definition.name} (V={card.definition.link_capacity}) en L{layer}:{m}")
                cards_played += 1

        return cards_played

    def _play_spy(self, game: GameState, player: int, idx: int, card, log) -> bool:
        """Try to infiltrate a spy. Returns True if played."""
        for li in range(3):
            for m in range(15):
                if game.board.cells[player][li][m] is None:
                    err = game.play_card(player, idx, li + 1, m)
                    if err is None:
                        log(f"IA infiltra espía {card.definition.name} en L{li+1}:{m}")
                        return True
        return False

    @staticmethod
    def _valid_layers(card) -> list[int]:
        """Determine which layers this card can enter."""
        if card.definition.is_logistron:
            return card.definition.allowed_layers
        has_vg = any("Vanguardia" in a.description for a in card.definition.abilities)
        has_lf = any("Línea de fuego" in a.description for a in card.definition.abilities)
        valid = [1]
        if has_vg or has_lf:
            valid.append(2)
        if has_lf:
            valid.append(3)
        return [l for l in valid if l in card.definition.allowed_layers]

    @staticmethod
    def _get_positions(game: GameState, player: int) -> list[tuple[int, int]]:
        """Get (layer_index, meridian) of all cards on the player's board."""
        pos = []
        for li in range(3):
            for m in range(15):
                if game.board.cells[player][li][m] is not None:
                    pos.append((li, m))
        return pos

    @staticmethod
    def _find_best_position(
        game: GameState, player: int, valid_layers: list[int],
        bot_pos: list[tuple[int, int]],
    ) -> Optional[tuple[int, int, int]]:
        """Find the best (layer, meridian) to play near existing cards.

        Returns (layer, meridian, score) or None if no good spot.
        """
        if not bot_pos:
            return None

        best = None
        for li_0 in range(3):
            layer = li_0 + 1
            if layer not in valid_layers:
                continue
            for m in range(15):
                if game.board.cells[player][li_0][m] is not None:
                    continue
                near_count = 0
                for bl, bm in bot_pos:
                    if li_0 == bl and abs(m - bm) == 2:
                        near_count += 2  # same-layer dh=2 (triangle-ready)
                    elif li_0 == bl and abs(m - bm) <= 2:
                        near_count += 0  # dh=1 would fail; dh=0 impossible
                    elif abs(li_0 - bl) == 1 and abs(m - bm) <= 1:
                        near_count += 1  # cross-layer proximity
                if near_count >= 1 and (best is None or near_count > best[2]):
                    best = (layer, m, near_count)
        return best

    # ═══════════════════════════════════════════════════════════════
    # Internal: Vanguardia bridge
    # ═══════════════════════════════════════════════════════════════

    def _vanguardia_bridge(
        self, game: GameState, player: int, log,
        result: BotTurnResult,
    ) -> None:
        """Play a VG card at L2 bridge to enable L1-L2-L1 cross-layer triangles."""
        l1_occupied = sorted([
            m for m in range(15)
            if game.board.cells[player][0][m] is not None
        ])

        for i, m_a in enumerate(l1_occupied):
            for m_b in l1_occupied[i + 1:]:
                if m_b - m_a != 2:
                    continue
                bridge_m = m_a + 1
                if game.board.cells[player][1][bridge_m] is not None:
                    continue
                # Found dh=2 L1 pair with empty L2 bridge
                for hi, hc in enumerate(game.hands[player]):
                    if hc.definition.is_spy:
                        continue
                    has_vg = any(
                        "Vanguardia" in a.description
                        for a in hc.definition.abilities
                    )
                    if not has_vg:
                        continue
                    if hc.definition.link_capacity < 2:
                        continue
                    if 2 not in hc.definition.allowed_layers:
                        continue
                    err = game.play_card(player, hi, 2, bridge_m)
                    if err is None:
                        log(
                            f"IA coloca {hc.definition.name} (Vanguardia) "
                            f"en L2:{bridge_m} — ¡puente de triángulo!"
                        )
                        result.cards_played += 1
                        log(f"IA forma puente L1–L2–L1 en m={bridge_m} — ¡triángulo posible!")
                        return

    # ═══════════════════════════════════════════════════════════════
    # Internal: Ascension
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _use_ascension(game: GameState, player: int, log) -> None:
        """Use [1]: asciende abilities on board cards."""
        for li in range(3):
            for m in range(15):
                cid = game.board.cells[player][li][m]
                if not cid:
                    continue
                card = game.all_cards.get(cid)
                if not card:
                    continue
                for ability in card.definition.abilities:
                    if any(
                        kw in ability.description.lower()
                        for kw in ['[1]: asciende', '[1]: Asciende']
                    ):
                        if game.actions_remaining >= 1:
                            err = game.ascend(player, card)
                            if err is None:
                                log(f"IA asciende {card.definition.name}")
                                break

    # ═══════════════════════════════════════════════════════════════
    # Internal: Horizontal movement
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _horizontal_move(game: GameState, player: int, log) -> None:
        """Move V>=2 cards toward center for better squad formation."""
        # The MP bot had this as Step 2.6 but it was a simple reposition
        # for V>=2 cards. SP bot already did this. Keep for MP parity.
        for li in range(3):
            for m in range(15):
                cid = game.board.cells[player][li][m]
                if not cid:
                    continue
                card = game.all_cards.get(cid)
                if card and card.definition.link_capacity >= 2:
                    if m < 5:
                        for _ in range(2):
                            err = game.move_card(player, card, 1)
                            if err:
                                break
                    elif m > 9:
                        for _ in range(2):
                            err = game.move_card(player, card, -1)
                            if err:
                                break

    # ═══════════════════════════════════════════════════════════════
    # Internal: Smart linking
    # ═══════════════════════════════════════════════════════════════

    def _link_cards(self, game: GameState, player: int, log) -> int:
        """Smart linking: triangles first, then adjacent pairs. Returns count."""
        link_count = 0
        placed = self._get_positions(game, player)

        # Phase A: Triangle hunt
        for i, ci in enumerate(placed):
            for j_, cj in enumerate(placed[i + 1:], i + 1):
                for k_, ck in enumerate(placed[j_ + 1:], j_ + 1):
                    dist_ij = game.board.spatial_distance(
                        (player, ci[0] + 1, ci[1]),
                        (player, cj[0] + 1, cj[1]),
                    )
                    dist_jk = game.board.spatial_distance(
                        (player, cj[0] + 1, cj[1]),
                        (player, ck[0] + 1, ck[1]),
                    )
                    dist_ki = game.board.spatial_distance(
                        (player, ck[0] + 1, ck[1]),
                        (player, ci[0] + 1, ci[1]),
                    )
                    if not (dist_ij == 'corta' and dist_jk == 'corta' and dist_ki == 'corta'):
                        continue

                    cid_i = game.board.cells[player][ci[0]][ci[1]]
                    cid_j = game.board.cells[player][cj[0]][cj[1]]
                    cid_k = game.board.cells[player][ck[0]][ck[1]]
                    ca = game.all_cards[cid_i]
                    cb = game.all_cards[cid_j]
                    cc = game.all_cards[cid_k]

                    if not (
                        ca.definition.link_capacity >= 2
                        and cb.definition.link_capacity >= 2
                        and cc.definition.link_capacity >= 2
                        and game.network.link_count(ca) < ca.definition.link_capacity
                        and game.network.link_count(cb) < cb.definition.link_capacity
                        and game.network.link_count(cc) < cc.definition.link_capacity
                    ):
                        continue

                    for a, b in [(ca, cb), (cb, cc), (cc, ca)]:
                        if game.actions_remaining >= 1:
                            err = game.link_cards(player, a, b)
                            if err is None:
                                link_count += 1
                    log(
                        f"IA forma TRIÁNGULO: "
                        f"{ca.definition.name}/{cb.definition.name}/{cc.definition.name}"
                    )

        # Phase B: Adjacent pairs
        for ci_idx, ci in enumerate(placed):
            for cj in placed[ci_idx + 1:]:
                same_layer = ci[0] == cj[0] and abs(ci[1] - cj[1]) == 2
                cross_layer = abs(ci[0] - cj[0]) == 1 and abs(ci[1] - cj[1]) <= 1
                if not (same_layer or cross_layer):
                    continue
                cid_a = game.board.cells[player][ci[0]][ci[1]]
                cid_b = game.board.cells[player][cj[0]][cj[1]]
                a_card = game.all_cards.get(cid_a)
                b_card = game.all_cards.get(cid_b)
                if not a_card or not b_card:
                    continue
                if game.network.link_count(a_card) >= a_card.definition.link_capacity:
                    continue
                if game.network.link_count(b_card) >= b_card.definition.link_capacity:
                    continue
                if game.actions_remaining < 1:
                    return link_count
                err = game.link_cards(player, a_card, b_card)
                if err is None:
                    log(f"IA vincula L{ci[0]+1}:{ci[1]} - L{cj[0]+1}:{cj[1]}")
                    link_count += 1

        return link_count

    # ═══════════════════════════════════════════════════════════════
    # Internal: Attack queue
    # ═══════════════════════════════════════════════════════════════

    def _build_attacks(
        self, game: GameState, player: int,
        squads: list, log,
    ) -> list[AttackIntent]:
        """Build attack queue with smart targeting. Returns list of AttackIntent."""
        attacks = []
        squads_sorted = sorted(squads, key=lambda s: s.base_damage, reverse=True)

        for squad in squads_sorted[:2]:
            target = 'grimoire'
            target_id = None

            # Check for isolated enemy cards
            enemy = 1 - player
            human_isolated = []
            for li in range(3):
                for m in range(15):
                    cid = game.board.cells[enemy][li][m]
                    if cid:
                        card = game.all_cards.get(cid)
                        if card and game.network.link_count(card) == 0:
                            human_isolated.append((cid, card.definition.name))

            if human_isolated:
                target = 'card'
                target_id = human_isolated[0][0]
                log(f"IA apunta a carta aislada: {human_isolated[0][1]}")

            members_names = [
                game.all_cards[cid].definition.name
                for cid in squad.members
            ]

            attacks.append(AttackIntent(
                squad_type=squad.squad_type,
                squad_damage=squad.base_damage,
                members_ids=list(squad.members),
                members_names=members_names,
                squad_color=(
                    squad.dominant_color.value
                    if squad.dominant_color else 'incoloro'
                ),
                target=target,
                target_id=target_id,
            ))

        return attacks

    # ═══════════════════════════════════════════════════════════════
    # End turn
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def end_turn(game: GameState, player: int) -> bool:
        """End the bot's turn: exit_phase → start_turn → entry_phase.

        The host calls this after all attacks are resolved and the attack
        queue is empty. Returns True if game continues, False if game over.
        """
        game.phase = Phase.ATTACK
        game.active_player = player
        game.exit_phase()
        if game.game_over:
            return False
        game.start_turn()
        game.entry_phase()
        return True
