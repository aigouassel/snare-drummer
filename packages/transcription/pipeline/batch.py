#!/usr/bin/env python3
"""
Read many sequences in one pass, and write what came of each.

Transcribing one score is a thing you watch; transcribing a catalogue is a
thing you measure. So this reports per piece how many of its bars closed and
how many are flagged, and prints the totals -- which is the only way to tell
whether a change to the pipeline helped, since nobody is going to proof read
the result.

    python3 batch.py --repertoire         # each corps' most recent season
    python3 batch.py --sample 80          # a spread across the catalogue
    python3 batch.py 2019-circus-1 ...    # named sequences
    python3 batch.py --all                # everything listed

PDFs land in work/corpus/ and stay there, ignored by git. They are working
files: the piece records the URL it was read from, so the source is one click
away from the page that shows it.
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from fractions import Fraction

import transcribe

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE = os.path.join(HERE, '..', '..', 'catalogue', 'src', 'catalogue.json')
CORPUS = os.path.join(HERE, '..', 'work', 'corpus')
PIECES = os.path.join(HERE, '..', 'src', 'pieces')

# The share of a piece that must verify before it is worth shipping. Zero was
# the rule at first -- one good bar among any number -- and it let through a
# score of 118 bars holding a single playable one, which is a catalogue entry
# with a staff drawn under it rather than something anyone can practise.
#
# Measured over the 117 pieces the repertoire then held, the proportions run
# continuously up from 2.7% and that score sat alone at 0.8%, with nothing
# between. The floor is placed in that gap rather than at a round number, and
# it is a share and not a count on purpose: one good bar out of nine is a page
# a player can still use, one out of a hundred and eighteen is not.
WORKERS = max(1, (os.cpu_count() or 4) - 1)

FLOOR = 0.02


def _read(job):
    """Transcribe one score in a worker, returning either it or why not.

    An exception must come back as a value rather than kill the pool: one
    unreadable score out of a hundred is a line in the report, not a run
    thrown away.
    """
    path, entry = job
    if not isinstance(path, str):
        return None, f'telechargement: {str(path)[:40]}'
    try:
        return transcribe.transcribe(path, entry), None
    except Exception as exc:
        return None, f'{type(exc).__name__}: {str(exc)[:40]}'


def _discard(piece_id):
    """Forget a piece that no longer qualifies.

    The manifest is built from whatever `src/pieces/` happens to hold, so a
    score that stops verifying keeps its last good file and goes on being
    served. That is not hypothetical: `training-day` was played from a
    transcription older than the code that had produced it, and looked fine.
    A piece left behind is worse than one missing, because nothing says so.
    """
    stale = os.path.join(PIECES, piece_id + '.json')
    if os.path.exists(stale):
        os.remove(stale)

AGENT = 'snare-drummer/0.1'
PAUSE = 0.3          # between requests, because this is someone else's server


def sequences(repertoire=False):
    """Every sequence, carrying the work it belongs to.

    `repertoire` narrows it to each corps' most recent season, which is the
    reduction the app works from. Which season that is comes from the
    catalogue file rather than being worked out here: the same rule computed
    twice, once in TypeScript and once in Python, would drift, and both sides
    would go on producing a plausible library.
    """
    with open(CATALOGUE, encoding='utf-8') as f:
        data = json.load(f)
    works = [w for w in data['works'] if w.get('current')] if repertoire \
        else data['works']
    return data, [
        {**sequence, 'workId': work['id'], 'corps': work['corps'],
         'circuit': work['circuit'], 'listedAt': data['source'],
         'read': data['read'],
         **({'year': work['year']} if work.get('year') else {})}
        for work in works for sequence in work['sequences']
    ]


def fetch(entry):
    """The local copy of a sequence's PDF, downloading it if it is not there."""
    path = os.path.join(CORPUS, entry['id'] + '.pdf')
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    request = urllib.request.Request(entry['url'], headers={'User-Agent': AGENT})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
    except Exception as exc:
        return exc
    with open(path, 'wb') as f:
        f.write(body)
    time.sleep(PAUSE)
    return path


def score(piece):
    """How many bars of a piece are both trustworthy and worth playing.

    The trust half mirrors what @snare-drummer/core will decide once the piece
    crosses into TypeScript -- it is not the authority, which stays there,
    only a way of seeing the run.

    A bar also has to contain a stroke. A bar of rests that fills its metre
    is verified and silent, and one score here came out as 204 bars holding
    five rests and nothing else: entirely trustworthy, and nothing to practise.
    """
    playable = 0
    for bar in piece['bars']:
        if bar['unnamedSymbols'] or bar['readFrom'] != 'notation':
            continue
        if bar['meter'] is None or not bar['events']:
            continue
        if not any(not e.get('rest') for e in bar['events']):
            continue
        played = sum(Fraction(*e['duration']) for e in bar['events'])
        if played == Fraction(bar['meter'][0] * 4, bar['meter'][1]):
            playable += 1
    return playable


MANIFEST_HEAD = '''/**
 * Every transcribed sequence, as the pipeline wrote it.
 *
 * Generated by packages/transcription/pipeline/batch.py -- edit the pipeline,
 * not this file. It exists so the pieces are ordinary typed imports rather
 * than a bundler's directory glob: the package has to compile with plain tsc,
 * and a list somebody can read is worth more than one line of cleverness.
 */
'''


def manifest(ids):
    lines = [MANIFEST_HEAD]
    for i, piece in enumerate(ids):
        lines.append(f"import piece{i} from './{piece}.json' with {{ type: 'json' }}")
    lines.append('')
    lines.append('export const RAW_PIECES: readonly unknown[] = [')
    for i in range(len(ids)):
        lines.append(f'  piece{i},')
    lines.append(']')
    lines.append('')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ids', nargs='*')
    parser.add_argument('--sample', type=int, help='that many, spread at random')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--repertoire', action='store_true',
                        help="each corps' most recent season")
    parser.add_argument('--seed', type=int, default=7)
    args = parser.parse_args()

    _data, entries = sequences(repertoire=args.repertoire)
    if args.repertoire or args.all:
        chosen = entries
    elif args.sample:
        random.seed(args.seed)
        chosen = random.sample(entries, min(args.sample, len(entries)))
    elif args.ids:
        by_id = {e['id']: e for e in entries}
        missing = [i for i in args.ids if i not in by_id]
        if missing:
            raise SystemExit(f"inconnu: {', '.join(missing)}")
        chosen = [by_id[i] for i in args.ids]
    else:
        parser.error('donner des ids, --sample N, --repertoire ou --all')

    return run(chosen)


def refresh_manifest():
    """Rewrite the manifest from what `src/pieces/` actually holds.

    The app imports this list, so it is the app's view of the library. It is
    derived from the directory rather than from the run that just happened:
    a run of one score must still produce a manifest that names the other
    hundred and fifteen, and a score that has just been discarded must
    disappear from it in the same breath.
    """
    kept = sorted(os.listdir(PIECES))
    ids = [name[:-5] for name in kept if name.endswith('.json')]
    with open(os.path.join(PIECES, 'index.ts'), 'w', encoding='utf-8') as f:
        f.write(manifest(ids))
    return ids


def run(chosen):
    """Transcribe these sequences, write what verified, report the totals."""
    os.makedirs(CORPUS, exist_ok=True)
    os.makedirs(PIECES, exist_ok=True)

    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(fetch, chosen))

    # Reading a score is arithmetic, not waiting, so it needs cores and not
    # threads -- and separate processes rather than shared ones, because the
    # readers memoise font attribution per document and nothing here was
    # written to be entered twice at once. `map` keeps the order of `chosen`,
    # so a run remains reproducible and `--sample --seed` still means one
    # fixed sample.
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(_read, zip(paths, chosen)))

    written, skipped, bars_total, bars_trusted = [], [], 0, 0
    for entry, (piece, failure) in zip(chosen, results):
        if failure is not None:
            skipped.append((entry['id'], failure))
            if not failure.startswith('telechargement'):
                _discard(entry['id'])
            continue
        if not piece['bars']:
            # Nothing was read at all. A piece with no bars has nothing to
            # show and nothing to flag, so it is left out and said so.
            skipped.append((entry['id'], 'aucune mesure trouvée'))
            _discard(entry['id'])
            continue
        good = score(piece)
        if good < FLOOR * len(piece['bars']):
            # A suspect bar belongs in the app: it is shown marked, beside
            # the bars around it that can be trusted. A piece where almost
            # nothing verified has no such neighbours -- there is nothing to
            # play and nothing to compare against -- so it is left out rather
            # than shipped as a score that cannot be believed anywhere.
            skipped.append((entry['id'],
                            f"{good}/{len(piece['bars'])} mesures jouables"))
            _discard(entry['id'])
            continue
        with open(os.path.join(PIECES, entry['id'] + '.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(piece, f, ensure_ascii=False, separators=(',', ':'))
        written.append((entry['id'], good, len(piece['bars'])))
        bars_total += len(piece['bars'])
        bars_trusted += good

    ids = refresh_manifest()

    written.sort(key=lambda r: -(r[1] / r[2]))
    for piece_id, good, total in written[:10]:
        print(f"  {piece_id:<40} {good:>4}/{total:<4} mesures jouables")
    if len(written) > 10:
        print(f"  … et {len(written) - 10} autres")
    print()
    print(f"{len(written)} séquences écrites, {len(skipped)} laissées de côté")
    for piece_id, why in skipped[:8]:
        print(f"    {piece_id:<40} {why}")
    if bars_total:
        print(f"{bars_total} mesures, {bars_trusted} jouables "
              f"({100 * bars_trusted / bars_total:.1f}%)")
    print(f"{len(ids)} pièces dans src/pieces/")


if __name__ == '__main__':
    main()
