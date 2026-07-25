"""
Network Fantasy War — Multiplayer Server
Flask-SocketIO real-time online play for 2 players.
"""
import os, random, string
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

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


def filtered_state(game, player_id):
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
                        "color": card.definition.color.value,
                        "abilities": [a.description for a in card.definition.abilities] if card.definition.abilities else [],
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
            members = [{"layer": m[0], "meridian": m[1]} for m in s.members]
            squads[f"p{p}"].append({
                "type": s.squad_type,
                "damage": s.base_damage,
                "potenciamiento": s.empowerment,
                "members": members,
            })
    
    # Links — use position-based keys matching DOM data-cid format
    links = {}
    links_pairs = []
    for cid, c in game.all_cards.items():
        if c.position:
            owner_p, owner_li, owner_m = c.position
            pos_key = f"{owner_p},{owner_li},{owner_m}"
            linked = list(game.network.links.get(cid, set()))
            if linked:
                links[pos_key] = [f"{game.all_cards[lid].position[0]},{game.all_cards[lid].position[1]},{game.all_cards[lid].position[2]}" for lid in linked if game.all_cards.get(lid) and game.all_cards[lid].position]
                for lid in linked:
                    if cid < lid:
                        tc = game.all_cards.get(lid)
                        if tc and tc.position:
                            tp, tl, tm = tc.position
                            links_pairs.append({
                                "from": f"{owner_p},{owner_li},{owner_m}",
                                "to": f"{tp},{tl},{tm}",
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
        "player_id": player_id,
        "board": board,
        "links": links,
        "links_pairs": links_pairs,
        "squads": squads,
        "pending_attack": None,
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
    return jsonify({
        k: {"name": DECK_NAMES[k], "count": len(v)}
        for k, v in DECKS.items()
    })


# ─── Socket Events ─────────────────────────────────────────
@socketio.on('create_room')
def on_create(data):
    code = gen_code()
    while code in rooms:
        code = gen_code()
    deck_key = data.get('deck', 'filo')
    rooms[code] = {
        "players": {request.sid: {"player_id": 0, "deck": deck_key}},
        "game": None,
        "host_sid": request.sid,
    }
    join_room(code)
    emit('room_created', {"code": code, "player_id": 0})
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
    
    rooms[code] = {
        "players": {request.sid: {"player_id": 0, "deck": deck_key}},
        "game": None,
        "host_sid": request.sid,
        "solo": True,
        "bot_deck": ai_deck_key,
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
    
    # Actions phase: play up to 4 cards
    for _ in range(4):
        if game.phase != Phase.ACTIONS:
            break
        if not game.hands[player_id]:
            break
        card = game.hands[player_id][0]
        if card.definition.is_spy:
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
    
    # Link adjacent cards
    # Collect positions of placed cards
    placed = []
    for li in range(3):
        for m in range(15):
            if game.board.cells[player_id][li][m] is not None:
                placed.append((li, m))
    
    for ci_idx, ci in enumerate(placed):
        cid_a = game.board.cells[player_id][ci[0]][ci[1]]
        a_card = game.all_cards.get(cid_a)
        if not a_card:
            continue
        if game.network.link_count(a_card) >= 2:
            continue
        for cj in placed:
            if ci == cj:
                continue
            cid_b = game.board.cells[player_id][cj[0]][cj[1]]
            b_card = game.all_cards.get(cid_b)
            if not b_card:
                continue
            if game.network.link_count(b_card) >= 2:
                continue
            if ci[0] == cj[0] and abs(ci[1] - cj[1]) == 1:
                res = game.link_cards(player_id, a_card, b_card)
                if res is None:
                    logs.append(f"IA vincula L{ci[0]+1}:{ci[1]} - L{cj[0]+1}:{cj[1]}")
                    break
        break
    
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
    
    # End turn — skip exit_phase to avoid purging human player's cards
    if not game.game_over:
        game.phase = Phase.ACTIONS  # reset for next player
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
    room["players"][request.sid] = {"player_id": 1, "deck": deck_key}
    join_room(code)

    emit('room_joined', {"code": code, "player_id": 1}, to=request.sid)
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
    
    if code not in rooms:
        emit('error', {"message": "Sala no encontrada."})
        return
    
    room = rooms[code]
    if not room["game"]:
        emit('error', {"message": "Juego no iniciado."})
        return
    
    # Update the player's socket to the new connection
    # Find the player by player_id and update their SID
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

    if game.active_player != player_id:
        emit('error', {"message": "No es tu turno."})
        return

    action = data.get('action')
    args = data.get('args', {})

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
        # Parse card positions: "0,2,5" -> (player, layer, meridian)
        pa = tuple(int(x) for x in ca.split(','))
        pb = tuple(int(x) for x in cb.split(','))
        err = game.link(player_id, (pa[1], pa[2]), (pb[1], pb[2]))

    elif action == 'ascend':
        cid = args.get('card_id', '')
        parts = cid.split(',')
        li, m = int(parts[1]), int(parts[2])
        err = game.ascend(player_id, li, m)

    elif action == 'attack':
        si = args.get('squad_index', 0)
        squads = game.get_player_squads(player_id)
        if 0 <= si < len(squads):
            err = game.attack(squads[si], args.get('target', 'grimoire'))

    elif action == 'defend':
        di = args.get('defender_squad_index', -1)
        # Handle defense — resolve pending attack
        from webui.app import pending_attacks
        pa = pending_attacks.pop(None, None)  # simplified: find by game
        if pa:
            game.active_player = pa['attacker']
            def_squads = game.get_player_squads(1 - pa['attacker'])
            defending = def_squads[di] if 0 <= di < len(def_squads) else None
            game.attack(
                game.get_player_squads(pa['attacker'])[pa['squad_idx']],
                pa['target'], defending, pa.get('target_id')
            )

    elif action == 'next_phase':
        if game.phase == Phase.ACTIONS:
            game.start_attack_phase()
        elif game.phase == Phase.ATTACK:
            game.exit_phase()
            if not game.game_over:
                game.start_turn()
                game.entry_phase()

    elif action == 'end_turn':
        game.phase = Phase.ATTACK
        game.exit_phase()
        if not game.game_over:
            game.start_turn()
            game.entry_phase()

    else:
        emit('error', {"message": f"Accion desconocida: {action}"})
        return

    if err:
        emit('error', {"message": str(err)})
        return

    # Broadcast updated state to both players
    for sid, pinfo in room["players"].items():
        s = filtered_state(game, pinfo["player_id"])
        emit('state_update', s, to=sid)

    # Check game over
    if game.game_over:
        emit('game_over', {
            "winner": game.winner,
            "seals": [game.seals[0], game.seals[1]],
        }, to=code)
        return
    
    # Solo mode: auto-play bot turn
    if room.get("solo") and game.active_player == 1:
        import time
        time.sleep(0.3)  # brief pause so the human sees their result
        logs = play_bot_turn(game, 1)
        # Send updated state to human
        for sid, pinfo in room["players"].items():
            s = filtered_state(game, pinfo["player_id"])
            s["log"] = (s.get("log", []) + logs)[-10:]
            emit('state_update', s, to=sid)
        
        if game.game_over:
            emit('game_over', {
                "winner": game.winner,
                "seals": [game.seals[0], game.seals[1]],
            }, to=code)


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
