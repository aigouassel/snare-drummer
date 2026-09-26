#!/usr/bin/env python3
"""
What the page says in words, as opposed to what it draws in notes.

A score is not only notation. It also prints a tempo, a sticking under the
notes, a dynamic beneath the staff and a rehearsal letter over it, and every
one of those is *typed text* in an ordinary font rather than a symbol in an
engraving font. The rest of this pipeline identifies symbols by their outline,
which is exactly the wrong instrument here: two hundred scores draw the letter
R in two hundred subsetted fonts, and no shape vocabulary should have to learn
each one.

So this layer reads the other thing a PDF carries -- the characters the codes
stand for -- and it only ever looks at fonts that are *not* an engraving
family. The two readings stay apart on purpose: a music font's letters are
meaningless, and a text font's shapes are somebody else's typeface.

Three dialects have to be understood, and only one of them is plain:

  - plain text, "q = 168" or "mm=180", set in Arial or Times;
  - the Sibelius convention, where the metronome mark is typed into a music
    font as "q»¡§•" -- a quarter note, an equals sign, and the digits 1, 6, 8
    in a keyboard layout that has nothing to do with Unicode;
  - a metre or a dynamic typed as a letter, "f" and "p" and "ƒ", where the
    glyph is a symbol but the code arrives here as a letter.
"""
import re
import unicodedata

# What the metronome's note value is worth in quarter-note beats. A tempo is
# a number *per something*, and a mark reading 150 over a dotted quarter is a
# different speed from 150 over a quarter -- in 6/8, which this repertoire is
# full of, reading the note value wrong halves or doubles the piece.
NOTE_VALUES = {
    'w': 4.0, 'h': 2.0, 'q': 1.0, 'e': 0.5, 'x': 0.25,
    '': 4.0, '': 2.0, '': 1.0, '': 0.5,
    '𝅗𝅥': 2.0, '♩': 1.0, '♪': 0.5, '♩': 1.0,
}

# Sibelius types a metronome mark into its music font, where the digits sit on
# the option-number keys. The characters that arrive here are therefore
# punctuation, and mean nothing at all read as punctuation.
SIBELIUS_DIGITS = str.maketrans({
    '¡': '1', '™': '2', '£': '3', '¢': '4', '∞': '5',
    '§': '6', '¶': '7', '•': '8', 'ª': '9', 'º': '0',
})

# Dynamics, in the order a louder one must beat a quieter one when both are
# read. Relative weight is decided in TypeScript, not here.
# Dynamics, as the page spells them on the left and as the model names them
# on the right. The variants are spellings of one thing -- sf, sfz and sffz
# are one engraver's habit against another's -- and collapsing them here keeps
# the model's list short enough to be given a sound apiece.
DYNAMICS = {
    'pppp': 'pppp', 'ppp': 'ppp', 'pp': 'pp', 'p': 'p', 'mp': 'mp',
    'mf': 'mf', 'f': 'f', 'ff': 'ff', 'fff': 'fff', 'ffff': 'ffff',
    'sf': 'sfz', 'sfz': 'sfz', 'sffz': 'sfz', 'rfz': 'sfz', 'rf': 'sfz',
    'fz': 'fz', 'fp': 'fp',
}

# A sticking letter, and nothing else. `b` is a common shorthand in this
# repertoire for a stroke played with both hands.
STICKING = {'r': ('right', False), 'R': ('right', True),
            'l': ('left', False), 'L': ('left', True)}


def spell(glyph, font):
    """The text a glyph draws, or '' where it draws a shape and not a letter."""
    chars = font.get('chars', {})
    return ''.join(chars.get(code, '') for code in glyph['codes'])


def baselines(items):
    """Glyphs or words gathered onto the lines they were set on, left to right.

    Everything this layer reads depends on getting this right, and getting it
    wrong is silent. Sorting by a rounded y and then by x looks like the same
    thing and is not: two glyphs of one word whose baselines differ by a
    hundredth of a point round into different lines and swap, so a title comes
    out as "eatureF-Drum2102" and a metronome mark as "081q=". So the line is
    established first, by tolerance, and only then is anything ordered along
    it.
    """
    lines = []
    for order, item in enumerate(items):
        item.setdefault('seq', order)
    for item in sorted(items, key=lambda i: (-i['y'], i['seq'])):
        tolerance = max(item.get('size') or 1.0, 1.0) * 0.4
        for line in lines:
            if abs(line['y'] - item['y']) < tolerance:
                line['items'].append(item)
                break
        else:
            lines.append({'y': item['y'], 'items': [item]})
    for line in lines:
        # The stream's own order breaks a tie, and ties do happen: a font
        # whose advances are unknown leaves a whole run on one x. Falling
        # back to the order the producer wrote the glyphs in is the reading
        # order, and never worse than an arbitrary one.
        line['items'].sort(key=lambda i: (i['x'], i['seq']))
    return lines


def words(page):
    """Every glyph that spells something, grouped into the words it spells.

    Every font, including the engraving ones, and that is deliberate. It would
    look consistent to read text from text fonts and shapes from music fonts,
    and it is wrong: Sibelius types its metronome mark into *Opus Text*, whose
    name makes it an engraving family, and its dynamics are the plain letters
    f and p in the music font itself. Excluding music families lost exactly
    the marks this layer exists to find.

    The reverse risk is real but small. A notehead in an engraving font may
    spell some arbitrary letter, so the readers below match whole shapes -- a
    number beside an equals sign, a lone sticking letter, one of a closed set
    of dynamics -- and never a character in isolation.

    Grouping is by proximity, because a PDF has no notion of a word: glyphs
    are positioned one at a time, and only the gaps say where one ends. The
    gap is measured against the type size, so it holds for a 6pt sticking
    letter and a 24pt title alike.
    """
    fonts = page['fonts']
    placed = []
    for glyph in page['glyphs']:
        font = fonts.get(glyph['font'] or '', {})
        text = spell(glyph, font)
        if not text or not text.strip():
            continue
        placed.append({'text': text, 'x': glyph['x'], 'y': glyph['y'],
                       'size': glyph['size'] or 10.0,
                       'music': bool(font.get('family')),
                       'font': font.get('basefont') or ''})

    out = []
    for line in baselines(placed):
        current = None
        for glyph in line['items']:
            if current and glyph['x'] - current['x1'] < current['size'] * 0.45:
                current['text'] += glyph['text']
                current['x1'] = glyph['x'] + glyph['size'] * 0.55
                current['glyphs'].append(
                    (glyph['text'], glyph['x'], glyph['size']))
            else:
                if current:
                    out.append(current)
                # The glyphs are kept beside the text they spell, because a
                # word's x is only where its *first* glyph stands. A tuplet
                # number wedged between the two ends of its bracket -- three
                # glyphs, two of them from the music font -- has its digit
                # some way into the word, and estimating that from a type size
                # put it at the bracket's end instead of in the gap.
                current = {'text': glyph['text'], 'x': glyph['x'],
                           'x1': glyph['x'] + glyph['size'] * 0.55,
                           'y': glyph['y'], 'size': glyph['size'],
                           'music': glyph['music'], 'font': glyph['font'],
                           'glyphs': [(glyph['text'], glyph['x'],
                                       glyph['size'])]}
        if current:
            out.append(current)
            current = None
    return out


def runs(page_words):
    """Words joined into the phrases they were set as.

    A metronome mark reaches this layer as three separate runs -- the note,
    the equals sign and the number, often in three different fonts -- so it
    has to be reassembled before it can be read. What must not happen is
    reassembling a whole horizontal band of the page: bar numbers, stickings
    and a dynamic that merely share a baseline joined into one string, and a
    real "q = 158" disappeared into "=81733333". So a phrase ends at a real
    typographic gap.
    """
    out = []
    for line in baselines(page_words):
        current = None
        for word in line['items']:
            if (current
                    and word['x'] - current['x1'] < max(word['size'], 1.0) * 2.5):
                current['text'] += ' ' + word['text']
                current['x1'] = max(current['x1'], word['x1'])
            else:
                if current:
                    out.append(current)
                current = dict(word)
        if current:
            out.append(current)
    return out


# A metronome mark: a note value, an equals sign, a number. The junk allowed
# around the equals sign is not laxity -- an accent or a staccato dot drawn on
# the same baseline joins the phrase, so a real "q = 180" arrives as "q>=>180"
# and a mark refusing it would be refusing most of Sibelius's output. What
# stays strict is the shape: a note value, a separator and two or three
# digits, in that order.
_TEMPO = re.compile(
    r'(?:^|[^A-Za-z0-9])'
    r'(?:(?P<note>[whqex\uf065\uf068\uf071\uf077\u2669\u266a])'
    r'(?P<dot>\.?)[^A-Za-z0-9]{0,3})?'
    r'(?:=|»|＝)[^A-Za-z0-9]{0,3}'
    r'(?P<bpm>\d{2,3})(?!\d)')

_BARE = re.compile(r'\b(?:mm|m\.m\.)\s*[=»]?\s*(?P<bpm>\d{2,3})', re.I)


def tempo(page):
    """The tempo the page prints, in quarter-note beats per minute.

    Returns None where the page prints none, and that absence is meaningful:
    a show was played at a tempo somebody chose, and a default invented here
    would be indistinguishable from a marking that was read.

    The note value is read along with the number. "150" over a dotted quarter
    is 225 quarter-note beats, and this repertoire writes enough 6/8 for that
    to be the difference between a playable tempo and a comical one.
    """
    found = []
    for run in runs(words(page)):
        line = _normalise(run['text'])
        for match in _TEMPO.finditer(line):
            bpm = int(match.group('bpm'))
            unit = NOTE_VALUES.get(match.group('note') or 'q', 1.0)
            if match.group('dot'):
                unit *= 1.5
            found.append((run['y'], bpm * unit))
        for match in _BARE.finditer(line):
            found.append((run['y'], float(match.group('bpm'))))
    # The topmost mark on the page. A score prints its opening tempo at the
    # head and any change where the change happens, so the highest one is the
    # tempo the piece starts at -- which is the one to hand a player.
    plausible = [(y, bpm) for y, bpm in found if 30 <= bpm <= 300]
    if not plausible:
        return None
    return round(max(plausible, key=lambda p: p[0])[1])


def _normalise(line):
    """One string, with the dialects folded into plain characters."""
    line = line.translate(SIBELIUS_DIGITS)
    return unicodedata.normalize('NFKC', line)


def sticking(page_words):
    """Which hand plays which note, where the page writes it under the notes.

    A sticking letter is a word of its own -- one character, sometimes with a
    trailing dot or a dash -- so it is matched as a whole word and never as a
    letter found inside one. "Rolls" is not an R.

    Case is read as well as the letter. This repertoire writes an accented
    stroke as a capital and a tap as a lowercase, consistently enough to be a
    convention, and it is often the only thing distinguishing the two in a
    passage the engraver never marked with an accent. A printed accent still
    wins wherever both are present; deciding that is not this layer's job, and
    the emphasis is reported beside the hand rather than folded into it.

    `b` and `B` are left unread on purpose. They are common here and they are
    not a hand -- backsticking in some books, both hands in others -- and a
    guess would put a stroke in the wrong hand for a whole passage.
    """
    out = []
    for word in page_words:
        letter = word['text'].strip().rstrip('.-·')
        if letter not in STICKING:
            continue
        hand, emphatic = STICKING[letter]
        out.append({'x': word['x'], 'y': word['y'],
                    'hand': hand, 'emphatic': emphatic})
    return out


def dynamics(page_words):
    """Dynamics printed on the page, as a level and where it sits.

    Matched against a closed set, whole word, because the alternative is a
    disaster in a repertoire whose engraving fonts spell arbitrary letters:
    an f found inside a word is as likely to be a notehead as a forte.

    Only fonts that draw music qualify. A dynamic is engraved in the music
    font -- that is what makes it slanted and bold -- and the f of "Transcribed
    from footage" is set in the body face. This is the one reader that uses
    the distinction, because it is the one whose vocabulary is a single
    letter.
    """
    out = []
    for word in page_words:
        if not word.get('music'):
            continue
        mark = word['text'].strip().rstrip('.')
        if mark.lower() not in DYNAMICS:
            continue
        out.append({'x': word['x'], 'y': word['y'],
                    'level': DYNAMICS[mark.lower()]})
    return out
