"""Build the Confluence exploration without changing the integration's brand.

Run: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 assets/brand-exploration/generate.py
Requires CairoSVG and Pillow. Typography: system DIN Alternate / Arial.
"""

from pathlib import Path
import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT_DIR = Path('/System/Library/Fonts/Supplemental')
PALETTES = {
    'light': dict(ink='#123D3A', muted='#53716B', line='#147D73', node='#147D73', output='#123D3A', dot='#BDFB7A'),
    'dark': dict(ink='#F0F8F1', muted='#ACBEB6', line='#83D8BD', node='#83D8BD', output='#BDFB7A', dot='#123D3A'),
}


def mark(p):
    return f'''<g fill="none" stroke="{p['line']}" stroke-width="28" stroke-linecap="round" stroke-linejoin="round">
      <path d="M88 104H148C212 104 190 256 276 256H332"/>
      <path d="M88 408H148C212 408 190 256 276 256"/>
      <path d="M88 256H332"/>
    </g>
    <g fill="{p['node']}"><circle cx="72" cy="104" r="36"/><circle cx="72" cy="256" r="36"/><circle cx="72" cy="408" r="36"/></g>
    <rect x="284" y="198" width="200" height="116" rx="58" fill="{p['output']}"/>
    <circle cx="424" cy="256" r="36" fill="{p['dot']}"/>'''


def svg(content, width=512, height=512):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><title>Input Boolean Group — Confluence</title>{content}</svg>'


def export():
    for mode, p in PALETTES.items():
        prefix = 'dark_' if mode == 'dark' else ''
        for kind in ['icon', 'logo']:
            width, height = (512, 512) if kind == 'icon' else (512, 128)
            content = mark(p)
            if kind == 'logo':
                content = f'''<g transform="translate(0 4) scale(.235)">{content}</g>
                <g font-family="DIN Alternate, Arial, sans-serif">
                  <text x="144" y="64" font-size="56" font-weight="700" fill="{p['ink']}">Input Boolean</text>
                  <text x="145" y="105" font-size="25" font-weight="700" letter-spacing="4" fill="{p['muted']}">GROUP</text>
                </g>'''
            source = ROOT / f'{prefix}{kind}.svg'
            source.write_text(svg(content, width, height))
            base = (256, 256) if kind == 'icon' else (512, 128)
            for scale in [1, 2]:
                suffix = '@2x' if scale == 2 else ''
                cairosvg.svg2png(url=str(source), write_to=str(ROOT / f'{prefix}{kind}{suffix}.png'), output_width=base[0]*scale, output_height=base[1]*scale)


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR / ('DIN Alternate Bold.ttf' if bold else 'Arial.ttf')), size)


def draw_text(draw, xy, text, size, color, bold=False):
    draw.text(xy, text, font=font(size, bold), fill=color, spacing=0)


def paste(canvas, filename, xy, size):
    im = Image.open(filename).convert('RGBA').resize(size, Image.Resampling.LANCZOS)
    canvas.paste(im, xy, im)


def board():
    canvas = Image.new('RGB', (1600, 1180), '#F4F5EE')
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, 1600, 650), fill='#123D3A')
    draw_text(d, (64, 44), 'INPUT BOOLEAN GROUP / BRAND EXPLORATION 01', 19, '#ACBEB6', True)
    draw_text(d, (64, 105), 'Confluence', 98, '#BDFB7A', True)
    draw_text(d, (68, 234), 'Many inputs.\nOne clear state.', 71, '#F0F8F1', True)
    draw_text(d, (70, 444), 'Tre segnali si incontrano in un unico interruttore.', 25, '#ACBEB6')
    paste(canvas, ROOT / 'dark_logo@2x.png', (68, 521), (448, 112))
    paste(canvas, ROOT / 'dark_icon@2x.png', (982, 126), (430, 430))
    d.line((64, 690, 1536, 690), fill='#CED8CC', width=1)
    for x, label in [(64, '01 / CHIARO'), (446, '02 / SCURO'), (838, '03 / PICCOLE DIMENSIONI'), (1200, '04 / EVOLUZIONE')]:
        draw_text(d, (x, 716), label, 18, '#53716B', True)
    paste(canvas, ROOT / 'icon@2x.png', (109, 771), (212, 212))
    d.rounded_rectangle((446, 763, 756, 1008), radius=24, fill='#123D3A')
    paste(canvas, ROOT / 'dark_icon@2x.png', (496, 779), (212, 212))
    paste(canvas, ROOT / 'icon@2x.png', (843, 787), (64, 64))
    paste(canvas, ROOT / 'icon@2x.png', (949, 803), (32, 32))
    draw_text(d, (843, 870), '64 px', 17, '#53716B')
    draw_text(d, (942, 870), '32 px', 17, '#53716B')
    d.rounded_rectangle((827, 916, 1111, 1008), radius=18, fill='#123D3A')
    paste(canvas, ROOT / 'dark_icon@2x.png', (843, 930), (64, 64))
    paste(canvas, ROOT / 'dark_icon@2x.png', (949, 946), (32, 32))
    current = ROOT.parents[1] / 'custom_components/input_boolean_group/brand/icon@2x.png'
    paste(canvas, current, (1201, 807), (104, 104))
    paste(canvas, ROOT / 'icon@2x.png', (1401, 807), (104, 104))
    draw_text(d, (1331, 835), '→', 32, '#53716B')
    draw_text(d, (1200, 944), 'Attuale', 19, '#53716B')
    draw_text(d, (1400, 944), 'Confluence', 19, '#53716B')
    d.line((64, 1050, 1536, 1050), fill='#CED8CC', width=1)
    draw_text(d, (64, 1082), 'PETROLIO / MENTA / LIME', 18, '#53716B', True)
    for x, color in [(64, '#123D3A'), (105, '#147D73'), (146, '#83D8BD'), (187, '#BDFB7A')]:
        d.ellipse((x, 1122, x+27, 1149), fill=color)
    draw_text(d, (410, 1082), 'Un segno semplice, organico e riconoscibile.', 26, '#123D3A', True)
    draw_text(d, (410, 1125), 'SVG modificabili · PNG trasparenti · varianti light / dark · 1x / 2x', 21, '#53716B')
    canvas.save(ROOT / 'presentation.png', optimize=True)


if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    export()
    board()
