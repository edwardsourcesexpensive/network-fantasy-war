"""
Network Fantasy War — Multiplayer Server
Flask-SocketIO real-time online play for 2 players.
"""
import os, random, string, secrets
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prototype.game import GameState, Phase
from prototype.decks import DECKS, DECK_NAMES

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*")

# ─── Room management ───────────────────────────────────────
rooms = {}  # code -> {players: {sid: {player_id, deck}}, game: GameState, active_sid: str, state: dict}

def gen_code():
    """4-char room code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))


def filtered_state(game, player_id, pending_attack=None):
    """Build complete game state with per-player hand filtering."""
    # Board cells
    board = {"p0": [], "p1": []}
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
                        "abilities": [a.description for a in card.definition.abilities] if card.definition.abilities else [],
                        "abilities_meta": [{"desc": a.description, "type": a.ability_type.name, "cost": a.action_cost} for a in card.definition.abilities],
                        "allowed_layers": card.definition.allowed_layers,
                    })
                else:
                    row.append(None)
            board[f"p{p}"].append(row)
    
    # Hand: only show requesting player's hand
    hand = []
    for i, card in enumerate(game.hands[player_id]):
        d = card.definition
        hand.append({
            "index": i,
            "name": d.name,
            "color": d.color.value,
            "hp": d.hp,
            "damage_bonus": d.damage_bonus,
            "link_capacity": d.link_capacity,
            "grado": d.grado,
            "allowed_layers": d.allowed_layers,
            "allowed_formations": d.allowed_formations,
            "abilities": [a.description for a in d.abilities] if d.abilities else [],
            "is_spy": d.is_spy,
        })
    opp_hand_size = len(game.hands[1 - player_id])
    
    # Squads
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
            })
    
    # Links — use position-based keys matching DOM data-cid format
    links = {}
    links_pairs = []
    for cid, c in game.all_cards.items():
        if c.position:
            owner_p, owner_li, owner_m = c.position
            # position uses 1-indexed layers, convert to 0-indexed for data-cid
            owner_li_idx = owner_li - 1
            pos_key = f"{owner_p},{owner_li_idx},{owner_m}"
            linked = list(game.network.links.get(cid, set()))
            if linked:
                links[pos_key] = [f"{game.all_cards[lid].position[0]},{game.all_cards[lid].position[1]-1},{game.all_cards[lid].position[2]}" for lid in linked if game.all_cards.get(lid) and game.all_cards[lid].position]
                for lid in linked:
                    if cid < lid:
                        tc = game.all_cards.get(lid)
                        if tc and tc.position:
                            tp, tl, tm = tc.position
                            # Check if either card is a logistron
                            has_logi = c.definition.is_logistron or tc.definition.is_logistron
                            links_pairs.append({
                                "from": f"{owner_p},{owner_li_idx},{owner_m}",
                                "to": f"{tp},{tl-1},{tm}",
                                "has_logistron": has_logi,
                            })
    
    return {
        "active_player": game.active_player,
        "phase": game.phase.value,
        "game_over": game.game_over,
        "winner": game.winner,
        "seals": game.seals[:],
        "turn": game.turn_number,
        "actions": game.actions_remaining,
        "hand": hand,
        "opponent_hand_size": opp_hand_size,
        "deck_sizes": [len(game.decks[0]), len(game.decks[1])],
        "hand_sizes": [len(game.hands[0]), len(game.hands[1])],
        "discard_sizes": [len(game.discard_piles[0]), len(game.discard_piles[1])],
        "attached": {str(k): v for k, v in game._attached.items()},
        "player_id": player_id,
        "board": board,
        "links": links,
        "links_pairs": links_pairs,
        "squads": squads,
        "pending_attack": pending_attack,
        "log": game.log[-10:] if game.log else [],
    }


# ─── Routes ────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('lobby.html')

@app.route('/mp-game')
def mp_game():
    return render_template('mp-game.html')

@app.route('/api/decks')
def api_decks():
    from collections import Counter
    result = {}
    for k, v in DECKS.items():
        colors = Counter(c.color.value for c in v)
        avg_v = round(sum(c.link_capacity for c in v) / len(v), 1)
        avg_d = round(sum(c.damage_bonus for c in v) / len(v), 1)
        spies = sum(1 for c in v if c.is_spy)
        logis = sum(1 for c in v if c.is_logistron)
        result[k] = {
            "name": DECK_NAMES[k],
            "count": len(v),
            "avg_v": avg_v,
            "avg_d": avg_d,
            "spies": spies,
            "logistrones": logis,
            "colors": dict(colors),
        }
    return jsonify(result)


@app.route('/api/decks/<deck_key>')
def api_deck_detail(deck_key):
    """Return detailed card list for a specific deck."""
    if deck_key not in DECKS:
        return jsonify({"error": "Deck no encontrado"}), 404
    deck = DECKS[deck_key]
    import sys, os as _os
    _here = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from prototype.game import ability_implementation_status
    
    cards = []
    for c in deck:
        abilities = [a.description for a in c.abilities] if c.abilities else []
        abilities_data = []
        impl_count = 0
        for a in (c.abilities or []):
            status = ability_implementation_status(a)
            if status == "implemented":
                impl_count += 1
            abilities_data.append({
                "desc": a.description,
                "type": a.ability_type.name,
                "cost": a.action_cost,
                "status": status,
            })
        cards.append({
            "name": c.name,
            "color": c.color.value,
            "hp": c.hp,
            "v": c.link_capacity,
            "d": c.damage_bonus,
            "layers": c.allowed_layers,
            "formations": c.allowed_formations if c.allowed_formations else [],
            "is_spy": c.is_spy,
            "is_logistron": c.is_logistron,
            "abilities": abilities,
            "abilities_detail": abilities_data,
            "impl_count": impl_count,
            "total_abilities": len(c.abilities) if c.abilities else 0,
        })
    return jsonify({
        "key": deck_key,
        "name": DECK_NAMES[deck_key],
        "count": len(cards),
        "cards": sorted(cards, key=lambda x: (x["color"], x["name"]))
    })


@app.route('/rules')
def serve_rules():
    """Serve the rules reference PDF."""
    import os as _os
    from flask import send_file as _send_file
    rules_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), 
                                'rules-reference-comprehensive.pdf')
    return _send_file(rules_path, mimetype='application/pdf')


# ─── Socket Events ─────────────────────────────────────────
@socketio.on('create_room')
def on_create(data):
    code = gen_code()
    while code in rooms:
        code = gen_code()
    deck_key = data.get('deck', 'filo')
    if deck_key not in DECKS:
        emit('error', {"message": f"Mazo desconocido: {deck_key}"})
        return
    p0_token = secrets.token_hex(16)
    rooms[code] = {
        "players": {request.sid: {"player_id": 0, "deck": deck_key}},
        "game": None,
        "host_sid": request.sid,
        "player_tokens": {"0": p0_token},
    }
    join_room(code)
    emit('room_created', {"code": code, "player_id": 0, "token": p0_token})
    print(f"[Room {code}] Created by {request.sid} (host, P0)")


@socketio.on('create_solo_room')
def on_create_solo(data):
    """Create a room with human + AI bot."""
    code = gen_code()
    while code in rooms:
        code = gen_code()
    deck_key = data.get('deck', 'filo')
    
    # Pick AI deck (different from human's)
    ai_keys = [k for k in DECKS if k != deck_key]
    import random
    ai_deck_key = random.choice(ai_keys)
    
    # Validate the human's deck key before touching game state.
    if deck_key not in DECKS:
        emit('error', {"message": f"Mazo desconocido: {deck_key}"})
        return

    rooms[code] = {
        "players": {request.sid: {"player_id": 0, "deck": deck_key}},
        "game": None,
        "host_sid": request.sid,
        "solo": True,
        "bot_deck": ai_deck_key,
        "player_tokens": {"0": secrets.token_hex(16)},
    }
    join_room(code)
    
    # Start game immediately
    room = rooms[code]
    deck1 = DECKS[deck_key][:]
    deck2 = DECKS[ai_deck_key][:]
    game = GameState(deck1, deck2)
    game.start_turn()
    game.entry_phase()
    room["game"] = game
    
    s = filtered_state(game, 0)
    s["room_code"] = code
    s["solo"] = True
    emit('solo_started', s)
    print(f"[Room {code}] Solo game vs AI ({ai_deck_key}) started")


def play_bot_turn(game, player_id):
    """Execute AI turn for the bot player. Returns list of log messages."""
    logs = []
    
    # Ensure we're in actions phase
    game.phase = Phase.ACTIONS
    game.actions_remaining = 10  # give AI plenty of actions
    
    # Actions phase: play up to 4 cards
    for _ in range(4):
        if game.phase != Phase.ACTIONS:
            break
        if not game.hands[player_id]:
            break
        # Skip spies — pop them to try the next card
        card = game.hands[player_id][0]
        if card.definition.is_spy:
            game.hands[player_id].pop(0)  # discard spy
            continue
        played = False
        for li in range(3):
            for m in range(15):
                if game.board.cells[player_id][li][m] is None:
                    res = game.play_card(player_id, 0, li + 1, m)
                    if res is None:
                        logs.append(f"IA juega {card.definition.name} en L{li+1}:{m}")
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
            if game.board.cells[player_id][li][m] is not None:
                placed.append((li, m))
    
    linked_any = False
    for ci_idx, ci in enumerate(placed):
        for cj in placed[ci_idx+1:]:
            if ci[0] == cj[0] and abs(ci[1] - cj[1]) <= 2:
                cid_a = game.board.cells[player_id][ci[0]][ci[1]]
                cid_b = game.board.cells[player_id][cj[0]][cj[1]]
                a_card = game.all_cards.get(cid_a)
                b_card = game.all_cards.get(cid_b)
                if not a_card or not b_card:
                    continue
                if game.network.link_count(a_card) >= a_card.definition.link_capacity:
                    continue
                if game.network.link_count(b_card) >= b_card.definition.link_capacity:
                    continue
                res = game.link_cards(player_id, a_card, b_card)
                if res is None:
                    logs.append(f"IA vincula L{ci[0]+1}:{ci[1]} - L{cj[0]+1}:{cj[1]}")
                    linked_any = True
    
    # Attack phase
    if game.phase == Phase.ACTIONS:
        game.start_attack_phase()
        logs.append("IA entra en fase de ataque")
    
    if game.phase == Phase.ATTACK:
        squads = game.get_player_squads(player_id)
        for sq_idx, squad in enumerate(squads[:2]):  # max 2 attacks
            err = game.attack(squad, 'grimoire')
            if err is None:
                logs.append(f"IA ataca con escuadron {sq_idx} ({squad.squad_type})")
                if game.game_over:
                    break
    
    # End turn — skip exit_phase to avoid purging human cards, manually switch player
    if not game.game_over:
        game.active_player = 1 - game.active_player  # switch to human
        game.phase = Phase.ACTIONS
        game.start_turn()
        game.entry_phase()
    logs.append("IA termina turno")
    return logs


@socketio.on('join_room')
def on_join(data):
    code = data.get('code', '').upper()
    if code not in rooms:
        emit('error', {"message": "Sala no encontrada."})
        return
    room = rooms[code]
    if len(room["players"]) >= 2:
        emit('error', {"message": "Sala llena."})
        return
    if request.sid in room["players"]:
        emit('error', {"message": "Ya estas en esta sala."})
        return

    deck_key = data.get('deck', 'jardin')
    if deck_key not in DECKS:
        emit('error', {"message": f"Mazo desconocido: {deck_key}"}, to=request.sid)
        return
    p1_token = secrets.token_hex(16)
    room.setdefault("player_tokens", {})["1"] = p1_token
    room["players"][request.sid] = {"player_id": 1, "deck": deck_key}
    join_room(code)

    emit('room_joined', {"code": code, "player_id": 1, "token": p1_token}, to=request.sid)
    emit('opponent_joined', {"message": "Oponente conectado."}, to=room["host_sid"])

    # Start game: both players ready
    host = room["players"][room["host_sid"]]
    joiner = room["players"][request.sid]
    deck1 = DECKS[host["deck"]][:]
    deck2 = DECKS[joiner["deck"]][:]

    game = GameState(deck1, deck2)
    game.start_turn()
    game.entry_phase()
    room["game"] = game

    # Send filtered state to each player
    for sid, pinfo in room["players"].items():
        s = filtered_state(game, pinfo["player_id"])
        s["room_code"] = code
        emit('state_update', s, to=sid)

    print(f"[Room {code}] {request.sid} joined. Game started.")


@socketio.on('rejoin_game')
def on_rejoin(data):
    """Rejoin a room after page navigation (new socket connection)."""
    code = data.get('code', '').upper()
    player_id = data.get('player_id')
    token = data.get('token', '')

    if code not in rooms:
        emit('error', {"message": "Sala no encontrada."})
        return

    room = rooms[code]
    if not room["game"]:
        emit('error', {"message": "Juego no iniciado."})
        return

    # Authenticate: the reconnecting client must prove it owns this seat.
    # player_tokens[code][player_id] was minted server-side when the seat
    # was created and is only ever sent to that seat's socket.
    expected = room.get("player_tokens", {}).get(str(player_id))
    if not expected or token != expected:
        emit('error', {"message": "No autorizado para reconectar a ese asiento."})
        print(f"[Room {code}] REJECTED rejoin for player {player_id} (bad token) from {request.sid}")
        return

    # Update the player's socket to the new connection
    old_sid = None
    for sid, pinfo in room["players"].items():
        if pinfo["player_id"] == player_id:
            old_sid = sid
            break

    if old_sid:
        del room["players"][old_sid]

    room["players"][request.sid] = {"player_id": player_id, "deck": None}
    join_room(code)

    # Send current state to the reconnected player
    s = filtered_state(room["game"], player_id)
    s["room_code"] = code
    emit('state_update', s, to=request.sid)
    print(f"[Room {code}] Player {player_id} rejoined (new SID: {request.sid})")


@socketio.on('game_action')
def on_action(data):
    """Process a game action from the active player's client."""
    # Find the room this socket belongs to
    code = None
    for c, room in rooms.items():
        if request.sid in room["players"]:
            code = c
            break
    if code is None:
        emit('error', {"message": "No estas en ninguna sala."})
        return

    room = rooms[code]
    game = room["game"]
    if not game:
        emit('error', {"message": "El juego no ha empezado."})
        return

    player_info = room["players"][request.sid]
    player_id = player_info["player_id"]

    action = data.get('action')
    args = data.get('args', {})

    # Allow defend and surrender regardless of whose turn it is
    if action not in ('defend', 'surrender') and game.active_player != player_id:
        emit('error', {'message': 'No es tu turno.'})
        return

    result = {}
    err = None

    if action == 'play':
        hi = args.get('hand_index', 0)
        layer = args.get('layer', 1)
        meridian = args.get('meridian', 0)
        err = game.play_card(player_id, hi, layer, meridian)

    elif action == 'link':
        ca = args.get('card_a')
        cb = args.get('card_b')
        if not ca or not cb:
            err = "Selecciona dos cartas para vincular."
        else:
            def _parse_cell(s):
                try:
                    p = tuple(int(x) for x in str(s).split(','))
                    if len(p) != 3:
                        return None
                    if not (0 <= p[0] < 2 and 0 <= p[1] < 3 and 0 <= p[2] < 15):
                        return None
                    return p
                except (ValueError, TypeError):
                    return None
            pa = _parse_cell(ca)
            pb = _parse_cell(cb)
            cid_a = game.board.cells[pa[0]][pa[1]][pa[2]] if pa else None
            cid_b = game.board.cells[pb[0]][pb[1]][pb[2]] if pb else None
            card_a = game.all_cards.get(cid_a) if cid_a else None
            card_b = game.all_cards.get(cid_b) if cid_b else None
            if card_a and card_b:
                err = game.link_cards(player_id, card_a, card_b)
            else:
                err = "Cartas no encontradas en el tablero."

    elif action == 'ascend':
        cid = args.get('card_id', '')
        card = None
        try:
            parts = str(cid).split(',')
            li, m = int(parts[1]), int(parts[2])
            if 0 <= li < 3 and 0 <= m < 15:
                cell_cid = game.board.cells[player_id][li][m]
                card = game.all_cards.get(cell_cid) if cell_cid else None
        except (ValueError, TypeError, IndexError):
            card = None
        if card:
            err = game.ascend(player_id, card)
        else:
            err = "Carta no encontrada."

    elif action == 'move':
        cid = args.get('card_id', '')
        card = None
        try:
            parts = str(cid).split(',')
            li, m = int(parts[1]), int(parts[2])
            if 0 <= li < 3 and 0 <= m < 15:
                cell_cid = game.board.cells[player_id][li][m]
                card = game.all_cards.get(cell_cid) if cell_cid else None
        except (ValueError, TypeError, IndexError):
            card = None
        direction = args.get('direction', 0)
        if card:
            err = game.move_card(player_id, card, direction)
        else:
            err = "Carta no encontrada."

    elif action == 'use_ability':
        card_id = args.get('card_id')
        ability_index = args.get('ability_index', 0)
        targets = args.get('targets', {})
        card = game.all_cards.get(card_id)
        if card:
            err = game.use_ability(player_id, card, ability_index, targets)
        else:
            err = "Carta no encontrada."

    elif action == 'attack':
        si = args.get('squad_index', 0)
        squads = game.get_player_squads(player_id)
        if not squads:
            err = "No tienes escuadrones. Forma triangulos, cuadrados o pentagonos."
        elif 0 <= si < len(squads):
            squad = squads[si]
            if room.get("solo"):
                # Solo mode: resolve immediately (defense vs bot not used here)
                if game.phase != Phase.ATTACK:
                    game.start_attack_phase()
                target = args.get('target', 'grimoire')
                target_id = args.get('target_id')
                print(f"[Room {code}] Attack (solo): player={player_id}, squad={si}/{len(squads)}, target={target}")
                err = game.attack(squad, target, None, target_id)
                print(f"[Room {code}] Attack result: err={err}, seals={game.seals}")
            else:
                # PvP mode: store pending attack for opponent's defense.
                # Ensure we are in ATTACK phase so defend can resolve it.
                if game.phase != Phase.ATTACK:
                    game.start_attack_phase()
                print(f"[Room {code}] Attack pending: player={player_id}, squad={si}/{len(squads)}")
                room['pending_attack'] = {
                    'attacker': player_id,
                    'squad_idx': si,
                    'members_ids': list(squad.members),  # stable identity across recomputation
                    'target': args.get('target', 'grimoire'),
                    'target_id': args.get('target_id'),
                    'squad_type': squad.squad_type,
                    'squad_damage': squad.base_damage,
                    'squad_color': squad.dominant_color.value if squad.dominant_color else 'incoloro',
                    'members': [game.all_cards[cid].definition.name for cid in squad.members],
                }
        else:
            err = "Escuadron no encontrado."

    elif action == 'defend':
        di = args.get('defender_squad_index', -1)
        pa = room.get('pending_attack')
        if not pa:
            err = "No hay ataque pendiente."
        elif player_id == pa['attacker']:
            # The attacker may NOT resolve their own attack (defense bypass).
            err = "Solo el defensor puede resolver este ataque."
        else:
            room.pop('pending_attack', None)  # only consume once the defender acts
            game.active_player = pa['attacker']  # restore attacker
            # Re-locate the attacking squad by its stable member ids, not a stale index
            attacker_squads = game.get_player_squads(pa['attacker'])
            member_ids = set(pa.get('members_ids') or [])
            attacking_squad = None
            for sq in attacker_squads:
                if set(sq.members) == member_ids:
                    attacking_squad = sq
                    break
            # Fallback: index (legacy) if member ids not stored
            if attacking_squad is None and pa['squad_idx'] < len(attacker_squads):
                attacking_squad = attacker_squads[pa['squad_idx']]
            # Get defending squad (may be None = no defense)
            defending_squad = None
            if di is not None and di >= 0:
                def_squads = game.get_player_squads(1 - pa['attacker'])
                if di < len(def_squads):
                    defending_squad = def_squads[di]
            if attacking_squad is not None:
                err = game.attack(attacking_squad, pa['target'], defending_squad, pa.get('target_id'))
            else:
                err = "Escuadrón atacante ya no existe."

    elif action == 'next_phase':
        if game.phase == Phase.ACTIONS:
            game.start_attack_phase()
        elif game.phase == Phase.ATTACK:
            # Return to actions phase (same player keeps remaining actions)
            game.phase = Phase.ACTIONS

    elif action == 'end_turn':
        if game.active_player != player_id:
            err = "No es tu turno."
        else:
            print(f"[Room {code}] end_turn by player {player_id}")
            game.phase = Phase.ATTACK
            game.exit_phase()
            print(f"[Room {code}] after exit_phase: active_player={game.active_player}")
            if not game.game_over:
                game.start_turn()
                game.entry_phase()

    elif action == 'surrender':
        game._end_game(1 - player_id)
        print(f"[Room {code}] Player {player_id} surrendered. Winner: {game.winner}")

    else:
        emit('error', {"message": f"Accion desconocida: {action}"})
        return

    if err:
        emit('error', {"message": str(err)})
        # SOLO safety net: if a bot attack failed to resolve but more bot
        # attacks remain queued, keep the queue moving so the game never
        # freezes with the human unable to act.
        if room.get("solo") and action == 'defend' and room.get("bot_attacks"):
            room.pop('pending_attack', None)
            next_attack = room['bot_attacks'].pop(0)
            room['pending_attack'] = next_attack
            print(f"[Room {code}] Bot attack error recovered, advancing queue: {err}")
            for sid, pinfo in room["players"].items():
                s = filtered_state(game, pinfo["player_id"], room.get('pending_attack'))
                emit('state_update', s, to=sid)
        return

    # Broadcast updated state to both players
    for sid, pinfo in room["players"].items():
        s = filtered_state(game, pinfo["player_id"], room.get('pending_attack'))
        emit('state_update', s, to=sid)

    # Check game over
    if game.game_over:
        emit('game_over', {
            "winner": game.winner,
            "seals": [game.seals[0], game.seals[1]],
        }, to=code)
        return
    
    # Solo mode: continue bot attacks after defense
    if room.get("solo") and room.get("bot_attacks") and action == 'defend':
        # More bot attacks queued — pop next one
        next_attack = room['bot_attacks'].pop(0)
        room['pending_attack'] = next_attack
        print(f"[Room {code}] Bot next attack: {next_attack['squad_type']}")
        # Broadcast with new pending_attack (triggers another defense popup)
        for sid, pinfo in room["players"].items():
            s = filtered_state(game, pinfo["player_id"], room.get('pending_attack'))
            emit('state_update', s, to=sid)
        return
    
    # Solo mode: bot attacks done, end bot turn
    if room.get("solo") and action == 'defend' and game.active_player == 1:
        print(f"[Room {code}] Bot turn ended, human's turn")
        game.phase = Phase.ATTACK
        game.exit_phase()  # triggers faction effects, purge, discard
        if not game.game_over:
            game.start_turn()
            game.entry_phase()
        for sid, pinfo in room["players"].items():
            s = filtered_state(game, pinfo["player_id"])
            emit('state_update', s, to=sid)
        if game.game_over:
            emit('game_over', {"winner": game.winner, "seals": [game.seals[0], game.seals[1]]}, to=code)
        return
    
    # Solo mode: auto-play bot turn
    if room.get("solo") and game.active_player == 1:
        print(f"[Room {code}] Bot turn triggered, active_player={game.active_player}")
        try:
            def emit_bot_state(logs):
                for sid, pinfo in room["players"].items():
                    s = filtered_state(game, pinfo["player_id"], room.get('pending_attack'))
                    s["log"] = logs[-10:] if logs else []
                    emit('state_update', s, to=sid)
        
            all_logs = []
            socketio.sleep(0.5)
        
            # Step 1: Enter actions phase
            game.phase = Phase.ACTIONS
            game.actions_remaining = 10  # plenty of actions to form squads
            all_logs.append("IA comienza su turno (10 acciones)")
            emit_bot_state(all_logs)
            socketio.sleep(1)
        
            # ═══ Step 2: Play cards (priority: V desc, D desc, prefer squad-friendly positions) ═══
            # Sort hand by link capacity desc, then damage desc
            hand_with_idx = [(i, game.hands[1][i]) for i in range(len(game.hands[1]))]
            # Reserve Vanguardia cards for bridge placement — sort them lower
            def _sort_key(item):
                idx, c = item
                has_vg = any("Vanguardia" in a.description for a in c.definition.abilities)
                vg_penalty = -10 if has_vg else 0  # deprioritize VG cards
                return (vg_penalty, c.definition.link_capacity, c.definition.damage_bonus)
            hand_sorted = sorted(hand_with_idx, key=_sort_key, reverse=True)
        
            # Get existing bot positions to play near them
            def get_bot_positions():
                pos = []
                for li in range(3):
                    for m in range(15):
                        if game.board.cells[1][li][m] is not None:
                            pos.append((li, m))
                return pos
        
            cards_played = 0
            for orig_idx, card in hand_sorted:
                if cards_played >= 4 or game.actions_remaining < 1:
                    break
                if not game.hands[1]:
                    break
            
                # Find card in current hand (indices shifted after plays)
                current_idx = None
                for i, hc in enumerate(game.hands[1]):
                    if hc.card_id == card.card_id:
                        current_idx = i
                        break
                if current_idx is None:
                    continue
            
                # Spy handling: infiltrate to enemy territory
                if card.definition.is_spy:
                    # Try to play on enemy L1 or L2
                    # Spies have special placement rules — just play as normal for now
                    # (spy infiltration is complex, skip for now but don't discard)
                    played_spy = False
                    for li in range(3):
                        for m in range(15):
                            if game.board.cells[1][li][m] is None:
                                res = game.play_card(1, current_idx, li + 1, m)
                                if res is None:
                                    all_logs.append(f"IA infiltra espía {card.definition.name} en L{li+1}:{m}")
                                    cards_played += 1
                                    played_spy = True
                                    break
                        if played_spy:
                            break
                    if played_spy:
                        emit_bot_state(all_logs)
                        socketio.sleep(0.8)
                        continue
                    else:
                        # Can't place spy, skip
                        continue
            
                # Determine valid entry layers for this card
                # Logistrones and spies are exempt from entry rule
                if card.definition.is_logistron:
                    valid_layers = card.definition.allowed_layers
                else:
                    has_vg = any("Vanguardia" in a.description for a in card.definition.abilities)
                    has_lf = any("Línea de fuego" in a.description for a in card.definition.abilities)
                    valid_layers = [1]  # always L1
                    if has_vg or has_lf: valid_layers.append(2)
                    if has_lf: valid_layers.append(3)
                    # Filter by allowed_layers too
                    valid_layers = [l for l in valid_layers if l in card.definition.allowed_layers]
            
                # Try to play near existing cards to form potential squads
                # IMPORTANT: same-layer must have dh>=2 spacing (engine blocks dh=1 adjacency)
                bot_pos = get_bot_positions()
                best_pos = None
            
                if bot_pos:
                    for li_0 in range(3):
                        layer = li_0 + 1
                        if layer not in valid_layers:
                            continue
                        for m in range(15):
                            if game.board.cells[1][li_0][m] is not None:
                                continue
                            # Count existing cards within valid link range (dh=2 for same layer, dh<=1 for cross)
                            near_count = 0
                            for bl, bm in bot_pos:
                                if li_0 == bl and abs(m - bm) == 2:
                                    near_count += 2  # same-layer dh=2 is preferred (triangle-ready)
                                elif li_0 == bl and abs(m - bm) <= 2:
                                    near_count += 0  # dh=1 would fail; dh=0 impossible
                                elif abs(li_0 - bl) == 1 and abs(m - bm) <= 1:
                                    near_count += 1  # cross-layer proximity
                            if near_count >= 1 and (best_pos is None or near_count > best_pos[2]):
                                best_pos = (layer, m, near_count)
            
                if best_pos:
                    layer, m, _ = best_pos
                else:
                    # No existing cards or no good spot — pick first valid layer
                    layer, m = None, None
                    for li_0 in range(3):
                        lyr = li_0 + 1
                        if lyr not in valid_layers:
                            continue
                        found_m = game.board.find_empty_meridian(1, lyr)
                        if found_m is not None:
                            layer, m = lyr, found_m
                            break
                    if layer is None:
                        continue
            
                res = game.play_card(1, current_idx, layer, m)
                if res is None:
                    all_logs.append(f"IA juega {card.definition.name} (V={card.definition.link_capacity}) en L{layer}:{m}")
                    cards_played += 1
                    emit_bot_state(all_logs)
                    socketio.sleep(0.8)
        
            if cards_played == 0:
                all_logs.append("IA no pudo jugar cartas")
                emit_bot_state(all_logs)
                socketio.sleep(0.5)
        
            # ═══ Step 2.4: Vanguardia bridge — play VG card at L2 to enable L1-L2-L1 triangles ═══
            # Only geometry for cross-layer triangle: L1:m, L2:m+1, L1:m+2 (all pairwise corta).
            # Since same-layer placement requires dh>=2, the L2 bridge must be placed directly.
            # Strategy: if any Vanguardia card remains in hand, play it at L2 midpoint of a dh=2 L1 pair.
            if cards_played >= 2 and game.actions_remaining >= 1:
                # Find dh=2 L1 pairs with empty L2 bridge position
                l1_occupied = sorted([m for m in range(15) if game.board.cells[1][0][m] is not None])
                bridge_target = None
            
                for i, m_a in enumerate(l1_occupied):
                    for m_b in l1_occupied[i+1:]:
                        if m_b - m_a != 2:
                            continue
                        bridge_m = m_a + 1
                        if game.board.cells[1][1][bridge_m] is not None:
                            continue
                        # Found valid bridge position — look for Vanguardia card in hand
                        for hi, hc in enumerate(game.hands[1]):
                            if hc.definition.is_spy:
                                continue
                            has_vg = any("Vanguardia" in a.description for a in hc.definition.abilities)
                            if not has_vg:
                                continue
                            if hc.definition.link_capacity < 2:  # triangle needs V>=2
                                continue
                            if 2 not in hc.definition.allowed_layers:
                                continue
                            # Play it at L2:bridge_m
                            err = game.play_card(1, hi, 2, bridge_m)
                            if err is None:
                                all_logs.append(f"IA coloca {hc.definition.name} (Vanguardia) en L2:{bridge_m} — ¡puente de triángulo!")
                                cards_played += 1
                                bridge_target = bridge_m
                                emit_bot_state(all_logs)
                                socketio.sleep(0.8)
                                break
                        if bridge_target is not None:
                            break
                    if bridge_target is not None:
                        break
            
                if bridge_target is not None:
                    all_logs.append(f"IA forma puente L1–L2–L1 en m={bridge_target} — ¡triángulo posible!")
                    emit_bot_state(all_logs)
                    socketio.sleep(0.3)
        
        
            # ═══ Step 2.5: Use ascension abilities (cards with [1]: asciende) ═══
            # ═══ Step 2.5: Use ascension abilities (cards with [1]: asciende) ═══
            for li in range(3):
                for m in range(15):
                    cid = game.board.cells[1][li][m]
                    if not cid:
                        continue
                    card = game.all_cards.get(cid)
                    if not card:
                        continue
                    for ability in card.definition.abilities:
                        if any(kw in ability.description.lower() for kw in ['[1]: asciende', '[1]: Asciende']):
                            if game.actions_remaining >= 1:
                                err = game.ascend(1, card)
                                if err is None:
                                    all_logs.append(f"IA asciende {card.definition.name}")
                                    emit_bot_state(all_logs)
                                    socketio.sleep(0.5)
                                    break
        
            # ═══ Step 2.6: Horizontal movement — reposition for better squad formation ═══
            # Move V>=2 cards closer together to form triangles
            bot_positions = [(li, m, game.board.cells[1][li][m]) for li in range(3) for m in range(15) if game.board.cells[1][li][m]]
            for li, m, cid in bot_positions:
                card = game.all_cards.get(cid)
                if not card or card.definition.link_capacity < 2:
                    continue
                # Check if moving this card would bring it closer to other V>=2 cards
                best_dir = 0
                best_near = 0
                for direction in [-1, 1]:
                    new_m = m + direction
                    if new_m < 0 or new_m >= 15:
                        continue
                    if game.board.cells[1][li][new_m] is not None:
                        continue
                    # Count V>=2 cards within distance 2 on same or adjacent layer
                    near = 0
                    for bli, bm, bcid in bot_positions:
                        if bcid == cid:
                            continue
                        bcard = game.all_cards.get(bcid)
                        if not bcard or bcard.definition.link_capacity < 2:
                            continue
                        if abs(li - bli) <= 1 and abs(new_m - bm) <= 2:
                            near += 1
                    if near > best_near:
                        best_near = near
                        best_dir = direction
                if best_dir != 0:
                    err = game.move_card(1, card, best_dir)
                    if err is None:
                        all_logs.append(f"IA reposiciona {card.definition.name}")
                        emit_bot_state(all_logs)
                        socketio.sleep(0.3)
                        break  # One move per turn to keep it fast
        
            # ═══ Step 3: Smart linking — build squads intentionally ═══
            link_count = 0
            placed = []
            for li in range(3):
                for m in range(15):
                    if game.board.cells[1][li][m] is not None:
                        placed.append((li, m))
        
            if len(placed) >= 3:
                # Phase A: Try to form triangles (3 cards in cycle)
                for i, ci in enumerate(placed):
                    for j, cj in enumerate(placed[i+1:], i+1):
                        for ck in placed[j+1:]:
                            # Check if these 3 can form triangle: all pairwise distances must be 'corta'
                            dist_ij = game.board.spatial_distance(
                                (1, ci[0]+1, ci[1]), 
                                (1, cj[0]+1, cj[1])
                            )
                            dist_jk = game.board.spatial_distance(
                                (1, cj[0]+1, cj[1]), 
                                (1, ck[0]+1, ck[1])
                            )
                            dist_ki = game.board.spatial_distance(
                                (1, ck[0]+1, ck[1]), 
                                (1, ci[0]+1, ci[1])
                            )
                            if dist_ij == 'corta' and dist_jk == 'corta' and dist_ki == 'corta':
                                cid_i = game.board.cells[1][ci[0]][ci[1]]
                                cid_j = game.board.cells[1][cj[0]][cj[1]]
                                cid_k = game.board.cells[1][ck[0]][ck[1]]
                                ca = game.all_cards[cid_i]
                                cb = game.all_cards[cid_j]
                                cc = game.all_cards[cid_k]
                            
                                # Only link if all have V>=2 capacity (triangle requires 2 links per card)
                                if (ca.definition.link_capacity >= 2 and 
                                    cb.definition.link_capacity >= 2 and
                                    cc.definition.link_capacity >= 2 and
                                    game.network.link_count(ca) < ca.definition.link_capacity and
                                    game.network.link_count(cb) < cb.definition.link_capacity and
                                    game.network.link_count(cc) < cc.definition.link_capacity):
                                
                                    for a, b in [(ca, cb), (cb, cc), (cc, ca)]:
                                        if game.actions_remaining >= 1:
                                            res = game.link_cards(1, a, b)
                                            if res is None:
                                                link_count += 1
                                    all_logs.append(f"IA forma TRIÁNGULO: {ca.definition.name}/{cb.definition.name}/{cc.definition.name}")
                                    emit_bot_state(all_logs)
                                    socketio.sleep(0.5)
        
            # Phase B: Link all remaining adjacent pairs
            for ci_idx, ci in enumerate(placed):
                for cj in placed[ci_idx+1:]:
                    same_layer = ci[0] == cj[0] and abs(ci[1] - cj[1]) == 2  # only dh=2 is valid for same-layer links
                    cross_layer = abs(ci[0] - cj[0]) == 1 and abs(ci[1] - cj[1]) <= 1
                    if same_layer or cross_layer:
                        cid_a = game.board.cells[1][ci[0]][ci[1]]
                        cid_b = game.board.cells[1][cj[0]][cj[1]]
                        a_card = game.all_cards.get(cid_a)
                        b_card = game.all_cards.get(cid_b)
                        if not a_card or not b_card:
                            continue
                        if game.network.link_count(a_card) >= a_card.definition.link_capacity:
                            continue
                        if game.network.link_count(b_card) >= b_card.definition.link_capacity:
                            continue
                        if game.actions_remaining < 1:
                            break
                        res = game.link_cards(1, a_card, b_card)
                        if res is None:
                            all_logs.append(f"IA vincula L{ci[0]+1}:{ci[1]} - L{cj[0]+1}:{cj[1]}")
                            link_count += 1
                            emit_bot_state(all_logs)
                            socketio.sleep(0.3)
        
            if link_count == 0:
                all_logs.append("IA no pudo vincular cartas")
                emit_bot_state(all_logs)
                socketio.sleep(0.5)
        
            # ═══ Step 4: Attack with target selection ═══
            squads = game.get_player_squads(1)
            print(f"[Room {code}] Bot: cards_played={cards_played}, links={link_count}, squads={len(squads)}, actions_left={game.actions_remaining}")
            if squads:
                all_logs.append(f"IA tiene {len(squads)} escuadron(es)")
                game.start_attack_phase()
                emit_bot_state(all_logs)
                socketio.sleep(1)
            
                # Sort squads by damage desc
                squads_sorted = sorted(squads, key=lambda s: s.base_damage, reverse=True)
            
                # Build attack queue with smart targeting
                bot_attacks = []
                for squad in squads_sorted[:2]:
                    # Check if human has isolated cards to destroy
                    target = 'grimoire'
                    target_id = None
                    human_isolated = []
                    for li in range(3):
                        for m in range(15):
                            cid = game.board.cells[0][li][m]
                            if cid:
                                card = game.all_cards.get(cid)
                                if card and game.network.link_count(card) == 0:
                                    human_isolated.append((cid, card.definition.name))
                
                    if human_isolated:
                        # Attack weakest isolated card
                        target = 'card'
                        target_id = human_isolated[0][0]
                        all_logs.append(f"IA apunta a carta aislada: {human_isolated[0][1]}")
                
                    bot_attacks.append({
                        'attacker': 1,
                        'squad_idx': 0,  # legacy fallback only
                        'members_ids': list(squad.members),  # stable identity for defend re-resolution
                        'target': target,
                        'target_id': target_id,
                        'squad_type': squad.squad_type,
                        'squad_damage': squad.base_damage,
                        'squad_color': squad.dominant_color.value if squad.dominant_color else 'incoloro',
                        'members': [game.all_cards[cid].definition.name for cid in squad.members],
                    })
            
                room['bot_attacks'] = bot_attacks
            
                # Pop first attack as pending
                first_attack = room['bot_attacks'].pop(0)
                room['pending_attack'] = first_attack
                target_str = f"a {first_attack['target']}" + (f" ({target_id})" if target_id else "")
                all_logs.append(f"IA prepara ataque con {first_attack['squad_type']} {target_str} — ¡defiéndete!")
                print(f"[Room {code}] Bot attacks: {first_attack['squad_type']} dmg={first_attack['squad_damage']}, queue={len(room.get('bot_attacks',[]))} more")
            
                # Broadcast with pending_attack (triggers defense popup)
                for sid, pinfo in room["players"].items():
                    s = filtered_state(game, pinfo["player_id"], room.get('pending_attack'))
                    s["log"] = all_logs[-10:]
                    emit('state_update', s, to=sid)
                return  # Wait for human to defend
        
            # Step 5: End turn (only reached if bot has no squads)
            print(f"[Room {code}] Bot: NO squads, ending turn silently")
            # Run exit_phase on the bot's own turn so purge, temp-link
            # dissolution, end-of-turn modifiers and turn_number all advance
            # exactly like a human end_turn (previously skipped → desync).
            game.active_player = 1
            game.phase = Phase.ATTACK
            game.exit_phase()      # bot's end-of-turn effects + purge
            if not game.game_over:
                game.start_turn()    # now switches to the human
                game.entry_phase()
            all_logs = []
            emit_bot_state(all_logs)
        
            if game.game_over:
                emit('game_over', {"winner": game.winner, "seals": [game.seals[0], game.seals[1]]}, to=code)


        except Exception as e:
            print(f"[Room {code}] Bot error: {e}")
            import traceback; traceback.print_exc()
            # Recovery: transition back to human player
            try:
                game.active_player = 0
                game.phase = Phase.ACTIONS
                game.start_turn()
                game.entry_phase()
                for sid, pinfo in room["players"].items():
                    s = filtered_state(game, pinfo["player_id"])
                    s["log"] = ["⚠️ Error en IA, turno pasado."]
                    emit("state_update", s, to=sid)
            except:
                pass

@socketio.on('disconnect')
def on_disconnect():
    for code, room in list(rooms.items()):
        if request.sid in room["players"]:
            if room.get("solo"):
                # Solo rooms: keep alive, player will rejoin
                print(f"[Room {code}] Solo player disconnected (will rejoin)")
                continue
            emit('opponent_left', {"message": "Oponente desconectado."}, to=code, skip_sid=request.sid)
            del room["players"][request.sid]
            if not room["players"]:
                del rooms[code]
                print(f"[Room {code}] Closed (no players).")
            break


# ─── Main ──────────────────────────────────────────────────
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    prod = os.environ.get('RAILWAY_ENVIRONMENT', '') == 'production' or os.environ.get('RENDER', '')
    
    print(f"\n  NFW Multiplayer Server")
    print(f"  Port: {port} | Debug: {debug} | Production: {prod}\n")
    
    if prod:
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
    else:
        socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
