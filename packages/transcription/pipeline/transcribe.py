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
import text
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

# A flam is one grace note, a drag two, a ruff three. There is no fourth.
MAX_GRACES = 3

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


def read_meter(named, system, words=()):
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

    Two sources, tried in order and never mixed. Most engravers set the
    signature in the music font, where the shape vocabulary names it; several
    set it in a text font, which no shape vocabulary can ever name, because a
    4 in Times is a 4 in Times and enrolling it would make every body face a
    music font. Mixing the two reads the same signature twice -- the families
    whose digits are both a named shape and a letter turned 4/4 into 44/44 --
    so the letters are consulted only where the shapes said nothing.
    """
    span = system['top'] - system['bottom']

    def on_staff(y):
        return system['bottom'] - span / 2 <= y <= system['top'] + span / 2

    drawn = [({**g, 'y': g.get('inkY', g['y'])}, int(s.split('.')[1]))
             for g, s in named
             if s and s.startswith('digit.')
             and on_staff(g.get('inkY', g['y']))]

    spelled = []
    for word in words:
        characters = word['text'].strip()
        if not characters.isdigit() or not on_staff(word['y']):
            continue
        for offset, character in enumerate(characters):
            spelled.append(({'x': word['x'] + offset * word['size'] * 0.5,
                             'y': word['y']}, int(character)))

    for digits in (drawn, spelled):
        found = _signature(digits, system)
        if found:
            return found
    return None


def _signature(digits, system):
    """Two numbers out of a cluster of digits, or nothing.

    Which digits are the numerator is decided *relatively*, from the two
    heights the cluster itself occupies, and not by comparing each digit to
    the middle of the staff. A glyph's y is where its origin was placed, and
    engravers place the numerator's origin on the middle line itself -- so an
    absolute test puts the numerator on the wrong side of the divide by a
    tenth of a point and finds no signature at all. Whole pieces came out
    metreless that way.
    """
    if not digits:
        return None

    # One time signature is a tight cluster in x; a tuplet number further
    # along the bar is a separate one, and must not be read into it.
    digits = sorted(digits, key=lambda p: p[0]['x'])
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
    #
    # Three ways that reading can be wrong, and each of them used to lose a
    # note in silence rather than report one. Past three it is not an
    # ornament: a flam is one grace note, a drag two and a ruff three, so a
    # run of four means the cue-size test failed and they are notes written
    # small. Nothing decorates a rest. And nothing decorates the barline --
    # a run left pending at the end of the bar has no note to attach to.
    #
    # In all three the pending heads are put back as notes. They then take
    # time, the sum stops adding up and the bar is reported, where as
    # ornaments they were attacks removed from the bar without changing its
    # arithmetic -- the one kind of error nothing downstream can catch.
    onsets, graces, pending = [], [], []

    def flush():
        for item in pending:
            onsets.append(item)
            graces.append(0)
        pending.clear()

    for g, symbol in marks:
        if role(symbol) == 'notehead' and rhythm.is_grace(g.get('size', 0.0),
                                                          context['notehead']):
            pending.append((g, symbol))
            continue
        if len(pending) > MAX_GRACES or role(symbol) == 'rest':
            flush()
        onsets.append((g, symbol))
        graces.append(len(pending))
        pending.clear()
    flush()

    if not onsets or meter is None:
        return [], unnamed, 'none', onsets

    total = Fraction(meter[0] * 4, meter[1])

    lengths = [rhythm.written(symbol, g['x'], g['y'], g.get('inkY', g['y']),
                              g.get('ink', 0.0), context)
               for g, symbol in onsets]
    # A rest alone in its bar is a whole-bar rest and lasts exactly the bar,
    # whatever the metre says: three beats in 3/4, three and a half in 7/8.
    # Reading it as four made every such bar in a metre other than 4/4 fail
    # its own arithmetic, and is also the only thing that can be said about
    # one on a staff with no fourth line to hang from.
    if len(onsets) == 1 and role(onsets[0][1]) == 'rest' and \
            onsets[0][1] in ('rest.rectangle', 'rest.whole'):
        lengths = [total]

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
            return [], unnamed, 'none', onsets

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

    return events, unnamed, source, onsets


def _notehead_size(page, fonts, vocabularies):
    """The type size a full-size notehead is drawn at on this page, in points.

    The *commonest* size, not the largest. A page carries both sizes and a
    handful of outsized noteheads besides -- a cue, a heading, an oversized
    example -- and taking the largest lets one of those redefine full size and
    turn every real note on the page into a grace note. The commonest is the
    one the music is written in.

    The type size and not the ink width, which was measured here before. Ink
    width mixes the scale with the shape of the head, so a cross or a diamond
    at full size reads as a cue-size oval; type size is the scale alone, and
    on this catalogue it comes out cleanly bimodal.
    """
    seen = defaultdict(int)
    for glyph in page['glyphs']:
        font = fonts.get(glyph['font'] or '', {})
        vocab = vocabularies.get(glyph['family'])
        if not vocab:
            continue
        for code in glyph['codes']:
            fp = font.get('codes', {}).get(code)
            if fp and role(vocab.resolve(fp)) == 'notehead':
                seen[round(glyph['size'], 2)] += 1
    if not seen:
        return 0.0
    return max(seen.items(), key=lambda kv: (kv[1], kv[0]))[0]


# How far outside the staff a tuplet number is still a tuplet number. It is
# printed against the beam of the notes it governs, so it sits close; a bar
# number or a rehearsal mark stands clear of the music. Measured at 2.6 spaces
# on the score this was found on.
TUPLET_REACH = 4.0

# How far past the barline a digit has to be before it can be a tuplet number.
# A bar number is set against the barline itself -- measured at 0.2 to 1.2
# points from it on three engravers -- while a tuplet number is centred over
# the notes it governs, so even one starting on the downbeat sits several
# spaces in. Without this, a system beginning at bar 5 read a quintuplet.
BAR_NUMBER_EDGE = 1.5


def tuplet_numbers(named, system, words=(), x0=None):
    """Tuplet counts printed in a bar, with what they stand in the time of.

    Read outside the staff only. A time signature is printed *on* the staff
    and a tuplet number above or below it, which is the whole difference
    between the two and needs no other test.

    A printed ratio -- 4:3, 7:6, which this repertoire does use -- states both
    numbers, so it is read as written rather than assumed.

    Two sources, tried in order and never merged, for the same reason the time
    signature has two: Finale sets its tuplet numbers in a text italic and
    Sibelius engraves them in the music font, and reading only the shapes lost
    every tuplet of a whole engraver. Merged, a family whose digits are both a
    named shape and a letter would yield the same number twice and the ratio
    would be applied twice -- silently, and wrong by an exact factor.

    A digit read as text has to sit near the staff, and clear of the barline.
    A bar number is printed above the staff at the start of its bar and is
    otherwise indistinguishable from a tuplet number -- same size, same
    height, and 3, 5 and 6 are all counts a tuplet can have. What separates
    them is where they sit horizontally: a bar number is set against the
    barline, a tuplet number over its notes.
    """
    marks = sorted(
        [(g, s) for g, s in named
         if s and (s.startswith('digit.') or s == 'text.colon')
         and not (system['bottom'] - 1 <= g['y'] <= system['top'] + 1)],
        key=lambda p: p[0]['x'])

    if not marks:
        reach = TUPLET_REACH * system['spacing']
        for word in words:
            characters = word['text'].strip()
            if not (characters.isdigit() or characters.replace(':', '').isdigit()):
                continue
            if system['bottom'] - 1 <= word['y'] <= system['top'] + 1:
                continue
            if not (system['bottom'] - reach <= word['y']
                    <= system['top'] + reach):
                continue
            if x0 is not None and word['x'] - x0 < BAR_NUMBER_EDGE * system['spacing']:
                continue
            for offset, character in enumerate(characters):
                marks.append(({'x': word['x'] + offset * word['size'] * 0.5,
                               'y': word['y']},
                              'text.colon' if character == ':'
                              else f'digit.{character}'))
        marks.sort(key=lambda p: p[0]['x'])

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


def shape_dynamics(named, spacing):
    """Dynamics drawn as symbols rather than spelled as letters.

    MuseScore and the SMuFL fonts engrave a dynamic as one glyph per letter,
    and those glyphs spell nothing at all -- so the text reader, which is what
    catches Sibelius and Finale, sees no dynamic on a third of the catalogue.
    Here the letters come back from the shape vocabulary instead and are
    joined in the order they were set.

    Joined, and then matched against the closed set whole. A lone p from a
    vocabulary is worth no more than a lone p from a font: only "mf", "ff",
    "sfz" and their kin are a dynamic, and anything else assembled here is
    dropped rather than approximated.
    """
    letters = sorted(
        [(g['x'], s.split('.')[1]) for g, s in named
         if s and s.startswith('dynamic.')],
        key=lambda pair: pair[0])
    if not letters:
        return []

    out, current = [], None
    for x, letter in letters:
        if current and x - current['x1'] <= spacing * 1.2:
            current['text'] += letter
            current['x1'] = x
        else:
            if current:
                out.append(current)
            current = {'x': x, 'x1': x, 'text': letter}
    if current:
        out.append(current)

    return [{'x': item['x'], 'level': text.DYNAMICS[item['text'].lower()]}
            for item in out if item['text'].lower() in text.DYNAMICS]


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


def decorate(events, named, onsets):
    """Hang articulations on the note they sit above or below.

    Proximity is the only available evidence -- a PDF says where a mark was
    drawn, not what it belongs to -- so this is the one genuinely heuristic
    step, and the place where a wrong reading is least likely to be caught by
    arithmetic. Kept deliberately narrow: nearest onset, or nothing.

    The onsets are the ones reconstruction actually used, not a fresh reading
    of the bar. Rebuilding the list here counted grace noteheads as notes
    while reconstruction had folded them into the note they decorate, so in
    every bar holding a flam each accent landed one note late.
    """
    marks = [(g, s) for g, s in named
             if s in ('articulation.accent', 'articulation.marcato',
                      'tremolo.slash', 'roll.buzz')]
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


def annotate(events, onsets, marks, spacing):
    """Hang the page's words on the notes they were written under.

    Nearest onset by x, and only within half a notehead's reach. A sticking
    letter is set directly under its note -- that is what makes it readable
    at all -- so a mark that lands between two notes belongs to neither and
    is dropped. Being wrong here is quiet: a hand attached to the note next
    door teaches a sticking nobody wrote, and no arithmetic downstream would
    ever catch it.
    """
    if not onsets or not events:
        return events
    for mark in marks:
        index = min(range(len(onsets)),
                    key=lambda i: abs(onsets[i][0]['x'] - mark['x']))
        if index >= len(events):
            continue
        if abs(onsets[index][0]['x'] - mark['x']) > spacing * 1.6:
            continue
        event = events[index]
        if event.get('rest'):
            continue
        if 'hand' in mark:
            event['hand'] = mark['hand']
            # A capital is an accented stroke and a lowercase a tap, which is
            # often the only weight a passage states. The printed accent
            # still wins: it is the engraver saying so outright, where the
            # case is a convention being relied on.
            if 'accent' not in event:
                event['accent'] = 'accent' if mark['emphatic'] else 'tap'
        if 'level' in mark:
            event['dynamic'] = mark['level']
    return events


def transcribe(path, entry):
    data = ink.read(path)

    # The metre carries across pages. A signature printed once on page 1
    # governs page 2 as well, because that is what a reader does with it.
    meter = None
    bpm = None
    bars = []
    families = set()
    systems_total = 0

    known = {f: Vocabulary(f) for f in KNOWN_FAMILIES}
    attributed = {}

    for page in data['pages']:
        if bpm is None:
            bpm = text.tempo(page)
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
            chars = font.get('chars', {})
            upem = font.get('upem') or 1000
            vocab = vocabularies.get(glyph['family'])
            out = []
            for code in glyph['codes']:
                fp = codes.get(code)
                # A space draws nothing, so there is nothing to recognise and
                # nothing to report. Counted as unnamed it made a bar suspect
                # for containing a word gap -- forty-two of them on one score
                # -- which is a warning that fires on correct input, the one
                # kind this project treats as worse than no warning at all.
                if not fp and not (chars.get(code) or '').strip():
                    continue
                symbol = vocab.resolve(fp) if (fp and vocab) else None
                if fp:
                    scale = glyph['size'] / upem
                    width = fp['width'] * scale
                    middle = glyph['y'] + (fp['ymin'] + fp['height'] / 2) * scale
                else:
                    width, middle = 0.0, glyph['y']
                out.append((symbol, width, middle))
            return out

        notehead_size = _notehead_size(page, fonts, vocabularies)
        page_words = text.words(page)

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

            in_bar = [w for w in page_words
                      if bar['x0'] - 1 <= w['x'] < bar['x1'] - 1
                      and system['bottom'] - 8 * system['spacing']
                      <= w['y'] <= system['top'] + 8 * system['spacing']]

            printed = read_meter(named, system, in_bar)
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
                'notehead': notehead_size,
                'lines': len(system.get('lines') or []),
                'tuplets': tuplet_numbers(named, system, in_bar, bar['x0']),
            }
            events, unnamed, source, onsets = reconstruct(
                named, bar, meter, context)
            events = decorate(events, named, onsets)
            # The page's own words, last: they say who plays the note and how
            # loud, neither of which any other reading can recover.
            events = annotate(
                events, onsets,
                sorted(text.sticking(in_bar)
                       + text.dynamics(in_bar)
                       + shape_dynamics(named, system['spacing']),
                       key=lambda mark: mark['x']),
                system['spacing'])

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
        # Absent where the page prints none, which is most of the point: a
        # tempo invented here would be indistinguishable from one that was
        # read, and the app already plays at whatever tempo you set.
        **({'bpm': bpm} if bpm else {}),
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
