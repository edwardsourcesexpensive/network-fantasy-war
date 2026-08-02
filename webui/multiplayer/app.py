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
from prototype.ai import BotPlayer

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*")

# ─── Room management ───────────────────────────────────────
rooms = {}  # code -> {players: {sid: {player_id, deck}}, game: GameState, active_sid: str, state: dict}

def gen_code():
    """4-char room code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))


def filtered_state(game, player_id, pending_attack=None):
    """Build complete game state. Delegates to unified serializer."""
    from prototype.serialize import serialize_state
    return serialize_state(game, player_id=player_id, pending_attack=pending_attack)


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
                                'NFW-Reglas-Jugador.pdf')
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
    p0_token = rooms[code]["player_tokens"]["0"]
    
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
    s["token"] = p0_token  # solo seat needs its token to rejoin after navigation
    emit('solo_started', s)
    print(f"[Room {code}] Solo game vs AI ({ai_deck_key}) started")



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
        bot = BotPlayer()
        game_over = not bot.end_turn(game, 1)
        for sid, pinfo in room["players"].items():
            s = filtered_state(game, pinfo["player_id"])
            emit('state_update', s, to=sid)
        if game_over:
            emit('game_over', {"winner": game.winner, "seals": [game.seals[0], game.seals[1]]}, to=code)
        return
    # Solo mode: auto-play bot turn
    if room.get("solo") and game.active_player == 1:
        print(f"[Room {code}] Bot turn triggered, active_player={game.active_player}")
        try:
            bot = BotPlayer()

            def emit_bot_state(logs):
                for sid, pinfo in room["players"].items():
                    s = filtered_state(game, pinfo["player_id"], room.get('pending_attack'))
                    s["log"] = logs[-10:] if logs else []
                    emit('state_update', s, to=sid)

            all_logs = []

            def on_log(msg):
                all_logs.append(msg)
                emit_bot_state(all_logs)
                socketio.sleep(0.3)

            result = bot.take_turn(game, 1, on_log=on_log)

            if result.attacks:
                # Build attack queue from AttackIntent objects
                bot_attacks = []
                for attack in result.attacks:
                    bot_attacks.append({
                        'attacker': 1,
                        'squad_idx': 0,
                        'members_ids': attack.members_ids,
                        'target': attack.target,
                        'target_id': attack.target_id,
                        'squad_type': attack.squad_type,
                        'squad_damage': attack.squad_damage,
                        'squad_color': attack.squad_color,
                        'members': attack.members_names,
                    })

                room['bot_attacks'] = bot_attacks

                # Pop first attack as pending
                first_attack = room['bot_attacks'].pop(0)
                room['pending_attack'] = first_attack
                target_str = f"a {first_attack['target']}" + (f" ({first_attack['target_id']})" if first_attack.get('target_id') else "")
                all_logs.append(f"IA prepara ataque con {first_attack['squad_type']} {target_str} — ¡defiéndete!")
                print(f"[Room {code}] Bot attacks: {first_attack['squad_type']} dmg={first_attack['squad_damage']}, queue={len(room.get('bot_attacks',[]))} more")

                # Broadcast with pending_attack
                for sid, pinfo in room["players"].items():
                    s = filtered_state(game, pinfo["player_id"], room.get('pending_attack'))
                    s["log"] = all_logs[-10:]
                    emit('state_update', s, to=sid)
                return  # Wait for human to defend

            # No squads — end turn immediately
            print(f"[Room {code}] Bot: NO squads, ending turn silently")
            bot.end_turn(game, 1)
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
