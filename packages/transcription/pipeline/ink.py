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

qpdf does the decompression, and PyMuPDF reads the fonts (see fonts.py); the
content stream itself is interpreted here, because what is needed from it --
the raw glyph code, before any Unicode mapping -- is precisely what the
higher-level readers throw away.
"""
import os
import re
import subprocess
from collections import defaultdict

from fonts import family_of, font_table

OBJ = re.compile(rb'(\d+) 0 obj\s*(.*?)\bendobj', re.S)
STREAM = re.compile(rb'stream\r?\n(.*?)\r?\nendstream', re.S)

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


def expand(path):
    """qpdf's QDF mode: object streams disabled, stream contents decoded."""
    out = path + '.qdf'
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(path):
        result = subprocess.run(
            ['qpdf', '--qdf', '--object-streams=disable', '--decode-level=all',
             path, out], capture_output=True)
        if not os.path.exists(out):
            raise RuntimeError(f'qpdf failed on {path}: {result.stderr.decode()[:200]}')
    return open(out, 'rb').read()


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


def read(path):
    """Everything drawn on the page: glyphs with codes, and stroked segments."""
    raw = expand(path)
    fonts = font_table(path)

    streams = STREAM.findall(raw)
    if not streams:
        return {'glyphs': [], 'segments': [], 'fonts': fonts, 'unhandled': {}}
    content = max(streams, key=len)

    ctm, stack = IDENTITY, []
    tm = tlm = IDENTITY
    font_ref, size = None, 0.0
    px = py = sx = sy = 0.0
    glyphs, segments, pending, operands = [], [], [], []
    unhandled = defaultdict(int)

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
            # Beams, slurs and hairpins are curves. Only the endpoint matters
            # for the current point; the shape is not read here.
            px, py = number(-2), number(-1)
        elif op in ('S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'):
            closing = op in ('s', 'b', 'b*')
            if closing:
                pending.append((px, py, sx, sy))
            for x0, y0, x1, y1 in pending:
                a = apply(ctm, x0, y0)
                b = apply(ctm, x1, y1)
                segments.append({'x0': round(a[0], 3), 'y0': round(a[1], 3),
                                 'x1': round(b[0], 3), 'y1': round(b[1], 3),
                                 'fill': op.lower().startswith(('f', 'b'))})
            pending = []
        elif op == 'n':
            pending = []
        elif op not in IGNORED:
            unhandled[op] += 1

        operands = []

    return {'glyphs': glyphs, 'segments': segments, 'fonts': fonts,
            'unhandled': dict(unhandled)}


def musical(glyphs):
    """Only the glyphs drawn in an engraving font."""
    return [g for g in glyphs if g['family']]


if __name__ == '__main__':
    import sys, json
    data = read(sys.argv[1])
    if len(sys.argv) > 2:
        json.dump(data, open(sys.argv[2], 'w'), indent=1)
    notes = musical(data['glyphs'])
    print(f"{len(data['glyphs'])} glyphes ({len(notes)} musicaux), "
          f"{len(data['segments'])} segments")
    print(f"familles: {sorted({g['family'] for g in notes})}")
    print(f"operateurs non geres: {data['unhandled'] or 'aucun'}")
