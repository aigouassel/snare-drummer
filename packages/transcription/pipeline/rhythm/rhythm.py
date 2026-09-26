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

# A tremolo stroke -- the slash that says "roll this note" -- is filled, and
# short, and so is a beam stub. What separates them is slant.
#
# Measured over the whole corpus: of 52,188 filled horizontals long enough to
# span a run, all but 25 slant less than 0.2, so that is as steep as beaming
# gets here. Among the short ones the distribution is in two pieces -- 9,704
# level, then a near-empty band, then some eight thousand at 0.20 and above,
# with barely 130 in between. A stub belongs to a beam group and shares its
# slope, so a stub slanting more steeply than any beam does is not a stub.
#
# It is worth the trouble because of what happens otherwise. A tremolo stroke
# counted as a beam halves its note, and the bar comes up short by exactly
# that difference -- no symbol is unnamed, nothing is unread, and the bar is
# simply wrong. 6,619 of them across 47 scores.
TREMOLO_SLOPE = 0.2        # steeper than any beam this catalogue draws
TREMOLO_LENGTH = 2.5       # spaces; longer than this is a beam, however slanted
BEAM_MAX_THICKNESS = 0.9   # spaces; a beam is about half a space
NEAR_STEM = 0.35           # spaces; how far a stem may sit from a head's edge
DOT_REACH = 2.2            # spaces to the right of a notehead
DOT_LEVEL = 0.6            # spaces; a dot further off in y is a staccato

# A grace notehead is engraved at cue size, which engravers set at three
# fifths and SMuFL defines as 0.6. Measured on this catalogue as a type size:
# 14.7pt against 8.9pt on one score and 20.5 against 12.3 on another, both
# exactly 0.60, with nothing drawn in between. The threshold sits in that gap
# rather than at its edge.
GRACE_RATIO = 0.8


# How far apart two rules may be drawn and still be the two edges of one
# filled staff line, and how far apart their ends. Both are layout.py's
# allowances for the same measurement, repeated rather than imported because
# they say something about a page here and about a page there.
STAFF_LINE_LEVEL = 1.0
STAFF_LINE_EXTENT = 3.0
# A staff line drawn one segment per bar meets its neighbour to within a fifth
# of a point. layout.py measures that gap across the catalogue and stitches on
# it; the same allowance is repeated here for the same reason the two above
# are -- it says something about a page there and about a page here.
STAFF_LINE_ABUTTING = 1.0


def _staff_line_edges(edges, staves):
    """Which of these filled edges are staff lines rather than beams.

    The distinction a beam reader rests on -- filled is a beam, stroked is a
    staff line -- is a fact about typesetters, not about pages. Where a
    producer has converted the music to outlines every staff line is filled
    too, so a five-line staff offers ten more horizontal edges that pair
    cleanly into five beams running the whole width of the system. Every stem
    then crosses three or four of them, and the bar reads four times too fast
    while closing on nothing.

    What separates them is not thickness or length but *identity*: layout.py
    has already found these lines and said where they are, so a beam reader
    need not guess. An edge is dropped only when it lies at the height of a
    line of a staff and belongs to a run that reaches that staff's own two
    ends -- a beam spans a few notes, never a system.

    The run, and not the edge, is what has to reach the ends, because a page
    that outlines its staff lines may also draw each of them in pieces, one
    per bar. Testing the piece alone then matches nothing: the halves of a
    line reach one end each and neither reaches both, so every staff line on
    the page was counted as a beam and one score read eight times too fast.
    Chaining first restores exactly the guarantee the single-edge test gave,
    since a chain of beams cannot span a system either.
    """
    drop = set()
    for staff in staves:
        for line in staff.get('lines') or ():
            mine = sorted(
                (i for i, (x0, x1, y) in enumerate(edges)
                 if abs(y - line) <= STAFF_LINE_LEVEL
                 and x0 >= staff['x0'] - STAFF_LINE_EXTENT
                 and x1 <= staff['x1'] + STAFF_LINE_EXTENT),
                key=lambda i: edges[i][0])
            run, reach = [], None
            for i in mine + [None]:
                # A rule filled as a rectangle arrives as two edges at the
                # same x, so runs are unioned rather than merely abutted.
                if i is not None and (reach is None
                                      or edges[i][0] <= reach + STAFF_LINE_ABUTTING):
                    reach = edges[i][1] if reach is None else max(reach, edges[i][1])
                    run.append(i)
                    continue
                if (run and abs(edges[run[0]][0] - staff['x0']) <= STAFF_LINE_EXTENT
                        and abs(reach - staff['x1']) <= STAFF_LINE_EXTENT):
                    drop.update(run)
                if i is None:
                    break
                run, reach = [i], edges[i][1]
    return drop


def _is_tremolo(dx, dy, spacing):
    """A short filled run, slanted more steeply than beaming ever is here."""
    return dx < TREMOLO_LENGTH * spacing and dy > TREMOLO_SLOPE * dx


def tremolos(segments, spacing):
    """The tremolo strokes on a page, each as the point it crosses a stem.

    Returned rather than merely refused. A stroke dropped from the beams and
    nowhere else would make the bar close while losing the roll the page
    prints -- a score that reads as plain eighths where the engraver wrote a
    roll, correct in its arithmetic and wrong on its face. That is the one
    kind of error this project holds to be worse than an open bar.
    """
    out = []
    for s in segments:
        if not s['fill']:
            continue
        dx, dy = abs(s['x1'] - s['x0']), abs(s['y1'] - s['y0'])
        if dx < BEAM_MIN_LENGTH * spacing or dy > 0.5 * dx:
            continue
        if _is_tremolo(dx, dy, spacing):
            out.append({'x': (s['x0'] + s['x1']) / 2,
                        'y': (s['y0'] + s['y1']) / 2})
    return out


def beams(segments, spacing, staves=()):
    """The beams on a page, each as the span it covers.

    A beam is filled, not stroked -- it is a quadrilateral the engraver fills,
    where a staff line is a line it strokes -- and it reaches this module as
    its two long edges. Pairing the edges back into one beam is what keeps a
    single beam from being counted twice.

    `staves` is what layout.py read off the same page, and it is what keeps a
    drawn page's own staff lines out of the count; see `_is_staff_line`.

    Tremolo strokes are filled too, and short enough to pass for a beam stub.
    They are taken out here and read by `tremolos()` instead; leaving them in
    halved a note apiece.
    """
    edges = []
    for s in segments:
        if not s['fill']:
            continue
        dx, dy = abs(s['x1'] - s['x0']), abs(s['y1'] - s['y0'])
        if dx < BEAM_MIN_LENGTH * spacing or dy > 0.5 * dx:
            continue
        if _is_tremolo(dx, dy, spacing):
            continue
        x0, x1 = min(s['x0'], s['x1']), max(s['x0'], s['x1'])
        y = (s['y0'] + s['y1']) / 2
        edges.append((x0, x1, y))
    edges = [e for i, e in enumerate(edges)
             if i not in _staff_line_edges(edges, staves)]

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


def stem_of(x, widths, y, candidates, spacing):
    """The stem belonging to a notehead whose ink starts at x.

    A stem is drawn at one edge of the notehead and not through its middle:
    up at the right edge, down at the left. Searching near the origin alone
    misses every up-stem by a full notehead -- measured at 1.34 spaces on the
    reference piece -- and widening the search until it hits instead picks up
    the neighbouring note's stem, since consecutive notes are only two and a
    half spaces apart. Both edges, narrowly, is the only version that is right
    for the right reason.

    Which edge, though, depends on what the glyph carries. A plain head's own
    ink ends at the stem. A circled head's circle is wider and the stem is at
    *its* edge. A slashed head is wider still and the stem is not at its edge
    at all, because the stroke sticks out past it -- measured on one score the
    glyph runs 1.89 times its height against 1.31 for a plain head. So the
    caller offers every width the head might have and each is tried.
    """
    reach = NEAR_STEM * spacing
    edges = [x] + [x + w for w in widths]
    best, best_gap = None, reach
    for stem in candidates:
        gap = min(abs(stem['x'] - edge) for edge in edges)
        if gap > best_gap:
            continue
        if not (stem['y0'] - 0.6 * spacing <= y <= stem['y1'] + 0.6 * spacing):
            continue
        best, best_gap = stem, gap
    return best


def stem_direction(x, y, widths, candidates, spacing):
    """Which way the stem of this notehead points, or None if it has none.

    Read against the notehead itself and not against the staff's middle line.
    A snare staff carries one pitch, so direction there says nothing about
    where the note sits and everything about which voice it belongs to -- a
    divisi is written as one part stemmed up and the other stemmed down. The
    middle line would answer a different question and answer it wrongly for
    every note engraved away from the centre.
    """
    stem = stem_of(x, widths, y, candidates, spacing)
    if stem is None:
        return None
    return 'up' if (stem['y0'] + stem['y1']) / 2 > y else 'down'


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


def is_grace(size, full):
    """Whether a notehead was engraved at cue size.

    Judged on the type size the glyph was drawn at, not on how wide its
    outline came out. Those are different measurements and only the first is
    about scale: a cross notehead is narrower than an oval one at the same
    size, so measuring ink conflates the shape of the head with the cue. On
    one score that put a whole class of full-size noteheads at 0.79 of the
    commonest width -- just inside the threshold -- and deleted ninety-nine
    real notes from the arithmetic as ornaments.

    It matters more here than in most repertoires. A flam is a grace note and
    a snare part is full of them, and a grace note read as a real one does
    not break anything visibly: it just makes the bar longer than its metre,
    which is indistinguishable from a duration misread.
    """
    return bool(full) and size > 0 and size < GRACE_RATIO * full


def dotted(length, count):
    """A dot adds half of what precedes it, and a second dot half of that."""
    total, add = length, length
    for _ in range(count):
        add /= 2
        total += add
    return total


# Where a rectangle rest's ink sits, in spaces above the middle line, when it
# is a whole rest rather than a half. Measured across the catalogue on
# five-line staves: 0.76 for the one that hangs under the fourth line and 0.24
# for the one that sits on the third, fifty-six of each and nothing between.
RECTANGLE_SPLIT = 0.5


def written(symbol, x, y, ink_y, widths, context):
    """The length an engraver wrote for one note or rest, or None.

    None is a real answer and the important one: it means this module could
    not read the notation, and the caller must not be handed a number that
    looks like it came from somewhere.
    """
    spacing = context['spacing']
    if symbol in RESTS:
        return RESTS[symbol]
    if symbol == 'rest.rectangle':
        # One glyph serves as both whole and half rest; the engraver tells
        # them apart by hanging one under the fourth line and sitting the
        # other on the third. So the answer is in where the *ink* went, not
        # where the glyph was placed: both are placed with their origin on the
        # middle line, and comparing that origin to the middle -- which is
        # what this did -- cannot separate them at all. Whole-bar rests were
        # read as half rests throughout.
        if context.get('lines', 0) < 5:
            # A one-line staff has no fourth line to hang from, and centres
            # both on its single line: measured, the two populations sit at
            # -0.16 and +0.16 spaces, which is noise. There is nothing to
            # read here, and the caller's whole-bar rule covers the case that
            # matters -- a rest alone in its bar.
            return None
        above = (ink_y - context['middle']) / spacing
        return Fraction(4) if above > RECTANGLE_SPLIT else Fraction(2)
    if symbol in STEMLESS:
        return STEMLESS[symbol]

    stem = stem_of(x, widths, y, context['stems'], spacing)
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

    The runs are disjoint and in order, which is not a refinement but the
    whole difference between right and wrong. Chosen independently, two
    numbers in one bar can claim the same note: a bar of four triplets came
    out as runs 0-3, 3-6, 5-8 and 9-12, so one note had the ratio applied
    twice and another never got it at all. Each number therefore searches
    only from where the previous group ended.

    A number that cannot be matched to a run of the right length is dropped
    rather than applied to a guess, and the bar then fails to close, which is
    the outcome this project prefers to a plausible one.
    """
    groups = []
    centres = [g['x'] for g, _ in onsets]
    floor = 0
    for x, count, inthe in sorted(numbers):
        if count < 2 or floor + count > len(centres):
            continue
        best, best_gap = None, None
        for start in range(floor, len(centres) - count + 1):
            run = centres[start:start + count]
            gap = abs((run[0] + run[-1]) / 2 - x)
            if best_gap is None or gap < best_gap:
                best, best_gap = start, gap
        if best is None or best_gap > spacing * 12:
            continue
        groups.append((best, best + count, Fraction(inthe, count)))
        floor = best + count
    return groups
