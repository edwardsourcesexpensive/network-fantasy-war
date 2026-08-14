"""Unified state serializer for NFW.

Single canonical format for both single-player and multiplayer UIs.
Prevents field-name drift between the two webui apps.

Usage:
    serialize_state(game)              # SP mode: both hands visible
    serialize_state(game, player_id)   # MP mode: filtered to one player
    serialize_state(game, player_id, pending_attack)  # with defense prompt
"""

from typing import Optional


def serialize_state(game: 'GameState', player_id: Optional[int] = None,
                    pending_attack=None) -> dict:
    """Serialize complete game state to a JSON-safe dict.

    Board cells use short field names (d, v, v_used) — both UIs agree on these.
    Hand cards use long field names (damage_bonus, link_capacity).

    Args:
        game: GameState instance
        player_id: If provided, filter hand to this player only (MP mode).
                   If None, return both hands unfiltered (SP debug mode).
        pending_attack: Attack data for defense prompt (MP mode).
    """
    # ─── Frontier spies ───
    frontier = []
    for cid in game.board.frontier_cards:
        card = game.all_cards[cid]
        frontier.append({
            "id": cid,
            "name": card.definition.name,
            "owner": card.owner,
            "grado": card.definition.grado,
        })

    # ─── Board cells ───
    board = {"p0": [], "p1": [], "frontier": frontier}
    for p in [0, 1]:
        for layer in range(3):
            row = []
            for m in range(15):
                cid = game.board.cells[p][layer][m]
                if cid:
                    card = game.all_cards[cid]
                    row.append({
                        "id": cid,
                        "name": card.definition.name,
                        "short": card.definition.name[:4],
                        "hp": card.current_hp,
                        "max_hp": card.definition.hp,
                        "d": card.definition.damage_bonus,
                        "v": card.definition.link_capacity,
                        "v_used": game.network.link_count(card),
                        "grado": card.definition.grado,
                        "color": card.definition.color.value,
                        "is_spy": card.definition.is_spy,
                        "is_logistron": card.definition.is_logistron,
                        "allowed_layers": card.definition.allowed_layers,
                        "abilities": [a.description for a in card.definition.abilities] if card.definition.abilities else [],
                        "abilities_meta": [{"desc": a.description, "type": a.ability_type.name,
                                           "cost": a.action_cost} for a in card.definition.abilities],
                    })
                else:
                    row.append(None)
            board[f"p{p}"].append(row)

    # ─── Hands ───
    def _serialize_hand_card(idx, card):
        d = card.definition
        return {
            "index": idx,
            "name": d.name,
            "color": d.color.value,
            "hp": d.hp,
            "damage_bonus": d.damage_bonus,
            "link_capacity": d.link_capacity,
            "grado": d.grado,
            "allowed_layers": d.allowed_layers,
            "allowed_formations": d.allowed_formations,
            "is_spy": d.is_spy,
            "is_logistron": d.is_logistron,
            "abilities": [a.description for a in d.abilities] if d.abilities else [],
            "abilities_meta": [{"desc": a.description, "type": a.ability_type.name,
                               "cost": a.action_cost} for a in d.abilities],
        }

    hands = []
    for p in [0, 1]:
        hands.append([_serialize_hand_card(i, c) for i, c in enumerate(game.hands[p])])

    # Filtered hand for MP mode
    hand = None
    opponent_hand_size = None
    if player_id is not None:
        hand = hands[player_id]
        opponent_hand_size = len(game.hands[1 - player_id])

    # ─── Squads ───
    squads = {"p0": [], "p1": []}
    for p in [0, 1]:
        player_squads = game.get_player_squads(p)
        for s in player_squads:
            members = []
            for cid in s.members:
                card = game.all_cards.get(cid)
                if card and card.position:
                    _, li, m = card.position
                    members.append({"layer": li, "meridian": m})
            squads[f"p{p}"].append({
                "type": s.squad_type,
                "damage": s.base_damage,
                "potenciamiento": s.empowerment,
                "color": s.dominant_color.value if s.dominant_color else "Incoloro",
                "members": members,
                "members_ids": list(s.members),
            })

    # ─── Links ───
    links = {}
    links_pairs = []
    for cid, c in game.all_cards.items():
        if c.position:
            owner_p, owner_li, owner_m = c.position
            owner_li_idx = owner_li - 1  # 1-indexed → 0-indexed for DOM
            pos_key = f"{owner_p},{owner_li_idx},{owner_m}"
            linked = list(game.network.links.get(cid, set()))
            if linked:
                links[pos_key] = [
                    f"{game.all_cards[lid].position[0]},"
                    f"{game.all_cards[lid].position[1]-1},"
                    f"{game.all_cards[lid].position[2]}"
                    for lid in linked
                    if game.all_cards.get(lid) and game.all_cards[lid].position
                ]
                for lid in linked:
                    if cid < lid:
                        tc = game.all_cards.get(lid)
                        if tc and tc.position:
                            tp, tl, tm = tc.position
                            has_logi = c.definition.is_logistron or tc.definition.is_logistron
                            links_pairs.append({
                                "from": f"{owner_p},{owner_li_idx},{owner_m}",
                                "to": f"{tp},{tl-1},{tm}",
                                "has_logistron": has_logi,
                            })

    # ─── Assemble response ───
    state = {
        "active_player": game.active_player,
        "phase": game.phase.value,
        "game_over": game.game_over,
        "winner": game.winner,
        "seals": game.seals[:],
        "turn": game.turn_number,
        "actions": game.actions_remaining,
        "hand_sizes": [len(game.hands[0]), len(game.hands[1])],
        "deck_sizes": [len(game.decks[0]), len(game.decks[1])],
        "discard_sizes": [len(game.discard_piles[0]), len(game.discard_piles[1])],
        "discard_piles": [
            [{"name": c.definition.name, "color": c.definition.color.value,
              "hp": c.definition.hp, "damage_bonus": c.definition.damage_bonus,
              "link_capacity": c.definition.link_capacity, "id": c.card_id}
             for c in game.discard_piles[0]],
            [{"name": c.definition.name, "color": c.definition.color.value,
              "hp": c.definition.hp, "damage_bonus": c.definition.damage_bonus,
              "link_capacity": c.definition.link_capacity, "id": c.card_id}
             for c in game.discard_piles[1]],
        ],
        "attached": {str(k): v for k, v in game._attached.items()},
        "board": board,
        "frontier": frontier,
        "hands": hands,
        "squads": squads,
        "links": links,
        "links_pairs": links_pairs,
        "log": game.log[-10:] if game.log else [],
    }


    # ─── Pending faction-effect choices (audit #7) ───
    pending_faction_choice = None
    pending_politico_swap = None
    pfc = getattr(game, "pending_faction_choices", None)
    pps = getattr(game, "pending_politico_swap", None)
    if pfc and (player_id is None or player_id == game.active_player):
        sab = pfc.get("saboteador") or {}
        mon = pfc.get("monstruo") or {}
        pending_faction_choice = {
            "saboteador": {
                "max": sab.get("max", 0),
                "links": [
                    {"a": _card_brief(game, cid), "b": _card_brief(game, nid)}
                    for cid, nid in (sab.get("links") or [])
                ],
            },
            "monstruo": {
                "max": mon.get("max", 0),
                "damage": mon.get("damage", 0),
                "nodes": [_card_brief(game, cid) for cid in (mon.get("nodes") or [])],
            },
        }
    if pps and (player_id is None or player_id == game.active_player):
        pairs = pps.get("pairs") or []
        seen_cards = {}
        for a_id, b_id in pairs:
            for cid in (a_id, b_id):
                card = game.all_cards.get(cid)
                if card and cid not in seen_cards:
                    seen_cards[cid] = card
        pending_politico_swap = {
            "max": pps.get("max", 0),
            "cards": [{
                "id": cid,
                "name": card.definition.name,
                "color": card.definition.color.value,
                "grado": card.definition.grado,
                "layer": card.position[1] if card.position else None,
                "meridian": card.position[2] if card.position else None,
            } for cid, card in sorted(seen_cards.items())],
            "pairs": [[a_id, b_id] for a_id, b_id in pairs],
        }

    if player_id is not None:
        state["hand"] = hand
        state["opponent_hand_size"] = opponent_hand_size
        state["player_id"] = player_id
        state["pending_attack"] = pending_attack
        state["pending_faction_choice"] = pending_faction_choice
        state["pending_politico_swap"] = pending_politico_swap

    else:
        state["pending_faction_choice"] = pending_faction_choice
        state["pending_politico_swap"] = pending_politico_swap

    return state


def _card_brief(game, cid):
    """Minimal card info for choice pickers (audit #7)."""
    card = game.all_cards.get(cid)
    if not card:
        return {"id": cid, "name": "?", "grado": 0}
    return {
        "id": cid,
        "name": card.definition.name,
        "grado": card.definition.grado,
        "color": card.definition.color.value,
        "layer": card.position[1] if card.position else None,
        "meridian": card.position[2] if card.position else None,
    }
