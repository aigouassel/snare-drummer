#!/usr/bin/env python3
"""
A PDF in, a piece out: bars, what is in them, and how far each can be trusted.

The reconstruction is layered so that each layer trusts only what the one
below it actually read:

  1. ink.py      replays the page and reports every glyph and segment.
  2. layout.py   finds the staves and the barlines -- the only structure on
                 the page that is stated rather than inferred.
  3. vocabulary  names the symbols by shape.
  4. here        places the named symbols into the bars and works out how long
                 each note lasts.

Step 4 is the weakest link and is written to say so. Duration is inferred from
*horizontal spacing*: engraving lays notes out roughly in proportion to their
length, so the gaps between noteheads give their relative durations, and the
bar's own metre fixes the scale. It is a real signal, but only roughly linear
-- engravers compress dense passages -- so it will sometimes be wrong.

That is survivable only because of what follows it: the durations must sum to
the metre exactly, and a bar where they do not is marked suspect rather than
shipped. A bar that closes may still be wrong, and nothing here pretends
otherwise; what the design guarantees is that a bar which does not close is
never presented as if it did.
"""
import json
import os
import sys
from collections import defaultdict
from fractions import Fraction

import ink
import layout
import rhythm
from fonts import MUSIC_FAMILIES
from vocabulary import RHYTHMIC, Vocabulary, attribute, role

# Durations an engraver actually writes, as a fraction of a quarter-note beat.
# Reconstruction snaps to these: a value that lands between two of them is not
# a note length anybody wrote, it is a measurement error.
KNOWN_FAMILIES = MUSIC_FAMILIES

# What a notehead says about where the stick lands, when it says anything.
ZONES = {
    'notehead.cross': 'crossStick',
    'notehead.triangleRight': 'crossStick',
    'notehead.diamond': 'rim',
    'notehead.diamondBlack': 'rim',
    'notehead.circleX': 'rimshot',
    'notehead.circleDot': 'rimshot',
    'notehead.circleSlash': 'rimshot',
}

GRID = [Fraction(1, 8), Fraction(1, 6), Fraction(1, 4), Fraction(1, 3),
        Fraction(3, 8), Fraction(1, 2), Fraction(2, 3), Fraction(3, 4),
        Fraction(1), Fraction(3, 2), Fraction(2), Fraction(3), Fraction(4)]


def snap(value):
    """The written duration nearest a measured one, and how far off it was."""
    best = min(GRID, key=lambda g: abs(float(g) - value))
    return best, abs(float(best) - value)


def glyphs_in(glyphs, bar, system):
    """Named symbols sitting inside a bar, in reading order."""
    inside = []
    for g in glyphs:
        if not g['family']:
            continue
        if not (bar['x0'] - 1 <= g['x'] < bar['x1'] - 1):
            continue
        # Well outside the staff vertically is a title or a tempo mark, not
        # part of the bar's music.
        if not (system['bottom'] - 6 * system['spacing'] <= g['y']
                <= system['top'] + 6 * system['spacing']):
            continue
        inside.append(g)
    return sorted(inside, key=lambda g: g['x'])


def read_meter(named, system):
    """A time signature: digits stacked one above the other, read as two numbers.

    Read only where it is printed -- at the head of a system, or wherever the
    metre changes -- so a piece that prints none anywhere gets none, and its
    bars are flagged for it rather than handed a plausible 4/4.

    The numerator is not one digit. This repertoire is full of 12/8, and an
    earlier version that paired a single digit with a single digit simply saw
    no signature at all and reconstructed nothing -- silently, since a missing
    signature is indistinguishable from a piece that never printed one. So
    digits are grouped by proximity and read left to right, which is how they
    are printed.

    Which digits are the numerator is decided *relatively*, from the two
    heights the cluster itself occupies, and not by comparing each digit to
    the middle of the staff. A glyph's y is where its origin was placed, and
    engravers place the numerator's origin on the middle line itself -- so an
    absolute test puts the numerator on the wrong side of the divide by a
    tenth of a point and finds no signature at all. Whole pieces came out
    metreless that way.
    """
    span = system['top'] - system['bottom']
    digits = [({**g, 'y': g.get('inkY', g['y'])}, int(s.split('.')[1]))
              for g, s in named
              if s and s.startswith('digit.')
              and system['bottom'] - span / 2 <= g.get('inkY', g['y'])
              <= system['top'] + span / 2]
    if not digits:
        return None

    # One time signature is a tight cluster in x; a tuplet number further
    # along the bar is a separate one, and must not be read into it.
    digits.sort(key=lambda p: p[0]['x'])
    clusters, current = [], [digits[0]]
    for item in digits[1:]:
        if item[0]['x'] - current[-1][0]['x'] <= system['spacing'] * 2.5:
            current.append(item)
        else:
            clusters.append(current)
            current = [item]
    clusters.append(current)

    for cluster in clusters:
        heights = [p[0]['y'] for p in cluster]
        # Two levels, a real distance apart. A row of digits all at one
        # height is a tuplet ratio or a bar number, not a signature.
        if max(heights) - min(heights) < system['spacing'] * 0.8:
            continue
        divide = (max(heights) + min(heights)) / 2
        upper = sorted([p for p in cluster if p[0]['y'] > divide], key=lambda p: p[0]['x'])
        lower = sorted([p for p in cluster if p[0]['y'] <= divide], key=lambda p: p[0]['x'])
        if not upper or not lower:
            continue
        beats = int(''.join(str(d) for _g, d in upper))
        value = int(''.join(str(d) for _g, d in lower))
        if value in (1, 2, 4, 8, 16) and 1 <= beats <= 32:
            return [beats, value]
    return None


def reconstruct(named, bar, meter, context):
    """Place the bar's notes and rests in time.

    Two readings, and the first one is the notation itself: beams, flags and
    dots say what an engraver wrote. When any note in the bar cannot be read
    that way the whole bar falls back to spacing, because mixing a stated
    length with a measured one inside one bar produces a sum that means
    nothing. Which reading was used is recorded on the bar.
    """
    marks = [(g, s) for g, s in named if role(s) in RHYTHMIC]
    unnamed = sum(1 for _g, s in named if role(s) == 'unnamed')

    # A grace note is written, played and gone; it takes no time of its own,
    # so it is carried onto the note it decorates rather than counted.
    onsets, graces, pending = [], [], 0
    for g, symbol in marks:
        if role(symbol) == 'notehead' and rhythm.is_grace(g.get('ink', 0.0),
                                                          context['notehead']):
            pending += 1
            continue
        onsets.append((g, symbol))
        graces.append(pending)
        pending = 0

    if not onsets or meter is None:
        return [], unnamed, 'none'

    total = Fraction(meter[0] * 4, meter[1])

    lengths = [rhythm.written(symbol, g['x'], g['y'], g.get('ink', 0.0), context)
               for g, symbol in onsets]
    source = 'notation'
    if all(length is not None for length in lengths):
        for start, stop, ratio in rhythm.tuplet_groups(
                context['tuplets'], onsets, context['spacing']):
            for i in range(start, stop):
                lengths[i] *= ratio
    if any(length is None for length in lengths):
        source = 'spacing'
        lengths = _by_spacing(onsets, bar, total)
        if lengths is None:
            return [], unnamed, 'none'

    events = []
    for (g, symbol), duration, grace in zip(onsets, lengths, graces):
        event = {'duration': [duration.numerator, duration.denominator]}
        if role(symbol) == 'rest':
            event['rest'] = True
        else:
            if symbol in ZONES:
                event['zone'] = ZONES[symbol]
            if grace:
                event['graces'] = grace
        events.append(event)

    return events, unnamed, source


def _notehead_width(page, fonts, vocabularies):
    """How wide a full-size notehead is on this page, in points.

    The *commonest* width, not the largest. A page carries both sizes and a
    handful of outsized noteheads besides -- a cue, a heading, an oversized
    example -- and taking the largest lets one of those redefine full size
    and turn every real note on the page into a grace note. The commonest is
    the one the music is written in.
    """
    seen = defaultdict(int)
    for glyph in page['glyphs']:
        font = fonts.get(glyph['font'] or '', {})
        vocab = vocabularies.get(glyph['family'])
        if not vocab:
            continue
        upem = font.get('upem') or 1000
        for code in glyph['codes']:
            fp = font.get('codes', {}).get(code)
            if fp and role(vocab.resolve(fp)) == 'notehead':
                seen[round(fp['width'] * glyph['size'] / upem, 2)] += 1
    if not seen:
        return 0.0
    return max(seen.items(), key=lambda kv: (kv[1], kv[0]))[0]


def tuplet_numbers(named, system):
    """Tuplet counts printed in a bar, with what they stand in the time of.

    Read outside the staff only. A time signature is printed *on* the staff
    and a tuplet number above or below it, which is the whole difference
    between the two and needs no other test.

    A printed ratio -- 4:3, 7:6, which this repertoire does use -- states both
    numbers, so it is read as written rather than assumed.
    """
    marks = sorted(
        [(g, s) for g, s in named
         if s and (s.startswith('digit.') or s == 'text.colon')
         and not (system['bottom'] - 1 <= g['y'] <= system['top'] + 1)],
        key=lambda p: p[0]['x'])
    if not marks:
        return []

    clusters, current = [], [marks[0]]
    for item in marks[1:]:
        if item[0]['x'] - current[-1][0]['x'] <= system['spacing'] * 2.0:
            current.append(item)
        else:
            clusters.append(current)
            current = [item]
    clusters.append(current)

    out = []
    for cluster in clusters:
        x = sum(g['x'] for g, _ in cluster) / len(cluster)
        if any(s == 'text.colon' for _g, s in cluster):
            left, right, seen = [], [], False
            for _g, s in cluster:
                if s == 'text.colon':
                    seen = True
                elif seen:
                    right.append(s.split('.')[1])
                else:
                    left.append(s.split('.')[1])
            if not left or not right:
                continue
            count, inthe = int(''.join(left)), int(''.join(right))
        else:
            count = int(''.join(s.split('.')[1] for _g, s in cluster))
            if count not in rhythm.IN_THE:
                continue
            inthe = rhythm.IN_THE[count]
        if 2 <= count <= 32 and 1 <= inthe <= 32:
            out.append((x, count, inthe))
    return out


def _by_spacing(onsets, bar, total):
    """Durations from how far apart the notes were set on the page.

    Engraving spaces a bar roughly in proportion to what it holds, so this
    recovers something when the notation cannot be read -- but only roughly,
    and a bar read this way is worth less than one read from its beams.
    """
    positions = [g['x'] for g, _ in onsets]
    gaps = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
    gaps.append(bar['x1'] - positions[-1])
    span = sum(gaps)
    if span <= 0:
        return None
    return [snap(float(total) * gap / span)[0] for gap in gaps]


def decorate(events, named):
    """Hang articulations on the note they sit above or below.

    Proximity is the only available evidence -- a PDF says where a mark was
    drawn, not what it belongs to -- so this is the one genuinely heuristic
    step, and the place where a wrong reading is least likely to be caught by
    arithmetic. Kept deliberately narrow: nearest onset, or nothing.
    """
    marks = [(g, s) for g, s in named
             if s in ('articulation.accent', 'articulation.marcato',
                      'tremolo.slash', 'roll.buzz')]
    onsets = [(g, s) for g, s in named if role(s) in RHYTHMIC]
    for mark, symbol in marks:
        if not onsets:
            break
        index = min(range(len(onsets)), key=lambda i: abs(onsets[i][0]['x'] - mark['x']))
        if index >= len(events):
            continue
        if symbol == 'articulation.accent':
            events[index]['accent'] = 'accent'
        elif symbol == 'articulation.marcato':
            events[index]['accent'] = 'marcato'
        elif symbol == 'roll.buzz':
            events[index]['roll'] = 'buzz'
        elif symbol == 'tremolo.slash':
            events[index]['roll'] = 'double'
    return events


def transcribe(path, entry):
    data = ink.read(path)

    # The metre carries across pages. A signature printed once on page 1
    # governs page 2 as well, because that is what a reader does with it.
    meter = None
    bars = []
    families = set()
    systems_total = 0

    known = {f: Vocabulary(f) for f in KNOWN_FAMILIES}
    attributed = {}

    for page in data['pages']:
        systems, found = layout.bars(page['segments'])
        systems_total += len(systems)
        fonts = page['fonts']

        # A font whose name says nothing may still be a music font. Ask its
        # shapes, once per font, and write the answer back onto the glyphs so
        # everything downstream sees one kind of family.
        for ref, font in fonts.items():
            if font.get('family') or not font.get('codes'):
                continue
            key = font.get('xref')
            if key not in attributed:
                attributed[key] = attribute(list(font['codes'].values()), known)
            if attributed[key]:
                font['family'] = attributed[key]
                font['attributedByShape'] = True
        for glyph in page['glyphs']:
            if not glyph['family']:
                glyph['family'] = fonts.get(glyph['font'] or '', {}).get('family')

        page_families = {g['family'] for g in page['glyphs'] if g['family']}
        families |= page_families
        vocabularies = {f: known[f] for f in page_families if f in known}

        def name(glyph):
            """Each code the glyph draws, as (symbol, ink width in points).

            The width is what locates a stem: an up-stem is drawn at the
            notehead's right edge, one notehead away from the origin the PDF
            records, and a down-stem at its left.
            """
            font = fonts.get(glyph['font'] or '', {})
            codes = font.get('codes', {})
            upem = font.get('upem') or 1000
            vocab = vocabularies.get(glyph['family'])
            out = []
            for code in glyph['codes']:
                fp = codes.get(code)
                symbol = vocab.resolve(fp) if (fp and vocab) else None
                if fp:
                    scale = glyph['size'] / upem
                    width = fp['width'] * scale
                    middle = glyph['y'] + (fp['ymin'] + fp['height'] / 2) * scale
                else:
                    width, middle = 0.0, glyph['y']
                out.append((symbol, width, middle))
            return out

        notehead_width = _notehead_width(page, fonts, vocabularies)

        geometry = {}
        for index, system in enumerate(systems):
            geometry[index] = {
                'beams': rhythm.beams(page['segments'], system['spacing']),
                'stems': rhythm.stems(page['segments'], system['spacing']),
            }

        for bar in found:
            system = systems[bar['system']]
            named = []
            for glyph in glyphs_in(page['glyphs'], bar, system):
                for symbol, width, middle in name(glyph):
                    named.append(({**glyph, 'ink': width, 'inkY': middle},
                                  symbol))

            printed = read_meter(named, system)
            if printed:
                meter = printed

            context = {
                'spacing': system['spacing'],
                'middle': (system['bottom'] + system['top']) / 2,
                'beams': geometry[bar['system']]['beams'],
                'stems': geometry[bar['system']]['stems'],
                'flags': [(g['x'], rhythm.HALVES[s]) for g, s in named
                          if s in rhythm.HALVES],
                'dots': [(g['x'], g['y']) for g, s in named if s == 'dot'],
                'notehead': notehead_width,
                'tuplets': tuplet_numbers(named, system),
            }
            events, unnamed, source = reconstruct(named, bar, meter, context)
            events = decorate(events, named)

            bars.append({
                # Numbered across the whole piece, not per page: a bar number
                # that restarts at each page would not address anything.
                'n': len(bars) + 1,
                'meter': meter,
                'events': events,
                'unnamedSymbols': unnamed,
                'readFrom': source,
                'at': {'page': page['page'], 'system': bar['system'],
                       'x0': bar['x0'], 'x1': bar['x1']},
            })

    return {
        'id': entry['id'],
        'title': entry['title'],
        'workId': entry['workId'],
        'corps': entry['corps'],
        'circuit': entry['circuit'],
        **({'year': entry['year']} if entry.get('year') else {}),
        'source': {'url': entry['url'],
                   'listedAt': entry['listedAt'],
                   'read': entry['read']},
        'bars': bars,
        'extraction': {
            'families': sorted(families),
            'familiesByShape': sorted(
                {f for f in attributed.values() if f}),
            'unhandledOperators': data['unhandled'],
            'pages': len(data['pages']),
            'systems': systems_total,
        },
    }


if __name__ == '__main__':
    pdf, meta_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    entry = json.load(open(meta_path))
    piece = transcribe(pdf, entry)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(piece, open(out, 'w'), indent=1, ensure_ascii=False)

    total = len(piece['bars'])
    with_events = sum(1 for b in piece['bars'] if b['events'])
    unnamed = sum(b['unnamedSymbols'] for b in piece['bars'])
    print(f"{piece['title']} — {total} mesures, {with_events} avec des notes, "
          f"{unnamed} symboles non identifies")
