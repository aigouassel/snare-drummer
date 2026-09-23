#!/usr/bin/env python3
"""
Fetch a score by its catalogue id into work/, with the metadata beside it.

The metadata file is the point. It carries the entry straight from the
catalogue -- title, corps, circuit, year, and the URL -- so the transcription
records where it came from without anybody retyping it, and so the PDF itself
stays disposable: everything needed to find it again is in the piece.

    python3 fetch.py 2019-circus-1
    python3 fetch.py --search "blue devils 2019"
"""
import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(__file__)
CATALOGUE = os.path.join(HERE, '..', '..', 'catalogue', 'src', 'catalogue.json')
WORK = os.path.join(HERE, '..', 'work')


def catalogue():
    with open(CATALOGUE, encoding='utf-8') as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('id', nargs='?')
    ap.add_argument('--search', help='list matching entries instead of fetching')
    args = ap.parse_args()

    data = catalogue()
    entries = data['entries']

    if args.search:
        needle = args.search.lower()
        hits = [e for e in entries
                if needle in f"{e['title']} {e['corps']} {e.get('year', '')}".lower()]
        for e in hits[:40]:
            print(f"  {e['id']:<44} {e.get('year', '????')}  {e['corps']} — {e['title']}")
        print(f"{len(hits)} entrees")
        return

    if not args.id:
        ap.error('donner un id, ou --search')

    entry = next((e for e in entries if e['id'] == args.id), None)
    if entry is None:
        raise SystemExit(f"aucune entree '{args.id}' (essayer --search)")

    os.makedirs(WORK, exist_ok=True)
    pdf = os.path.join(WORK, f"{entry['id']}.pdf")
    request = urllib.request.Request(entry['url'],
                                     headers={'User-Agent': 'snare-drummer/0.1'})
    with urllib.request.urlopen(request, timeout=90) as response:
        body = response.read()
    with open(pdf, 'wb') as f:
        f.write(body)

    meta = dict(entry)
    meta['listedAt'] = data['source']
    meta['read'] = data['read']
    with open(os.path.join(WORK, f"{entry['id']}.meta.json"), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)

    print(f"{len(body):,} octets -> {pdf}")
    print(f"  {entry['corps']} — {entry['title']} ({entry.get('year', '????')})")
    print(f"  source: {entry['url']}")


if __name__ == '__main__':
    main()
