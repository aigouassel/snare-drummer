# snare-drummer

Read snare drum transcriptions out of their PDFs, and play them back, so a
score can be *heard* before it is practised on a pad.

The material comes from the snare drum transcriptions listed at
[lothype.com](https://lothype.com/transcriptions/snare-drum-transcriptions/) —
884 PDFs from DCI, WGI and DCA. Every piece the app shows carries the URL it
was read from, and the app prints it.

**A PDF is not a piece of music.** A corps performs one show per season and
writes it in passages — Opener, Drum Feature, Lick, Movement 2 Part 1, 2 and
3 — and the site publishes one PDF per passage. So the library is 327 *works*
(one corps, one season), each holding its *sequences*. The page states that
grouping only in the link text, as the year each title begins with; there is
no section markup on it at all. The passages of one season are worked
together, and flat they were 884 unrelated rows.

## What makes it hard

Not the scraping: the index is one page and the links are direct PDFs.

Not the reading, either — and that was the surprise. These scores are
*engraved*, not scanned: a census of 40 random entries found one glyph-outlined
file, no raster scans, and 39 whose symbols carry an identity and exact
coordinates. Optical music recognition never enters into it. This is a parser.

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
resolves everywhere after. Five families cover the catalogue: Opus (Sibelius,
42%), Maestro (Finale, 25%), MScore (MuseScore), Engraver (Finale) and Bravura
(SMuFL). A shape with no label stays unnamed, is counted, and makes its bar
suspect — never matched to the nearest thing and waved through.

## Layout

```
packages/
  core/           Fraction, Duration, Stroke, Bar, Piece, timeline — and the
                  confidence rule. Depends on nothing.
  catalogue/      327 works and their 884 sequences, and the scraper.
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
cd packages/transcription
python3 pipeline/fetch.py --search "blue devils 2019"   # find a score
python3 pipeline/fetch.py 2019-circus-1                 # fetch it into work/

pipeline/.venv/bin/python pipeline/label.py 'work/*.pdf' \
    --family Opus --out work/opus-sheet.png --json work/opus-listing.json

pipeline/.venv/bin/python pipeline/transcribe.py \
    work/<id>.pdf work/<id>.meta.json src/pieces/<id>.json
```

Four layers, each trusting only what the one below actually read:

1. `ink.py` replays the page's drawing instructions. Any operator it does not
   understand is **counted**, never skipped.
2. `layout.py` finds the staves and barlines — the only structure on the page
   that is stated rather than inferred.
3. `vocabulary.py` names symbols by shape.
4. `transcribe.py` places them in bars and works out how long each note lasts.

Step 4 is the weakest and is written to say so: duration is inferred from
horizontal spacing, which engraving only makes *roughly* proportional. It is
survivable only because the arithmetic check follows it.

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
- [x] Vocabulary for Opus — 59 of 76 symbols named
- [x] First piece read end to end: 10 of 11 bars verified by arithmetic
- [ ] Vocabularies for Maestro, MScore, Engraver, Bravura
- [x] Notation rendering, one line per bar, doubts outlined on the music
- [x] Playback: lookahead scheduler, snare voice, metronome, bar ranges
- [ ] Reading rhythm from beams and flags rather than from spacing
