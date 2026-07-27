"""
Network Fantasy War — Web UI
Flask server for browser-based gameplay.
"""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, session
from prototype.card import ALL_CARDS, Color
from prototype.game import GameState, Phase
from prototype.decks import DECKS, DECK_NAMES

app = Flask(__name__)
app.secret_key = 'nfw-secret-key-2024'

# Store game state per session
games = {}
pending_attacks = {}  # sid -> {attacker, squad_idx, target}

def get_game():
    """Get or create game for current session."""
    sid = session.get('game_id')
    if sid and sid in games:
        return games[sid]
    return None

@app.route('/')
def index():
    return render_template('game.html')

@app.route('/api/decks')
def api_decks():
    """List available decks with stats."""
    from collections import Counter
    result = {}
    for k, v in DECKS.items():
        colors = Counter(c.color.value for c in v)
        avg_v = round(sum(c.link_capacity for c in v) / len(v), 1)
        avg_d = round(sum(c.damage_bonus for c in v) / len(v), 1)
        spies = sum(1 for c in v if c.is_spy)
        logis = sum(1 for c in v if c.is_logistron)
        result[k] = {
            "name": DECK_NAMES[k], "count": len(v),
            "avg_v": avg_v, "avg_d": avg_d,
            "spies": spies, "logistrones": logis,
            "colors": dict(colors),
        }
    return jsonify(result)


@app.route('/api/decks/<deck_key>')
def api_deck_detail(deck_key):
    """Return detailed card list for a specific deck."""
    if deck_key not in DECKS:
        return jsonify({"error": "Deck no encontrado"}), 404
    deck = DECKS[deck_key]
    cards = []
    for c in deck:
        abilities = [a.description for a in c.abilities] if c.abilities else []
        cards.append({
            "name": c.name, "color": c.color.value,
            "hp": c.hp, "v": c.link_capacity, "d": c.damage_bonus,
            "layers": c.allowed_layers,
            "formations": c.allowed_formations if c.allowed_formations else [],
            "is_spy": c.is_spy, "is_logistron": c.is_logistron,
            "abilities": abilities,
        })
    return jsonify({
        "key": deck_key, "name": DECK_NAMES[deck_key], "count": len(cards),
        "cards": sorted(cards, key=lambda x: (x["color"], x["name"]))
    })


@app.route('/rules')
def serve_rules():
    """Serve the rules reference PDF."""
    from flask import send_file as _send_file
    rules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               'rules-reference-comprehensive.pdf')
    return _send_file(rules_path, mimetype='application/pdf')

@app.route('/api/new_game', methods=['POST'])
def api_new_game():
    """Start a new game with selected decks."""
    data = request.get_json()
    deck1 = data.get('deck1', 'filo')
    deck2 = data.get('deck2', 'jardin')
    
    sid = os.urandom(8).hex()
    session['game_id'] = sid
    
    game = GameState(DECKS[deck1][:], DECKS[deck2][:])
    game.start_turn()
    game.entry_phase()
    games[sid] = game
    
    return jsonify({"game_id": sid, "state": game_state(game)})

@app.route('/api/state')
def api_state():
    """Get current game state."""
    game = get_game()
    if not game:
        return jsonify({"error": "No active game"}), 404
    return jsonify(game_state(game))

@app.route('/api/action', methods=['POST'])
def api_action():
    """Execute a game action."""
    game = get_game()
    if not game:
        return jsonify({"error": "No active game"}), 404
    
    data = request.get_json()
    action = data.get('action')
    args = data.get('args', {})
    player = game.active_player
    
    result = {"ok": False, "error": None}
    
    if action == 'play':
        idx = args.get('hand_index')
        layer = args.get('layer')
        meridian = args.get('meridian')
        err = game.play_card(player, idx, layer, meridian)
        if err: result["error"] = err
        else: result["ok"] = True
    
    elif action == 'link':
        id_a = args.get('card_a')
        id_b = args.get('card_b')
        card_a = game.all_cards.get(id_a)
        card_b = game.all_cards.get(id_b)
        if card_a and card_b:
            err = game.link_cards(player, card_a, card_b)
            if err: result["error"] = err
            else: result["ok"] = True
        else:
            result["error"] = "Card not found"
    
    elif action == 'ascend':
        card_id = args.get('card_id')
        card = game.all_cards.get(card_id)
        if card:
            err = game.ascend(player, card)
            if err: result["error"] = err
            else: result["ok"] = True
    
    elif action == 'move':
        card_id = args.get('card_id')
        direction = args.get('direction', 0)
        card = game.all_cards.get(card_id)
        if card:
            err = game.move_card(player, card, direction)
            if err: result["error"] = err
            else: result["ok"] = True
        else:
            result["error"] = "Carta no encontrada."
    
    elif action == 'attack':
        squad_idx = args.get('squad_index', 0)
        target = args.get('target', 'grimoire')
        target_id = args.get('target_id')
        
        squads = game.get_player_squads(player)
        if not squads:
            result["error"] = "No tienes escuadrones para atacar. Forma líneas, triángulos, cuadrados o pentágonos primero."
        elif squad_idx < 0:
            result["error"] = "Selecciona un escuadrón específico de la lista para atacar."
        elif 0 <= squad_idx < len(squads):
            game.start_attack_phase() if game.phase != Phase.ATTACK else None
            # Store pending attack for defense
            sid = session.get('game_id')
            pending_attacks[sid] = {
                'attacker': player,
                'squad_idx': squad_idx,
                'target': target,
                'target_id': target_id,
                'squad_type': squads[squad_idx].squad_type,
                'squad_damage': squads[squad_idx].base_damage,
                'squad_color': squads[squad_idx].dominant_color.value if squads[squad_idx].dominant_color else 'incoloro',
                'members': [game.all_cards[cid].definition.name for cid in squads[squad_idx].members],
            }
            result["ok"] = True
            result["pending_attack"] = pending_attacks[sid]
    
    elif action == 'defend':
        sid = session.get('game_id')
        pa = pending_attacks.pop(sid, None)
        if not pa:
            result["error"] = "No hay ataque pendiente."
        else:
            game.active_player = pa['attacker']  # restore attacker
            squads = game.get_player_squads(pa['attacker'])
            def_squad_idx = args.get('defender_squad_index')
            
            # Get defending squad (may be None = no defense)
            defending_squad = None
            if def_squad_idx is not None and def_squad_idx >= 0:
                def_squads = game.get_player_squads(1 - pa['attacker'])
                if def_squad_idx < len(def_squads):
                    defending_squad = def_squads[def_squad_idx]
            
            if pa['squad_idx'] < len(squads):
                err = game.attack(squads[pa['squad_idx']], pa['target'], defending_squad, pa.get('target_id'))
                if err: result["error"] = err
                else: result["ok"] = True
            else:
                result["error"] = "Escuadrón atacante ya no existe."
    
    elif action == 'next_phase':
        if game.phase == Phase.ACTIONS:
            game.start_attack_phase()
            result["ok"] = True
        elif game.phase == Phase.ATTACK:
            game.exit_phase()
            if not game.game_over:
                game.start_turn()
                game.entry_phase()
            result["ok"] = True
    
    elif action == 'end_turn':
        game.phase = Phase.ATTACK
        game.exit_phase()
        if not game.game_over:
            game.start_turn()
            game.entry_phase()
        result["ok"] = True
    
    elif action == 'surrender':
        game._end_game(1 - player)
        result["ok"] = True
    
    elif action == 'ai_turn':
        result["log"] = []
        # Ensure actions phase is active
        game.phase = Phase.ACTIONS
        game.actions_remaining = 10  # give AI plenty of actions
        # Actions phase: play up to 4 cards with valid layer selection
        for _ in range(4):
            if game.phase != Phase.ACTIONS:
                break
            if not game.hands[player]:
                break
            card = game.hands[player][0]
            if card.definition.is_spy:
                continue
            
            # Determine valid entry layers
            has_vg = any("Vanguardia" in a.description for a in card.definition.abilities)
            has_lf = any("Línea de fuego" in a.description for a in card.definition.abilities)
            valid_layers = [1]
            if has_vg or has_lf: valid_layers.append(2)
            if has_lf: valid_layers.append(3)
            valid_layers = [l for l in valid_layers if l in card.definition.allowed_layers]
            
            played = False
            for layer in valid_layers:
                for m in range(15):
                    if game.board.cells[player][layer-1][m] is None:
                        res = game.play_card(player, 0, layer, m)
                        if res is None:
                            result["log"].append(f"AI juega {card.definition.name} en L{layer}:{m}")
                            played = True
                            break
                if played:
                    break
            if not played:
                break
        
        # Link adjacent cards — link all possible adjacent pairs
        placed = []
        for li in range(3):
            for m in range(15):
                if game.board.cells[player][li][m] is not None:
                    placed.append((li, m))
        
        for ci_idx, ci in enumerate(placed):
            for cj in placed[ci_idx+1:]:
                if ci[0] == cj[0] and abs(ci[1] - cj[1]) <= 2:
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
                    res = game.link_cards(player, a_card, b_card)
                    if res is None:
                        result["log"].append(f"AI vincula L{ci[0]+1}:{ci[1]} - L{cj[0]+1}:{cj[1]}")
        
        # Attack phase
        if game.phase == Phase.ACTIONS:
            game.start_attack_phase()
            result["log"].append("AI entra en fase de ataque")
        
        if game.phase == Phase.ATTACK:
            squads = game.get_player_squads(player)
            for sq_idx, squad in enumerate(squads):
                if sq_idx > 1:  # limit to 2 attacks
                    break
                err = game.attack(squad, 'grimoire')
                if err is None:
                    result["log"].append(f"AI ataca grimorio con escuadron {sq_idx} ({squad.type})")
                    if game.game_over:
                        break
        
        # End turn
        game.exit_phase()
        if not game.game_over:
            game.start_turn()
            game.entry_phase()
        result["ok"] = True
        result["log"].append("AI termina turno")
    
    elif action == 'spy':
        idx = args.get('hand_index')
        card = game.hands[player][idx] if idx < len(game.hands[player]) else None
        if card and card.definition.is_spy:
            err = game.play_card(player, idx, 0, 0)
            if err: result["error"] = err
            else: result["ok"] = True
    
    elif action == 'use_ability':
        card_id = args.get('card_id')
        ability_index = args.get('ability_index', 0)
        targets = args.get('targets', {})
        card = game.all_cards.get(card_id)
        if card:
            err = game.use_ability(player, card, ability_index, targets)
            if err: result["error"] = err
            else: result["ok"] = True
        else:
            result["error"] = "Carta no encontrada."
    
    result["state"] = game_state(game)
    return jsonify(result)


def game_state(game):
    """Serialize game state to JSON."""
    # Board cells
    board = {"p0": [], "p1": [], "frontier": []}
    for p in [0, 1]:
        for layer in range(3):
            row = []
            for m in range(15):
                cid = game.board.cells[p][layer][m]
                if cid:
                    card = game.all_cards[cid]
                    owner_mark = "*" if card.owner != p else ""
                    row.append({
                        "id": cid,
                        "name": card.definition.name,
                        "short": card.definition.name[:4],
                        "hp": card.current_hp,
                        "max_hp": card.definition.hp,
                        "d": card.definition.damage_bonus,
                        "v": card.definition.link_capacity,
                        "v_used": game.network.link_count(card),
                        "color": card.definition.color.value,
                        "layer_restrict": card.definition.allowed_layers,
                        "is_spy": card.definition.is_spy,
                        "is_logistron": card.definition.is_logistron,
                        "owner": card.owner,
                        "foreign": owner_mark,
                        "abilities": [a.description for a in card.definition.abilities] if card.definition.abilities else [],
                        "abilities_meta": [{"desc": a.description, "type": a.ability_type.name, "cost": a.action_cost} for a in card.definition.abilities],
                    })
                else:
                    row.append(None)
            board[f"p{p}"].append(row)
    
    # Frontier spies
    for cid in game.board.frontier_cards:
        card = game.all_cards[cid]
        board["frontier"].append({
            "id": cid,
            "name": card.definition.name,
            "owner": card.owner,
        })
    
    # Hands
    hands = []
    for p in [0, 1]:
        hand = []
        for i, card in enumerate(game.hands[p]):
            hand.append({
                "index": i,
                "id": card.card_id,
                "name": card.definition.name,
                "color": card.definition.color.value,
                "hp": card.definition.hp,
                "d": card.definition.damage_bonus,
                "v": card.definition.link_capacity,
                "layers": card.definition.allowed_layers,
                "forms": card.definition.allowed_formations,
                "is_spy": card.definition.is_spy,
                "is_logistron": card.definition.is_logistron,
                "abilities": [a.description[:50] for a in card.definition.abilities],
                "abilities_meta": [{"desc": a.description, "type": a.ability_type.name, "cost": a.action_cost} for a in card.definition.abilities],
            })
        hands.append(hand)
    
    # Squads (all players, always available)
    squads = {"p0": [], "p1": []}
    for p in [0, 1]:
        player_squads = game.get_player_squads(p)
        for s in player_squads:
            members = []
            for cid in s.members:
                c = game.all_cards.get(cid)
                if c:
                    members.append({"id": cid, "name": c.definition.name})
            squads[f"p{p}"].append({
                "type": s.squad_type,
                "damage": s.base_damage,
                "empowerment": s.empowerment,
                "color": s.dominant_color.value if s.dominant_color else "incoloro",
                "members": members,
            })
    
    # Pending attack info
    sid = session.get('game_id', '')
    pa = pending_attacks.get(sid)
    
    # Links — also provide as pairs for SVG drawing
    links = {}
    links_pairs = []  # [{from_id, to_id, from_layer, from_m, to_layer, to_m, p0, p1}]
    for cid, c in game.all_cards.items():
        if c.position:
            linked = list(game.network.links.get(cid, set()))
            if linked:
                links[cid] = linked
                for lid in linked:
                    if cid < lid:  # each pair once
                        tc = game.all_cards.get(lid)
                        if tc and tc.position:
                            _, fl, fm = c.position
                            _, tl, tm = tc.position
                            links_pairs.append({
                                "from": cid, "to": lid,
                                "p0": c.owner, "l0": fl, "m0": fm,
                                "p1": tc.owner, "l1": tl, "m1": tm,
                            })
    
    return {
        "active_player": game.active_player,
        "phase": game.phase.value,
        "actions": game.actions_remaining,
        "turn": game.turn_number,
        "seals": game.seals,
        "hand_sizes": [len(game.hands[0]), len(game.hands[1])],
        "deck_sizes": [len(game.decks[0]), len(game.decks[1])],
        "game_over": game.game_over,
        "winner": game.winner,
        "board": board,
        "hands": hands,
        "squads": squads,
        "links": links,
        "links_pairs": links_pairs,
        "pending_attack": pa,
        "log": game.log[-10:] if game.log else [],
    }


if __name__ == '__main__':
    print("╔══════════════════════════════════════════╗")
    print("║   NETWORK FANTASY WAR — Web UI         ║")
    print("║   http://localhost:5000                ║")
    print("╚══════════════════════════════════════════╝")
    app.run(debug=True, host='0.0.0.0', port=5000)
