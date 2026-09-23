#!/usr/bin/env python3
"""
Read a note's length from how it is written.

Until now duration came from *horizontal spacing*: engraving lays notes out
roughly in proportion to their length, so the gaps between noteheads give
their relative durations. It is a real signal and it was never better than
approximate -- engravers compress dense passages, stretch sparse ones, and
pad a bar's last note to the barline -- so bars that were read correctly and
bars that were not looked identical until the arithmetic ran.

What an engraver actually states is the beaming. A sixteenth note is a
notehead with a stem carrying two beams, and both the stem and the beams are
in the content stream as exact coordinates. That is a statement, not an
inference, and it is what this module reads:

    stem            a vertical segment rising or falling from the notehead
    beams           filled horizontal bars crossing the stem
    flags           a glyph at the stem's tip, for a note that stands alone
    augmentation    a dot to the right of the notehead, at its own height

A note whose stem cannot be found returns nothing rather than a guess. The
caller falls back to spacing for that bar and the bar says so, which keeps
the failure visible instead of turning it into a plausible wrong length.
"""
from fractions import Fraction

# A stemmed notehead with nothing on its stem is a quarter; each beam or flag
# halves it. Lengths are in quarter-note beats, like everything else here.
QUARTER = Fraction(1)

# How tall a stem is, in staff spaces. Below the first it is a tie or a hook;
# above the second it is a barline or a bracket.
STEM_MIN = 1.6
STEM_MAX = 6.5

BEAM_MIN_LENGTH = 0.8      # spaces; shorter than this is a stub, still a beam
BEAM_MAX_THICKNESS = 0.9   # spaces; a beam is about half a space
NEAR_STEM = 0.35           # spaces; how far a stem may sit from a head's edge
DOT_REACH = 2.2            # spaces to the right of a notehead
DOT_LEVEL = 0.6            # spaces; a dot further off in y is a staccato

# A grace notehead is engraved at cue size. Measured across the catalogue the
# two populations sit at 1.37 and 0.82 spaces wide, or 1.28 and 0.77 -- always
# about three fifths -- with nothing in between, so the threshold falls in a
# gap rather than at a guess.
GRACE_RATIO = 0.8


def beams(segments, spacing):
    """The beams on a page, each as the span it covers.

    A beam is filled, not stroked -- it is a quadrilateral the engraver fills,
    where a staff line is a line it strokes -- and it reaches this module as
    its two long edges. Pairing the edges back into one beam is what keeps a
    single beam from being counted twice.
    """
    edges = []
    for s in segments:
        if not s['fill']:
            continue
        dx, dy = abs(s['x1'] - s['x0']), abs(s['y1'] - s['y0'])
        if dx < BEAM_MIN_LENGTH * spacing or dy > 0.5 * dx:
            continue
        edges.append((min(s['x0'], s['x1']), max(s['x0'], s['x1']),
                      (s['y0'] + s['y1']) / 2))

    found, used = [], set()
    for i, (x0, x1, y) in enumerate(edges):
        if i in used:
            continue
        for j in range(i + 1, len(edges)):
            if j in used:
                continue
            a0, a1, b = edges[j]
            if (abs(a0 - x0) < 0.4 * spacing and abs(a1 - x1) < 0.4 * spacing
                    and 0 < abs(b - y) <= BEAM_MAX_THICKNESS * spacing):
                used.update((i, j))
                found.append({'x0': x0, 'x1': x1, 'y': (y + b) / 2})
                break
        else:
            # An unpaired edge is a beam drawn some other way, not nothing.
            found.append({'x0': x0, 'x1': x1, 'y': y})
    return found


def stems(segments, spacing):
    """Vertical segments of about the height a stem has."""
    out = []
    for s in segments:
        if abs(s['x1'] - s['x0']) > 0.25 * spacing:
            continue
        y0, y1 = sorted((s['y0'], s['y1']))
        height = (y1 - y0) / spacing
        if STEM_MIN <= height <= STEM_MAX:
            out.append({'x': (s['x0'] + s['x1']) / 2, 'y0': y0, 'y1': y1})
    return out


def stem_of(x, width, y, candidates, spacing):
    """The stem belonging to a notehead whose ink starts at x and runs `width`.

    A stem is drawn at one edge of the notehead and not through its middle:
    up at the right edge, down at the left. Searching near the origin alone
    misses every up-stem by a full notehead -- measured at 1.34 spaces on the
    reference piece -- and widening the search until it hits instead picks up
    the neighbouring note's stem, since consecutive notes are only two and a
    half spaces apart. Both edges, narrowly, is the only version that is
    right for the right reason.
    """
    reach = NEAR_STEM * spacing
    best, best_gap = None, reach
    for stem in candidates:
        gap = min(abs(stem['x'] - x), abs(stem['x'] - (x + width)))
        if gap > best_gap:
            continue
        if not (stem['y0'] - 0.6 * spacing <= y <= stem['y1'] + 0.6 * spacing):
            continue
        best, best_gap = stem, gap
    return best


def on_stem(stem, page_beams, spacing):
    """How many beams cross a stem."""
    return sum(1 for b in page_beams
               if b['x0'] - 0.3 * spacing <= stem['x'] <= b['x1'] + 0.3 * spacing
               and stem['y0'] - 0.3 * spacing <= b['y'] <= stem['y1'] + 0.3 * spacing)


def dots(x, y, marks, spacing):
    """Augmentation dots: to the right of the notehead, at its own height.

    A staccato dot is the same glyph and sits a space or more above or below,
    which is the whole difference between a note half again as long and a
    note played short.
    """
    return sum(1 for mx, my in marks
               if 0 < mx - x <= DOT_REACH * spacing
               and abs(my - y) <= DOT_LEVEL * spacing)


HALVES = {'flag.eighth': 1, 'flag.sixteenth': 2, 'flag.thirtysecond': 3}

STEMLESS = {'notehead.whole': Fraction(4), 'notehead.half': Fraction(2)}

RESTS = {
    'rest.quarter': Fraction(1),
    'rest.eighth': Fraction(1, 2),
    'rest.sixteenth': Fraction(1, 4),
    'rest.thirtysecond': Fraction(1, 8),
    'rest.half': Fraction(2),
    'rest.whole': Fraction(4),
}


def is_grace(width, full):
    """Whether a notehead was engraved at cue size.

    This matters more here than in most repertoires. A flam is a grace note
    and a snare part is full of them, and a grace note read as a real one
    does not break anything visibly -- it just makes the bar longer than its
    metre, which is indistinguishable from a duration misread. The two sizes
    are far apart and nothing is engraved between them.
    """
    return bool(full) and width > 0 and width < GRACE_RATIO * full


def dotted(length, count):
    """A dot adds half of what precedes it, and a second dot half of that."""
    total, add = length, length
    for _ in range(count):
        add /= 2
        total += add
    return total


def written(symbol, x, y, width, context):
    """The length an engraver wrote for one note or rest, or None.

    None is a real answer and the important one: it means this module could
    not read the notation, and the caller must not be handed a number that
    looks like it came from somewhere.
    """
    spacing = context['spacing']
    if symbol in RESTS:
        return RESTS[symbol]
    if symbol == 'rest.rectangle':
        # One glyph serves as both whole and half rest in some families; the
        # engraver tells them apart by hanging one under the fourth line and
        # sitting the other on the third.
        return Fraction(4) if y > context['middle'] else Fraction(2)
    if symbol in STEMLESS:
        return STEMLESS[symbol]

    stem = stem_of(x, width, y, context['stems'], spacing)
    if stem is None:
        return None

    halves = on_stem(stem, context['beams'], spacing)
    for flag, count in context['flags']:
        if abs(flag - stem['x']) <= NEAR_STEM * spacing:
            halves = max(halves, count)

    length = QUARTER / (2 ** halves)
    return dotted(length, dots(x, y, context['dots'], spacing))


# How many notes a tuplet number stands in the time of, when the engraver
# prints only the count. Three in the time of two, five in the time of four:
# the convention is the largest power of two below the number, and the two
# inverted forms are duplets in compound time.
IN_THE = {2: 3, 3: 2, 4: 3, 5: 4, 6: 4, 7: 4, 9: 8, 10: 8, 11: 8, 13: 8}


def tuplet_groups(numbers, onsets, spacing):
    """Which notes each tuplet number governs, and by what ratio.

    A tuplet number is printed over the group it applies to, so the group is
    the run of notes it sits over: the `count` consecutive onsets whose span
    is centred nearest the number. Nothing else on the page states the extent
    -- a bracket does when there is one, and beamed tuplets, which is most of
    them here, have no bracket at all.

    A number that cannot be matched to a run of the right length is dropped
    rather than applied to a guess, and the bar then fails to close, which is
    the outcome this project prefers to a plausible one.
    """
    groups = []
    centres = [g['x'] for g, _ in onsets]
    for x, count, inthe in numbers:
        if count < 2 or count > len(centres):
            continue
        best, best_gap = None, None
        for start in range(len(centres) - count + 1):
            run = centres[start:start + count]
            gap = abs((run[0] + run[-1]) / 2 - x)
            if best_gap is None or gap < best_gap:
                best, best_gap = start, gap
        if best is None or best_gap > spacing * 12:
            continue
        groups.append((best, best + count, Fraction(inthe, count)))
    return groups
