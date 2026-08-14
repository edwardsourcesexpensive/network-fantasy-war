"""Audit #7: Saboteador / Monstruo / Político faction choice effects.

Run: python -m pytest tests/test_faction_effects.py -v
"""

import sys
sys.path.insert(0, r"D:/DocumentsD/Proyectos-Personales/Network-Fantasy-War")

import pytest
from prototype.game import GameState
from prototype.card import CardInstance, ALL_CARDS
from prototype.enums import Phase
from prototype import turn_manager as tm


def _def(name):
    for c in ALL_CARDS:
        if c.name == name:
            return c
    raise ValueError(f"Card not found: {name}")


def _fat_deck():
    """≥15 cards, no spies/logistrons, so entry draws never fatigue."""
    return [c for c in ALL_CARDS if not c.is_spy and not c.is_logistron][:15]


@pytest.fixture
def gs():
    g = GameState(_fat_deck(), _fat_deck())
    g.start_turn()
    g.entry_phase()
    return g


def _make_card(gs, player, name, layer, meridian):
    """Create a card instance for `player` and place it on the board."""
    cid = len(gs.all_cards)
    card = CardInstance(cid, _def(name), player)
    card.current_hp = card.definition.hp
    gs.all_cards[cid] = card
    assert gs.board.place_card(player, card, layer, meridian), \
        f"place failed {name}@{layer},{meridian}"
    return card


def _link(gs, a, b):
    gs.network.add_link(a, b)


def _logistron_name():
    for c in ALL_CARDS:
        if c.is_logistron:
            return c.name
    raise ValueError("no logistrón card")


def _incoloro_name():
    for c in ALL_CARDS:
        if c.color.name == "INCOLORO" and not c.is_spy and not c.is_logistron and c.link_capacity >= 2:
            return c.name
    raise ValueError("no incoloro card")


def _linked(gs, a, b):
    return b.card_id in gs.network.get_links(a)


def _saboteador_squad(gs, m0=0, m2=2):
    s1 = _make_card(gs, 0, "Agente del Silencio", 1, m0)
    s2 = _make_card(gs, 0, "Sabueso del Nexo", 1, m2)
    _link(gs, s1, s2)
    return s1, s2


# ═══════════════════════════════════════════════════════════════
# Saboteador: break up to 2 'corta' links in the enemy network
# ═══════════════════════════════════════════════════════════════

class TestSaboteador:

    def test_breaks_corta_enemy_links_only(self, gs):
        s1, s2 = _saboteador_squad(gs, 0, 2)

        # Enemy network: corta link (e1-e2), media links (e2-e3, e3-e4)
        e1 = _make_card(gs, 1, "Desestabilizador", 1, 4)
        e2 = _make_card(gs, 1, "Desestabilizador", 1, 6)
        e3 = _make_card(gs, 1, "Desestabilizador", 1, 9)
        e4 = _make_card(gs, 1, "Desestabilizador", 1, 12)
        _link(gs, e1, e2)  # corta (dh2)
        _link(gs, e2, e3)  # media (dh3)
        _link(gs, e3, e4)  # media (dh3)

        gs.exit_phase()  # auto_resolve=True

        assert not _linked(gs, e1, e2), "corta enemy link must be broken"
        assert _linked(gs, e2, e3), "media enemy link must stay"
        assert _linked(gs, e3, e4), "media enemy link must stay"
        assert _linked(gs, s1, s2), "own link must stay"
        assert gs.active_player == 1, "turn must switch"

    def test_max_two_links_per_squad(self, gs):
        _saboteador_squad(gs, 0, 2)

        # Three corta links in the enemy network → only 2 may break
        e1 = _make_card(gs, 1, "Desestabilizador", 1, 0)
        e2 = _make_card(gs, 1, "Desestabilizador", 1, 2)
        e3 = _make_card(gs, 1, "Desestabilizador", 1, 4)
        e4 = _make_card(gs, 1, "Desestabilizador", 1, 6)
        _link(gs, e1, e2)
        _link(gs, e2, e3)
        _link(gs, e3, e4)

        gs.exit_phase()

        broken = sum(not _linked(gs, a, b) for a, b in
                     [(e1, e2), (e2, e3), (e3, e4)])
        assert broken == 2, f"expected exactly 2 broken, got {broken}"

    def test_no_candidates_no_effect(self, gs):
        _saboteador_squad(gs, 0, 2)

        # Enemy has only media links
        e1 = _make_card(gs, 1, "Desestabilizador", 1, 0)
        e2 = _make_card(gs, 1, "Desestabilizador", 1, 3)
        _link(gs, e1, e2)

        gs.exit_phase()

        assert _linked(gs, e1, e2)


# ═══════════════════════════════════════════════════════════════
# Monstruo: remove 1 enemy node with Grado < squad damage
# ═══════════════════════════════════════════════════════════════

class TestMonstruo:

    def _triangle_squad(self, gs):
        """3 Monstruo cards in a triangle → base damage 2."""
        m1 = _make_card(gs, 0, "Dragón Ancestral", 1, 0)
        m2 = _make_card(gs, 0, "Devorador de Capas", 1, 2)
        m3 = _make_card(gs, 0, "Kraken del Abismo", 2, 1)
        _link(gs, m1, m2)
        _link(gs, m2, m3)
        _link(gs, m1, m3)
        return m1, m2, m3

    def test_removes_g1_but_not_g2(self, gs):
        self._triangle_squad(gs)

        e1 = _make_card(gs, 1, "Envenenador de Suministros", 1, 4)  # G1, degree 0
        e2 = _make_card(gs, 1, "Desestabilizador", 1, 6)            # G2, degree 1
        e3 = _make_card(gs, 1, "Envenenador de Suministros", 1, 8)  # G1, degree 1
        _link(gs, e2, e3)

        gs.exit_phase()

        assert e3.card_id not in gs.all_cards, "G1 node with links must be removed"
        assert e2.card_id in gs.all_cards, "G2 node must survive (G >= damage)"
        assert e1.card_id in gs.all_cards, "G1 node with degree 0 is valid but not the top pick"

    def test_one_node_per_squad(self, gs):
        self._triangle_squad(gs)

        # Two G1 candidates, both with degree 1 → only one removed
        e1 = _make_card(gs, 1, "Envenenador de Suministros", 1, 0)
        e2 = _make_card(gs, 1, "Envenenador de Suministros", 1, 2)
        e3 = _make_card(gs, 1, "Envenenador de Suministros", 1, 4)
        _link(gs, e1, e2)
        _link(gs, e2, e3)

        gs.exit_phase()

        removed = sum(1 for c in (e1, e2, e3) if c.card_id not in gs.all_cards)
        assert removed == 1, f"expected exactly 1 removed, got {removed}"

    def test_attack_includes_potenciamiento(self, gs):
        """Monstruo attack = base damage + potenciamiento (logistrón bridge)."""
        m1 = _make_card(gs, 0, "Dragón Ancestral", 1, 0)
        m2 = _make_card(gs, 0, "Devorador de Capas", 1, 2)
        m3 = _make_card(gs, 0, "Kraken del Abismo", 2, 1)
        _link(gs, m1, m2)
        _link(gs, m2, m3)
        _link(gs, m1, m3)  # triangle, base damage 2

        # logistrón bridge to an INCOLORO line (donor empowerment 1) → pot +1
        lg = _make_card(gs, 0, _logistron_name(), 2, 3)
        _link(gs, m3, lg)
        n1 = _make_card(gs, 0, _incoloro_name(), 1, 4)
        n2 = _make_card(gs, 0, _incoloro_name(), 1, 6)
        _link(gs, lg, n1)
        _link(gs, n1, n2)  # line {n1,n2}

        tri = next(s for s in gs.get_player_squads(0) if s.squad_type == "triangle")
        assert tm._squad_attack(gs, tri) == 3, \
            f"expected base 2 + pot 1, got {tm._squad_attack(gs, tri)}"

        # A G2 enemy node (not removable at base 2) is now removable
        e1 = _make_card(gs, 1, "Desestabilizador", 1, 8)  # G2
        gs.exit_phase()
        assert e1.card_id not in gs.all_cards, "G2 node must fall to attack 3"


# ═══════════════════════════════════════════════════════════════
# Político: swap positions of 2 own cards (links must survive)
# ═══════════════════════════════════════════════════════════════

class TestPolitico:

    def test_valid_swap_applies(self, gs):
        a = _make_card(gs, 0, "Estratega de los Cien Hilos", 1, 0)
        b = _make_card(gs, 0, "Tejedor de Alianzas", 1, 4)

        pairs = tm.politico_candidates(gs, 0)
        assert len(pairs) == 1 and pairs[0] == (a.card_id, b.card_id)

        assert tm.apply_politico_swap(gs, 0, a.card_id, b.card_id)
        assert a.position == (0, 1, 4)
        assert b.position == (0, 1, 0)
        assert gs.board.cells[0][0][0] == b.card_id
        assert gs.board.cells[0][0][4] == a.card_id

    def test_rejects_link_breaking_swap(self, gs):
        a = _make_card(gs, 0, "Estratega de los Cien Hilos", 1, 0)
        c = _make_card(gs, 0, "Tejedor de Alianzas", 1, 2)
        _link(gs, a, c)  # corta — moving a far away would break the rod
        b = _make_card(gs, 0, "Estratega de los Cien Hilos", 1, 10)

        assert not tm.apply_politico_swap(gs, 0, a.card_id, b.card_id)
        assert (a.card_id, b.card_id) not in tm.politico_candidates(gs, 0)
        assert a.position == (0, 1, 0), "positions must be unchanged"

    def test_auto_swaps_when_beneficial(self, gs):
        # x1-x2 same color at MEDIA distance; z sits at m5 → swap x1↔z
        # brings x1 to 'corta' of x2 (+1 same-color corta).
        x1 = _make_card(gs, 0, "Agente del Silencio", 1, 0)
        x2 = _make_card(gs, 0, "Sabueso del Nexo", 1, 3)
        _link(gs, x1, x2)  # media (dh3)
        z = _make_card(gs, 0, "Estratega de los Cien Hilos", 1, 5)

        tm.resolve_politico_auto(gs, 0, budget=1)

        assert x1.position == (0, 1, 5), f"x1 should swap with z, got {x1.position}"
        assert z.position == (0, 1, 0)
        assert _linked(gs, x1, x2), "link must survive the swap"

    def test_auto_skips_without_benefit(self, gs):
        x1 = _make_card(gs, 0, "Agente del Silencio", 1, 0)
        x2 = _make_card(gs, 0, "Sabueso del Nexo", 1, 2)
        _link(gs, x1, x2)  # already corta + same color → nothing to gain
        z = _make_card(gs, 0, "Estratega de los Cien Hilos", 1, 4)

        tm.resolve_politico_auto(gs, 0, budget=1)

        assert x1.position == (0, 1, 0)
        assert x2.position == (0, 1, 2)
        assert z.position == (0, 1, 4)

    def test_entry_phase_auto_swap_with_politico_squad(self, gs):
        p1 = _make_card(gs, 0, "Estratega de los Cien Hilos", 1, 0)
        p2 = _make_card(gs, 0, "Tejedor de Alianzas", 1, 2)
        _link(gs, p1, p2)  # line squad, dominant Político

        x1 = _make_card(gs, 0, "Agente del Silencio", 1, 6)
        x2 = _make_card(gs, 0, "Sabueso del Nexo", 1, 9)
        _link(gs, x1, x2)  # media
        z = _make_card(gs, 0, "Desestabilizador", 1, 11)

        gs.entry_phase()  # auto → politico squad → beneficial swap

        assert x1.position == (0, 1, 11), f"x1 should swap with z, got {x1.position}"
        assert z.position == (0, 1, 6)


# ═══════════════════════════════════════════════════════════════
# Non-auto path (B2 hosts): pending choices + apply
# ═══════════════════════════════════════════════════════════════

class TestPendingChoices:

    def test_exit_pending_and_apply(self, gs):
        s1, s2 = _saboteador_squad(gs, 0, 2)
        e1 = _make_card(gs, 1, "Desestabilizador", 1, 4)
        e2 = _make_card(gs, 1, "Desestabilizador", 1, 6)
        _link(gs, e1, e2)

        gs.exit_phase(auto_resolve=False)

        pending = gs.pending_faction_choices
        assert pending is not None
        assert pending["saboteador"]["max"] == 2
        assert pending["saboteador"]["links"] == [(e1.card_id, e2.card_id)]
        assert gs.active_player == 0, "must NOT switch before choices applied"
        assert gs.phase == Phase.EXIT

        # Apply the pick, then finish the phase
        tm.apply_faction_choices(gs, 0, pending["saboteador"]["links"], [])
        tm._finish_exit_phase(gs)

        assert not _linked(gs, e1, e2)
        assert gs.pending_faction_choices is None
        assert gs.active_player == 1

    def test_entry_pending_politico(self, gs):
        p1 = _make_card(gs, 0, "Estratega de los Cien Hilos", 1, 0)
        p2 = _make_card(gs, 0, "Tejedor de Alianzas", 1, 2)
        _link(gs, p1, p2)
        a = _make_card(gs, 0, "Desestabilizador", 1, 4)
        b = _make_card(gs, 0, "Desestabilizador", 1, 6)

        gs.entry_phase(auto_resolve=False)

        pending = gs.pending_politico_swap
        assert pending is not None
        assert pending["max"] == 1
        assert (a.card_id, b.card_id) in pending["pairs"]
        assert gs.phase == Phase.ACTIONS

        assert tm.apply_politico_swap(gs, 0, a.card_id, b.card_id)
        assert a.position == (0, 1, 6)
