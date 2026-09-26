"""List what the catalogue holds, and show one score in detail.

A listing must not invent. How a score is engraved is a property of its PDF,
known for free once the score is transcribed -- it is recorded in the piece --
and otherwise not known at all. Rather than open a hundred and twenty-eight
files to fill a column, the listing leaves it blank, says how many it could not
tell, and `--probe` is there for when you do want them read."""
import json
import os

from pipeline import paths, transcribe as transcriber
from pipeline.run import batch

WIDTH = 42


def _shipped():
    """What `src/pieces/` holds, by sequence id: families, bars, playable."""
    out = {}
    if not os.path.isdir(batch.PIECES):
        return out
    for name in sorted(os.listdir(batch.PIECES)):
        if not name.endswith('.json'):
            continue
        with open(os.path.join(batch.PIECES, name), encoding='utf-8') as f:
            piece = json.load(f)
        out[name[:-5]] = {
            'families': piece.get('extraction', {}).get('families', []),
            'drawn': piece.get('extraction', {}).get('pagesDrawn', 0),
            'bars': len(piece['bars']),
            'good': batch.score(piece),
        }
    return out


def _probe(entry):
    """Read a not-shipped score far enough to name its engraving family.

    There is no cheaper honest answer: the family is decided by matching the
    outlines a page draws against the named vocabularies, which is most of the
    reading. The PDF must already be in the corpus -- this will not fetch, so
    that a listing never turns into a download.
    """
    path = os.path.join(batch.CORPUS, entry['id'] + '.pdf')
    if not os.path.exists(path):
        return None
    try:
        piece = transcriber.transcribe(path, entry)
    except Exception:
        return None
    return {
        'families': piece.get('extraction', {}).get('families', []),
        'drawn': piece.get('extraction', {}).get('pagesDrawn', 0),
        'bars': len(piece['bars']),
        'good': batch.score(piece),
    }


def _format(info):
    """How a score is engraved, as one short column."""
    if info is None:
        return '?'
    names = info['families'] or ['—']
    return ('+'.join(names) + (' tracé' if info['drawn'] else ''))[:24]


def do_list(args):
    _data, entries = batch.sequences(repertoire=args.repertoire)
    shipped = _shipped()
    rows = []

    for entry in entries:
        info = shipped.get(entry['id'])
        if info is None and args.probe:
            info = _probe(entry)
        is_shipped = entry['id'] in shipped
        if args.held and is_shipped:
            continue
        if args.shipped and not is_shipped:
            continue
        if args.family:
            names = [n.lower() for n in (info or {}).get('families', [])]
            if args.family.lower() not in names:
                continue
        rows.append((entry, info, is_shipped))

    for entry, info, is_shipped in rows:
        mark = '·' if is_shipped else ' '
        if info and info['bars']:
            tally = f"{info['good']:>4}/{info['bars']:<4}"
        else:
            tally = '       —'
        print(f"{mark} {entry['id'][:WIDTH]:<{WIDTH}} {tally}  {_format(info)}")

    print()
    kept = sum(1 for _e, _i, s in rows if s)
    print(f"{len(rows)} séquences · {kept} livrées · "
          f"{len(rows) - kept} non livrées")
    # Counted over what was printed, not over the catalogue: a count that
    # answers a question nobody asked is how a listing starts lying.
    unknown = sum(1 for _e, i, _s in rows if i is None)
    if unknown and not args.probe:
        print(f"{unknown} dont la gravure n'est pas connue sans la lire "
              f"— `--probe` les lit")
    print("  · = livrée · les deux nombres sont mesures jouables / mesures")


def do_show(args):
    _data, entries = batch.sequences()
    entry = next((e for e in entries if e['id'] == args.id), None)
    if entry is None:
        raise SystemExit(f"inconnu: {args.id}")

    path = os.path.join(batch.PIECES, args.id + '.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            piece = json.load(f)
        state = 'livrée'
    else:
        pdf = os.path.join(batch.CORPUS, args.id + '.pdf')
        if not os.path.exists(pdf):
            raise SystemExit(f"{args.id}: pas dans le corpus, "
                             f"`transcribe {args.id}` la télécharge")
        piece = transcriber.transcribe(pdf, entry)
        state = 'non livrée'

    bars = piece['bars']
    good = batch.score(piece)
    extraction = piece.get('extraction', {})
    print(f"{args.id} — {state}")
    print(f"  {entry.get('corps', '?')} · {entry.get('year', '?')}")
    print(f"  gravure     {_format({'families': extraction.get('families', []),
                                    'drawn': extraction.get('pagesDrawn', 0)})}")
    print(f"  mesures     {len(bars)}, dont {good} jouables")
    print(f"  source      {entry.get('url', '—')}")

    # The same seven reasons `held.py` groups by, so that one score's account
    # and the catalogue's cannot disagree about the same bar.
    from collections import Counter
    from fractions import Fraction
    counts = Counter()
    for bar in bars:
        if bar['meter'] is None:
            counts['sans métrique'] += 1
        elif not bar['events']:
            counts['vide'] += 1
        elif bar['unnamedSymbols']:
            counts['symbole inconnu'] += 1
        elif bar['readFrom'] != 'notation':
            counts["lue à l'espacement"] += 1
        else:
            played = sum(Fraction(*e['duration']) for e in bar['events'])
            whole = Fraction(bar['meter'][0] * 4, bar['meter'][1])
            if played != whole:
                counts['somme fausse'] += 1
            elif any(not e.get('rest') for e in bar['events']):
                counts['jouable'] += 1
            else:
                counts['que des silences'] += 1
    print()
    for reason, n in counts.most_common():
        print(f"  {n:>5}  {reason}")
