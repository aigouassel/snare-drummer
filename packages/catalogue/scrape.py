#!/usr/bin/env python3
"""
Read the transcription index off lothype.com into src/catalogue.json.

The catalogue is the cheap half of this project and it is worth having whole:
it lists every score, including the ones nothing has transcribed yet, so the
app can show what exists and link to it rather than pretending the library is
only what has been read so far.

The page is WordPress with "spoiler" shortcodes, and its structure carries
exactly the three facts worth keeping, in document order:

    <h3>DCI</h3>                                   the circuit
      <div class="su-spoiler-title">Blue Devils    the corps
        <a href=".../2019-Opener.pdf">2019 Opener Blue Devils</a>

so a single pass with a position in the hierarchy is enough; there is no
pagination and no detail page to follow.

Run it with `yarn workspace @snare-drummer/catalogue scrape`.
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, timezone, datetime

PAGE = 'https://lothype.com/transcriptions/snare-drum-transcriptions/'
OUT = os.path.join(os.path.dirname(__file__), 'src', 'catalogue.json')

# One regex, three alternatives, matched in document order: the circuit
# heading, the corps a spoiler is titled with, and a link to a PDF. Reading
# them in order is what lets a flat page describe a three-level hierarchy.
TOKEN = re.compile(
    r'<h3[^>]*>(?P<circuit>[^<]{1,60})</h3>'
    r'|<div class="su-spoiler-title"[^>]*>(?:<span[^>]*></span>)?(?P<corps>[^<]{1,80})</div>'
    r'|<a href="(?P<url>https://lothype\.com/wp-content/uploads/[^"]+\.pdf)"[^>]*>(?P<label>.*?)</a>',
    re.S,
)

CIRCUITS = {'DCI': 'DCI', 'WGI': 'WGI', 'DCA': 'DCA'}


def circuit_of(heading):
    """The catalogue's own top-level sections, mapped onto our four."""
    h = heading.strip()
    if h in CIRCUITS:
        return CIRCUITS[h]
    if 'BYOS' in h or 'Other' in h:
        return 'other'
    return None


def identifier(url, seen):
    """A stable id from the PDF's own filename.

    The filename is what the site will keep if it re-files the page, and it
    survives a title being edited. Collisions are possible -- two corps can
    both have a "2013-Opener.pdf" under different upload folders -- so the
    year folder is folded in when one occurs, rather than silently letting one
    entry overwrite another.
    """
    stem = url.rsplit('/', 1)[-1][:-4]
    slug = re.sub(r'[^a-z0-9]+', '-', html.unescape(stem).lower()).strip('-')
    if slug not in seen:
        return slug
    parts = url.split('/')
    return f"{parts[-3]}-{parts[-2]}-{slug}"


def strip_tags(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def parse(page):
    circuit = corps = None
    entries, seen = [], set()

    for m in TOKEN.finditer(page):
        if m.group('circuit'):
            c = circuit_of(m.group('circuit'))
            if c:
                circuit = c
            continue
        if m.group('corps'):
            corps = strip_tags(m.group('corps'))
            continue

        label = strip_tags(m.group('label'))
        url = m.group('url')
        if not label or circuit is None:
            # A link before any heading is furniture, not repertoire.
            continue

        # Titles read "<year> <title> <corps>"; the corps is repeated from the
        # spoiler it sits under, so drop it rather than storing it twice.
        title = label
        year = None
        ym = re.match(r'^((?:19|20)\d{2})\s+(.*)$', title)
        if ym:
            year = int(ym.group(1))
            title = ym.group(2)
        if corps and title.endswith(corps):
            title = title[: -len(corps)].strip()
        title = title.strip(' -_') or label

        ident = identifier(url, seen)
        seen.add(ident)
        entry = {
            'id': ident,
            'title': title,
            'corps': corps or 'Unknown',
            'circuit': circuit,
            'url': url,
        }
        if year is not None:
            entry['year'] = year
        entries.append(entry)

    return entries


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src and os.path.exists(src):
        page = open(src, encoding='utf-8').read()
    else:
        req = urllib.request.Request(PAGE, headers={'User-Agent': 'snare-drummer/0.1'})
        page = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')

    entries = parse(page)
    if len(entries) < 500:
        raise SystemExit(f'only {len(entries)} entries parsed; the page layout has changed')

    data = {
        'source': PAGE,
        'read': date.today().isoformat(),
        'entries': entries,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write('\n')

    circuits = {}
    for e in entries:
        circuits[e['circuit']] = circuits.get(e['circuit'], 0) + 1
    print(f"{len(entries)} entries -> {OUT}")
    print('  ' + '  '.join(f'{k}:{v}' for k, v in sorted(circuits.items())))
    print(f"  {len({e['corps'] for e in entries})} distinct corps")


if __name__ == '__main__':
    main()
