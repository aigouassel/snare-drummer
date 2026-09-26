"""Counting a transcription that has already been read.

This is arithmetic over a piece that is on disk, and it imports nothing that
reads a PDF -- which is what lets `pipeline.cli list` report the state of the
repertoire without the reading half of the package being installed at all.
"""
from fractions import Fraction


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
