"""The listing, flattened to the sequences a reader actually works from.

Kept apart from anything that opens a PDF, so that finding out what exists
costs a single JSON read. Listing the catalogue and transcribing it are wildly
different prices, and a module that mixes them makes every caller pay the
higher one.
"""
import json

from pipeline import paths


def load():
    with open(paths.CATALOGUE, encoding='utf-8') as f:
        return json.load(f)


def sequences(repertoire=False):
    """Every sequence, carrying the work it belongs to.

    `repertoire` narrows it to each corps' most recent season, which is the
    reduction the app works from. Which season that is comes from the
    catalogue file rather than being worked out here: the same rule computed
    twice, once in TypeScript and once in Python, would drift, and both sides
    would go on producing a plausible library.
    """
    data = load()
    works = [w for w in data['works'] if w.get('current')] if repertoire \
        else data['works']
    return data, [
        {**sequence, 'workId': work['id'], 'corps': work['corps'],
         'circuit': work['circuit'], 'listedAt': data['source'],
         'read': data['read'],
         **({'year': work['year']} if work.get('year') else {})}
        for work in works for sequence in work['sequences']
    ]
