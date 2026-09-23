#!/usr/bin/env python3
"""
Replay a page's drawing instructions and write down what was drawn.

This is not optical music recognition. A PDF produced by Sibelius, Finale,
MuseScore or Dorico states exactly what it put on the page and where: a
notehead is a glyph code at a coordinate, a staff line is a stroked segment
between two points. So there is nothing to infer from pixels -- the job is to
interpret the content stream faithfully and hand on the result.

Faithfully is the operative word. Everything downstream trusts that what comes
out of here is everything that went in, so an operator this interpreter does
not understand is *counted*, never skipped quietly. A parser that drops what it
cannot read does not fail; it produces a plausible page with things missing,
which is the one failure mode this project cannot detect later.

That is also why this reads **every page**. An earlier version took the
longest stream in the file and called it the content, which is true of a
one-page score and silently wrong for the rest -- and 38% of this catalogue
runs to two pages or more. Nothing downstream could have noticed: a score
whose second page was never read looks exactly like a score that is half as
long.

PyMuPDF supplies each page's decoded content stream and its fonts (see
fonts.py); the stream itself is interpreted here, because what is needed from
it -- the raw glyph code, before any Unicode mapping -- is precisely what the
higher-level readers throw away.
"""
import re
from collections import defaultdict

import pymupdf

from fonts import font_table

TOKEN = re.compile(rb"""
      (?P<hex><[0-9A-Fa-f\s]*>)
    | (?P<lit>\((?:[^()\\]|\\.)*\))
    | (?P<open>\[)
    | (?P<shut>\])
    | (?P<num>[-+]?[\d.]+)
    | (?P<name>/[^\s/\[\]<>(){}]+)
    | (?P<op>[A-Za-z'"*]+)
""", re.X)

# Operators that legitimately change nothing this pipeline reads: colour,
# line width, clipping, marked content. Listed explicitly so that anything
# genuinely unrecognised still shows up in the report.
IGNORED = {
    'ET', 'gs', 'g', 'G', 'rg', 'RG', 'k', 'K', 'w', 'J', 'j', 'M', 'd', 'i',
    'ri', 'cs', 'CS', 'sc', 'scn', 'SC', 'SCN', 'W', 'W*', 'BDC', 'EMC',
    'BMC', 'DP', 'MP', 'Do', 'sh', 'TL', 'Tc', 'Tw', 'Tz', 'Ts', 'Tr', 'BX',
    'EX', 'd0', 'd1',
}

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D,
            c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _codes(strings, width):
    """Raw glyph codes out of the strings a text operator was given."""
    out = []
    for kind, raw in strings:
        if kind == 'hex':
            digits = re.sub(rb'\s', b'', raw[1:-1]).decode()
            if len(digits) % 2:
                digits += '0'          # PDF pads a trailing nibble with zero
            data = bytes.fromhex(digits)
        else:
            data = re.sub(rb'\\(\d{1,3})',
                          lambda m: bytes([int(m.group(1), 8) & 0xFF]), raw[1:-1])
            data = re.sub(rb'\\(.)', rb'\1', data)
        if width == 2:
            out += ['%04x' % int.from_bytes(data[i:i + 2], 'big')
                    for i in range(0, len(data) - 1, 2)]
        else:
            out += ['%04x' % b for b in data]
    return out


def replay(content, fonts, unhandled):
    """Interpret one content stream: the glyphs it draws, and the ink it lays.

    Filled paths are kept apart from stroked ones. A beam is a filled
    quadrilateral and a staff line is a stroked segment; telling them apart
    here costs one flag and saves the reader above from guessing.
    """
    ctm, stack = IDENTITY, []
    tm = tlm = IDENTITY
    font_ref, size = None, 0.0
    px = py = sx = sy = 0.0
    glyphs, segments, pending, operands = [], [], [], []

    def number(i):
        try:
            return float(operands[i])
        except (IndexError, ValueError, TypeError):
            return 0.0

    for match in TOKEN.finditer(content):
        kind = match.lastgroup
        token = match.group()

        if kind == 'num':
            operands.append(token)
            continue
        if kind in ('name', 'open', 'shut'):
            operands.append(token.decode('latin-1'))
            continue
        if kind in ('hex', 'lit'):
            operands.append(('hex' if kind == 'hex' else 'lit', token))
            continue

        op = token.decode('latin-1')

        if op == 'q':
            stack.append(ctm)
        elif op == 'Q':
            ctm = stack.pop() if stack else IDENTITY
        elif op == 'cm':
            ctm = mul(tuple(number(i) for i in range(-6, 0)), ctm)

        elif op == 'BT':
            tm = tlm = IDENTITY
        elif op == 'Tf':
            size = number(-1)
            name = operands[-2] if len(operands) >= 2 else None
            font_ref = name[1:] if isinstance(name, str) and name.startswith('/') else None
        elif op in ('Td', 'TD'):
            tlm = mul((1, 0, 0, 1, number(-2), number(-1)), tlm)
            tm = tlm
        elif op == 'Tm':
            tm = tlm = tuple(number(i) for i in range(-6, 0))
        elif op == 'T*':
            tlm = mul((1, 0, 0, 1, 0, -size), tlm)
            tm = tlm
        elif op in ('Tj', 'TJ', "'", '"'):
            font = fonts.get(font_ref or '', {})
            codes = _codes([o for o in operands if isinstance(o, tuple)],
                           font.get('bytes', 1))
            if codes:
                matrix = mul(tm, ctm)
                x, y = apply(matrix, 0, 0)
                glyphs.append({
                    'font': font_ref,
                    'basefont': font.get('basefont'),
                    'family': font.get('family'),
                    'codes': codes,
                    'x': round(x, 3), 'y': round(y, 3),
                    'size': round(size * (matrix[3] or 1), 3),
                })

        elif op == 'm':
            px, py = sx, sy = number(-2), number(-1)
        elif op == 'l':
            x, y = number(-2), number(-1)
            pending.append((px, py, x, y))
            px, py = x, y
        elif op == 'h':
            pending.append((px, py, sx, sy))
            px, py = sx, sy
        elif op == 're':
            x, y, w, h = number(-4), number(-3), number(-2), number(-1)
            pending += [(x, y, x + w, y), (x + w, y, x + w, y + h),
                        (x + w, y + h, x, y + h), (x, y + h, x, y)]
            px, py = sx, sy = x, y
        elif op in ('c', 'v', 'y'):
            # Slurs and hairpins are curves. Only the endpoint matters for the
            # current point; the shape itself is not read here.
            px, py = number(-2), number(-1)
        elif op in ('S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'):
            closing = op in ('s', 'b', 'b*')
            if closing:
                pending.append((px, py, sx, sy))
            filled = op.lower().startswith(('f', 'b'))
            for x0, y0, x1, y1 in pending:
                a = apply(ctm, x0, y0)
                b = apply(ctm, x1, y1)
                segments.append({'x0': round(a[0], 3), 'y0': round(a[1], 3),
                                 'x1': round(b[0], 3), 'y1': round(b[1], 3),
                                 'fill': filled})
            pending = []
        elif op == 'n':
            pending = []
        elif op not in IGNORED:
            unhandled[op] += 1

        operands = []

    return glyphs, segments


def read(path):
    """Every page of a score, in reading order, with what was drawn on each."""
    doc = pymupdf.open(path)
    unhandled = defaultdict(int)
    cache = {}
    pages = []
    for number, page in enumerate(doc, start=1):
        fonts = font_table(doc, page, cache)
        glyphs, segments = replay(page.read_contents(), fonts, unhandled)
        pages.append({
            'page': number,
            'glyphs': glyphs,
            'segments': segments,
            'fonts': fonts,
        })
    doc.close()
    return {'pages': pages, 'unhandled': dict(unhandled)}


def musical(glyphs):
    """Only the glyphs drawn in an engraving font."""
    return [g for g in glyphs if g['family']]


if __name__ == '__main__':
    import sys, json
    data = read(sys.argv[1])
    if len(sys.argv) > 2:
        json.dump(data, open(sys.argv[2], 'w'), indent=1)
    for page in data['pages']:
        notes = musical(page['glyphs'])
        print(f"page {page['page']}: {len(page['glyphs'])} glyphes "
              f"({len(notes)} musicaux), {len(page['segments'])} segments, "
              f"familles {sorted({g['family'] for g in notes}) or 'aucune'}")
    print(f"operateurs non geres: {data['unhandled'] or 'aucun'}")
