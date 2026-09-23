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

Two distinctions carry the whole module, and both are geometric:

  * a **staff** is five evenly spaced horizontal lines of the same extent.
    Requiring exactly five, evenly spaced, is what stops a tie, a hairpin or
    an underlined title from being taken for a staff.

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


def find_systems(segments, page_width):
    lines = {}
    for x0, x1, y in horizontals(segments, min_length=page_width * 0.25):
        lines.setdefault(round(y, 1), []).append((x0, x1))

    ys = sorted(lines)
    systems, i = [], 0
    while i + 4 < len(ys):
        window = ys[i:i + 5]
        gaps = [window[k + 1] - window[k] for k in range(4)]
        if max(gaps) - min(gaps) < TOLERANCE and 2 < gaps[0] < 40:
            spans = [span for y in window for span in lines[y]]
            systems.append({
                'lines': window,
                'bottom': window[0],
                'top': window[-1],
                'spacing': sum(gaps) / 4,
                'x0': min(s[0] for s in spans),
                'x1': max(s[1] for s in spans),
            })
            i += 5
        else:
            i += 1

    systems.sort(key=lambda s: -s['top'])      # reading order, down the page
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
