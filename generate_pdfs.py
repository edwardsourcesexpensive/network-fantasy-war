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
              'Como jugar desde el navegador\nhttp://localhost:5000')
    
    pdf.new_page('1. Instalacion y Arranque')
    pdf.txt('Requisito unico: Python 3.10+.')
    pdf.box([
        ('Instalar Flask', 'pip install flask'),
        ('Arrancar servidor', 'python -m webui.app'),
        ('Abrir en navegador', 'http://localhost:5000'),
    ])
    
    pdf.sec('2. Pantalla de Inicio')
    pdf.txt(
        'Al abrir, veras la seleccion de modo:\n'
        '- 1 Jugador vs IA: controlas a J1, la IA juega automaticamente\n'
        '- 2 Jugadores (hotseat): ambos comparten la misma pantalla, alternando turnos'
    )
    pdf.sub('Seleccion de Mazo')
    pdf.txt(
        'En modo 2 jugadores, J1 elige primero (fondo azul oscuro), luego J2 (fondo verde). '
        'En modo 1 jugador, tu eliges y la IA recibe uno aleatorio.\n\n'
        '8 mazos disponibles: Muro Inquebrantable, Filo Carmesi, Red de Sombras, '
        'Colegio Arcano, Asamblea Popular, Legion de Acero, Jardin Salvaje, Consejo Arcano.'
    )
    
    pdf.sec('3. El Tablero')
    pdf.txt(
        'Muestra los territorios de J2 (arriba) y J1 (abajo) separados por la frontera. '
        'Cada territorio tiene 3 filas (L1, L2, L3) de 15 celdas.\n\n'
        '- Celda azul oscuro: libre para jugar\n'
        '- Celda azul marino con nombre: carta en juego (HP abajo-derecha, V arriba-derecha)\n'
        '- Celda rojo oscuro: carta enemiga infiltrada (espia)\n\n'
        'Lineas doradas: vinculos entre cartas aliadas\n'
        'Lineas rojas punteadas: vinculos entre territorios (espias/logistrones)'
    )
    pdf.sub('Hover y Panel de Detalle')
    pdf.txt(
        'Pasar el cursor sobre una carta del tablero muestra tooltip con nombre, color, HP, D, V.\n'
        'Al hacer CLIC en una carta del tablero: panel flotante con todas sus habilidades.\n'
        'Las cartas en la mano muestran sus habilidades en texto directamente.'
    )
    pdf.sub('Fondo por Jugador')
    pdf.txt(
        'El fondo cambia segun el turno: azul oscuro para J1, verde oscuro para J2. '
        'El indicador superior muestra de quien es el turno.'
    )
    pdf.sub('Boton Flip')
    pdf.txt(
        'El boton Flip (ultimo a la derecha) invierte el tablero: el jugador activo queda '
        'arriba, cerca de su mano. Util en hotseat sin girar la pantalla.'
    )
    
    pdf.sec('4. Acciones del Jugador')
    
    pdf.sub('4.1 Jugar una Carta')
    pdf.txt(
        '1. Clic en una carta de tu mano (se resalta con borde rojo)\n'
        '2. Clic en una celda vacia del tablero (borde azul punteado)\n'
        '3. Boton "Jugar carta" - la carta aparece en el tablero. Cuesta 1 accion.'
    )
    
    pdf.sub('4.2 Vincular Cartas')
    pdf.txt(
        '1. Clic en una carta del tablero (se selecciona)\n'
        '2. Boton "Vincular" - la carta queda en modo vinculacion\n'
        '3. Clic en otra carta - el vinculo se crea automaticamente\n'
        'Si no es valido, aparece mensaje de error.'
    )
    
    pdf.sub('4.3 Ascender')
    pdf.txt(
        '1. Selecciona una carta en el tablero\n'
        '2. Boton "Ascender" - sube un layer\n'
        'L1-L2: 1 accion. L2-L3: 2 acciones. Respeta restricciones de capa.'
    )
    
    pdf.sub('4.4 Fase de Ataque')
    pdf.txt(
        'Boton "Atacar ->" entra en fase de ataque. Aparece lista de tus escuadrones '
        'con tipo y daño. Clic en un escuadron para atacar.\n\n'
        'El defensor recibe un POP-UP preguntando que escuadron usar para bloquear. '
        'Puede elegir "Sin defensor" para recibir el daño directo.\n\n'
        'Cada escuadron ataca una vez por turno. "Finalizar ataque" termina la fase.'
    )
    
    pdf.sub('4.5 Fin del Turno')
    pdf.txt(
        '"Fin Turno" salta a la fase de salida y empieza el siguiente turno.\n'
        '"Finalizar ataque" solo termina la fase de ataque y pasa al oponente.'
    )
    
    pdf.sec('5. Pantalla de Victoria')
    pdf.txt(
        'Al reducir los sellos enemigos a 0 o menos, aparece overlay con:\n'
        '- Jugador ganador\n- Sellos finales de ambos\n- Turnos jugados\n'
        '- Boton "Nueva partida"'
    )
    
    pdf.sec('6. Referencia de Controles')
    pdf.tbl(
        ['Boton', 'Fase', 'Accion'],
        [
            ['Jugar carta', 'Acciones', 'Coloca carta de la mano en el tablero'],
            ['Vincular', 'Acciones', 'Enlaza dos cartas seleccionadas'],
            ['Ascender', 'Acciones', 'Sube 1 layer la carta seleccionada'],
            ['Atacar ->', 'Acciones', 'Entra en fase de ataque'],
            ['Finalizar ataque', 'Ataque', 'Sale de fase de ataque'],
            ['Fin Turno', 'Ambas', 'Termina el turno actual'],
            ['Refresh', 'Ambas', 'Refresca estado del juego'],
            ['Flip', 'Ambas', 'Invierte orientacion del tablero'],
        ],
        [35, 35, 110]
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
