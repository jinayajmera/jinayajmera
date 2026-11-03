"""
Turn a NAME into a clean, monochrome ASCII-art SVG that "types" itself in like a
terminal and then holds -- a drop-in replacement for the photo-based ASCII
portrait (no photo needed).

Pipeline (same idea as a photo portrait, just with text as the source image):
  1. draw the name in a heavy font on a square white canvas
  2. shade the letters with a soft vertical gradient and darken their outlines,
     so the character ramp (@ % # * + = - :) shows depth instead of one flat fill
  3. sample the canvas into a COLS x ROWS grid and map luminance -> characters
  4. emit an SVG: one <text> per row, revealed with a left-to-right clip wipe
     and a block cursor, rows staggered top -> bottom (GitHub runs SMIL inside
     <img> SVGs, never JS)

    python scripts/make_name_ascii_svg.py                       # defaults below
    python scripts/make_name_ascii_svg.py "Jinay Ajmera" out.svg
    STATIC=1 python scripts/make_name_ascii_svg.py              # frozen preview
"""
import html
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = sys.argv[1] if len(sys.argv) > 1 else "Jinay Ajmera"
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "name-ascii.svg")

HANDLE = "jinay"                                   # prompt: jinay@github:~$
FONT = os.environ.get(
    "NAME_FONT", "/usr/share/fonts/opentype/inter/Inter-Black.otf"
)

# ---- ascii grid (kept identical to the 840x880 canvas the stats card uses) --
COLS = int(os.environ.get("COLS", 180))
ART_W_TARGET = 800
CELL_W = ART_W_TARGET / COLS
CELL_H = CELL_W * 15 / 8
ROWS = round(COLS * 8 / 15)                 # 96 -> a SQUARE source maps 1:1
RAMP = " .`:-=+*cs#%@"                      # sparse(bright) -> dense(dark)
GAMMA = 1.18
WHITE_FLOOR = 0.80                          # luminance above this -> blank

PAD, TITLEBAR_H, STATUS_H = 20, 30, 30
ART_W, ART_H = COLS * CELL_W, ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG, BG2, FRAME = "#0d1117", "#111722", "#30363d"
TITLE_TEXT, INK, CURSOR = "#7d8590", "#c9d1d9", "#c9d1d9"

ROW_DUR = 5.8 / ROWS                        # whole name prints in ~6s
STAGGER = ROW_DUR
STATIC = bool(os.environ.get("STATIC"))


# ---- 1. draw the name ------------------------------------------------------
S = 1440                                    # square source canvas
SS = 2                                      # supersample for smooth edges


def fit_font(text, max_w, start):
    size = start
    while size > 20:
        f = ImageFont.truetype(FONT, size)
        l, t, r, b = f.getbbox(text)
        if r - l <= max_w:
            return f
        size -= 6
    return ImageFont.truetype(FONT, 20)


VSTRETCH = float(os.environ.get("VSTRETCH", 1.8))   # tall glyphs: ascii cells are tall too
WIDTH_FRAC = 0.92                                    # widest word spans this much of the canvas

first, _, last = NAME.partition(" ")
words = [first.upper()] + ([last.upper()] if last else [])
W = S * SS
big = [fit_font(w, W * WIDTH_FRAC, 600 * SS) for w in words]
size = min(f.size for f in big)                      # same size -> one lockup
big = [ImageFont.truetype(FONT, size) for _ in words]


def word_mask(text, font, vs):
    """one word as a white-on-black mask, stretched vertically by vs"""
    l, t, r, b = font.getbbox(text)
    m = Image.new("L", (r - l, b - t), 0)
    ImageDraw.Draw(m).text((-l, -t), text, font=font, fill=255)
    return m.resize((r - l, int((b - t) * vs)), Image.LANCZOS)


raw_h = [f.getbbox(w)[3] - f.getbbox(w)[1] for w, f in zip(words, big)]
gap = int(size * 0.24)
rule_pad = int(size * 0.30)
rule_h = 14 * SS
# shrink the stretch if the lockup (+ rules) would not fit the square canvas
vs = min(VSTRETCH, (W * 0.84 - gap * (len(words) - 1) - 2 * (rule_pad + rule_h)) / sum(raw_h))
wm = [word_mask(w, f, vs) for w, f in zip(words, big)]
total = sum(m.height for m in wm) + gap * (len(words) - 1)
y = (W - total) / 2
mask = Image.new("L", (W, W), 0)
top_of_block = y
for m in wm:
    mask.paste(m, ((W - m.width) // 2, int(y)))
    y += m.height + gap
bottom_of_block = y - gap

# thin rules above / below the lockup (they become rows of '%' / '=' characters)
rule = ImageDraw.Draw(mask)
rx0, rx1 = int(W * 0.05), int(W * 0.95)
ry0 = int(top_of_block - rule_pad - rule_h)
rule.rectangle([rx0, ry0, rx1, ry0 + rule_h], fill=255)
ry1 = int(bottom_of_block + rule_pad)
rule.rectangle([rx0, ry1, rx1, ry1 + rule_h], fill=255)
mask = mask.resize((S, S), Image.LANCZOS)

# ---- 2. shade: gradient fill + dark outline --------------------------------
inner = mask.filter(ImageFilter.MinFilter(9))            # eroded -> interior
edge = ImageChops.subtract(mask, inner)                  # thin outline band
grad = Image.linear_gradient("L").resize((S, S))         # 0 (top) -> 255 (bottom)
# interior luminance: 0.12 at the top of the canvas -> 0.55 at the bottom
fill = grad.point(lambda v: int(255 * (0.12 + 0.43 * v / 255)))
canvas = Image.new("L", (S, S), 255)
canvas.paste(fill, mask=inner)
canvas.paste(0, mask=edge.point(lambda v: 255 if v > 80 else 0))

# ---- 3. sample into the char grid ------------------------------------------
px = canvas.resize((COLS, ROWS), Image.LANCZOS).load()
rows_txt = []
for ry in range(ROWS):
    chars = []
    for cx in range(COLS):
        lum = pow(px[cx, ry] / 255.0, GAMMA)
        if lum >= WHITE_FLOOR:
            chars.append(" ")
            continue
        idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
        chars.append(RAMP[max(0, min(len(RAMP) - 1, idx))])
    rows_txt.append("".join(chars))

# ---- 4. assemble the SVG ---------------------------------------------------
art_top = TITLEBAR_H + PAD * 0.35
p = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">',
    '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
    '</linearGradient></defs>',
    f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
    f'fill="none" stroke="{FRAME}" stroke-width="1"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
]
for i, col in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    p.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{col}"/>')
p.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
         f'text-anchor="middle">{HANDLE}@github: ~$ ./name.sh</text>')

font_size = CELL_H * 0.86
for ry, line in enumerate(rows_txt):
    ty = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    text = (f'<text xml:space="preserve" x="{PAD}" y="{ty:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">'
            f'{html.escape(line)}</text>')
    if STATIC or not line.strip():
        if line.strip():
            p.append(text)
        continue
    p.append(
        f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>')
    p.append(f'<g clip-path="url(#r{ry})">{text}</g>')
    p.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>')

status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19
prompt = f"{HANDLE}@github:~$ whoami "
p.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
p.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
         f'{prompt}<tspan fill="{INK}">{html.escape(NAME)}</tspan></text>')
cursor_x = PAD + (len(prompt) + len(NAME) + 1) * 13 * 0.6
p.append(f'<rect x="{cursor_x:.1f}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
         f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
         f'dur="1s" repeatCount="indefinite"/></rect>')
p.append("</svg>")

svg = "".join(p)
with open(OUT, "w") as f:
    f.write(svg)
print("wrote", OUT, len(svg), "bytes;", int(CANVAS_W), "x", int(CANVAS_H))
if os.environ.get("PRINT_TXT"):
    print("\n".join(rows_txt))
