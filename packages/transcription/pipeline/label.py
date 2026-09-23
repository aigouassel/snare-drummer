#!/usr/bin/env python3
"""
Draw the symbols a score uses, so they can be named.

Fingerprinting (fonts.py) establishes that a symbol is *the same* symbol
across the catalogue; it says nothing about what it means. Nothing in the file
does: the names were stripped by the subsetter. The only way to learn that a
shape is a notehead is to look at it.

So this renders one tile per distinct fingerprint onto a contact sheet, with
an index under each. Looking at the sheet once per family produces the
vocabulary table in vocabulary.py, and that table then resolves every score in
the family -- which is the whole leverage of the shape-first approach: a few
dozen symbols to name, against a catalogue of 884 scores.

The count under each tile is how often the symbol was actually **drawn**, not
how many fonts contain it. Subsetters are not consistent about dropping unused
glyphs, and a font's repertoire turns out to be a poor guide to a family's:
of nine Maestro shapes picked out of the sheet for checking, six were never
placed on a page at all. Ordering by what the engraver used puts the work
where the repertoire is, and a symbol drawn a thousand times is worth more
care than one drawn twice.

    ./label.py ../work/*.pdf --family Opus --out ../work/opus-sheet.png
"""
import argparse
import glob
import os

from fontTools.pens.recordingPen import RecordingPen

import pymupdf

import ink
from fonts import _encoding, _flatten, _glyphset, base_encoding

TILE = 90          # points per tile on the sheet
COLUMNS = 10
MARGIN = 16


def collect(paths, family):
    """Distinct fingerprints in a family, with the outline and usage of each.

    Keyed by fingerprint, so a symbol seen in six scores is drawn once -- and
    counted every time it appears, so the tally tells you which symbols carry
    the repertoire and which are a long tail not worth naming yet.
    """
    seen = {}
    for path in paths:
        try:
            data = ink.read(path)
        except Exception:
            continue
        doc = pymupdf.open(path)
        for page in data['pages']:
            for glyph in page['glyphs']:
                if glyph['family'] != family:
                    continue
                font = page['fonts'].get(glyph['font'] or '', {})
                for code in glyph['codes']:
                    fp = font.get('codes', {}).get(code)
                    if not fp:
                        continue
                    record = seen.setdefault(fp['bits'], {
                        'fingerprint': fp, 'count': 0, 'outline': None,
                        'fonts': set(),
                    })
                    record['count'] += 1
                    record['fonts'].add((font.get('basefont') or '').split('+')[-1])
                    if record['outline'] is None:
                        record['outline'] = _outline(doc, font, code)
        doc.close()
    return {bits: r for bits, r in seen.items() if r['outline']}


def _outline(doc, font, code):
    """The points of a drawn glyph, fetched back out of its embedded program.

    Which glyph a code addresses depends on the encoding, and getting that
    wrong here would draw a contact sheet of the wrong symbols -- a sheet
    that looks entirely plausible and names the whole family incorrectly. So
    it goes through the same resolution the fingerprints did.
    """
    try:
        _n, _fmt, _ft, buf = doc.extract_font(font['xref'])
        glyphs, order, builtin, _adv = _glyphset(buf)
    except Exception:
        return None
    if font['bytes'] == 2:
        addressed = dict(enumerate(order))
    else:
        base, differences = _encoding(doc, font['xref'])
        addressed = base_encoding(base)
        addressed.update(builtin)
        addressed.update(differences)
    name = addressed.get(int(code, 16))
    if name not in glyphs:
        return None
    pen = RecordingPen()
    try:
        glyphs[name].draw(pen)
    except Exception:
        return None
    return _contours(pen.value) or None


def _contours(commands):
    """The glyph's outlines, kept apart.

    Flattening a glyph into one run of points is right for fingerprinting --
    the grid does not care where one contour ends -- and wrong for drawing.
    Two dots rendered as a single polyline become two blobs joined by a spoke,
    and a repeat sign came out looking like a flower, which is not a thing to
    try to recognise on a contact sheet.
    """
    out = []
    run = []
    for op, args in commands:
        if op == 'moveTo' and run:
            out.append(run)
            run = []
        run.append((op, args))
    if run:
        out.append(run)
    return [pts for pts in (_flatten(c) for c in out) if len(pts) >= 3]


def contact_sheet(records, out, title):
    """One tile per symbol, indexed, so the sheet can be read against a list."""
    items = sorted(records.items(), key=lambda kv: -kv[1]['count'])
    rows = (len(items) + COLUMNS - 1) // COLUMNS
    width = MARGIN * 2 + COLUMNS * TILE
    height = MARGIN * 3 + rows * TILE

    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    page.draw_rect(pymupdf.Rect(0, 0, width, height), fill=(1, 1, 1), color=None)
    page.insert_text((MARGIN, MARGIN), title, fontsize=11, color=(0, 0, 0))

    for i, (_bits, record) in enumerate(items):
        col, row = i % COLUMNS, i // COLUMNS
        ox = MARGIN + col * TILE
        oy = MARGIN * 2 + row * TILE

        contours = record['outline']
        pts = [p for c in contours for p in c]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        w = (max(xs) - min(xs)) or 1
        h = (max(ys) - min(ys)) or 1
        # Fit the glyph in the upper part of the tile, leaving room for the
        # index; y is flipped because PDF counts upward and the page down.
        scale = min((TILE - 24) / w, (TILE - 30) / h)
        cx = ox + TILE / 2 - w * scale / 2 - min(xs) * scale
        cy = oy + TILE - 26 + min(ys) * scale

        shape = page.new_shape()
        for contour in contours:
            shape.draw_polyline([(cx + x * scale, cy - y * scale) for x, y in contour])
        shape.finish(fill=(0, 0, 0), color=(0, 0, 0), width=0.3, even_odd=True,
                     closePath=True)
        shape.commit()

        page.insert_text((ox + 4, oy + TILE - 12), f"{i}", fontsize=7,
                         color=(0.1, 0.1, 0.6))
        page.insert_text((ox + 16, oy + TILE - 12),
                         f"x{record['count']} r{record['fingerprint']['aspect']}",
                         fontsize=6, color=(0.4, 0.4, 0.4))

    page.get_pixmap(dpi=180).save(out)
    doc.close()
    return [
        {'index': i, 'bits': bits, 'count': r['count'],
         'aspect': r['fingerprint']['aspect'], 'fonts': sorted(r['fonts'])}
        for i, (bits, r) in enumerate(items)
    ]


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('pdfs', nargs='+')
    ap.add_argument('--family', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--json', help='write the listing, with full fingerprints, here')
    args = ap.parse_args()

    paths = [p for pattern in args.pdfs for p in glob.glob(pattern)]
    records = collect(paths, args.family)
    listing = contact_sheet(records, args.out, f"{args.family} — {len(records)} symboles distincts")
    if args.json:
        import json
        json.dump(listing, open(args.json, 'w'), indent=1)
    print(f"{len(records)} symboles distincts sur {len(paths)} partitions -> {args.out}")
    for item in listing:
        print(f"  {item['index']:>3}  x{item['count']:<3} aspect={item['aspect']:<6} "
              f"{','.join(item['fonts'])}  {item['bits'][:16]}")
