"""
Network Fantasy War - Digital Prototype
CLI interface for 2-player hotseat gameplay.
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prototype.card import MINI_SET, CardDef, Color
from prototype.game import GameState, Phase
from prototype.decks import DECKS, DECK_NAMES


def build_starter_deck() -> list[CardDef]:
    """Build a 50-card starter deck from the mini-set (fallback)."""
    deck = []
    for card_def in MINI_SET:
        copies = card_def.max_copies
        for _ in range(copies):
            deck.append(card_def)
    while len(deck) < 50:
        for card_def in MINI_SET:
            if card_def.color in (Color.LOGISTRON, Color.GUERRERO, Color.SELLADOR):
                deck.append(card_def)
                if len(deck) >= 50:
                    break
    random.shuffle(deck)
    return deck[:50]


def select_deck(player_num: int) -> list[CardDef]:
    """Let a player select their deck."""
    print(f"\n  Jugador {player_num} — Elige tu mazo:")
    keys = list(DECKS.keys())
    for i, key in enumerate(keys):
        print(f"    [{i+1}] {DECK_NAMES[key]}")
    print(f"    [0] Mazo aleatorio (pool de 300 cartas)")
    
    while True:
        try:
            choice = input(f"  Mazo J{player_num} > ").strip()
            if choice == "0":
                return build_starter_deck()
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                key = keys[idx]
                print(f"  ✓ {DECK_NAMES[key]}")
                return DECKS[key][:]
            print(f"  Número inválido (1-{len(keys)} o 0)")
        except ValueError:
            print(f"  Ingresa un número (1-{len(keys)} o 0)")
        except (EOFError, KeyboardInterrupt):
            print("\n  Usando mazo aleatorio.")
            return build_starter_deck()


def print_help():
    print("""
╔══════════════════════════════════════════════════════════════╗
║          NETWORK FANTASY WAR — Prototype v2                 ║
╠══════════════════════════════════════════════════════════════╣
║ COMANDOS:                                                   ║
║   board / b       — Mostrar tablero                         ║
║   hand / h        — Mostrar tu mano                         ║
║   squads / sq     — Mostrar tus escuadrones                 ║
║   log             — Mostrar registro de eventos             ║
║   play N L M      — Jugar carta N en layer L, meridiano M  ║
║   spy N           — Jugar espía N en la frontera            ║
║   ascend ID       — Ascender carta / infiltrar espía        ║
║   link ID1 ID2    — Vincular dos cartas                     ║
║   attack N grimoire         — Atacar grimorio con escuadrón ║
║   attack N card ID [def N]  — Atacar nodo (def N opcional)  ║
║   sabotage ID     — Sabotear vínculo con espía infiltrado   ║
║   next / n        — Pasar a la siguiente fase               ║
║   end             — Terminar turno directamente             ║
║   help / ?        — Mostrar esta ayuda                      ║
║   quit / q        — Salir del juego                         ║
╠══════════════════════════════════════════════════════════════╣
║ FASES: ENTRY → ACTIONS (4 acc) → ATTACK → EXIT              ║
╚══════════════════════════════════════════════════════════════╝
""")


def find_card_by_id(game: GameState, card_id: int):
    """Find a card by its numeric ID."""
    return game.all_cards.get(card_id)


def cmd_play(game: GameState, args: list[str]):
    if len(args) < 3:
        print("  Uso: play <índice_mano> <layer(1-3)> <meridiano(0-14)>")
        print("  Para espías: spy <índice_mano>")
        return
    try:
        idx = int(args[0])
        layer = int(args[1])
        meridian = int(args[2])
    except ValueError:
        print("  Números inválidos.")
        return

    err = game.play_card(game.active_player, idx, layer, meridian)
    if err:
        print(f"  ERROR: {err}")
    else:
        game.display_board()


def cmd_spy(game: GameState, args: list[str]):
    if len(args) < 1:
        print("  Uso: spy <índice_mano>")
        return
    try:
        idx = int(args[0])
    except ValueError:
        print("  Índice inválido.")
        return

    card = game.hands[game.active_player][idx] if idx < len(game.hands[game.active_player]) else None
    if not card or not card.definition.is_spy:
        print("  Esa carta no es un espía. Usa 'spy' solo para espías.")
        return

    err = game.play_card(game.active_player, idx, 0, 0)
    if err:
        print(f"  ERROR: {err}")
    else:
        print(f"  {card.definition.name} desplegado en la frontera.")
        game.display_board()


def cmd_ascend(game: GameState, args: list[str]):
    if len(args) < 1:
        print("  Uso: ascend <card_id>")
        print("  Para espías en frontera, esto los infiltra en territorio enemigo.")
        return
    try:
        card_id = int(args[0])
    except ValueError:
        print("  ID inválido.")
        return

    card = game.all_cards.get(card_id)
    if not card:
        print(f"  Carta {card_id} no encontrada.")
        return

    err = game.ascend(game.active_player, card)
    if err:
        print(f"  ERROR: {err}")
    else:
        if card.definition.is_spy:
            print(f"  ¡{card.definition.name} infiltrado en territorio enemigo!")
        else:
            print(f"  {card.definition.name} ascendido a L{card.position[1]}")
        game.display_board()


def cmd_link(game: GameState, args: list[str]):
    if len(args) < 2:
        print("  Uso: link <id_a> <id_b>")
        return
    try:
        id_a = int(args[0])
        id_b = int(args[1])
    except ValueError:
        print("  IDs inválidos.")
        return

    card_a = game.all_cards.get(id_a)
    card_b = game.all_cards.get(id_b)
    if not card_a or not card_b:
        print("  Una o ambas cartas no existen.")
        return

    err = game.link_cards(game.active_player, card_a, card_b)
    if err:
        print(f"  ERROR: {err}")
    else:
        print(f"  Vínculo: {card_a.definition.name} <-> {card_b.definition.name}")
        game.display_board()


def cmd_attack(game: GameState, args: list[str]):
    if game.phase != Phase.ATTACK:
        print("  No estás en fase de ataque. Usa 'next'.")
        return

    player_squads = game.get_player_squads(game.active_player)
    if not player_squads:
        print("  No tienes escuadrones para atacar.")
        return

    if not args:
        print("  Uso: attack <índice_escuadrón> grimoire")
        print("       attack <índice_escuadrón> card <card_id> [def <squad_idx>]")
        game.display_squads()
        return

    try:
        squad_idx = int(args[0])
    except ValueError:
        print("  Índice de escuadrón inválido.")
        return

    if squad_idx < 0 or squad_idx >= len(player_squads):
        print("  Índice fuera de rango. Usa 'sq' para ver tus escuadrones.")
        return

    squad = player_squads[squad_idx]

    if len(args) < 2:
        print("  Especifica objetivo: 'grimoire' o 'card <id>'")
        return

    target = args[1]
    target_id = None
    def_squad = None

    if target == "grimoire":
        pass
    elif target == "card" and len(args) >= 3:
        try:
            target_id = int(args[2])
        except ValueError:
            print("  ID de carta inválido.")
            return

        # Check for optional defense squad
        if len(args) >= 5 and args[3] == "def":
            try:
                def_idx = int(args[4])
                defender = 1 - game.active_player
                def_squads = game.get_player_squads(defender)
                if 0 <= def_idx < len(def_squads):
                    def_squad = def_squads[def_idx]
                    print(f"  Defensa: escuadrón {def_squad.squad_type}")
            except (ValueError, IndexError):
                pass
    else:
        print("  Objetivo inválido. Usa 'grimoire' o 'card <id>'.")
        return

    err = game.attack(squad, target, def_squad, target_id)
    if err:
        print(f"  ERROR: {err}")
    else:
        game.show_log()


def cmd_sabotage(game: GameState, args: list[str]):
    if len(args) < 1:
        print("  Uso: sabotage <spy_id>")
        return
    try:
        spy_id = int(args[0])
    except ValueError:
        print("  ID inválido.")
        return

    spy = game.all_cards.get(spy_id)
    if not spy:
        print(f"  Espía {spy_id} no encontrado.")
        return

    err = game.spy_sabotage(game.active_player, spy)
    if err:
        print(f"  ERROR: {err}")
    else:
        print(f"  Sabotaje ejecutado.")


def main():
    print("╔══════════════════════════════════════════╗")
    print("║   NETWORK FANTASY WAR — Prototype v2    ║")
    print("╚══════════════════════════════════════════╝")
    # Let players choose decks
    deck0 = select_deck(1)
    deck1 = select_deck(2)

    print(f"\nCreando partida con mazos de {len(deck0)} cartas cada uno...")
    game.start_turn()
    game.entry_phase()
    if game.game_over:
        game.show_log()
        return

    game.display_board()

    while not game.game_over:
        try:
            prompt = f"\n[J{game.active_player + 1}] ({game.phase.value}, {game.actions_remaining} acc) > "
            cmd = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n¡Hasta luego!")
            break

        if not cmd:
            continue

        parts = cmd.split()
        command = parts[0].lower()
        args = parts[1:]

        if command in ("quit", "q", "exit"):
            break

        elif command in ("help", "?"):
            print_help()

        elif command in ("board", "b"):
            game.display_board()

        elif command in ("hand", "h"):
            game.display_hand()

        elif command in ("squads", "sq"):
            game.display_squads()

        elif command == "log":
            game.show_log()

        elif command == "play":
            cmd_play(game, args)

        elif command == "spy":
            cmd_spy(game, args)

        elif command == "ascend":
            cmd_ascend(game, args)

        elif command == "link":
            cmd_link(game, args)

        elif command == "attack":
            cmd_attack(game, args)

        elif command == "sabotage":
            cmd_sabotage(game, args)

        elif command in ("next", "n"):
            if game.phase == Phase.ACTIONS:
                game.start_attack_phase()
                game.show_log()
                print("  Fase de ataque. Usa 'attack' o 'sq' para ver escuadrones.")
                game.display_squads()
            elif game.phase == Phase.ATTACK:
                game.exit_phase()
                game.show_log()
                if not game.game_over:
                    game.start_turn()
                    game.entry_phase()
                    if not game.game_over:
                        game.display_board()
            else:
                print(f"  No se puede avanzar desde {game.phase.value}.")

        elif command == "end":
            game.phase = Phase.ATTACK
            game.exit_phase()
            game.show_log()
            if not game.game_over:
                game.start_turn()
                game.entry_phase()
                if not game.game_over:
                    game.display_board()

        else:
            print(f"  Comando desconocido: '{command}'. Usa 'help'.")


if __name__ == "__main__":
    main()
