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
            even.append(height)
    return even


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
    even = _crossings(rule, columns)
    if len(even) < 2:
        return None
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


def bars(segments):
    """Every bar on the page, numbered in reading order."""
    xs = [v for s in segments for v in (s['x0'], s['x1'])]
    page_width = (max(xs) - min(xs)) if xs else 0
    systems = find_systems(segments, page_width)

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
