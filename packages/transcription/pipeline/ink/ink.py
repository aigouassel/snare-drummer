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

from pipeline.ink.fonts import font_table, outline

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
    'BMC', 'DP', 'MP', 'Do', 'sh', 'Tc', 'Tw', 'Tz', 'Ts', 'Tr', 'BX',
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


def orientation(page):
    """The matrix that puts a page's content the way up it is read.

    /Rotate is a viewing instruction: the content stream is written in one
    frame and the reader is told to turn the paper. Three percent of this
    catalogue is engraved landscape and rotated into portrait, and ignoring
    the instruction does not produce an error -- it produces a page whose
    staff lines are vertical, which layout.py then reports as having no
    staves at all. So the rotation is folded into the initial transform and
    everything downstream works in reading orientation.
    """
    turn = page.rotation % 360
    if turn == 0:
        return IDENTITY
    # page.rect is the rotated box, so the unrotated one is its transpose
    # for a quarter turn.
    w, h = (page.rect.height, page.rect.width) if turn in (90, 270) \
        else (page.rect.width, page.rect.height)
    if turn == 90:
        return (0.0, -1.0, 1.0, 0.0, 0.0, float(w))
    if turn == 180:
        return (-1.0, 0.0, 0.0, -1.0, float(w), float(h))
    return (0.0, 1.0, -1.0, 0.0, float(h), 0.0)


# What to advance by when the font does not say. Zero would be the obvious
# default and is the dangerous one: every glyph of a run then lands on the
# same x, and the run sorts into an anagram of itself -- "Blue Devils 2009"
# came out as "lBuedevis2l009". Half an em is wrong by a little for every
# glyph, which keeps a line in the order it was written, and it is only ever
# reached by the standard text faces a PDF is allowed to leave unembedded on
# the grounds that a reader knows their metrics already.
NOMINAL_ADVANCE = 500.0

# How finely a curve is broken into points when a shape is fingerprinted.
# Six matches what fonts.py uses for a glyph outline, which is what these
# shapes have to be comparable with.
CURVE_STEPS = 6


def _bezier(p0, c1, c2, p1):
    out = []
    for i in range(1, CURVE_STEPS + 1):
        t = i / CURVE_STEPS
        u = 1 - t
        out.append((u**3 * p0[0] + 3*u*u*t * c1[0] + 3*u*t*t * c2[0] + t**3 * p1[0],
                    u**3 * p0[1] + 3*u*u*t * c1[1] + 3*u*t*t * c2[1] + t**3 * p1[1]))
    return out


def replay(content, fonts, unhandled, base=IDENTITY):
    """Interpret one content stream: the glyphs it draws, and the ink it lays.

    Filled paths are kept apart from stroked ones. A beam is a filled
    quadrilateral and a staff line is a stroked segment; telling them apart
    here costs one flag and saves the reader above from guessing.
    """
    ctm, stack = base, []
    tm = tlm = IDENTITY
    font_ref, size, leading = None, 0.0, 0.0
    px = py = sx = sy = 0.0
    glyphs, segments, pending, operands = [], [], [], []
    # The path's outline, curves included. Kept apart from `pending`, which
    # holds straight segments only: layout, stems and beams all measure
    # straight lines, and flattening a slur into a hundred little segments
    # would drown them. Here the curve is the point -- some engravers draw
    # their music as paths rather than as characters, and the shape is the
    # only thing that identifies it. Kept one list per contour, which is what
    # fonts.outline walks.
    drawn, shapes = [[]], []

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
            ctm = stack.pop() if stack else base
        elif op == 'cm':
            ctm = mul(tuple(number(i) for i in range(-6, 0)), ctm)

        elif op == 'BT':
            tm = tlm = IDENTITY
        elif op == 'Tf':
            size = number(-1)
            name = operands[-2] if len(operands) >= 2 else None
            font_ref = name[1:] if isinstance(name, str) and name.startswith('/') else None
        elif op == 'TL':
            leading = number(-1)
        elif op in ('Td', 'TD'):
            if op == 'TD':
                leading = -number(-1)
            tlm = mul((1, 0, 0, 1, number(-2), number(-1)), tlm)
            tm = tlm
        elif op == 'Tm':
            tm = tlm = tuple(number(i) for i in range(-6, 0))
        elif op == 'T*':
            tlm = mul((1, 0, 0, 1, 0, -leading), tlm)
            tm = tlm
        elif op in ('Tj', 'TJ', "'", '"'):
            if op in ("'", '"'):
                # Quote shows text on the *next* line: it is T* followed by
                # Tj. Read as a plain Tj it leaves the second line sitting on
                # top of the first -- which is exactly how a stacked time
                # signature came out with its numerator and denominator at
                # one height, and how whole pieces came out metreless.
                tlm = mul((1, 0, 0, 1, 0, -leading), tlm)
                tm = tlm
            font = fonts.get(font_ref or '', {})
            advances = font.get('advances', {})
            # Walk the run the way a renderer does: place a glyph, then move
            # on by its advance. Recording the run's origin for all of them
            # puts a time signature's numerator and denominator at identical
            # coordinates, and nothing downstream can then say which is on
            # top -- whole pieces came out metreless for exactly that.
            for operand in operands:
                if not isinstance(operand, tuple):
                    # A number inside a TJ array shifts the next glyph back
                    # by that many thousandths of the text size.
                    try:
                        tm = mul((1, 0, 0, 1, -float(operand) / 1000 * size, 0), tm)
                    except (TypeError, ValueError):
                        pass
                    continue
                for code in _codes([operand], font.get('bytes', 1)):
                    matrix = mul(tm, ctm)
                    x, y = apply(matrix, 0, 0)
                    glyphs.append({
                        'font': font_ref,
                        'basefont': font.get('basefont'),
                        'family': font.get('family'),
                        'codes': [code],
                        'x': round(x, 3), 'y': round(y, 3),
                        'size': round(size * (matrix[3] or 1), 3),
                    })
                    tm = mul((1, 0, 0, 1,
                              advances.get(code, NOMINAL_ADVANCE)
                              / 1000 * size, 0), tm)

        elif op == 'm':
            px, py = sx, sy = number(-2), number(-1)
            drawn.append([(px, py)])
        elif op == 'l':
            x, y = number(-2), number(-1)
            pending.append((px, py, x, y))
            px, py = x, y
            drawn[-1].append((px, py))
        elif op == 'h':
            pending.append((px, py, sx, sy))
            px, py = sx, sy
            drawn[-1].append((px, py))
        elif op == 're':
            x, y, w, h = number(-4), number(-3), number(-2), number(-1)
            pending += [(x, y, x + w, y), (x + w, y, x + w, y + h),
                        (x + w, y + h, x, y + h), (x, y + h, x, y)]
            drawn.append([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)])
            px, py = sx, sy = x, y
        elif op in ('c', 'v', 'y'):
            end = (number(-2), number(-1))
            if op == 'c':
                first, second = (number(-6), number(-5)), (number(-4), number(-3))
            elif op == 'v':
                first, second = (px, py), (number(-4), number(-3))
            else:
                first, second = (number(-4), number(-3)), end
            drawn[-1] += _bezier((px, py), first, second, end)
            px, py = end
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
            shape = outline([[apply(ctm, x, y) for x, y in contour]
                             for contour in drawn])
            if shape:
                shapes.append(shape)
            pending, drawn = [], [[]]
        elif op == 'n':
            pending, drawn = [], [[]]
        elif op not in IGNORED:
            unhandled[op] += 1

        operands = []

    return glyphs, segments, shapes


def read(path):
    """Every page of a score, in reading order, with what was drawn on each."""
    doc = pymupdf.open(path)
    unhandled = defaultdict(int)
    cache = {}
    pages = []
    for number, page in enumerate(doc, start=1):
        fonts = font_table(doc, page, cache)
        glyphs, segments, shapes = replay(page.read_contents(), fonts,
                                          unhandled, base=orientation(page))
        pages.append({
            'page': number,
            'glyphs': glyphs,
            'segments': segments,
            # Every painted path, fingerprinted. Only wanted where a page
            # draws its music instead of setting it, which is why nothing
            # downstream looks at these unless the page carries no music font.
            'shapes': shapes,
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
