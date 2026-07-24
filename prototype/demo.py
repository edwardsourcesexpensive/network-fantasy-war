"""
Automated test: two players play a few turns to demonstrate the prototype.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prototype.card import MINI_SET, Color, CardDef
from prototype.game import GameState, Phase
import random

random.seed(99)

# Build decks with variety
deck_p1 = []
deck_p2 = []
for cdef in MINI_SET:
    copies = cdef.max_copies
    for _ in range(copies):
        deck_p1.append(cdef)
        deck_p2.append(cdef)

# Pad to 50
while len(deck_p1) < 50:
    deck_p1.append(MINI_SET[0])
    deck_p2.append(MINI_SET[0])

random.shuffle(deck_p1)
random.shuffle(deck_p2)

game = GameState(deck_p1[:50], deck_p2[:50])

def do_turn(player, actions_sequence):
    """Execute a sequence of actions for a player."""
    game.start_turn()
    game.entry_phase()
    if game.game_over:
        return
    
    print(f"\n{'='*70}")
    print(f"TURNO {game.turn_number} — JUGADOR {player+1}")
    print(f"Mano: {len(game.hands[player])} cartas | Sellos propios: {game.seals[player]} | Sellos rival: {game.seals[1-player]}")
    game.display_board()
    
    for action in actions_sequence:
        if game.game_over:
            return
        cmd = action[0]
        
        if cmd == "play":
            # play <name_substring> <layer> <meridian>
            name = action[1]
            layer = action[2]
            meridian = action[3]
            found = False
            for i, c in enumerate(game.hands[player]):
                if name.lower() in c.definition.name.lower():
                    err = game.play_card(player, i, layer, meridian)
                    if not err:
                        print(f"  ▶ Juega {c.definition.name} en L{layer}:{meridian}")
                        found = True
                    else:
                        print(f"  ✗ No se pudo jugar {c.definition.name}: {err}")
                        # Try to place anyway if error is about cell
                    break
            if not found:
                print(f"  ✗ Carta '{name}' no encontrada en mano")
        
        elif cmd == "link":
            # link all cards in a layer
            layer = action[1]
            cards_in_layer = []
            li = layer - 1
            for m in range(15):
                cid = game.board.cells[player][li][m]
                if cid and game.all_cards[cid].owner == player:
                    cards_in_layer.append(game.all_cards[cid])
            
            for i in range(len(cards_in_layer)):
                for j in range(i+1, len(cards_in_layer)):
                    # Only link if distance is valid and actions remain
                    if game.actions_remaining <= 0:
                        return
                    if game.network.can_link(cards_in_layer[i]) and game.network.can_link(cards_in_layer[j]):
                        err = game.link_cards(player, cards_in_layer[i], cards_in_layer[j])
                        if not err:
                            print(f"  ▶ Vincula {cards_in_layer[i].definition.name} <-> {cards_in_layer[j].definition.name}")
        
        elif cmd == "link_pair":
            name_a = action[1]
            name_b = action[2]
            cards = []
            for cid, c in game.all_cards.items():
                if c.position and c.position[0] == player and c.owner == player:
                    if name_a.lower() in c.definition.name.lower():
                        cards.append(c)
                        break
            for cid, c in game.all_cards.items():
                if c.position and c.position[0] == player and c.owner == player:
                    if name_b.lower() in c.definition.name.lower() and c != cards[0] if cards else True:
                        cards.append(c)
                        break
            if len(cards) == 2 and game.actions_remaining > 0:
                err = game.link_cards(player, cards[0], cards[1])
                if not err:
                    print(f"  ▶ Vincula {cards[0].definition.name} <-> {cards[1].definition.name}")
        
        elif cmd == "attack_all":
            game.start_attack_phase()
            squads = game.get_player_squads(player)
            print(f"\n  ⚔️  Fase de ataque — {len(squads)} escuadrones")
            for s in squads:
                if game.game_over:
                    return
                names = [game.all_cards[cid].definition.name[:15] for cid in s.members]
                print(f"     {s.squad_type}: {names}")
                game.attack(s, "grimoire")
            
            game.exit_phase()
            game.show_log()
            if not game.game_over:
                game.start_turn()
                game.entry_phase()
            return  # exit_phase already advances
    
    # Move to attack if still in actions
    if game.phase == Phase.ACTIONS and not game.game_over:
        game.start_attack_phase()
        squads = game.get_player_squads(player)
        if squads:
            print(f"\n  ⚔️  Ataque — {len(squads)} escuadrones")
            for s in squads:
                if game.game_over:
                    return
                names = [game.all_cards[cid].definition.name[:15] for cid in s.members]
                print(f"     {s.squad_type}: {names} (daño base={s.base_damage})")
                game.attack(s, "grimoire")
    
    game.exit_phase()
    game.show_log()


# ═══════════════════════════════════════════════════════
# SIMULATED GAME
# ═══════════════════════════════════════════════════════

print("╔══════════════════════════════════════════════════╗")
print("║   NETWORK FANTASY WAR — Partida Automática     ║")
print("╚══════════════════════════════════════════════════╝")

# Turn 1 — Player 1: play 2 cards + link
do_turn(0, [
    ("play", "guerrero", 1, 5),
    ("play", "transmutadora", 1, 7),
    ("link_pair", "guerrero", "transmutadora"),
])

if game.game_over:
    print(f"\n¡Juego terminado! Ganador: Jugador {game.winner + 1}")
    print(f"Sellos J1: {game.seals[0]}, J2: {game.seals[1]}")
    sys.exit(0)

# Turn 2 — Player 2: play 2 cards + link
do_turn(1, [
    ("play", "guerrero", 1, 5),
    ("play", "estratega", 1, 7),
    ("link_pair", "guerrero", "estratega"),
])

if game.game_over:
    print(f"\n¡Juego terminado! Ganador: Jugador {game.winner + 1}")
    sys.exit(0)

# Turn 3 — Player 1: play more, build triangle
game.actions_remaining = 10  # cheat for demo
do_turn(0, [
    ("play", "sargento", 2, 6),
    ("link_pair", "sargento", "guerrero"),
    ("link_pair", "sargento", "transmutadora"),
])

if game.game_over:
    print(f"\n¡Juego terminado! Ganador: Jugador {game.winner + 1}")
    sys.exit(0)

# Turn 4 — Player 2: play more
game.actions_remaining = 10
do_turn(1, [
    ("play", "sargento", 2, 6),
    ("play", "danzante", 1, 9),
    ("link_pair", "sargento", "guerrero"),
    ("link_pair", "sargento", "estratega"),
])

if game.game_over:
    print(f"\n¡Juego terminado! Ganador: Jugador {game.winner + 1}")
    sys.exit(0)

# Show final state
print(f"\n{'='*70}")
print(f"ESTADO FINAL")
print(f"  Sellos J1: {game.seals[0]} | Sellos J2: {game.seals[1]}")
print(f"  Turnos jugados: {game.turn_number - 1}")

# Show all cards on board with links
squads_p1 = game.get_player_squads(0)
squads_p2 = game.get_player_squads(1)
print(f"\n  Escuadrones J1: {len(squads_p1)}")
for s in squads_p1:
    names = [game.all_cards[cid].definition.name for cid in s.members]
    print(f"    {s.squad_type} ({s.base_damage} daño): {', '.join(names)}")
print(f"  Escuadrones J2: {len(squads_p2)}")
for s in squads_p2:
    names = [game.all_cards[cid].definition.name for cid in s.members]
    print(f"    {s.squad_type} ({s.base_damage} daño): {', '.join(names)}")

print(f"\n✓ Partida de demostración completada.")
print(f"  Ejecuta 'python -m prototype.cli' para jugar interactivamente.")
