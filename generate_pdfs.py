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
# RULES PDF
# ═══════════════════════════════════════════════════════════

def gen_rules():
    pdf = NFWPDF('Network Fantasy War - Reglas Completas')
    pdf.set_margin(15)
    
    pdf.cover('NETWORK FANTASY WAR', 'Reglas Oficiales - Version Completa', 'Manual de referencia detallado')
    
    # ═══ 1. Concepto ═══
    pdf.new_page('1. Concepto General')
    pdf.txt(
        'Network Fantasy War es un Trading Card Game para dos jugadores. Cada jugador '
        'comanda una civilizacion organizada como una red: las cartas son nodos y las '
        'conexiones entre ellas son vinculos. Las propiedades emergentes de la red '
        '(escuadrones, potenciamiento mutuo, coordinacion) son mas importantes que las '
        'estadisticas individuales de cada carta. El objetivo es destruir el grimorio '
        'del rival, protegido por 30 sellos. Gana el jugador que rompe el ultimo sello.'
    )
    
    # ═══ 2. Componentes ═══
    pdf.sec('2. Componentes')
    pdf.tbl(['Componente', 'Cantidad', 'Notas'], [
        ['Mazo principal', '50 cartas/jug.', 'Sideboard opcional de 10'],
        ['Carta de Grimorio', '1 por jugador', 'Marcador de sellos (30)'],
        ['Playmat', '1 por jugador', 'Territorio 3 layers x 15 meridianos'],
        ['Varillas de vinculo', '~40 por jugador', '3 tamanos: cortas, medias, largas'],
        ['Contadores de color', '~20 por jugador', 'Para marcar estados y sellos'],
        ['Dado de 6 caras', '1 compartido', 'Uso acotado (ver seccion 14)'],
    ])
    
    # ═══ 3. Territorio ═══
    pdf.sec('3. El Escenario de Guerra')
    pdf.sub('3.1 Territorios')
    pdf.txt(
        'Dos playmats enfrentados, uno por jugador, unidos por el borde. La linea de '
        'contacto es la frontera. Cada playmat representa el territorio de un jugador.'
    )
    pdf.sub('3.2 Estructura del Territorio')
    pdf.txt(
        'Cada territorio es una cuadricula de 3 layers x 15 meridianos:\n'
        '- L1 (Retaguardia): mas cercana al jugador\n'
        '- L2 (Vanguardia): zona intermedia\n'
        '- L3 (Linea de fuego): mas cercana a la frontera y al enemigo\n'
        '- Frontera: linea entre ambos territorios. Solo espias y cartas especiales aqui.\n\n'
        'LAYOUT (jugador arriba, jugador abajo):\n'
        '  J2 L1 [celdas...]\n  J2 L2 [celdas...]\n  J2 L3 [celdas...]\n'
        '  === FRONTERA ===\n'
        '  J1 L3 [celdas...]\n  J1 L2 [celdas...]\n  J1 L1 [celdas...]\n\n'
        'El territorio puede extenderse horizontalmente anadiendo meridianos si la red '
        'crece mas alla de 15 columnas.'
    )
    pdf.sub('3.3 Ubicacion de Cartas')
    pdf.txt(
        'REGLA FUNDAMENTAL: No puede ubicarse una carta en una celda horizontalmente '
        'adyacente a otra ocupada en el mismo layer. Esto no aplica a la frontera. '
        'Ejemplo: si hay carta en (L2, m5), las celdas (L2, m4) y (L2, m6) quedan '
        'bloqueadas para nuevas cartas en L2.\n\n'
        'Movimiento horizontal: en cualquier momento de tu turno, puedes desplazar cartas '
        'lateralmente sin costo. Si un desplazamiento deja dos cartas vinculadas a una '
        'distancia mayor que la permitida, ese vinculo se disuelve.\n\n'
        'Movimiento vertical: solo mediante la accion de ascenso.'
    )
    
    # ═══ 4. La Red ═══
    pdf.sec('4. La Red: Nodos, Vinculos y Escuadrones')
    pdf.sub('4.1 Nodos')
    pdf.txt('Toda carta en el territorio de guerra es un nodo de la red.')
    
    pdf.sub('4.2 Vinculos')
    pdf.txt(
        'Dos nodos pueden conectarse mediante una varilla de vinculo. Una varilla entre '
        'dos cartas representa un vinculo directo. Si dos cartas no estan conectadas '
        'directamente pero comparten una carta vecina, tienen un vinculo indirecto '
        '(distancia de red = 2). Cada carta tiene una capacidad de vinculos (V): el '
        'numero maximo de vinculos directos que puede sostener.'
    )
    
    pdf.sub('4.3 Distancia Espacial y Costo de Vinculos')
    pdf.tbl(['Tipo', 'Distancia', 'Costo base'], [
        ['Proxima (corta)', '0f x 2col, o 1f x 0-1col', '1 accion'],
        ['Media', '0f x 3col, o 1f x 2col', '1 accion (mismo color) / 2 acc (distinto)'],
        ['Distante (larga)', '2f x 1col, o 1f x 3col', '3 acciones'],
        ['Invalida', 'Cualquier distancia mayor', 'No se puede vincular'],
    ])
    pdf.txt(
        'Excepciones: vinculos con logistrones siempre 1 accion. Vinculos frontera-L3: 4 acciones.'
    )
    
    pdf.sub('4.4 Escuadrones')
    pdf.txt('Varios nodos conectados forman un escuadron. Se clasifican por forma geometrica:')
    pdf.tbl(['Tipo', 'Nodos min.', 'Vinculos requeridos'], [
        ['Linea', '2', '1 vinculo directo'],
        ['Triangulo', '3', '3 vinculos (poligono cerrado)'],
        ['Cuadrilatero basico', '4', '4 vinculos (ciclo cerrado)'],
        ['Cuadrilatero ampliado', '4 perim. + N int.', '4 perim. + vinculos int.'],
        ['Pentagono basico', '5', '5 vinculos (ciclo cerrado)'],
        ['Pentagono ampliado', '5 perim. + N int.', '5 perim. + vinculos int.'],
    ])
    pdf.txt(
        'Un escuadron es "ampliado" cuando, ademas del poligono perimetral, contiene '
        'al menos un nodo interior conectado a 3+ nodos del perimetro. Regla: las '
        'cartas no atacan solas. Solo los escuadrones pueden declarar ataques.'
    )
    
    pdf.sub('4.5 Logistrones y Conexion entre Escuadrones')
    pdf.txt(
        'Los nodos de un escuadron no pueden establecer vinculos directos con nodos de '
        'otro escuadron. Para conectar escuadrones se requiere un logistron (puente). '
        'Un logistron puede vincularse con nodos de distintos escuadrones. No forman '
        'parte de ningun poligono pero si son nodos de la red y cuentan para la '
        'distancia de red entre escuadrones.'
    )
    
    # ═══ 5. Turno ═══
    pdf.sec('5. Estructura del Turno')
    pdf.txt('Cada turno se divide en cuatro fases:')
    
    pdf.sub('5.1 Fase de Entrada')
    pdf.txt(
        '1. Habilidades de inicio: se activan las que digan "Al comienzo del turno..." '
        'en el orden que el dueño del turno elija. Luego, el rival activa las suyas.\n'
        '2. Robar: el jugador activo roba 2 cartas de su reserva.'
    )
    
    pdf.sub('5.2 Fase de Acciones (4 acciones)')
    pdf.txt(
        'El jugador dispone de 4 acciones por turno para:\n'
        '- Jugar cartas (1 accion): colocar carta de la mano en el territorio.\n'
        '- Ascender nodos (ver 5.3).\n'
        '- Establecer vinculos (ver 4.3).\n'
        '- Activar habilidades con coste [N]: consumen N acciones.\n\n'
        'Habilidades "Durante tu turno..." no consumen acciones.'
    )
    
    pdf.sub('5.3 Ascensos')
    pdf.txt(
        'Mover un nodo a un layer superior. SOLO puede ascenderse a capas listadas '
        'en allowed_layers de la carta. Una carta con [L1,L2] puede ascender a L2 '
        'pero nunca a L3.'
    )
    pdf.tbl(['Movimiento', 'Costo'], [
        ['L1 -> L2', '1 accion'],
        ['L2 -> L3', '2 acciones'],
        ['Infiltra espia', '1 accion (se considera ascenso)'],
    ])
    
    pdf.sub('5.4 Fase de Ataque')
    pdf.txt('Ver seccion 6 (Sistema de Combate).')
    
    pdf.sub('5.5 Fase de Salida')
    pdf.txt(
        '1. Purgar nodos aislados: remover nodos enemigos sin vinculos directos.\n'
        '2. Habilidades de cierre: "Al final del turno...". Dueño del turno primero.\n'
        '3. Descartar: hasta 5 cartas en mano. Por cada descarte: -1 sello propio.\n'
        '4. Efectos de escuadron al final del turno:\n'
        '   - Selladores: +10 sellos al grimorio por escuadron.\n'
        '   - Sabotaje: deshacer hasta 2 vinculos cortos en red enemiga.\n'
        '   - Monstruos: remover 1 nodo enemigo (grado < ataque) por escuadron.'
    )
    
    # ═══ 6. Combate ═══
    pdf.sec('6. Sistema de Combate')
    pdf.sub('6.1 Declaracion de Ataque')
    pdf.txt(
        'El dueño del turno puede atacar con cada uno de sus escuadrones, uno por uno. '
        'Por cada escuadron elige un objetivo: atacar el grimorio (daño a sellos) o '
        'atacar un nodo (daño a HP de carta enemiga). Si HP llega a 0, la carta es '
        'destruida y va a la pila de descartes. Los ataques son secuenciales. El '
        'defensor puede elegir un escuadron defensor distinto para cada ataque. '
        'Un escuadron no puede atacar mas de una vez por turno.'
    )
    
    pdf.sub('6.2 Calculo del Daño')
    pdf.txt('DANO = DANO_BASE + POTENCIAMIENTO + DANO_EXTRA')
    pdf.box([
        ('Daño base', 'Segun tipo de escuadron (ver tabla seccion 7)'),
        ('Potenciamiento', 'Bonificaciones de escuadrones aliados conectados via red'),
        ('Daño extra', 'Suma de +D de las cartas del escuadron + habilidades activas'),
    ])
    
    pdf.sub('6.3 Defensa')
    pdf.txt(
        'El defensor puede elegir UN escuadron defensor para bloquear. Si no elige, '
        'el daño va integro al objetivo. Si elige:\n'
        'DANO_NETO = DANO_ATACANTE - DEFENSA_ESCUADRON\n\n'
        'DEFENSA = POTENCIAMIENTO_DEFENSIVO + ARMADURA + BONUS_DEFENSA\n'
        '- Potenciamiento defensivo: +1 por escuadron conectado\n'
        '- Armadura: bonus por faccion (ej: Festivos +2)\n'
        '- Bonus de defensa: por habilidades (ej: Guardaespaldas)\n\n'
        'Si DANO_NETO <= 0, el ataque es completamente absorbido.'
    )
    
    pdf.sub('6.4 Aplicacion del Daño')
    pdf.txt(
        'Contra el grimorio: 1 punto de daño neto = 1 sello roto (30 iniciales).\n'
        'Contra un nodo: 1 punto = -1 HP. Si HP llega a 0, el nodo es destruido '
        'y todos sus vinculos se disuelven.'
    )
    
    pdf.sub('Regla de Guardaespaldas')
    pdf.txt(
        'Cuando una carta con Guardaespaldas es atacada, su controlador puede '
        'redirigir el daño neto a cualquier nodo vinculado directamente a ella.'
    )
    
    # ═══ 7. Tablas ═══
    pdf.sec('7. Tabla de Daño y Potenciamiento')
    pdf.tbl(
        ['Escuadron', 'Daño', 'Potenciamiento', 'Alcance'],
        [
            ['Linea', '1', '+1', 'Distancia 1'],
            ['Triangulo', '2', '+3', 'Distancia 1'],
            ['Cuadrilatero basico', '3', '+5', 'Distancia 2'],
            ['Cuadrilatero ampliado', '3+X', '5+X', 'Distancia 2'],
            ['Pentagono basico', '4', '+7', 'Ilimitado'],
            ['Pentagono ampliado', '4+2Y', '7+2Y', 'Ilimitado'],
        ],
        [40, 20, 35, 35]
    )
    pdf.txt(
        'X = nodos internos del cuadrilatero. Y = nodos internos del pentagono. '
        'Cada nodo interno anade daño (X o 2Y) al escuadron.'
    )
    
    pdf.sub('7.1 Como Funciona el Potenciamiento')
    pdf.txt(
        'Cuando el escuadron A ataca, recibe el potenciamiento de todo escuadron B '
        'conectado a traves de la red, cuya distancia de red sea menor o igual al '
        'alcance de B. El potenciamiento NO es simetrico. Se acumula: un escuadron '
        'conectado a tres triangulos a distancia 1 recibe +9 de potenciamiento.'
    )
    
    # ═══ 8. Colores ═══
    pdf.sec('8. Colores y Facciones')
    pdf.txt('El juego tiene 12 colores de carta: 10 facciones + 2 especiales.')
    pdf.tbl(
        ['#', 'Faccion', 'Color', 'Rol Mecanico'],
        [
            ['1', 'Selladores', 'Blanco', 'Defensa: reparan y anaden sellos'],
            ['2', 'Guerreros', 'Rojo', 'Alto daño, especialmente en L2/L3'],
            ['3', 'Politicos', 'Naranja', 'Gestion: intercambian posiciones'],
            ['4', 'Saboteadores', 'Negro', 'Destruyen vinculos enemigos'],
            ['5', 'Alquimistas', 'Purpura', 'Activan todas las habilidades de color'],
            ['6', 'Militares', 'Azul', 'Ascensos gratis y extra'],
            ['7', 'Festivos', 'Verde', '+2 armadura a vinculos'],
            ['8', 'Monstruos', 'Gris', 'Destruccion de nodos enemigos'],
            ['9', 'Sabios', 'Amarillo', 'Robo adicional de cartas'],
            ['10', 'Naturaleza', 'Marron', '+1 daño y +1 pot por unidad'],
            ['-', 'Logistrones', 'Plateado', 'Conectan escuadrones'],
            ['-', 'Espias', 'Dorado', 'Infiltran territorio enemigo'],
        ],
        [10, 30, 25, 95]
    )
    
    pdf.sub('8.1 Color de un Escuadron')
    pdf.txt(
        'Cuando mas de la mitad de las cartas comparten un color, el escuadron es de '
        'ese color. Si ningun color alcanza mayoria, es incoloro sin bonus de color.'
    )
    pdf.sub('8.2 Habilidades de Color vs. Color de Carta')
    pdf.txt(
        'Cada carta tiene un color propio, pero sus habilidades de color pueden ser '
        'de un color distinto. Ej: un Guerrero (rojo) con habilidad Azul que solo se '
        'active en escuadron azul.'
    )
    pdf.sub('8.3 Efectos de Faccion por Escuadron')
    pdf.tbl(
        ['Faccion', 'Efecto', 'Timing'],
        [
            ['Selladores', '+10 sellos al grimorio', 'Fin del turno'],
            ['Guerreros', '+1 daño base por nodo en L2/L3', 'Al atacar'],
            ['Politicos', 'Intercambiar 2 cartas por escuadron', 'Inicio del turno'],
            ['Saboteadores', 'Deshacer 2 vinculos cortos en red enemiga', 'Fin del turno'],
            ['Alquimistas', 'Todas las habilidades de color activas', 'Permanente'],
            ['Militares', 'Ascender 1 unidad sin costo', 'Inicio del turno'],
            ['Festivos', '+2 armadura a vinculos', 'Permanente'],
            ['Monstruos', 'Remover 1 nodo enemigo', 'Fin del turno'],
            ['Sabios', '+1 carta extra al robar', 'Al robar'],
            ['Naturaleza', 'Unidades +1 daño y +1 pot', 'Permanente'],
        ],
        [35, 70, 45]
    )
    
    # ═══ 9. Habilidades ═══
    pdf.sec('9. Habilidades')
    pdf.sub('9.1 Tipos de Habilidades')
    pdf.tbl(['Tipo', 'Condicion de Activacion'], [
        ['Habilidad de color', 'La carta esta en escuadron del color indicado'],
        ['Habilidad de formacion', 'La carta esta en escuadron de la forma indicada'],
        ['Habilidad general', 'La carta esta en el territorio de guerra'],
    ])
    pdf.txt(
        'Una habilidad de formacion puede anidarse en una de color: "[Azul][Pentagono]: '
        'efecto" requiere AMBAS condiciones.'
    )
    
    pdf.sub('9.2 Keywords')
    pdf.tbl(['Keyword', 'Efecto'], [
        ['Caudillismo', 'Al llegar a L3: vinculo gratis con nodo en L2'],
        ['Guardaespaldas', 'Redirige daño a nodo vinculado directamente'],
        ['Vanguardia', 'Entra en juego directamente en L2'],
        ['Sigilo', 'No puede ser blanco de ataques enemigos'],
        ['Autofobia', 'Sin vinculos al final del turno: va al cementerio'],
        ['Reticencia', 'No puede vincularse con nodos de colores indicados'],
    ])
    
    # ═══ 10. Espias ═══
    pdf.sec('10. Espias')
    pdf.txt(
        '1. Despliegue: se juegan en la frontera (1 accion).\n'
        '2. Movimiento: infiltracion a territorio enemigo cuenta como ascenso (1 accion). '
        'No pueden regresar.\n'
        '3. Vinculos: pueden vincularse con unidades enemigas y otros espias.\n'
        '4. Poligonos: forman parte de los poligonos del jugador en cuyo territorio estan.\n'
        '   - Sabotaje: 1 accion para deshacer 1 vinculo del escuadron que lo contiene.\n'
        '   - Inteligencia: al atacar el escuadron que contiene al espia, ves 1 carta '
        'al azar de la mano del atacante.\n'
        '   - Contraespionaje: puedes atacar espias enemigos en tu territorio directamente.'
    )
    
    # ═══ 11. Grimorio ═══
    pdf.sec('11. El Grimorio')
    pdf.txt(
        'Cada jugador comienza con 30 sellos. Cada punto de daño neto rompe 1 sello. '
        'Al destruir el ultimo sello, el grimorio colapsa y el jugador pierde. '
        'Los Selladores anaden 10 sellos al grimorio al final del turno.'
    )
    
    # ═══ 12. Reserva ═══
    pdf.sec('12. La Reserva (Mazo) y la Mano')
    pdf.box([
        ('Mazo principal', '50 cartas'),
        ('Mano inicial', '5 cartas'),
        ('Robo por turno', '2 cartas (+1 extra por escuadron de Sabios)'),
        ('Limite de mano', '5 cartas al final del turno'),
        ('Penalizacion descarte', '-1 sello propio por carta descartada'),
        ('Fatiga (deck-out)', '-1 sello por carta no robada al agotarse la reserva'),
    ])
    
    # ═══ 13. Anatomia ═══
    pdf.sec('13. Anatomia de una Carta')
    pdf.tbl(['Campo', 'Descripcion'], [
        ['Nombre', 'Identificador unico'],
        ["Color", 'Indicador de faccion'],
        ["Copias max. (C's)", '1, 3 o 5 por mazo'],
        ['HP', 'Puntos de vida. Al llegar a 0, destruida'],
        ['D', 'Daño adicional al escuadron al atacar'],
        ['V', 'Capacidad maxima de vinculos directos (2-6)'],
        ['Layers', 'Capas permitidas: L1, L2, L3'],
        ['Formaciones', 'Tipos de poligono: Triangulo, Cuad., Pent.'],
        ['H. de color', 'Efectos condicionados al color del escuadron'],
        ['H. de formacion', 'Efectos condicionados a la forma del escuadron'],
        ['H. generales', 'Efectos incondicionales o de timing'],
    ], [40, 130])
    
    # ═══ 14. Dado ═══
    pdf.sec('14. El Dado')
    pdf.txt(
        'El dado de 6 caras se usa exclusivamente para resolver empates de prioridad '
        'y efectos de carta que expliciten una tirada. No se usa para combate ni daño.'
    )
    
    # ═══ 15. Setup ═══
    pdf.sec('15. Setup de la Partida')
    pdf.txt(
        '1. Colocar playmats enfrentados con la frontera en contacto.\n'
        '2. Carta de Grimorio junto al playmat, con 30 contadores de sellos.\n'
        '3. Barajar mazo de 50 cartas y robar 5 como mano inicial.\n'
        '4. Decidir quien juega primero (dado o acuerdo).\n'
        '5. El primer jugador comienza su Fase de Entrada.'
    )
    pdf.sub('Regla de Mulligan')
    pdf.txt(
        'El jugador que comienza puede hacer mulligan: barajar su mano, robar 5 cartas '
        'nuevas y perder 1 sello. Luego el rival puede hacer lo mismo. Se alterna hasta '
        'que ambos se planten consecutivamente. Cada mulligan cuesta 1 sello adicional '
        '(1ro: 1 sello, 2do: 2 sellos, etc.). Sin limite.'
    )
    
    # ═══ 16. Glosario ═══
    pdf.sec('16. Glosario')
    pdf.tbl(['Termino', 'Definicion'], [
        ['Nodo', 'Carta en el territorio de guerra'],
        ['Vinculo directo', 'Conexion fisica (varilla) entre dos nodos'],
        ['Vinculo indirecto', 'Dos nodos conectados a traves de un tercero'],
        ['Distancia de red', 'Numero minimo de vinculos entre dos nodos'],
        ['Escuadron', 'Conjunto de nodos con forma poligonal definida'],
        ['Logistron', 'Unidad que conecta escuadrones entre si'],
        ['Potenciamiento', 'Bonificacion que un escuadron da a otros'],
        ['Grimorio', 'Fuente de poder, protegida por 30 sellos'],
        ['Sello', 'Punto de proteccion del grimorio'],
        ['Frontera', 'Linea divisoria entre los dos territorios'],
        ['Ascenso', 'Movimiento de un nodo a un layer superior'],
    ], [45, 135])
    
    pdf.ln(5)
    pdf.txt(
        'Documento generado a partir del diseño original de Eduardo Fuentes Caro. '
        'Version formalizada y expandida. Julio 2026.'
    )
    
    out = os.path.join(PROJECT, 'rules-reference.pdf')
    pdf.output(out)
    print(f'  rules-reference.pdf')
    return out


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
    gen_rules()
    gen_ui_guide()
    gen_deck_guide()
    print('Done.')
