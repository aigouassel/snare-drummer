#!/usr/bin/env python3
"""
Identify the symbols a score uses, by their shape.

The obvious approach does not work, and the reason shapes everything else in
this pipeline. A PDF writes a code for each glyph it draws -- but engraving
fonts are embedded as *subsets*, and the subsetter renumbers the glyphs per
file. The same Opus notehead is code 0004 in one score and 0011 in the next.
Worse, the subsetter usually strips the glyph names too, leaving "glyph00004",
so neither the PDF nor the font says what the symbol means.

What survives is the outline, because that is what gets drawn. Two scores that
embed the same original font carry the same shape for the same symbol, so a
normalised fingerprint of the outline is a stable identity across the whole
catalogue. That turns labelling from "884 scores" into "one label per distinct
symbol per family", resolved everywhere afterwards.

One trap: the same symbol arrives as TrueType (quadratic curves) in one file
and bare CFF (cubic) in another. The two describe one shape with different
control points, so any hash over control points calls them different. The
fingerprint is therefore taken over the *shape*: flatten the curves to points,
drop them into a normalised grid, and compare grids. Measured across two
unrelated Opus scores, matching symbols agree to within a few bits out of 256,
and their aspect ratios -- computed independently -- agree to two decimals.
"""
import logging
from io import BytesIO

import pymupdf
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

logging.getLogger('fontTools').setLevel(logging.ERROR)

GRID = 16    # fingerprint resolution: a 16x16 occupancy grid, 256 bits
STEPS = 12   # samples per curve segment when flattening

MUSIC_FAMILIES = ('Bravura', 'Maestro', 'Opus', 'MScore', 'Engraver',
                  'Petaluma', 'Sonata', 'November', 'Emmentaler')


def family_of(basefont):
    """The engraving family a font belongs to, or None for a text font.

    The subset prefix ("ABCDEF+Opus") is an artefact of embedding, not part of
    the identity, so it is dropped before matching.
    """
    bare = (basefont or '').split('+')[-1]
    for fam in MUSIC_FAMILIES:
        if bare.startswith(fam):
            return fam
    return None


def _flatten(commands):
    """Pen commands -> points lying on the outline."""
    pts, cur, start = [], (0.0, 0.0), (0.0, 0.0)

    def bezier(p0, ctrl, p1):
        for i in range(1, STEPS + 1):
            t = i / STEPS
            u = 1 - t
            if len(ctrl) == 1:
                c = ctrl[0]
                pts.append((u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
                            u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]))
            else:
                c1, c2 = ctrl
                pts.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
                            u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1]))

    for op, args in commands:
        if op == 'moveTo':
            cur = start = args[0]
            pts.append(cur)
        elif op == 'lineTo':
            cur = args[0]
            pts.append(cur)
        elif op == 'qCurveTo':
            # TrueType writes runs of off-curve points with the on-curve point
            # between two of them implied. Making that implicit point explicit
            # is what lets quadratic and cubic outlines be compared at all.
            prev, ctrl = cur, list(args)
            end = ctrl.pop() if ctrl and ctrl[-1] is not None else None
            for i, c in enumerate(ctrl):
                last = i == len(ctrl) - 1
                nxt = end if (last and end) else (
                    (c[0] + ctrl[i + 1][0]) / 2, (c[1] + ctrl[i + 1][1]) / 2)
                bezier(prev, [c], nxt)
                prev = nxt
            cur = prev
        elif op == 'curveTo':
            *ctrl, end = args
            bezier(cur, ctrl, end)
            cur = end
        elif op == 'closePath':
            pts.append(start)
            cur = start
    return pts


def fingerprint(glyphset, name):
    pen = RecordingPen()
    try:
        glyphset[name].draw(pen)
    except Exception:
        return None
    pts = _flatten(pen.value)
    if len(pts) < 3:
        return None

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if w <= 0 and h <= 0:
        return None

    # Normalise into the unit square by the larger side, so aspect is
    # preserved: a notehead and a whole-bar rest fill the same grid once
    # stretched independently, and must not be allowed to.
    scale = max(w, h) or 1
    ox, oy = min(xs), min(ys)
    bits = 0
    for x, y in pts:
        gx = min(GRID - 1, int((x - ox) / scale * GRID))
        gy = min(GRID - 1, int((y - oy) / scale * GRID))
        bits |= 1 << (gy * GRID + gx)

    return {
        'bits': '%064x' % bits,
        'aspect': round(w / h, 2) if h else 0.0,
        'width': round(w, 1),
        'height': round(h, 1),
    }


def _glyphset(buf):
    """(glyph set, glyph order) from an embedded font program, either flavour."""
    try:
        tt = TTFont(BytesIO(buf), fontNumber=0, lazy=True)
        return tt.getGlyphSet(), tt.getGlyphOrder()
    except Exception:
        pass
    cff = CFFFontSet()
    cff.decompile(BytesIO(buf), None)
    font = cff[cff.fontNames[0]]
    charstrings = font.CharStrings
    order = font.getGlyphOrder()

    class _Glyph:
        def __init__(self, cs):
            self._cs = cs

        def draw(self, pen):
            self._cs.draw(pen)

    return {n: _Glyph(charstrings[n]) for n in order}, order


def font_table(path):
    """Per font resource: its family, its code width, and a fingerprint per code.

    The code width matters as much as the fingerprints. A Type0 font in
    Identity-H encoding is addressed with *two* bytes per glyph, and reading
    such a string one byte at a time yields halves of codes -- which produces
    no error at all, just a plausible and entirely wrong set of symbols. That
    mistake cost three rounds of analysis before it was caught, which is why
    the width is carried here rather than assumed downstream.
    """
    doc = pymupdf.open(path)
    table = {}
    for page in doc:
        for entry in page.get_fonts(full=True):
            xref, _ext, _type, basefont, refname, encoding = entry[:6]
            if refname in table:
                continue
            _name, fmt, _ftype, buf = doc.extract_font(xref)
            record = {
                'basefont': basefont,
                'family': family_of(basefont),
                'format': fmt,
                'bytes': 2 if (encoding or '').startswith('Identity') else 1,
                'codes': {},
            }
            if buf:
                try:
                    glyphs, order = _glyphset(buf)
                    for gid, gname in enumerate(order):
                        fp = fingerprint(glyphs, gname)
                        if fp:
                            record['codes']['%04x' % gid] = fp
                except Exception as exc:
                    record['error'] = str(exc)[:80]
            table[refname] = record
    doc.close()
    return table


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count('1')
