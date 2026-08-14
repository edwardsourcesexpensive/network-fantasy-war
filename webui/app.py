"""
Network Fantasy War — Web UI
Flask server for browser-based gameplay.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, session
from prototype.game import GameState
from prototype.enums import Phase
from prototype.decks import DECKS, DECK_NAMES
from prototype.ai import BotPlayer
from prototype import turn_manager as tm

app = Flask(__name__)
app.secret_key = os.environ.get('NFW_SECRET_KEY') or os.urandom(32)

# Store game state per session
games = {}
pending_attacks = {}  # sid -> {attacker, squad_idx, target, members_ids, squad_type, ...}
bot_turn_active = {}  # sid -> True while the bot's turn is mid-flight (queue draining)

def _cleanup_sid(sid):
    """Drop all server-side state for a session id (prevents unbounded leaks)."""
    games.pop(sid, None)
    pending_attacks.pop(sid, None)
    bot_turn_active.pop(sid, None)

def get_game():
    """Get or create game for current session."""
    sid = session.get('game_id')
    if sid and sid in games:
        return games[sid]
    return None

@app.route('/')
def index():
    return render_template('game.html')

@app.route('/reglas')
def reglas():
    return app.send_static_file('NFW-Reglas-Jugador.pdf')

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
    from prototype.game import ability_implementation_status
    deck = DECKS[deck_key]
    cards = []
    for c in deck:
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
        total = len(abilities_data)
        cards.append({
            "name": c.name, "color": c.color.value,
            "hp": c.hp, "v": c.link_capacity, "d": c.damage_bonus,
            "layers": c.allowed_layers,
            "formations": c.allowed_formations if c.allowed_formations else [],
            "is_spy": c.is_spy, "is_logistron": c.is_logistron,
            "abilities": [a["desc"] for a in abilities_data],
            "abilities_detail": abilities_data,
            "impl_count": impl_count,
            "total_abilities": total,
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
    if deck1 not in DECKS or deck2 not in DECKS:
        return jsonify({"error": f"Mazo desconocido: {deck1}/{deck2}"}), 400

    # Free the previous session's state before minting a new sid (leak fix)
    old_sid = session.get('game_id')
    if old_sid:
        _cleanup_sid(old_sid)

    sid = os.urandom(8).hex()
    session['game_id'] = sid

    game = GameState(DECKS[deck1][:], DECKS[deck2][:])
    game.start_turn()
    game.entry_phase(auto_resolve=False)  # P0 is human — Político picker
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

    sid = session.get('game_id', '')
    data = request.get_json()
    action = data.get('action')
    args = data.get('args', {})
    player = game.active_player

    result = {"ok": False, "error": None}

    # Pending faction/politico choices must be resolved first (audit #7)
    if getattr(game, "pending_faction_choices", None) or getattr(game, "pending_politico_swap", None):
        result["error"] = "Resuelve los efectos de escuadrón pendientes primero."
        result["state"] = game_state(game)
        return jsonify(result)
    
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
            game.exit_phase(auto_resolve=False)  # human's exit — faction pickers
            if not game.game_over and not game.pending_faction_choices:
                game.start_turn()
                game.entry_phase(auto_resolve=(game.active_player != 0))
            elif game.game_over:
                _cleanup_sid(sid)
            result["ok"] = True

    elif action == 'end_turn':
        game.phase = Phase.ATTACK
        game.exit_phase(auto_resolve=False)  # human's exit — faction pickers
        if not game.game_over and not game.pending_faction_choices:
            game.start_turn()
            game.entry_phase(auto_resolve=(game.active_player != 0))
        elif game.game_over:
            _cleanup_sid(sid)
        result["ok"] = True
    
    elif action == 'surrender':
        game._end_game(1 - player)
        _cleanup_sid(sid)  # free the surrendered game
        result["ok"] = True
    
    elif action == 'ai_turn':
        result["log"] = []
        sid = session.get('game_id')
        
        # Check for stored attack queue from previous ai_turn call
        queue_key = f"{sid}_queue"
        stored_queue = pending_attacks.get(queue_key)
        
        if stored_queue:
            # Continue with next attack from stored queue
            next_attack = stored_queue.pop(0)
            pending_attacks[sid] = next_attack
            if not stored_queue:
                pending_attacks.pop(queue_key, None)
            result["pending_attack"] = next_attack
            result["log"].append(f"⚔️ AI ataca con escuadrón ({next_attack['squad_type']}) — ¡defiéndete!")
            result["ok"] = True
            result["state"] = game_state(game)
            return jsonify(result)

        # Bot turn already in flight (attacks were queued and the last one was
        # just defended) — the queue is empty, so END the bot's turn instead of
        # running take_turn again (that double-burst let the bot chain action
        # bursts within the same turn).
        if bot_turn_active.get(sid):
            if pending_attacks.get(sid):
                result["error"] = "Resuelve el ataque pendiente del IA primero."
                result["state"] = game_state(game)
                return jsonify(result)
            bot_turn_active.pop(sid, None)
            bot = BotPlayer()
            bot.end_turn(game, player, auto_resolve=False)
            if game.game_over:
                _cleanup_sid(sid)
            result["ok"] = True
            result["log"].append("AI termina turno")
            result["state"] = game_state(game)
            return jsonify(result)

        # Full bot turn
        bot = BotPlayer()
        bot_result = bot.take_turn(game, player, on_log=lambda msg: result["log"].append(msg))
        
        if bot_result.attacks:
            attack_queue = []
            for attack in bot_result.attacks:
                attack_queue.append({
                    'attacker': player,
                    'squad_idx': 0,
                    'members_ids': attack.members_ids,
                    'target': attack.target,
                    'target_id': attack.target_id,
                    'squad_type': attack.squad_type,
                    'squad_damage': attack.squad_damage,
                    'squad_color': attack.squad_color,
                    'members': attack.members_names,
                })
            
            first_attack = attack_queue.pop(0)
            pending_attacks[sid] = first_attack
            bot_turn_active[sid] = True  # bot's turn in flight until queue drains
            
            if attack_queue:
                pending_attacks[queue_key] = attack_queue
            
            result["pending_attack"] = first_attack
            result["log"].append(f"⚔️ AI ataca con escuadrón ({first_attack['squad_type']}) — ¡defiéndete!")
            result["ok"] = True
            result["state"] = game_state(game)
            return jsonify(result)
        
        # No attacks — end turn immediately (next entry is P0 human → politico picker)
        bot.end_turn(game, player, auto_resolve=False)
        if game.game_over:
            _cleanup_sid(sid)
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


@app.route('/api/faction_choice', methods=['POST'])
def api_faction_choice():
    """Apply the human's Saboteador/Monstruo picks (audit #7)."""
    game = get_game()
    if not game:
        return jsonify({"error": "No hay partida activa."}), 400
    if not game.pending_faction_choices:
        return jsonify({"error": "No hay efectos de escuadrón pendientes."}), 400
    data = request.get_json() or {}
    tm.apply_faction_choices(game, 0, data.get('links') or [], data.get('nodes') or [])
    tm._finish_exit_phase(game)
    if game.game_over:
        _cleanup_sid(session.get('game_id'))
    else:
        game.start_turn()
        game.entry_phase(auto_resolve=(game.active_player != 0))
    return jsonify({"ok": True, "state": game_state(game)})


@app.route('/api/politico_swap', methods=['POST'])
def api_politico_swap():
    """Apply (or skip) the human's Político position swap (audit #7)."""
    game = get_game()
    if not game:
        return jsonify({"error": "No hay partida activa."}), 400
    if not game.pending_politico_swap:
        return jsonify({"error": "No hay intercambio pendiente."}), 400
    data = request.get_json() or {}
    a, b = data.get('a'), data.get('b')
    if a is None:
        game.pending_politico_swap = None  # skip
    elif not tm.apply_politico_swap(game, 0, a, b):
        return jsonify({"error": "Intercambio inválido: los vínculos de las cartas no sobrevivirían."}), 400
    else:
        tm.refresh_pending_politico(game)
    return jsonify({"ok": True, "state": game_state(game)})


def game_state(game):
    """Serialize game state to JSON. Delegates to unified serializer."""
    from prototype.serialize import serialize_state
    return serialize_state(game, player_id=None)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print("╔══════════════════════════════════════════╗")
    print("║   NETWORK FANTASY WAR — Web UI         ║")
    print(f"║   http://0.0.0.0:{port}                ║")
    print("╚══════════════════════════════════════════╝")
    app.run(debug=debug, host='0.0.0.0', port=port)
