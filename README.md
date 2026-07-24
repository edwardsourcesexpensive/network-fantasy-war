# Network Fantasy War

Trading Card Game para 2 jugadores. Las cartas forman una red: los vinculos entre ellas crean escuadrones (lineas, triangulos, cuadrados, pentagonos) que determinan el poder de ataque.

## Requisitos

- Python 3.10+
- Flask + Flask-SocketIO: `pip install flask flask-socketio`

## Como jugar — Modo local (single player)

```bash
pip install flask
python -m webui.app
# Abrir http://localhost:5000
```

Dos modos: 1P vs IA o 2P hotseat (misma pantalla).

## Como jugar — Modo multijugador online

```bash
pip install flask flask-socketio
python -m webui.multiplayer.app
# Abrir http://localhost:5001
```

### Hosting gratuito (para que otros jueguen desde internet)

**Railway** (el mas facil):
1. Subi el ZIP a GitHub
2. En railway.app, crea nuevo proyecto desde GitHub
3. Configura: Start Command = `python -m webui.multiplayer.app`
4. Agrega la variable de entorno: `PORT=5001`
5. Railway te da una URL publica. Compartila.

**Render:**
1. Crea nuevo Web Service desde GitHub
2. Build Command: `pip install flask flask-socketio`
3. Start Command: `python -m webui.multiplayer.app`
4. Render te da `https://tu-app.onrender.com`

**PythonAnywhere:**
1. Subi los archivos via Files
2. Crea una Web App con Flask
3. Apunta a `webui.multiplayer.app`
4. URL: `https://tu-usuario.pythonanywhere.com`

En todos los casos, la persona que crea la sala comparte el codigo de 4 letras con su oponente, y ambos juegan desde sus navegadores.

## Estructura

| Carpeta | Contenido |
|----------|-----------|
| `prototype/` | Motor del juego (reglas, cartas, mazos) |
| `webui/app.py` | Servidor single-player (puerto 5000) |
| `webui/multiplayer/app.py` | Servidor multijugador online (puerto 5001) |
| `rules-reference.pdf` | Reglas completas (17 secciones) |
| `ui-guide.pdf` | Guia de la interfaz web |
| `deck-guide.pdf` | Los 8 mazos con todas las cartas y habilidades |
| `NFW-Playable.zip` | Todo lo necesario para jugar |

## Reglas basicas

- **Objetivo**: destruir los 30 sellos del grimorio enemigo
- **Turno**: Robar 2, 4 acciones (jugar/vincular/ascender), Atacar, Fin
- **Escuadrones**: linea(1), triangulo(2), cuadrado(3), pentagono(4)
- **Mazos**: 8 preconstruidos de 50 cartas cada uno
