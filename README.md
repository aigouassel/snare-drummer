# snare-drummer

Read snare drum transcriptions out of their PDFs, and play them back, so a
score can be *heard* before it is practised on a pad.

The material comes from the snare drum transcriptions listed at
[lothype.com](https://lothype.com/transcriptions/snare-drum-transcriptions/) —
884 PDFs from DCI, WGI and DCA. Every piece the app shows carries the URL it
was read from, and the app prints it.

**A PDF is not a piece of music.** A corps performs one show per season and
writes it in passages — Opener, Drum Feature, Lick, Movement 2 Part 1, 2 and
3 — and the site publishes one PDF per passage. So the listing is 327 *works*
(one corps, one season), each holding its *sequences*. The page states that
grouping only in the link text, as the year each title begins with; there is
no section markup on it at all. The passages of one season are worked
together, and flat they were 884 unrelated rows.

**The repertoire is narrower than the listing.** A corps rewrites its book
every year, so nineteen seasons of Blue Devils are nineteen different shows
rather than nineteen versions of one, and what is worth practising is the
latest. The app works from **each corps at its most recent season** — 66 works
and 129 sequences — and everything else stays listed behind it. Within a kept
season nothing is dropped: `(Early Season)` and `(Finals)` of one passage are
both real, and `Movement 2 Part 1/2/3` are consecutive passages rather than
variants, so a rule that stripped trailing numbers would delete two thirds of
a movement.

## What makes it hard

Not the scraping: the index is one page and the links are direct PDFs.

Not the reading, either — and that was the surprise. These scores are
*engraved*, not scanned: a census of 40 random entries found one glyph-outlined
file, no raster scans, and 39 whose symbols carry an identity and exact
coordinates. Optical music recognition never enters into it. This is a parser.

A page is less obliging than it sounds, mind. 38% of the catalogue runs to two
pages or more, 3% is engraved landscape and rotated into portrait, some
engravers stroke their staff lines and others fill them as hairline
rectangles, and a text-showing operator draws a whole *run* that has to be
walked one glyph at a time. None of that raises an error. Each of them simply
reports less music than the page holds.

The hard part is **checking nearly nine hundred scores that nobody will proof
read**. A parser that mis-reads a flam does not crash; it produces a plausible
score that is wrong, and plays a wrong note for ever. So the project's real
subject is not extraction, it is knowing which bars to trust.

## How trust is established

Every bar is judged, by machine, on signals a machine can take alone:

| Signal | Strength |
| --- | --- |
| The durations read fill the bar's metre **exactly** | strong — never a false alarm, but two errors can cancel |
| A symbol on the staff that nothing could name | a direct confession of ignorance |
| A bar with nothing in it | printed music writes a whole-bar rest, never nothing |
| Durations *measured* off the page rather than read from the beams | a weaker coincidence than the same sum reached from the notation |
| How wide the bar is on the page | **deliberately not used** — see below |

A bar that passes is playable. A bar that does not is shown with its reasons
and the link to the source, and stays in place so the bars around it keep
their timing. That is why the **bar is the unit of this project**: a piece is
ninety bars of which four are doubtful, and the other eighty-six should still
be playable.

Bar width is not a signal on purpose. Engraving spaces a bar in proportion to
what it holds, so a wide bar looks like a missed barline — and an early version
of the layout code flagged perfectly good music on exactly that reasoning. A
signal that fires on correct input is worse than none, because it teaches you
to ignore the warnings.

## How a symbol is identified

Not by its code, and not by its name — both are destroyed by the way fonts are
embedded. A PDF subsets its engraving font and renumbers the glyphs per file,
so the same notehead is code `0004` in one score and `0011` in the next, and
the subsetter usually strips the names too, leaving `glyph00004`.

What survives is the outline, because that is what gets drawn. The pipeline
fingerprints each glyph's *shape*, normalised, and that fingerprint is stable
across the catalogue. Measured between two unrelated scores — one embedding
TrueType, the other bare CFF — matching symbols agreed to within 0–11 bits out
of 256, with the nearest unrelated symbol at 30.

So naming happens **once per engraving family**, off a contact sheet, and
resolves everywhere after. Three families carry the catalogue — Opus
(Sibelius), Maestro (Finale) and MScore (MuseScore) — with five more in the
tail: Bravura and Engraver turn out to be text companions supplying accents,
digits and tremolo slashes while the notes come from elsewhere, Gootville and
Reprise were not recognised as music fonts at all, and BroadwayCopyist is
Finale's handwritten face. 99% of the musical glyphs in an 80-score sample now
carry a name. A shape with no label stays unnamed, is counted, and makes its
bar suspect — never matched to the nearest thing and waved through.

A family nobody has named is invisible for ever, and that is worth stating
plainly, because it looks like it should not be. Attribution by shape rescues
a font whose *name* embedding destroyed, but it can only compare against
vocabularies that already exist — so an engraver nobody has met reads as no
music at all. Eight held-back sequences turned out to be one such family.

The contact sheet also cannot settle anything positional. It shows a shape at
a fixed size with no staff around it, so a thick slash drawn 541 times could
be a notehead or a diddle; it took a cropped page to see that it crosses a
stem. Anything that might carry rhythm gets measured or cropped, because
misnaming an inert mark is free and calling an inert mark a notehead invents
an attack the arithmetic catches only half the time.

The sheet counts a symbol by how often it was **drawn**, not by how many fonts
contain it. A font's repertoire is a poor guide to a family's: of nine Maestro
shapes picked out for checking, six were never placed on a page at all, and
the family fell from 57 shapes to 24 that matter.

Which glyph a code addresses is its own problem, and four things had to be read
to get it right: the font's own cmap, the base encoding the PDF names, its
/Differences array, and — for a composite font — its /CIDToGIDMap, because
Identity-H means the code is the *CID* and the CID is the glyph index only when
the font says so. Reading a code as an index found a fingerprint for 2% of
single-byte codes, the wrong one by coincidence, and none for the other 98%.

## What the page says, as opposed to what it draws

A score is not only notation. It prints a tempo over the first bar, a sticking
letter under every note, a dynamic beneath the staff — and every one of those
is *typed text* in an ordinary font, not a symbol in an engraving one. None of
it was being read, because the shape vocabulary is the wrong instrument for
the letter R set in two hundred subsetted fonts.

Reading it meant a fourth encoding table, and one of a different kind. A
cmap, a `/Differences` array and a `/CIDToGIDMap` all answer *which outline
does this code draw*; `/ToUnicode` alone answers *what does this code mean*.
It is what a producer writes so that copying text out of a page works, nothing
on the page depends on it, and it is therefore optional — so a composite font
without one spells nothing, and must be reported rather than guessed at. 70%
of the words in this catalogue were mute without it.

The resolution order is the reverse of the one for shapes. For an outline the
font's own cmap has the last word, because it knows what it holds. For a
letter that same cmap is worse than useless: these subsets carry a symbol cmap
whose glyphs are named `glyph00012`, and applying it over WinAnsiEncoding
replaced the m of `mm=180` with a name spelling nothing.

Text is read from **every** font, engraving ones included, because Sibelius
types its metronome mark into Opus Text and its dynamics are the plain letters
f and p in the music font itself. Three dialects have to be understood: plain
`q = 168`, the Sibelius convention where the digits are typed on the
option-number keys and arrive as `q»¡§•`, and a dynamic that is a letter in a
font that draws music.

What comes back: the tempo on 77 of 90 pieces, the hand on 24,483 notes, a
dynamic on 3,809, an ornament on 2,552. Absence stays meaningful throughout —
a piece with no printed tempo gets none, and is played at whatever tempo you
are working at today.

## Layout

```
packages/
  core/           Fraction, Duration, Stroke, Bar, Piece, timeline — and the
                  confidence rule. Depends on nothing.
  catalogue/      the 327 listed works, the 66 in the repertoire, the scraper.
  transcription/  The transcribed sequences, and the pipeline that produces
                  them: pipeline/ is Python, src/ is the data it writes.
  notation/       VexFlow adapter. Layout is arithmetic and tested; drawing
                  is not.
apps/
  web/            The player: library, score, transport, audio engine.
```

The hierarchy is circuit → corps → **work (a season)** → **sequence (a PDF)**
→ bars. A transcription is a sequence read into bars, and carries the
`workId` that puts it back beside the passages it was written with.

**No package may reach a browser API.** `tsconfig.base.json` sets
`lib: ["ES2022"]` with no DOM, so `window` and `AudioContext` are type errors
outside the app. A transcription is data, read by playback, by rendering and by
the confidence checks alike; none of the three may own it.

**The verdict is computed in TypeScript, never in Python.** The pipeline ships
evidence — durations, and a count of symbols it could not name — and
`@snare-drummer/core` decides. One rule, with tests, rather than two copies
that drift.

## The pipeline

```bash
cd packages/transcription/pipeline
.venv/bin/python fetch.py --search "blue devils 2019"   # find a score
.venv/bin/python batch.py --sample 80                   # read a spread of them
.venv/bin/python batch.py 2019-circus-1 2019-circus-2   # or named ones

.venv/bin/python label.py '../work/corpus/*.pdf' \
    --family Opus --out ../work/opus-sheet.png --json ../work/opus-listing.json
```

Four layers, each trusting only what the one below actually read:

1. `ink.py` replays the page's drawing instructions. Any operator it does not
   understand is **counted**, never skipped.
2. `layout.py` finds the staves and barlines — the only structure on the page
   that is stated rather than inferred. Most of this repertoire is written on
   a **one-line staff**, which has no five-line pattern to recognise and looks
   exactly like an underline; what identifies it is what crosses it, since
   barlines straddle a staff evenly and are all drawn to one height where a
   stem hangs to one side.
3. `vocabulary.py` names symbols by shape.
4. `text.py` reads what the page *says* — the tempo, the sticking, the
   dynamics — from the characters its codes stand for rather than their
   outlines.
5. `rhythm.py` reads how long each note lasts, and `transcribe.py` places
   them in bars.

Duration comes from the notation: the stem rising from the notehead, the
filled beams crossing it, the flag at its tip, the dot beside it, and the
tuplet number printed over the run. Three things this repertoire insists on —
a stem is drawn at the notehead's *edge* and not its middle, a flam is a grace
note engraved at cue size and takes no time of its own, and triplets are
everywhere.

Reading it wrong is quiet, and quiet in a particular way worth naming. Half
the defects found here removed *notes* without changing the sum — an ornament
takes no time, so a note miscounted as one leaves a bar that still adds up and
simply has fewer notes in it than the page does. The arithmetic check cannot
see those at all; only looking at the bar can.

A note whose stem cannot be read returns nothing rather than a guess, and the
bar falls back to measuring the spacing as a whole — mixing a stated length
with a measured one inside one bar gives a sum that means nothing. Such a bar
is reported rather than trusted.

## PDFs are not committed

`.gitignore` covers `packages/transcription/work/**` as an **allowlist**:
anything dropped there is ignored unless named as safe. The scores are other
people's transcriptions of copyrighted shows, hosted elsewhere, and a
transcribed piece carries the URL it was read from — so the source is one click
from the page that displays it, and the downloaded copy is a working file.

The one thing committed from the pipeline's own work is the vocabulary in
`pipeline/vocabulary/*.json`: the labels read off a contact sheet once per
family. That is the only human judgement in the pipeline, it is small, and it
is what makes every other score readable without re-deriving anything.

## Scripts

```bash
yarn test        # every workspace, one vitest run
yarn typecheck   # tsc --noEmit in each workspace
yarn dev         # the player
```

## State

- [x] Catalogue: 327 works / 884 sequences, filterable, with provenance
- [x] Domain model, and the confidence rule, with tests
- [x] Extraction: content stream, staves, barlines, shape fingerprints
- [x] Vocabularies for all seven engraving families — 99% of drawn glyphs named
- [x] Notation rendering, one line per bar, doubts outlined on the music
- [x] Playback: lookahead scheduler, snare voice, metronome, bar ranges
- [x] Rhythm read from beams, flags, dots and tuplet numbers, not from spacing
- [x] The tempo, the sticking, the dynamics and the ornaments, read from the
      page's own words, drawn on the score and heard in playback
- [x] The repertoire read end to end: 98 of its 129 sequences, 5,606 bars,
      3,202 playable as read
- [x] Music that a page *draws* rather than sets. Some producers convert a
      score to outlines, so a notehead arrives as a painted path and not as a
      character. Nothing new was needed to name them: a fingerprint is taken
      from the points of an outline, and an outline is an outline wherever it
      came from, so they match the vocabularies learned from fonts
- [ ] **Bars whose durations do not add up: 17% of the repertoire.** Down from
      44.5%, by taking one failing bar at a time, cropping it out of its PDF
      and comparing it with what had been read. Ten causes so far and no two
      alike; the remainder is a long tail and the method still works
- [ ] Some of that 17% is the source being wrong rather than the reading. One
      4/4 bar of this catalogue holds a half rest and a quarter rest and
      nothing else: these are transcriptions people made by ear, and a bar
      that does not add up on the page cannot be made to add up here
- [ ] Beams on a page that draws its music. A drawn page draws its beams too,
      and the beam reader finds several hundred filled quadrilaterals where a
      set page has ninety-six — so those scores read a rhythm that is four
      times too fast. Geometry, not naming
- [ ] The 31 sequences held back. Six of them draw their music as vector
      outlines with no glyphs at all; the rest read a page but not a rhythm
