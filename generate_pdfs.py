"""
Network Fantasy War - PDF Generator v2
Dark theme throughout, expanded rules, Magic-style card guide.
"""
from fpdf import FPDF
import os, textwrap

PROJECT = r"D:\DocumentsD\Proyectos-Personales\Network-Fantasy-War"

# Colors
BG = (26, 26, 46)
DARK = (22, 33, 62)
ACCENT = (233, 69, 96)
BLUE = (79, 195, 247)
TEXT = (224, 224, 224)
MUTED = (150, 150, 160)
WHITE = (255, 255, 255)

class NFWPDF(FPDF):
    def __init__(self, title):
        super().__init__('P', 'mm', 'A4')
        self.t = title
        self.set_auto_page_break(True, 18)
        self.add_font('Arial', '', 'C:/Windows/Fonts/arial.ttf')
        self.add_font('Arial', 'B', 'C:/Windows/Fonts/arialbd.ttf')
        self.add_font('Arial', 'I', 'C:/Windows/Fonts/ariali.ttf')
        self.add_font('Arial', 'BI', 'C:/Windows/Fonts/arialbi.ttf')
        self.F = 'Arial'
        self._bg_done = False
    
    def add_page(self, *args, **kwargs):
        super().add_page(*args, **kwargs)
        self.bg_page()
    
    def bg_page(self):
        """Fill entire page with dark background."""
        self.set_fill_color(*BG)
        self.rect(0, 0, 210, 297, 'F')
        self.set_font(self.F, 'B', 8)
        self.set_text_color(*ACCENT)
        self.set_y(2.5)
        self.cell(0, 7, self.t, align='C')
        self.set_y(14)
    
    def footer(self):
        if self.page_no() <= 1: return
        self.set_y(-15)
        self.set_font(self.F, 'I', 6)
        self.set_text_color(*MUTED)
        self.cell(0, 8, str(self.page_no()), align='C')
    
    def bg_page(self):
        """Fill entire page with dark background."""
        self.set_fill_color(*BG)
        self.rect(0, 0, 210, 297, 'F')
    
    def cover(self, title, subtitle, extra=""):
        self.add_page()
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 85, 'F')
        self.set_fill_color(*ACCENT)
        self.rect(0, 85, 210, 4, 'F')
        self.set_y(30)
        self.set_font(self.F, 'B', 30)
        self.set_text_color(*ACCENT)
        self.cell(0, 15, title, align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font(self.F, '', 15)
        self.set_text_color(*TEXT)
        self.cell(0, 10, subtitle, align='C', new_x="LMARGIN", new_y="NEXT")
        if extra:
            self.ln(4)
            self.set_font(self.F, 'I', 10)
            self.set_text_color(*MUTED)
            self.cell(0, 7, extra, align='C', new_x="LMARGIN", new_y="NEXT")
    
    def new_page(self, title=""):
        self.add_page()
        if title:
            self.sec(title)
    
    def sec(self, t):
        self.check_space(20)
        self.ln(3)
        self.set_x(self.l_margin)
        self.set_font(self.F, 'B', 15)
        self.set_text_color(*ACCENT)
        self.cell(0, 9, t, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.line(self.l_margin, self.get_y(), 210-self.r_margin, self.get_y())
        self.ln(3)
    
    def check_space(self, needed):
        """Ensure at least `needed` mm of space remain. If not, new page."""
        if self.get_y() + needed > 280:
            self.add_page()
    
    def sub(self, t):
        self.set_x(self.l_margin)
        self.set_font(self.F, 'B', 11)
        self.set_text_color(*BLUE)
        self.cell(0, 7, t, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
    
    def txt(self, t):
        self.set_font(self.F, '', 9)
        self.set_text_color(*TEXT)
        self.set_x(self.l_margin)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 4.8, t)
    
    def bul(self, t):
        self.set_font(self.F, '', 9)
        self.set_text_color(*TEXT)
        self.cell(5, 4.8, chr(8226))
        self.set_x(self.l_margin + 7)
        self.multi_cell(self.w - self.l_margin - self.r_margin - 7, 4.8, t)
        self.set_x(self.l_margin)
    
    def box(self, items):
        self.check_space(8 * len(items) + 15)
        self.set_fill_color(*DARK)
        self.set_draw_color(60, 60, 80)
        y0 = self.get_y()
        w = self.w - self.l_margin - self.r_margin
        self.rect(self.l_margin, y0, w, 6*len(items)+10, 'DF')
        self.set_xy(self.l_margin + 3, y0+4)
        for k, v in items:
            self.set_font(self.F, 'B', 8)
            self.set_text_color(*BLUE)
            self.cell(55, 5.5, k)
            self.set_font(self.F, '', 8)
            self.set_text_color(*TEXT)
            self.cell(w - 61, 5.5, str(v), new_x="LMARGIN", new_y="NEXT")
            self.set_x(self.l_margin + 3)
        self.set_y(y0 + 6*len(items) + 12)
    
    def tbl(self, hdrs, rows, w=None):
        self.check_space(8 * (len(rows) + 1) + 15)
        avail = self.w - self.l_margin - self.r_margin
        if not w:
            w = [avail / len(hdrs)] * len(hdrs)
        self.set_fill_color(*DARK)
        self.set_draw_color(60, 60, 80)
        self.set_font(self.F, 'B', 7)
        self.set_text_color(*ACCENT)
        for i, h in enumerate(hdrs):
            self.cell(w[i], 5.5, h, border=1, fill=True, align='C')
        self.ln()
        self.set_font(self.F, '', 7)
        self.set_text_color(*TEXT)
        for row in rows:
            for i, c in enumerate(row):
                self.cell(w[i], 5, str(c)[:35], border=1, align='C')
            self.ln()
        self.ln(2)


# ═══════════════════════════════════════════════════════════
# UI GUIDE PDF
# ═══════════════════════════════════════════════════════════

def gen_ui_guide():
    pdf = NFWPDF('Network Fantasy War - Guia Web')
    pdf.set_margin(18)

    pdf.cover('NETWORK FANTASY WAR', 'Guia de la Interfaz Web',
              'Multijugador online + juego local')

    pdf.new_page('1. Como Jugar')
    pdf.txt('El juego se juega en el navegador. La version desplegada es la multijugador:')
    pdf.box([
        ('Online (desplegado)', 'https://network-fantasy-war-production.up.railway.app/'),
        ('Local multijugador', 'python -m webui.multiplayer.app  ->  http://localhost:5001'),
        ('Local 1 jugador (pruebas)', 'python -m webui.app  ->  http://localhost:5000'),
    ])
    pdf.txt('Requisitos (solo local): Python 3.10+ y flask / flask-socketio.')

    pdf.sec('2. Pantalla de Inicio (lobby)')
    pdf.txt(
        'Al abrir el juego ves tres modos:\n'
        '- Jugar vs IA: partida contra el bot; eliges mazo y empieza al instante\n'
        '- Crear sala (2 jugadores): generas un codigo de 4 letras/digitos y lo compartes\n'
        '- Unirse a sala: introduces el codigo que te paso tu oponente'
    )
    pdf.sub('Botones del lobby')
    pdf.txt(
        'Debajo de los modos hay accesos directos:\n'
        '- Reglas (PDF): abre el manual de reglas\n'
        '- Ver Decks: lista los 8 mazos con estadisticas y cartas\n'
        '- Cartas: galeria de las 370 cartas del juego\n'
        '- Ayuda: resumen rapido de la interfaz'
    )
    pdf.sub('Seleccion de Mazo')
    pdf.txt(
        'Al crear o unirte a una sala (y en vs IA) eliges tu mazo. Hay 8 mazos de 50 cartas:\n'
        'Muro Inquebrantable, Filo Carmesi, Red de Sombras, Colegio Arcano, '
        'Asamblea Popular, Legion de Acero, Jardin Salvaje, Consejo Arcano.'
    )

    pdf.sec('3. Crear / Unirse a Sala')
    pdf.txt(
        'Crear: eliges mazo y pulsas "Crear sala". Aparece un codigo de 4 letras que '
        'le pasas a tu oponente. Unirse: el oponente escribe ese codigo en "Unirse a sala", '
        'elige su mazo y pulsa "Unirse". Cuando ambos estan listos, la partida empieza '
        'y ambos van al tablero.'
    )

    pdf.sec('4. El Tablero')
    pdf.txt(
        'Muestra los territorios de ambos jugadores separados por la frontera. '
        'Cada territorio tiene 3 filas (L1, L2, L3) de 15 celdas.\n\n'
        '- Celda azul oscuro: libre para jugar\n'
        '- Celda con mini-carta: carta en juego (borde = faccion; HP/D abajo-derecha; V arriba-derecha)\n'
        '- Celda rojo oscuro: carta enemiga infiltrada (espia)\n\n'
        'Lineas de vinculo:\n'
        '- Amarilla solida: vinculo normal\n'
        '- Azul punteada: uno de los extremos es un Logistron\n'
        '- Roja punteada: vinculo entre jugadores distintos (espia)'
    )
    pdf.sub('Panel de Detalle')
    pdf.txt(
        'Al hacer CLIC en una carta del tablero se abre un panel flotante con sus '
        'habilidades completas y, si tiene habilidades activas, los botones para usarlas '
        '(con su coste en acciones).'
    )
    pdf.sub('Fondo por Jugador')
    pdf.txt(
        'El fondo cambia segun el turno (azul oscuro para J1, verde para J2) y el '
        'indicador superior muestra de quien es el turno.'
    )
    pdf.sub('Boton Flip')
    pdf.txt(
        'El boton Flip invierte el tablero para que el jugador activo quede abajo, '
        'cerca de su mano.'
    )

    pdf.sec('5. Acciones del Jugador')

    pdf.sub('5.1 Jugar una Carta')
    pdf.txt(
        '1. Clic en una carta de tu mano (se resalta)\n'
        '2. Clic en una celda vacia del tablero\n'
        '3. Boton "Jugar carta". Cuesta 1 accion.'
    )

    pdf.sub('5.2 Vincular Cartas')
    pdf.txt(
        '1. Clic en una carta del tablero\n'
        '2. Boton "Vincular"\n'
        '3. Clic en otra carta: el vinculo se crea si es valido (distancia, color, capacidad V).'
    )

    pdf.sub('5.3 Ascender')
    pdf.txt(
        'Selecciona una carta y pulsa "Ascender". L1->L2: 1 accion. L2->L3: 2 acciones. '
        'Respeta las restricciones de capa de la carta.'
    )

    pdf.sub('5.4 Fase de Ataque')
    pdf.txt(
        'Boton "Atacar ->" entra en fase de ataque. Clic en uno de tus escuadrones y elige '
        'objetivo (grimorio o nodo enemigo).\n\n'
        'En 2 jugadores, el defensor recibe un POP-UP para elegir escuadron defensor '
        '(o "Sin defensor" para recibir el daño directo). Cada escuadron ataca una vez por turno.'
    )

    pdf.sub('5.5 Fin del Turno')
    pdf.txt(
        '"Fin Turno" ejecuta la fase de salida (purga de nodos aislados, habilidades de cierre, '
        'descarte) y cede el turno. "Finalizar ataque" solo termina la fase de ataque.'
    )

    pdf.sec('6. Pantalla de Victoria')
    pdf.txt(
        'Al reducir los sellos enemigos a 0, aparece un overlay con el jugador ganador, '
        'los sellos finales y la opcion de nueva partida.'
    )

    pdf.sec('7. Referencia de Controles')
    pdf.tbl(
        ['Boton', 'Fase', 'Accion'],
        [
            ['Jugar carta', 'Acciones', 'Coloca una carta de la mano en el tablero'],
            ['Vincular', 'Acciones', 'Enlaza dos cartas seleccionadas'],
            ['Ascender', 'Acciones', 'Sube 1 layer la carta seleccionada'],
            ['Atacar ->', 'Acciones', 'Entra en fase de ataque'],
            ['Finalizar ataque', 'Ataque', 'Sale de fase de ataque'],
            ['Fin Turno', 'Ambas', 'Termina el turno (fase de salida)'],
            ['Rendirse', 'Ambas', 'Abandona la partida'],
            ['Refresh', 'Ambas', 'Recarga el estado del juego'],
            ['Flip', 'Ambas', 'Invierte la orientacion del tablero'],
            ['Reglas', 'Ambas', 'Abre el manual de reglas (PDF)'],
            ['Decks', 'Ambas', 'Muestra los 8 mazos'],
        ],
        [32, 28, 120]
    )

    out = os.path.join(PROJECT, 'ui-guide.pdf')
    pdf.output(out)
    print(f'  ui-guide.pdf')
    return out


# ═══════════════════════════════════════════════════════════
# DECK GUIDE PDF - Magic-style cards with all 370 cards
# ═══════════════════════════════════════════════════════════

def gen_deck_guide():
    from prototype.card import ALL_CARDS, CardDef, Color
    from prototype.decks import DECKS, DECK_NAMES
    
    pdf = NFWPDF('Network Fantasy War - Guia de Mazos')
    pdf.set_margin(12)
    
    pdf.cover('NETWORK FANTASY WAR', 'Guia de Mazos y Cartas',
              '8 mazos preconstruidos')
    
    for deck_id in ['muro', 'filo', 'sombras', 'colegio', 'asamblea', 'legion', 'jardin', 'consejo']:
        deck = DECKS[deck_id]
        name = DECK_NAMES[deck_id].split('(')[0].strip()
        subtitle = DECK_NAMES[deck_id].split('(')[1].rstrip(')') if '(' in DECK_NAMES[deck_id] else ''
        
        pdf.new_page(name)
        pdf.txt(f'Estilo: {subtitle}')
        pdf.ln(1)
        
        # Color distribution
        from collections import Counter
        colors = Counter(c.color.value for c in deck)
        color_line = ' | '.join(f'{c}: {n}' for c, n in colors.most_common())
        pdf.txt(f'Distribucion: {color_line}')
        pdf.ln(2)
        
        # Card list with faction, stats, and abilities
        for c in deck:
            # Card header
            pdf.set_x(pdf.l_margin)
            pdf.set_font(pdf.F, 'B', 9)
            pdf.set_text_color(*ACCENT)
            pdf.cell(80, 5, c.name)
            pdf.set_font(pdf.F, '', 8)
            pdf.set_text_color(*BLUE)
            faction = c.color.value
            pdf.cell(0, 5, f'{faction} | Cs:{c.max_copies}  HP:{c.hp}  D:{c.damage_bonus}  V:{c.link_capacity}  L:{",".join(f"L{x}" for x in c.allowed_layers)}', new_x="LMARGIN", new_y="NEXT")
            
            # Abilities
            if c.abilities:
                for a in c.abilities:
                    pdf.set_x(pdf.l_margin + 5)
                    pdf.set_font(pdf.F, '', 7)
                    pdf.set_text_color(*MUTED)
                    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 5, 4, chr(8226) + ' ' + a.description)
            else:
                pdf.set_x(pdf.l_margin + 5)
                pdf.set_font(pdf.F, 'I', 7)
                pdf.set_text_color(*MUTED)
                pdf.cell(0, 4, '(sin habilidades)', new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(1.5)
    
    out = os.path.join(PROJECT, 'deck-guide.pdf')
    pdf.output(out)
    print(f'  deck-guide.pdf')
    return out

if __name__ == '__main__':
    print('Generating PDFs...')
    gen_ui_guide()
    gen_deck_guide()
    print('Done.')
