#!/usr/bin/env python3
"""
What a fingerprint means, per engraving family.

The tables in vocabulary/*.json are written by looking at a contact sheet
(label.py) once per family, and they are the only place in this pipeline where
a human judgement enters. Everything else is arithmetic.

A fingerprint with no entry is *unnamed*, and that is a first-class outcome
rather than an error to swallow. An unnamed symbol found inside a bar is
counted and reported, and the bar is marked suspect. The alternative -- match
it to the nearest named symbol and move on -- is how a parser produces a score
that looks right and is wrong, which is the one failure this project has no
way to catch downstream.

Matching allows a small distance because the same symbol arrives as quadratic
curves in one score and cubic in another, so its grid can differ by a few bits.
Measured across unrelated scores, true matches sat at 0-11 bits out of 256 and
the nearest unrelated symbol at 30, so the threshold sits in a real gap rather
than at a guessed value. Aspect ratio -- computed from the raw dimensions,
sharing no arithmetic with the grid -- has to agree as well, which is what
keeps two symbols of similar outline but different proportions apart.
"""
import json
import os

from fonts import hamming

TABLE_DIR = os.path.join(os.path.dirname(__file__), 'vocabulary')

MAX_DISTANCE = 16      # bits out of 256; true matches measured at 0-11
MAX_ASPECT_DRIFT = 0.08


class Vocabulary:
    def __init__(self, family):
        self.family = family
        path = os.path.join(TABLE_DIR, f'{family.lower()}.json')
        self.known = []
        if os.path.exists(path):
            data = json.load(open(path))
            self.known = [s for s in data['symbols'] if 'symbol' in s]

    def resolve(self, fingerprint):
        """The symbol name for a fingerprint, or None if nothing matches."""
        if not self.known:
            return None
        best, best_distance = None, MAX_DISTANCE + 1
        for entry in self.known:
            if not _aspects_agree(entry['aspect'], fingerprint['aspect']):
                continue
            d = hamming(entry['bits'], fingerprint['bits'])
            if d < best_distance:
                best, best_distance = entry, d
        return best['symbol'] if best else None


# A shape only a music font has. Digits, letters and punctuation are shared
# with every text font on the page, so they cannot identify a family.
MUSICAL = {'notehead', 'rest', 'flag', 'clef', 'tremolo', 'roll'}

MIN_MATCHES = 4
MIN_SHARE = 0.4


def attribute(codes, families):
    """The family a font belongs to, judged by its shapes rather than its name.

    The name is the one thing embedding destroys. A producer that re-embeds a
    font commonly renames it -- `ODNMDG+TTE10193A0t00` is a real example from
    this catalogue -- and a family read off that name comes back as nothing,
    so every glyph the font draws is dropped and the score reports no music.
    Six documents in an eighty-score sample were unreadable for that reason
    alone.

    This project already holds that identity is the outline rather than the
    name, and the same argument settles the family: a font whose shapes are
    Maestro's *is* Maestro, whatever it is called.

    The trap is digits. Any text font has a 4 and an 8 that resemble an
    engraving font's, so matching on those alone would enrol Times-Roman as
    a music family. A match therefore has to include a shape only a music
    font carries.
    """
    best, best_score = None, 0.0
    for family, vocabulary in families.items():
        named = [vocabulary.resolve(fp) for fp in codes]
        found = [s for s in named if s]
        if len(found) < MIN_MATCHES:
            continue
        if not any(role(s) in MUSICAL for s in found):
            continue
        share = len(found) / len(named)
        if share >= MIN_SHARE and share > best_score:
            best, best_score = family, share
    return best


def _aspects_agree(a, b):
    """Whether two aspect ratios are the same ratio, measured twice.

    The allowance is proportional. Eight hundredths is the right distance
    near a ratio of one, where most symbols live, and is meaningless at a
    ratio of seven and a half: a ledger line measured at 7.70 against 7.61
    differs by one percent and was being rejected as a different symbol,
    which left two hundred of them unnamed on one score.
    """
    return abs(a - b) <= MAX_ASPECT_DRIFT * max(1.0, (a + b) / 2)


def role(symbol):
    """The part a symbol plays, which is what the reconstruction branches on."""
    if symbol is None:
        return 'unnamed'
    return symbol.split('.')[0]


# Symbols that occupy the staff without affecting rhythm. Naming them is what
# stops a dynamic marking from making an otherwise sound bar suspect.
INERT = {'dynamic', 'text', 'fermata', 'articulation', 'tremolo'}

# Symbols that place a note or a silence in time.
RHYTHMIC = {'notehead', 'rest'}
