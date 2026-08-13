"""
NFW Rules PDF Generator (v3 — limpio, sin fancy stuff)
Lee rules-reference.md y genera un PDF dark-theme con todo el texto visible.
"""
from fpdf import FPDF
import re, os

PROJECT = r"D:\DocumentsD\Proyectos-Personales\Network-Fantasy-War"
SRC = os.path.join(PROJECT, "rules-reference.md")
OUT = os.path.join(PROJECT, "rules-reference-comprehensive.pdf")

# ── Colors ──
BG      = (26, 26, 46)
ACCENT  = (233, 69, 96)
BLUE    = (79, 195, 247)
TEXT    = (224, 224, 224)
MUTED   = (150, 150, 160)
WHITE   = (255, 255, 255)
DARK_P  = (22, 33, 62)

class RulesPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(True, 16)
        # fpdf2 style: family, style, path
        self.add_font('Arial', '', 'C:/Windows/Fonts/arial.ttf')
        self.add_font('Arial', 'B', 'C:/Windows/Fonts/arialbd.ttf')
        self.add_font('Arial', 'I', 'C:/Windows/Fonts/ariali.ttf')
        self.add_font('Arial', 'BI', 'C:/Windows/Fonts/arialbi.ttf')
        self.F = 'Arial'

    def add_page(self, *args, **kwargs):
        super().add_page(*args, **kwargs)
        self.set_fill_color(*BG)
        self.rect(0, 0, 210, 297, 'F')

    def footer(self):
        self.set_y(-14)
        self.set_font(self.F, 'I', 6)
        self.set_text_color(*MUTED)
        self.cell(0, 8, str(self.page_no()), align='C')

    # ── helpers ──
    W = property(lambda s: s.w - s.l_margin - s.r_margin)

    def _x(self): self.set_x(self.l_margin)

    def space(self, mm=2):
        if self.get_y() + mm > 280:
            self.add_page()
        self.ln(mm)

    # ── elements ──
    def h1(self, t):
        self.space(8)
        self._x()
        self.set_font(self.F, 'B', 16)
        self.set_text_color(*ACCENT)
        self.cell(0, 10, t, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(3)

    def h2(self, t):
        self.space(6)
        self._x()
        self.set_font(self.F, 'B', 13)
        self.set_text_color(*BLUE)
        self.cell(0, 8, t, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def h3(self, t):
        self.space(4)
        self._x()
        self.set_font(self.F, 'B', 11)
        self.set_text_color(*BLUE)
        self.cell(0, 7, t, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def para(self, t):
        self._x()
        self.set_font(self.F, '', 8.5)
        self.set_text_color(*TEXT)
        self.multi_cell(self.W, 4.5, t)
        self.ln(1)

    def bold_para(self, t):
        self._x()
        self.set_font(self.F, 'B', 8.5)
        self.set_text_color(*TEXT)
        self.multi_cell(self.W, 4.5, t)
        self.ln(1)

    def bullet(self, t):
        self._x()
        self.set_font(self.F, '', 8.5)
        self.set_text_color(*TEXT)
        self.cell(5, 4.5, '•')
        self.set_x(self.l_margin + 6)
        self.multi_cell(self.W - 6, 4.5, t)
        self._x()

    def quote(self, t):
        """Blockquote with left bar."""
        t = sanitize(t)
        self.space(2)
        y0 = self.get_y()
        bar_x = self.l_margin + 1
        self.set_draw_color(*ACCENT)
        self.set_fill_color(*DARK_P)
        # Estimate height
        self.set_font(self.F, 'I', 8)
        lines = self.multi_cell(self.W - 10, 4.2, t, dry_run=True, output="LINES")
        h = max(len(lines) * 4.2 + 6, 10)
        self.rect(self.l_margin, y0, self.W, h, 'F')
        self.line(bar_x, y0 + 2, bar_x, y0 + h - 2)
        self.set_xy(self.l_margin + 6, y0 + 3)
        self.set_font(self.F, 'I', 8)
        self.set_text_color(*MUTED)
        self.multi_cell(self.W - 10, 4.2, t)
        self.set_y(y0 + h + 2)

    def hr(self):
        self.space(3)
        self.set_draw_color(60, 60, 80)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(3)

    def table(self, headers, rows):
        """Draw a markdown table. Headers: bold accent. Rows: regular text."""
        ncols = len(headers)
        avail = self.W
        # Proportional widths: wider columns get more space
        all_cells = [headers] + rows
        max_w = [max(len(str(r[c])) for r in all_cells) for c in range(ncols)]
        total_chars = sum(max_w) + ncols * 3
        widths = [avail * w / total_chars for w in max_w]

        self.space(2)
        self.set_draw_color(60, 60, 80)
        self.set_fill_color(*DARK_P)

        # Header
        self.set_font(self.F, 'B', 7)
        self.set_text_color(*ACCENT)
        self._x()
        for i, h in enumerate(headers):
            self.cell(widths[i], 5.5, sanitize(h), border=1, fill=True, align='C')
        self.ln()

        # Rows
        self.set_font(self.F, '', 7)
        self.set_text_color(*TEXT)
        for row in rows:
            self._x()
            for i, cell in enumerate(row):
                self.cell(widths[i], 5, sanitize(str(cell))[:60], border=1, align='C')
            self.ln()
        self.ln(2)

    def code_block(self, lines):
        self.space(2)
        y0 = self.get_y()
        h = len(lines) * 4 + 6
        self.set_fill_color(*DARK_P)
        self.set_draw_color(60, 60, 80)
        self.rect(self.l_margin, y0, self.W, h, 'DF')
        self.set_xy(self.l_margin + 4, y0 + 3)
        self.set_font(self.F, '', 7.5)
        self.set_text_color(*BLUE)
        for line in lines:
            self._x()
            self.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(self.l_margin + 4)
        self.set_y(y0 + h + 2)


# ── Markdown Parser ──

def sanitize(text):
    """Replace problematic Unicode chars + strip markdown for PDF compatibility."""
    text = text.replace('\u2014', '--').replace('\u2013', '-') \
               .replace('\u2018', "'").replace('\u2019', "'") \
               .replace('\u201c', '"').replace('\u201d', '"') \
               .replace('\u2026', '...').replace('\u00a0', ' ')
    # strip markdown emphasis/code/tags (bold, inline code, strikethrough, [TAG] markers)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    text = re.sub(r'\[(?:NUEVO|PENDIENTE|COMPLETADO[^\]]*|REDISEÑADO|REFORMULADO|EXPANDIDO|FORMALIZADO)\]', '', text)
    text = text.replace('**', '')  # any unpaired leftovers
    return text

def parse_md(path):
    """Parse markdown into a list of elements."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    elements = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Empty / whitespace only
        if not line.strip():
            i += 1
            continue

        # Horizontal rule
        if line.strip() == '---':
            elements.append(('hr',))
            i += 1
            continue

        # Code block ```
        if line.strip().startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].rstrip().startswith('```'):
                code_lines.append(lines[i].rstrip())
                i += 1
            i += 1  # skip closing ```
            if code_lines:
                elements.append(('code', code_lines))
            continue

        # Blockquote >
        if line.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                t = lines[i].strip()
                t = re.sub(r'^>\s*', '', t)
                quote_lines.append(t)
                i += 1
            elements.append(('quote', ' '.join(quote_lines)))
            continue

        # Table (starts with |)
        if line.strip().startswith('|') and line.strip().endswith('|'):
            headers = [c.strip() for c in line.strip().split('|')[1:-1]]
            i += 1
            # Skip separator row
            if i < len(lines) and re.match(r'^\|[\s\-:|]+\|$', lines[i].strip()):
                i += 1
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                cells = [c.strip() for c in lines[i].strip().split('|')[1:-1]]
                rows.append(cells)
                i += 1
            elements.append(('table', headers, rows))
            continue

        # Headings
        h1 = re.match(r'^##\s+(.+)', line)
        h2 = re.match(r'^###\s+(.+)', line)
        h3 = re.match(r'^####\s+(.+)', line)
        if h1:
            elements.append(('h1', sanitize(h1.group(1))))
            i += 1; continue
        if h2:
            elements.append(('h2', sanitize(h2.group(1))))
            i += 1; continue
        if h3:
            elements.append(('h3', sanitize(h3.group(1))))
            i += 1; continue

        # Bullet points
        bullet = re.match(r'^(\s*)-\s+(.+)', line)
        if bullet:
            text = sanitize(bullet.group(2))
            # Handle bold markers
            text = re.sub(r'\*\*(.+?)\*\*', lambda m: m.group(1), text)
            text = re.sub(r'~~(.+?)~~', lambda m: m.group(1), text)
            elements.append(('bullet', text))
            i += 1; continue

        # Bold paragraph (starts with **)
        if line.strip().startswith('**') and line.strip().endswith('**'):
            text = sanitize(re.sub(r'\*\*(.+?)\*\*', r'\1', line.strip()))
            elements.append(('bold', text))
            i += 1; continue

        # Regular paragraph
        # Collect multi-line paragraphs
        para_lines = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and \
              not lines[i].strip().startswith('#') and \
              not lines[i].strip().startswith('>') and \
              not lines[i].strip().startswith('|') and \
              not lines[i].strip().startswith('```') and \
              not lines[i].strip() == '---' and \
              not re.match(r'^\s*-\s+', lines[i]):
            para_lines.append(lines[i].strip())
            i += 1

        text = sanitize(' '.join(para_lines))
        # Clean markdown formatting
        text = re.sub(r'\*\*(.+?)\*\*', lambda m: m.group(1), text)
        text = re.sub(r'`(.+?)`', lambda m: m.group(1), text)
        text = re.sub(r'~~(.+?)~~', lambda m: m.group(1), text)
        text = re.sub(r'\[NUEVO\]', '', text)
        text = re.sub(r'\[PENDIENTE\]', '', text)
        text = re.sub(r'\[COMPLETADO[^\]]*\]', '', text)
        text = re.sub(r'\[REDISEÑADO\]', '', text)
        text = re.sub(r'\[REFORMULADO\]', '', text)
        text = re.sub(r'\[EXPANDIDO\]', '', text)
        text = re.sub(r'\[FORMALIZADO\]', '', text)
        elements.append(('para', text))

    return elements


# ── Main ──
def main():
    elements = parse_md(SRC)
    pdf = RulesPDF()
    pdf.set_left_margin(14)
    pdf.set_right_margin(14)

    # Title page
    pdf.add_page()
    pdf.set_fill_color(*DARK_P)
    pdf.rect(0, 0, 210, 80, 'F')
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 80, 210, 3, 'F')
    pdf.set_y(32)
    pdf.set_font(pdf.F, 'B', 26)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 14, 'Network Fantasy War', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf.F, '', 14)
    pdf.set_text_color(*TEXT)
    pdf.cell(0, 9, 'Manual de Reglas (Armonizacion v1.3)', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font(pdf.F, 'I', 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, 'Documento generado a partir de rules-reference.md', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, 'por Eduardo Fuentes Caro — Julio 2026', align='C', new_x="LMARGIN", new_y="NEXT")

    # TOC
    pdf.set_y(110)
    pdf.set_font(pdf.F, 'B', 12)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 8, 'Contenido', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    toc_items = [
        '1. Concepto general', '2. Componentes', '3. El escenario de guerra',
        '4. La red: nodos, vinculos y escuadrones', '5. Estructura del turno',
        '6. Sistema de combate', '7. Tabla de Dano y Potenciamiento',
        '8. Colores y facciones', '9. Habilidades', '10. Espias',
        '11. El grimorio', '12. La reserva (mazo) y la mano',
        '13. Anatomia de una carta', '14. El dado', '15. Setup de la partida',
        '16. Glosario', '17. Issues pendientes de resolucion'
    ]
    pdf.set_font(pdf.F, '', 9)
    pdf.set_text_color(*TEXT)
    for item in toc_items:
        pdf.set_x(pdf.l_margin + 20)
        pdf.cell(0, 5.5, item, new_x="LMARGIN", new_y="NEXT")

    # Render elements
    for el in elements:
        kind = el[0]
        if kind == 'hr':
            pdf.hr()
        elif kind == 'h1':
            pdf.h1(el[1])
        elif kind == 'h2':
            pdf.h2(el[1])
        elif kind == 'h3':
            pdf.h3(el[1])
        elif kind == 'para':
            pdf.para(el[1])
        elif kind == 'bold':
            pdf.bold_para(el[1])
        elif kind == 'bullet':
            pdf.bullet(el[1])
        elif kind == 'quote':
            pdf.quote(el[1])
        elif kind == 'code':
            pdf.code_block(el[1])
        elif kind == 'table':
            pdf.table(el[1], el[2])

    # Save
    pdf.output(OUT)
    print(f"PDF generado: {OUT}")
    print(f"Paginas: {pdf.page_no()}")

if __name__ == '__main__':
    main()
