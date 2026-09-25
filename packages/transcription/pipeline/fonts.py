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
import re
from io import BytesIO

import pymupdf
from fontTools.agl import UV2AGL, toUnicode
from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

logging.getLogger('fontTools').setLevel(logging.ERROR)

GRID = 16    # fingerprint resolution: a 16x16 occupancy grid, 256 bits
STEPS = 12   # samples per curve segment when flattening

MUSIC_FAMILIES = ('Bravura', 'Maestro', 'Opus', 'MScore', 'Engraver',
                  'BroadwayCopyist',
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
    """Pen commands -> one list of points per contour.

    Contours are kept apart because `outline` walks each of them, and a line
    from the end of one to the start of the next is ink nobody laid.
    """
    contours, cur, start = [[]], (0.0, 0.0), (0.0, 0.0)
    pts = contours[0]

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
            pts = []
            contours.append(pts)
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
    return [c for c in contours if c]


# How much finer than a grid cell the outline is walked before it is
# gridded. Four is enough that every cell the contour passes through is
# visited, and cheap enough to run on every glyph and every path.
SUBCELL = 4


def _walk(contours, scale):
    """Every point of the outline, plus the points between them.

    The grid below asks which cells the shape's outline occupies, and for a
    long time it answered with the cells the *samples* landed in -- so the
    fingerprint described the shape and how many curve segments its author
    used, which are not the same thing. A font draws a notehead as a dozen
    segments and twelve samples are taken along each; a producer that converts
    that same notehead to a path draws it as four cubic beziers, which is
    twenty-four points for the whole ellipse. Measured on
    `2019-closer-snare-break`, the page's cells came out a strict *subset* of
    Bravura's noteheadBlack -- the same ellipse, sampled more thinly -- 25
    bits away against a threshold of 16. Every notehead on that page went
    unnamed, and a sparse grid being a small target, shapes that are not
    noteheads landed inside 16 bits of one by coincidence: the slash of a
    diddle was read as a triangular notehead thirty-two times.

    Walking the outline instead takes the segment count out of the
    measurement without inventing anything, since every point added lies on a
    chord the shape already drew. Contours are walked one at a time, because
    the jump from the end of one to the start of the next is not ink.
    """
    step = scale / (GRID * SUBCELL)
    out = []
    for contour in contours:
        if not contour:
            continue
        out.append(contour[0])
        for (x0, y0), (x1, y1) in zip(contour, contour[1:]):
            steps = int(max(abs(x1 - x0), abs(y1 - y0)) / step) + 1
            for i in range(1, steps):
                t = i / steps
                out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
            out.append((x1, y1))
    return out


def outline(contours):
    """A fingerprint from the outline of a shape, contour by contour.

    Shared with the path reader, which is the whole point: an outline is an
    outline whether it came from a font program or from the page's own drawing
    instructions. Some of this catalogue draws its music as curves rather than
    as characters, and those shapes match the vocabularies learned from fonts
    because they are the same shapes, measured the same way.
    """
    points = [p for contour in contours for p in contour]
    # Below three points there is nothing to fingerprint, and walking one
    # would invent something: a stroked segment is two points, and filling it
    # in would turn every staff line on the page into a shape.
    if len(points) < 3:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if w <= 0 and h <= 0:
        return None

    # Normalise into the unit square by the larger side, so aspect is
    # preserved: a notehead and a whole-bar rest fill the same grid once
    # stretched independently, and must not be allowed to.
    scale = max(w, h) or 1
    ox, oy = min(xs), min(ys)
    bits = 0
    for x, y in _walk(contours, scale):
        gx = min(GRID - 1, int((x - ox) / scale * GRID))
        gy = min(GRID - 1, int((y - oy) / scale * GRID))
        bits |= 1 << (gy * GRID + gx)

    return {
        'bits': '%064x' % bits,
        'aspect': round(w / h, 2) if h else 0.0,
        'width': round(w, 1),
        'height': round(h, 1),
        # Where the ink sits relative to the origin. The grid above is
        # deliberately translation-invariant -- that is what lets the same
        # symbol match wherever it was drawn -- but some fonts stack a time
        # signature by shipping two glyphs of identical shape at different
        # heights, on one baseline. Shape alone cannot tell those apart.
        'ymin': round(min(ys), 1),
        'xmin': round(min(xs), 1),
    }


def fingerprint(glyphset, name):
    pen = RecordingPen()
    try:
        glyphset[name].draw(pen)
    except Exception:
        return None
    return outline(_flatten(pen.value))


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


def _advances(tt, order):
    """Each glyph's advance width, in font units.

    A text-showing operator draws a *run*, and the reader has to walk it the
    way a renderer does -- one glyph, then forward by its width. Recording
    the run's origin for every glyph in it puts them all at the same point,
    and a time signature written as the one run "44" then has its numerator
    and denominator at identical coordinates, so nothing can tell which is
    on top. Two percent of the glyphs in this catalogue arrive in runs, and
    they include most of its time signatures.
    """
    try:
        hmtx = tt['hmtx']
    except Exception:
        return {}
    out = {}
    for name in order:
        try:
            out[name] = hmtx[name][0]
        except Exception:
            continue
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
    """(glyph set, glyph order, code -> name, name -> advance) from a font."""
    try:
        tt = TTFont(BytesIO(buf), fontNumber=0, lazy=True)
        order, builtin = tt.getGlyphOrder(), _builtin(tt)
        advance = _advances(tt, order)
        try:
            return tt.getGlyphSet(), order, builtin, advance
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

            return {n: _Outline(n) for n in order}, order, builtin, advance
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

    advance = {}
    for name in order:
        try:
            advance[name] = charstrings[name].width
        except Exception:
            continue
    return {n: _Glyph(charstrings[n]) for n in order}, order, builtin, advance


def _pdf_widths(doc, xref):
    """Advance widths as the PDF states them, in thousandths of the text size.

    The PDF is the authority here -- it is what a renderer lays the page out
    with -- and it is also the only source that survives a subsetter having
    truncated the font's own metrics table, which happens in this catalogue.
    """
    kind, value = doc.xref_get_key(xref, 'Widths')
    # /Widths is routinely an indirect object rather than a literal array --
    # it is a long array, and producers share one between subsets. Reading
    # only the literal form found no widths at all for those fonts, and a
    # width that is missing becomes a width of zero one layer up: every glyph
    # of a run lands on the same x, and the run then sorts into nonsense.
    if kind == 'xref':
        try:
            value = doc.xref_object(int(value.split()[0]), compressed=False)
            kind = 'array' if value.strip().startswith('[') else kind
        except Exception:
            return {}
    if kind == 'array':
        first = doc.xref_get_key(xref, 'FirstChar')
        start = int(first[1]) if first[0] == 'int' else 0
        out = {}
        for i, token in enumerate(value.strip('[]').split()):
            try:
                out[start + i] = float(token)
            except ValueError:
                pass
        return out

    kind, value = doc.xref_get_key(xref, 'DescendantFonts')
    if kind != 'array':
        return {}
    try:
        descendant = int(value.strip('[] ').split()[0])
    except (ValueError, IndexError):
        return {}
    kind, value = doc.xref_get_key(descendant, 'W')
    if kind != 'array':
        return {}
    # /W is either "code [w w w]" for a run starting at code, or
    # "first last w" for a range that shares one width.
    tokens = value.replace('[', ' [ ').replace(']', ' ] ').split()
    out, pending, run, code = {}, [], None, None
    for token in tokens:
        if token == '[':
            run, code = [], int(pending[-1]) if pending else 0
        elif token == ']':
            for i, w in enumerate(run or []):
                out[code + i] = w
            run, pending = None, []
        elif run is not None:
            try:
                run.append(float(token))
            except ValueError:
                pass
        else:
            pending.append(token)
            if len(pending) == 3:
                try:
                    lo, hi, w = int(pending[0]), int(pending[1]), float(pending[2])
                    for c in range(lo, min(hi, lo + 65535) + 1):
                        out[c] = w
                except ValueError:
                    pass
                pending = []
    return out


def _cid_to_gid(doc, xref):
    """The map from character code to glyph index, for a composite font.

    Identity-H means the code *is* the CID, and it is tempting to read that
    as the code being the glyph index too. It is not: a CIDFontType2 may
    carry a /CIDToGIDMap stream, two bytes per CID, and then the codes on
    the page bear no relation to the glyphs in the font. One score here
    draws codes in the 0xF000 block against a font of fourteen glyphs, so
    every symbol on it resolved to nothing at all.

    Returns None when the mapping is the identity, which is the common case
    and wants no table.
    """
    kind, value = doc.xref_get_key(xref, 'DescendantFonts')
    if kind != 'array':
        return None
    try:
        descendant = int(value.strip('[] ').split()[0])
    except (ValueError, IndexError):
        return None
    kind, value = doc.xref_get_key(descendant, 'CIDToGIDMap')
    if kind != 'xref':
        return None
    try:
        data = doc.xref_stream(int(value.split()[0]))
    except Exception:
        return None
    return {i: int.from_bytes(data[2 * i:2 * i + 2], 'big')
            for i in range(len(data) // 2)
            if data[2 * i:2 * i + 2] != b'\x00\x00'}


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


def _to_unicode(doc, xref):
    """The font's /ToUnicode CMap, as code -> the text it stands for.

    This is a different kind of table from the three above it, and the
    difference is the point. A cmap, a /Differences array and a /CIDToGIDMap
    all answer "which outline does this code draw"; /ToUnicode alone answers
    "what does this code *mean*", and a producer writes it so that copying
    text out of the page works. Nothing on the page depends on it, which is
    why it is optional -- and why a composite font without one spells nothing
    and must be reported rather than guessed at.

    Without it, every Identity-H text font on these pages is mute: its glyphs
    are named glyph00042 and carry no letter at all. That is 70% of the words
    in this catalogue, including most of the tempo marks and stickings.
    """
    kind, value = doc.xref_get_key(xref, 'ToUnicode')
    if kind != 'xref':
        return {}
    try:
        stream = doc.xref_stream(int(value.split()[0])).decode('latin-1')
    except Exception:
        return {}

    out = {}
    for block in re.findall(r'beginbfchar(.*?)endbfchar', stream, re.S):
        for code, target in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>', block):
            text = _utf16(target)
            if text:
                out[int(code, 16)] = text
    for block in re.findall(r'beginbfrange(.*?)endbfrange', stream, re.S):
        # Two forms: a run mapping to consecutive code points, and a run
        # mapping to an explicit list.
        for low, high, body in re.findall(
                r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]*>)',
                block, re.S):
            start, end = int(low, 16), int(high, 16)
            if end - start > 0xFFFF:
                continue
            if body.startswith('['):
                targets = re.findall(r'<([0-9A-Fa-f]*)>', body)
                for offset, target in enumerate(targets):
                    text = _utf16(target)
                    if text:
                        out[start + offset] = text
            else:
                base = _utf16(body.strip('<>'))
                if not base:
                    continue
                for code in range(start, end + 1):
                    out[code] = chr(ord(base[0]) + code - start) + base[1:]
    return out


def _utf16(digits):
    """A bfchar target: big-endian UTF-16, however many code units long."""
    if not digits or len(digits) % 4:
        return ''
    try:
        return bytes.fromhex(digits).decode('utf-16-be')
    except (ValueError, UnicodeDecodeError):
        return ''


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
        'chars': {},
        'advances': {},
    }
    glyphs, order, builtin, addressed, advance = {}, [], {}, {}, {}
    if buf:
        try:
            glyphs, order, builtin, advance = _glyphset(buf)
            if record['bytes'] == 2:
                # Under Identity-H the code is the CID; the CID is the glyph
                # index only when the font says so, which is the common case
                # but not the only one.
                cids = _cid_to_gid(doc, xref)
                if cids is None:
                    addressed = dict(enumerate(order))
                else:
                    addressed = {code: order[gid] for code, gid in cids.items()
                                 if gid < len(order)}
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
                if gname in advance:
                    record['advances']['%04x' % code] = (
                        advance[gname] * 1000.0 / (record['upem'] or 1000))
        except Exception as exc:
            record['error'] = str(exc)[:80]
    # What a code *means* is a different question from which outline it
    # draws, and the same four sources answer them differently.
    #
    # For a shape the font's own cmap has the last word: it knows what it
    # holds. For a letter that cmap is often worse than useless -- a subset
    # carries a symbol cmap whose glyphs are named glyph00012 -- so it is
    # allowed to override the PDF's encoding only where its name actually
    # spells something. Letting it override regardless replaced the m of
    # "mm=180" with a name that spells nothing; ignoring it entirely lost the
    # Sibelius dialect, where the quarter-note glyph really is named q.
    #
    # Only codes the font can draw get a letter. A base encoding covers the
    # whole Latin range, and applying it wholesale had every font on the page
    # claiming to spell 213 characters it does not contain.
    if record['bytes'] == 1:
        base, differences = _encoding(doc, xref)
        # No /Encoding at all means the font's own, which for the standard
        # text faces is StandardEncoding -- and over the ASCII range that is
        # the one thing every base encoding here agrees on.
        spelling = base_encoding(base or 'StandardEncoding')
        spelling.update({code: gname for code, gname in builtin.items()
                         if toUnicode(gname)})
        spelling.update(differences)
        drawable = {code for code, gname in addressed.items()
                    if gname in glyphs} or set(spelling)
        for code, gname in spelling.items():
            if code not in drawable:
                continue
            char = toUnicode(gname)
            if char:
                record['chars']['%04x' % code] = char

    # /ToUnicode overrides whatever the glyph names spelled: it is the
    # producer stating outright what the code means, where the names are only
    # a convention the subsetter was free to destroy.
    for code, text in _to_unicode(doc, xref).items():
        record['chars']['%04x' % code] = text

    # The PDF has the last word: it is what the page was laid out with, and
    # it survives a font whose own metrics table was truncated.
    for code, width in _pdf_widths(doc, xref).items():
        record['advances']['%04x' % code] = width
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
