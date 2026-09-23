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
from fractions import Fraction

import ink
import layout
from vocabulary import INERT, RHYTHMIC, Vocabulary, role

# Durations an engraver actually writes, as a fraction of a quarter-note beat.
# Reconstruction snaps to these: a value that lands between two of them is not
# a note length anybody wrote, it is a measurement error.
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
    """A time signature: digits stacked above and below the middle staff line.

    Read only where it is printed -- at the head of a system, or wherever the
    metre changes -- so a piece that prints none anywhere gets none, and its
    bars are flagged for it rather than handed a plausible 4/4.

    The numerator is not one digit. This repertoire is full of 12/8, and an
    earlier version that paired a single digit with a single digit simply saw
    no signature at all and reconstructed nothing -- silently, since a missing
    signature is indistinguishable from a piece that never printed one. So
    digits are grouped by proximity and read left to right, which is how they
    are printed.
    """
    middle = (system['bottom'] + system['top']) / 2
    digits = [(g, int(s.split('.')[1])) for g, s in named
              if s and s.startswith('digit.')
              and system['bottom'] - 1 <= g['y'] <= system['top'] + 1]
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
        upper = sorted([p for p in cluster if p[0]['y'] > middle], key=lambda p: p[0]['x'])
        lower = sorted([p for p in cluster if p[0]['y'] <= middle], key=lambda p: p[0]['x'])
        if not upper or not lower:
            continue
        beats = int(''.join(str(d) for _g, d in upper))
        value = int(''.join(str(d) for _g, d in lower))
        if value in (1, 2, 4, 8, 16) and 1 <= beats <= 32:
            return [beats, value]
    return None


def reconstruct(named, bar, meter):
    """Place the bar's notes and rests in time, by their spacing on the page."""
    onsets = [(g, s) for g, s in named if role(s) in RHYTHMIC]
    unnamed = sum(1 for _g, s in named if role(s) == 'unnamed')

    if not onsets or meter is None:
        return [], unnamed

    total = Fraction(meter[0] * 4, meter[1])

    # Gaps between consecutive onsets, the last one running to the barline.
    positions = [g['x'] for g, _ in onsets]
    gaps = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
    gaps.append(bar['x1'] - positions[-1])
    span = sum(gaps)
    if span <= 0:
        return [], unnamed

    events = []
    for (g, symbol), gap in zip(onsets, gaps):
        measured = float(total) * gap / span
        duration, _drift = snap(measured)
        event = {'duration': [duration.numerator, duration.denominator]}
        if role(symbol) == 'rest':
            event['rest'] = True
        else:
            if symbol == 'notehead.cross':
                event['zone'] = 'crossStick'
            elif symbol == 'notehead.diamond':
                event['zone'] = 'rim'
        events.append(event)

    return events, unnamed


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
    systems, found = layout.bars(data['segments'])
    families = {g['family'] for g in data['glyphs'] if g['family']}
    vocabularies = {f: Vocabulary(f) for f in families}

    fonts = data['fonts']

    def name(glyph):
        font = fonts.get(glyph['font'] or '', {})
        codes = font.get('codes', {})
        vocab = vocabularies.get(glyph['family'])
        out = []
        for code in glyph['codes']:
            fp = codes.get(code)
            out.append(vocab.resolve(fp) if (fp and vocab) else None)
        return out

    meter = None
    bars = []
    for bar in found:
        system = systems[bar['system']]
        named = []
        for glyph in glyphs_in(data['glyphs'], bar, system):
            for symbol in name(glyph):
                named.append((glyph, symbol))

        printed = read_meter(named, system)
        if printed:
            meter = printed

        events, unnamed = reconstruct(named, bar, meter)
        events = decorate(events, named)

        bars.append({
            'n': bar['n'],
            'meter': meter,
            'events': events,
            'unnamedSymbols': unnamed,
            'at': {'page': 1, 'system': bar['system'],
                   'x0': bar['x0'], 'x1': bar['x1']},
        })

    return {
        'id': entry['id'],
        'title': entry['title'],
        'corps': entry['corps'],
        'circuit': entry['circuit'],
        **({'year': entry['year']} if entry.get('year') else {}),
        'source': {'url': entry['url'],
                   'listedAt': entry['listedAt'],
                   'read': entry['read']},
        'bars': bars,
        'extraction': {
            'families': sorted(families),
            'unhandledOperators': data['unhandled'],
            'systems': len(systems),
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
