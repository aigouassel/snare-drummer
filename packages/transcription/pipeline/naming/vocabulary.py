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
The threshold sits in a measured gap rather than at a guessed value, and the
gap moved once the grid started recording the cells an outline *passes
through* rather than the cells its samples landed in (see fonts._walk). Over
sixty scores, a glyph placed on a page now sits 0 to 6 bits from the entry
that names it -- 29 644 of 29 926 at zero -- while the nearest *different*
symbol of the same family sits at 19. Sixteen is therefore no longer the
middle of the gap but its upper edge, and it is left there deliberately:
tightening it to twelve was measured neutral over a sample of eighty and to
eight, worse. What lives in that upper band is not misreading but two scores
whose engraving family is in no table here, read on marginal matches to two
families at once -- which is a vocabulary to name, not a threshold to tune. Aspect ratio -- computed from the raw dimensions,
sharing no arithmetic with the grid -- has to agree as well, which is what
keeps two symbols of similar outline but different proportions apart.
"""
import json
import os

from pipeline import paths
from pipeline.ink.fonts import hamming

TABLE_DIR = paths.TABLES

MAX_DISTANCE = 16      # bits out of 256; true matches measured at 0-6
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


MIN_CORROBORATED = 2


def corroborate(codes, vocabularies, established):
    """The family of a subset too small to be judged on its own.

    A producer that re-embeds an engraving font does not always ship one
    subset per document. Three scores here carry the music in *two* fonts:
    one holding the clef, the rests, the flags and the digits, and a second
    holding nothing but three noteheads. The first passes `attribute` easily;
    the second cannot, because four matches are demanded of a font that
    contains three glyphs -- so every notehead on the page was dropped and
    the scores came out as bars with no strokes in them at all.

    Lowering the threshold is not the answer: the reason it is four is that a
    lone slash or ellipse is a shape any text font carries, and a font drawing
    one of those would be enrolled as music. The evidence here is not the
    shapes alone, it is the company they keep -- the family is *already*
    established in this document by a font that met the full test, and this
    one adds nothing but more of it. So the shapes have only to agree
    unanimously with a family that is already there: one unnamed shape and the
    font is something else, wrongly read.
    """
    # Sorted, so a font that could pass under two families passes under the
    # same one every run: a reading that changes between runs is a reading
    # nobody can check.
    for family in sorted(established):
        vocabulary = vocabularies.get(family)
        if not vocabulary:
            continue
        named = [vocabulary.resolve(fp) for fp in codes]
        if len(named) < MIN_CORROBORATED or not all(named):
            continue
        if any(role(s) in MUSICAL for s in named):
            return family
    return None


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
