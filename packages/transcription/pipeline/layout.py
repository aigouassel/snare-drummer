#!/usr/bin/env python3
"""
Find the page's skeleton: the staff systems, and the bars inside them.

This runs before anything tries to read music, and the order is the point.
Staff lines and barlines are stroked segments with exact coordinates -- read
off the page with no inference at all -- whereas every duration is
reconstructed. Trust should follow the evidence, so the structure is built
from what was read and the contents are placed into it afterwards. It is also
what makes a doubtful bar local: the bar exists independently of whether its
contents made sense.

Three distinctions carry the whole module, and all of them are geometric:

  * a **staff** is five evenly spaced horizontal lines *of the same extent*.
    Requiring exactly five, evenly spaced, is what stops a tie, a hairpin or
    an underlined title from being taken for a staff; requiring them to begin
    and end together is what keeps two staves printed side by side apart.

  * a **one-line staff** is how most of this repertoire is actually written,
    and it has no pattern to recognise -- a lone rule looks like an underline.
    What identifies it is what crosses it: barlines straddle it evenly and are
    all drawn to one height, where a stem hangs to one side.

  * a **barline** is a vertical segment spanning the staff's full height. A
    stem is also a vertical segment, and is roughly two thirds as tall and
    offset upward; the height test separates them without looking at a single
    glyph.

Deliberately absent: any reasoning from how wide a bar is. Engraving spaces a
bar roughly in proportion to what it holds, so an unusually wide bar looks like
a missed barline -- and an earlier version of this code flagged perfectly good
music on exactly that reasoning. Bar width varies legitimately with density;
it is not evidence of anything.
"""
TOLERANCE = 0.6        # coordinates closer than this are the same line
HAIRLINE = 1.0
# How far apart the ends of two rules may be and still be one rectangle's two
# edges. They are drawn from the same coordinates, so this is a rounding
# allowance rather than a real distance.
CO_EXTENT = 1.0         # a rule drawn as a thin rectangle is this thick, at most
EXTENT = 3.0           # the five lines of one staff start and end together
SYMMETRY = 0.15        # a barline straddles its staff evenly; a stem does not
# How far apart the ends of two collinear rules may be and still be one staff
# line drawn bar by bar. Measured over the 203 scores held locally: of 20 308
# pairs of collinear rules, 4 373 abut to within 0.2 points and the next
# nearest pair anywhere is 2.55 points away. Nothing at all falls between.
# The number below sits in that empty band rather than at a guessed value.
ABUTTING = 1.0


def horizontals(segments, min_length):
    out = []
    for s in segments:
        if abs(s['y1'] - s['y0']) < TOLERANCE and abs(s['x1'] - s['x0']) >= min_length:
            out.append((min(s['x0'], s['x1']), max(s['x0'], s['x1']),
                        (s['y0'] + s['y1']) / 2))
    return out


def verticals(segments):
    out = []
    for s in segments:
        if abs(s['x1'] - s['x0']) < TOLERANCE and abs(s['y1'] - s['y0']) > TOLERANCE:
            out.append(((s['x0'] + s['x1']) / 2,
                        min(s['y0'], s['y1']), max(s['y0'], s['y1'])))
    return out


def cluster(values, tolerance):
    """Group near-equal values; returns one representative per group."""
    groups = []
    for v in sorted(values):
        if groups and v - groups[-1][-1] <= tolerance:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [sum(g) / len(g) for g in groups]


def rules(segments, min_length):
    """Horizontal rules on the page, with the two edges of a thin one merged.

    A staff line reaches this module in one of two ways. Most engravers stroke
    it, and it arrives as a single segment at a single y. Others fill a very
    thin rectangle, and it arrives as two segments a fraction of a point
    apart -- so a five-line staff presents as ten lines, the five-line test
    below never fires, and the page reports no staves at all. Merging the two
    edges of a hairline here is what makes the two cases indistinguishable
    further up.

    Rules merge only when they run between the same two x, not merely when
    they overlap. Two edges of one filled rectangle are exactly co-extent by
    construction, and nothing else on a page is: a beam drawn three quarters
    of a point above a staff line overlaps it completely and is sixty points
    long against five hundred. Merging on overlap alone swallowed the top line
    of a staff into the beams above it and moved it off the even spacing, so
    the five-line test failed and the whole system was read as a one-line
    percussion staff -- which made every stem on it look like a barline and
    cut a twelve-note bar into twelve bars of one note.

    Two staves printed side by side sit at the same y and must also stay two
    rules, which co-extent settles for the same reason.
    """
    out = []
    for x0, x1, y in horizontals(segments, min_length):
        for rule in out:
            if (abs(rule['y'] - y) <= HAIRLINE
                    and abs(rule['x0'] - x0) <= CO_EXTENT
                    and abs(rule['x1'] - x1) <= CO_EXTENT):
                rule['x0'] = min(rule['x0'], x0)
                rule['x1'] = max(rule['x1'], x1)
                rule['y'] = (rule['y'] + y) / 2
                break
        else:
            out.append({'y': y, 'x0': x0, 'x1': x1})
    return _stitch(out)


def _stitch(found):
    """Rejoin a staff line that was drawn one segment per bar.

    A quarter of the scores here engrave the rule of a one-line staff as a
    run of abutting segments -- one per bar -- rather than as one line, and
    the page looks identical either way. Read unjoined, each segment is put
    to the one-line test as if it were a whole staff, and the two guards that
    test applies are both true of a staff and false of a single bar of one:
    the leftmost segment carries the head of the staff, whose double barline
    crosses at half the height of the rest, and a lone bar is 74 to 91 points
    wide against a floor of ten staff spaces. So the head of every staff was
    discarded -- with its metre, and with its bars. One page printing about
    thirty-five bars yielded sixteen.

    Joining is on abutment, not on overlap, for the same reason the hairline
    merge above is on co-extent: two segments of one rule are drawn from
    shared coordinates and meet to within a fifth of a point, whereas the two
    staves of a page set in columns are separated by a real gutter. Measured
    across the catalogue there is nothing whatever between the two, so this
    cannot silently fuse two neighbouring staves into one -- which would be a
    worse fault than the one it repairs, since it would read music across a
    line break that was never played that way.
    """
    out = []
    for rule in sorted(found, key=lambda r: r['x0']):
        for chain in out:
            if (abs(chain['y'] - rule['y']) <= TOLERANCE
                    and abs(rule['x0'] - chain['x1']) <= ABUTTING):
                chain['x1'] = max(chain['x1'], rule['x1'])
                break
        else:
            out.append(dict(rule))
    return out


def _crossings(rule, columns):
    """The verticals that cross a rule the way a barline crosses a staff.

    On a one-line percussion staff -- which is how most of this repertoire is
    written -- there is no five-line pattern to recognise, and a lone rule
    looks exactly like an underline or a hairpin. What distinguishes it is
    what crosses it: a barline straddles the line evenly and every barline on
    a staff is drawn to the same height, whereas a stem hangs to one side.
    Measured on real pages, barlines came out 12.27 above and 12.27 below to
    the hundredth of a point, and the stems beside them 2.32 above and 16.59
    below.
    """
    even = []
    for x, y0, y1 in columns:
        if not (rule['x0'] - 2 <= x <= rule['x1'] + 2):
            continue
        if not (y0 < rule['y'] < y1):
            continue
        above, below = y1 - rule['y'], rule['y'] - y0
        height = y1 - y0
        if abs(above - below) <= SYMMETRY * height:
            even.append((x, height))
    return even


def _barlines_among(even):
    """The crossings that are barlines, out of everything that straddles a rule.

    The height test below wants one height and one only, and on most pages it
    gets it. It does not on a page that prints a percussion clef: the clef is
    two thick strokes, arrives as four edges each about a space tall, and sits
    on the line as evenly as any barline. Read as barlines those four make the
    heights disagree, and the whole staff -- metre, bars and all -- is thrown
    away for carrying a clef.

    They are told apart by where they sit rather than by how tall they are. A
    clef is four verticals inside seven points; barlines are a bar apart. This
    is not the width reasoning the module refuses elsewhere: nothing here
    concludes anything from how wide a bar is, only that four strokes closer
    together than a single staff space cannot be four bars -- which is the
    same thing `bars` already says when it declines to open a bar between the
    two strokes of a double barline.

    So the crossings are grouped by height, and each group's positions are
    then clustered at that same 1.2 spaces, so that strokes too close to have
    a bar between them count once. A group that still leaves two marks is a
    set of barlines; a clef collapses to one and drops out. Where exactly one
    group survives it is taken; where several do the rule is left alone,
    because the reading is then genuinely ambiguous, and a silent choice
    between two of them is how a wrong staff gets built.

    A single height is returned untouched, and that restraint is the point.
    Applied to a rule that already agrees with itself, the mark test rejects
    correct music: the last system of a piece may carry no barline at all
    until its closing double bar, whose two strokes are four points apart and
    collapse to one mark. One score lost its final staff that way. So this
    only ever speaks where the test below would otherwise refuse the rule
    outright, and never overrules an answer that test could reach on its own.
    """
    groups = []
    for x, height in sorted(even, key=lambda e: e[1]):
        for group in groups:
            if abs(height - group[0][1]) <= 0.05 * height:
                group.append((x, height))
                break
        else:
            groups.append([(x, height)])
    if len(groups) <= 1:
        return even

    kept = []
    for group in groups:
        height = sorted(h for _, h in group)[len(group) // 2]
        # `bars` uses the same 1.2 spaces to refuse to open a bar between the
        # two strokes of a double barline; a clef falls under it as squarely.
        marks = cluster([x for x, _ in group], 1.2 * (height / 2))
        if len(marks) >= 2:
            kept.append(group)
    return kept[0] if len(kept) == 1 else None


def _single_line(rule, columns):
    """A one-line staff, or None.

    The staff's spacing has to be inferred, since there is no second line to
    measure it against, and the barline is the only thing here to infer it
    from: it is taken to be drawn one space above the line and one below.

    That is a guess, and on most of this catalogue it is wrong by a factor of
    two -- Maestro and BroadwayCopyist draw the barline of a one-line staff
    the full height of a five-line one. It was generalised from two Opus
    scores, where it happens to hold. The number below is therefore only a
    starting point: transcribe.py measures the noteheads actually drawn on
    the system and rescales, a notehead being exactly one space tall in every
    engraving font. The barline's own extent, which is measured rather than
    guessed, stays as the staff's top and bottom.
    """
    barlines = _barlines_among(_crossings(rule, columns))
    if barlines is None or len(barlines) < 2:
        return None
    even = [h for _, h in barlines]
    height = sorted(even)[len(even) // 2]
    # Every barline of one staff is the same height. A spread means these are
    # not barlines.
    if max(even) - min(even) > 0.05 * height:
        return None
    spacing = height / 2
    if not (2 < spacing < 40) or (rule['x1'] - rule['x0']) < spacing * 10:
        return None
    return {
        'lines': [rule['y']],
        'bottom': rule['y'] - spacing,
        'top': rule['y'] + spacing,
        'spacing': spacing,
        'x0': rule['x0'],
        'x1': rule['x1'],
    }


def find_systems(segments, page_width):
    """Every five-line staff on the page, in reading order.

    A staff is five rules that are evenly spaced *and co-extensive*: they
    begin and end together, because they are drawn as one object. Co-extent
    is the stronger of the two tests and it replaces an earlier rule that a
    staff line had to run a quarter of the page width. That proxy holds for a
    portrait page with one staff per system and fails on everything else --
    on a landscape page carrying two columns of music, the real staff lines
    measure a fifth of the width and were all discarded, silently.
    """
    candidates = [r for r in rules(segments, min_length=max(page_width * 0.05, 20))]

    # Lines belonging to one staff share their extent; lines of a staff
    # printed alongside do not.
    groups = []
    for rule in sorted(candidates, key=lambda r: (r['x0'], r['x1'])):
        for group in groups:
            if (abs(group[0]['x0'] - rule['x0']) <= EXTENT
                    and abs(group[0]['x1'] - rule['x1']) <= EXTENT):
                group.append(rule)
                break
        else:
            groups.append([rule])

    systems = []
    for group in groups:
        ys = sorted(r['y'] for r in group)
        i = 0
        while i + 4 < len(ys):
            window = ys[i:i + 5]
            gaps = [window[k + 1] - window[k] for k in range(4)]
            spacing = sum(gaps) / 4
            span = group[0]['x1'] - group[0]['x0']
            if (max(gaps) - min(gaps) < TOLERANCE and 2 < gaps[0] < 40
                    and span >= spacing * 6):
                systems.append({
                    'lines': window,
                    'bottom': window[0],
                    'top': window[-1],
                    'spacing': spacing,
                    'x0': min(r['x0'] for r in group),
                    'x1': max(r['x1'] for r in group),
                })
                i += 5
            else:
                i += 1

    spoken_for = {round(y, 1) for s in systems for y in s['lines']}
    columns = verticals(segments)
    for rule in candidates:
        if round(rule['y'], 1) in spoken_for:
            continue
        found = _single_line(rule, columns)
        if found:
            systems.append(found)

    # Reading order: down the page, then left to right across a page that
    # sets its music in columns.
    systems.sort(key=lambda s: (-round(s['top'], 0), s['x0']))
    return systems


def find_barlines(segments, system):
    height = system['top'] - system['bottom']
    found = []
    for x, y0, y1 in verticals(segments):
        if not (system['x0'] - 2 <= x <= system['x1'] + 2):
            continue
        spans_staff = (abs(y0 - system['bottom']) < 2.5
                       and abs(y1 - system['top']) < 2.5
                       and (y1 - y0) >= height - TOLERANCE)
        if spans_staff:
            found.append(x)
    return cluster(found, 1.5)


def principal_staves(systems, segments):
    """Drop the lower staff of every system written on more than one.

    A few of these transcriptions put two snare parts on two staves braced
    together, with the barlines running through both. Read as ordinary
    systems they come out one after the other, so the piece alternates
    between two parts that were meant to sound at once -- music that was
    never written, played back with no sign that anything is wrong.

    What identifies a brace is a barline that spans both staves: a system's
    own barlines stop at its own top and bottom. Only the top staff is kept,
    which is a choice rather than a reading -- the second part is not read at
    all, and the app says a piece is a snare part.

    The test is narrow enough to act on wherever it fires. A barline through
    a braced pair runs from the lower staff's bottom line to the upper
    staff's top and stops there, inside the staff's own horizontal extent;
    across two hundred scores it fires ten times, on five, and every one
    checked is a real brace. Requiring it to be systematic first was wrong:
    these scores mix braced pairs with single staves, so it never was.
    """
    columns = verticals(segments)
    order = sorted(range(len(systems)), key=lambda i: -systems[i]['top'])
    lower = set()
    # Adjacent staves only. A brace joins the staves of one system, which are
    # neighbours by definition; a vertical reaching from the top of a page to
    # the bottom is a margin rule or a bracket around the whole score, and
    # pairing across it would drop most of the page.
    for above, below in zip(order, order[1:]):
        upper, under = systems[above], systems[below]
        if under['top'] >= upper['bottom']:
            continue
        if not (upper['x0'] < under['x1'] and under['x0'] < upper['x1']):
            continue
        # Spanning both, and not much more: a barline through a braced pair
        # reaches from the lower staff's bottom line to the upper staff's
        # top, give or take a rounding, and stops there.
        margin = (upper['top'] - upper['bottom']) or 1.0
        for x, y0, y1 in columns:
            if (y0 <= under['bottom'] + 1 and y1 >= upper['top'] - 1
                    and y0 >= under['bottom'] - margin
                    and y1 <= upper['top'] + margin
                    and upper['x0'] - 2 <= x <= upper['x1'] + 2):
                lower.add(below)
                break
    return [s for i, s in enumerate(systems) if i not in lower]


def bars(segments):
    """Every bar on the page, numbered in reading order."""
    xs = [v for s in segments for v in (s['x0'], s['x1'])]
    page_width = (max(xs) - min(xs)) if xs else 0
    systems = principal_staves(find_systems(segments, page_width), segments)

    out, n = [], 0
    for index, system in enumerate(systems):
        edges = cluster([system['x0']] + find_barlines(segments, system) + [system['x1']],
                        tolerance=2.5)
        for left, right in zip(edges, edges[1:]):
            # A gap narrower than the staff is a double barline or a repeat
            # sign's two strokes, not a bar.
            if right - left < system['spacing'] * 1.2:
                continue
            n += 1
            out.append({
                'n': n,
                'system': index,
                'x0': round(left, 2),
                'x1': round(right, 2),
                'bottom': round(system['bottom'], 2),
                'top': round(system['top'], 2),
                'spacing': round(system['spacing'], 3),
            })
    return systems, out


def staff_position(system, y):
    """How far above the bottom staff line, in half-spaces.

    On a five-line percussion staff this is what distinguishes a notehead on
    the third space from one sitting above the staff -- which is how these
    scores write a rimshot or a cross-stick.
    """
    return round((y - system['bottom']) / (system['spacing'] / 2), 2)


if __name__ == '__main__':
    import sys, json
    data = json.load(open(sys.argv[1]))
    systems, found = bars(data['segments'])
    print(f"{len(systems)} systemes, {len(found)} mesures")
    for i, s in enumerate(systems):
        mine = [b for b in found if b['system'] == i]
        print(f"  systeme {i}: y={s['top']:8.2f} interligne={s['spacing']:5.2f} "
              f"mesures={[b['n'] for b in mine]}")


# A multi-bar rest is a thick horizontal bar centred on the staff, with the
# number of bars it stands for printed above it. These are the proportions it
# is recognised by, measured on the scores that use them.
MULTI_REST_SPAN = 0.5      # of the bar's width, at least
MULTI_REST_THICK = 0.3     # of a staff space, at least
MULTI_REST_CENTRED = 0.6   # spaces from the middle line, at most


def multi_rest(segments, bar, system):
    """Whether a bar holds a multi-bar rest, and how thick the bar is drawn.

    A multi-bar rest is not an empty bar and not a long one: it is *several*
    bars printed in one place, and a reader counts them off. Read as one bar
    it loses the others -- and every bar after it in the piece is then
    numbered wrong, which matters here more than in most projects, because the
    bar number is how a passage is addressed.

    What identifies it is a thick horizontal bar spanning most of the measure
    and centred on the middle line. A staff line is thin and runs the whole
    system; a beam is short and sits off the staff; a repeat sign is a slash
    with dots. Nothing else on these pages is a long thick horizontal centred
    on the staff.
    """
    middle = (system['bottom'] + system['top']) / 2
    width = bar['x1'] - bar['x0']
    spacing = system['spacing'] or 1.0
    edges = []
    for x0, x1, y in horizontals(segments, width * MULTI_REST_SPAN):
        if x0 < bar['x0'] - 1 or x1 > bar['x1'] + 1:
            continue
        if abs(y - middle) > MULTI_REST_CENTRED * spacing:
            continue
        edges.append(y)
    if len(edges) < 2:
        return False
    return (max(edges) - min(edges)) >= MULTI_REST_THICK * spacing
