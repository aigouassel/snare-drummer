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
from fontTools.agl import UV2AGL
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

logging.getLogger('fontTools').setLevel(logging.ERROR)

GRID = 16    # fingerprint resolution: a 16x16 occupancy grid, 256 bits
STEPS = 12   # samples per curve segment when flattening

MUSIC_FAMILIES = ('Bravura', 'Maestro', 'Opus', 'MScore', 'Engraver',
                  'Gootville', 'Reprise', 'Petaluma', 'Sonata', 'November',
                  'Emmentaler')


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


# The three base encodings a PDF names for a simple font. Each is a
# byte-oriented character set, so the glyph a code addresses is found by
# decoding the byte and asking the Adobe glyph list what that character is
# called.
BASE_ENCODINGS = {
    'WinAnsiEncoding': 'cp1252',
    'MacRomanEncoding': 'mac_roman',
    'StandardEncoding': 'latin-1',
    'PDFDocEncoding': 'latin-1',
}


def base_encoding(name):
    """A named base encoding as code -> glyph name."""
    codec = BASE_ENCODINGS.get(name)
    if not codec:
        return {}
    out = {}
    for code in range(32, 256):
        try:
            char = bytes([code]).decode(codec)
        except UnicodeDecodeError:
            continue
        glyph = UV2AGL.get(ord(char))
        if glyph:
            out[code] = glyph
    return out


def _builtin(tt):
    """The font program's own code -> glyph name map, if it carries one.

    An engraving font is *symbolic*: its characters are noteheads, not
    letters, so it is published with a (3,0) symbol cmap whose codes live in
    the private-use block at 0xF000. The low byte of such a code is the
    character the content stream writes.
    """
    try:
        cmap = tt['cmap']
    except Exception:
        return {}
    symbol = cmap.getcmap(3, 0)
    if symbol:
        return {code & 0xFF: name for code, name in symbol.cmap.items()}
    for platform, encoding in ((1, 0), (3, 1), (0, 3)):
        table = cmap.getcmap(platform, encoding)
        if table:
            return {code: name for code, name in table.cmap.items() if code < 256}
    return {}


def units_per_em(buf):
    """The font's design grid, which a glyph's dimensions are expressed in.

    It is 1000 for a PostScript outline and usually 2048 for a TrueType one,
    and assuming either turns every measured size into a number that is
    plausible and wrong by a factor of two.
    """
    try:
        return TTFont(BytesIO(buf), fontNumber=0, lazy=True)['head'].unitsPerEm
    except Exception:
        pass
    try:
        cff = CFFFontSet()
        cff.decompile(BytesIO(buf), None)
        matrix = cff[cff.fontNames[0]].FontMatrix
        return round(1 / matrix[0]) if matrix and matrix[0] else 1000
    except Exception:
        return 1000


def _glyphset(buf):
    """(glyph set, glyph order, code -> name) from an embedded font program."""
    try:
        tt = TTFont(BytesIO(buf), fontNumber=0, lazy=True)
        order, builtin = tt.getGlyphOrder(), _builtin(tt)
        try:
            return tt.getGlyphSet(), order, builtin
        except Exception:
            # Subsetters sometimes truncate the advance-width table, which
            # fontTools refuses to build a glyph set from. The outlines are
            # intact and they are all this pipeline reads, so they are taken
            # from the glyph table directly rather than losing the font.
            glyf = tt['glyf']

            class _Outline:
                def __init__(self, name):
                    self._name = name

                def draw(self, pen):
                    glyf[self._name].draw(pen, glyf)

            return {n: _Outline(n) for n in order}, order, builtin
    except Exception:
        pass
    cff = CFFFontSet()
    cff.decompile(BytesIO(buf), None)
    font = cff[cff.fontNames[0]]
    charstrings = font.CharStrings
    order = font.getGlyphOrder()

    encoding = getattr(font, 'Encoding', None)
    builtin = {}
    if isinstance(encoding, list):
        builtin = {code: name for code, name in enumerate(encoding)
                   if name and name != '.notdef'}

    class _Glyph:
        def __init__(self, cs):
            self._cs = cs

        def draw(self, pen):
            self._cs.draw(pen)

    return {n: _Glyph(charstrings[n]) for n in order}, order, builtin


def _encoding(doc, xref):
    """What the PDF says about a simple font's character codes.

    Returns the named base encoding, if any, and the /Differences array that
    overrides it. A producer that subsets a font commonly renumbers its
    characters and says so here rather than in the font program, so the
    differences have the last word.
    """
    kind, value = doc.xref_get_key(xref, 'Encoding')
    if kind == 'name':
        return value.lstrip('/'), {}
    if kind == 'xref':
        where, prefix = int(value.split()[0]), ''
    elif kind == 'dict':
        where, prefix = xref, 'Encoding/'
    else:
        return None, {}

    kind, value = doc.xref_get_key(where, prefix + 'BaseEncoding')
    base = value.lstrip('/') if kind == 'name' else None

    kind, value = doc.xref_get_key(where, prefix + 'Differences')
    if kind != 'array':
        return base, {}
    differences, code = {}, 0
    for token in value.strip('[]').split():
        if token.startswith('/'):
            differences[code] = token[1:]
            code += 1
        else:
            try:
                code = int(token)
            except ValueError:
                break
    return base, differences


def _describe(doc, xref, basefont, encoding):
    """One embedded font: its family, its code width, and a fingerprint per code.

    The code width matters as much as the fingerprints. A Type0 font in
    Identity-H encoding is addressed with *two* bytes per glyph, and reading
    such a string one byte at a time yields halves of codes -- which produces
    no error at all, just a plausible and entirely wrong set of symbols. That
    mistake cost three rounds of analysis before it was caught, which is why
    the width is carried here rather than assumed downstream.
    """
    _name, fmt, _ftype, buf = doc.extract_font(xref)
    record = {
        # Kept so the labeller can fetch the outline back out of the document
        # without a second pass over every font on the page.
        'xref': xref,
        'basefont': basefont,
        'family': family_of(basefont),
        'format': fmt,
        'bytes': 2 if (encoding or '').startswith('Identity') else 1,
        'upem': units_per_em(buf) if buf else 1000,
        'codes': {},
    }
    if buf:
        try:
            glyphs, order, builtin = _glyphset(buf)
            if record['bytes'] == 2:
                # Identity-H addresses glyphs by index, so the code the
                # content stream writes *is* the glyph id.
                addressed = dict(enumerate(order))
            else:
                # A simple font addresses them by character code, and that is
                # a different number entirely. Reading one as the other finds
                # a fingerprint for 2% of the codes drawn -- the wrong
                # fingerprint, by coincidence of index -- and none for the
                # rest, which is how half this catalogue came to be invisible.
                # Least to most specific: a named base encoding is a
                # generic character set, the font's own cmap knows better
                # what it holds, and /Differences is the producer stating
                # outright what it renumbered.
                base, differences = _encoding(doc, xref)
                addressed = base_encoding(base)
                addressed.update(builtin)
                addressed.update(differences)
            for code, gname in addressed.items():
                if gname not in glyphs:
                    continue
                fp = fingerprint(glyphs, gname)
                if fp:
                    record['codes']['%04x' % code] = fp
        except Exception as exc:
            record['error'] = str(exc)[:80]
    return record


def font_table(doc, page, cache):
    """The fonts one page can address, keyed by the name its stream uses.

    Per page, and that is not fussiness. /F1 is a name local to a page's
    resource dictionary: nothing stops page 2 from binding it to a different
    font than page 1 did, and PDF producers that emit one resource dictionary
    per page routinely do. A table built once for the whole document and keyed
    by /F1 would draw page 2's music with page 1's alphabet -- silently, and
    with entirely plausible-looking results.

    The expensive part -- fingerprinting every glyph -- is keyed by xref
    instead, so a font shared by twenty pages is read once.
    """
    table = {}
    for entry in page.get_fonts(full=True):
        xref, _ext, _type, basefont, refname, encoding = entry[:6]
        if xref not in cache:
            cache[xref] = _describe(doc, xref, basefont, encoding)
        table[refname] = cache[xref]
    return table


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count('1')
