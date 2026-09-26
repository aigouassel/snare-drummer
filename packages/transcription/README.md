# @snare-drummer/transcription

Reads engraved snare drum PDFs and writes the scores the player uses.

The TypeScript side of this package is small: `src/pieces/*.json` is data, and
`src/transcription.ts` exports it. Everything that produces that data is Python,
under `pipeline/`.

## Why this is harder than it looks

This package reads scores **nobody will proof read**. A parser that mis-reads
does not crash; it produces a plausible score that is wrong. Fifteen distinct
causes of that have been found here, and **not one raised an error** — a regex
stopping at a nested `>>`, one-byte reads of two-byte glyph codes, a fingerprint
that measured a shape *and how many curve segments its author used*, a staff
line swallowed by a beam so that one score read eight times too fast.

Two rules follow, and everything here obeys them:

- **Anything unrecognised is counted and surfaced, never absorbed.** `ink.py`
  counts operators it cannot handle. `vocabulary.py` returns `None` rather than
  the nearest match. A shape with no label leaves its bar suspect.
- **A change is judged on totals, not on one score.** Nobody will read 6,000
  bars, so the proportion that closes is the only evidence a change helped.

## The command line

Run everything as a module from this directory, with the pipeline's own venv:

```bash
PY=pipeline/.venv/bin/python

$PY -m pipeline.cli list                     # every sequence, and what came of it
$PY -m pipeline.cli list --repertoire        # only what the app ships from
$PY -m pipeline.cli list --held              # what is not shipped
$PY -m pipeline.cli list --family Ash        # one engraving family
$PY -m pipeline.cli show 2019-intro          # one score, bar by reason
$PY -m pipeline.cli transcribe 2019-intro    # one score; manifest updated
$PY -m pipeline.cli transcribe --repertoire  # the shipped repertoire
```

`list`, and `show` of a score already transcribed, read nothing but JSON: they
run under a plain `python3` with none of this installed, because the modules
that open a PDF are imported where the reading happens rather than at the top of
the file. That is worth keeping — it broke once, and listing what the catalogue
holds died on a missing `pymupdf`.

`list` is instant: it reads the transcriptions already on disk. How a score is
engraved is a property of its PDF, so for a score that has never been read the
column is left **blank** rather than guessed, and the footer says how many. Pass
`--probe` to read those PDFs and fill it in.

Transcribing anything rewrites `src/pieces/index.ts` from the directory, so a run
of one score still produces a manifest naming the other hundred and fifteen — and
a score that no longer qualifies disappears from it in the same breath. That
matters: the manifest *is* the app's library, and a stale piece left behind goes
on being served looking perfectly well.

### Measuring a change

```bash
$PY -m pipeline.run.batch --sample 80    # a fixed spread across the catalogue
$PY -m pipeline.run.batch --repertoire   # everything the app ships
$PY -m pipeline.run.held                 # regenerate HELD-BACK.md
```

`--sample` takes `--seed` (default 7) so the same eighty scores come back every
time; comparing two runs of *different* samples measures nothing. Reading is
spread across cores, so a repertoire pass is minutes rather than an hour.

## Layout

`pipeline/` follows the path a page takes, because that is the order in which
things can go wrong:

```
pipeline/
  paths.py          where everything lives, decided once
  transcribe.py     one score, end to end: it composes the stages below
  cli/              the front door — list, show, transcribe
  ink/              what the page draws
    ink.py            PDF content streams to glyphs and paths
    fonts.py          the fingerprint that gives a shape its identity
  layout/           the structure the page states: staves, systems, barlines
  naming/           what the marks mean
    vocabulary.py     shape to symbol, or None
    text.py           tempo, dynamics, sticking letters
    label.py          contact sheets, for naming a family by eye
    tables/           ash.json, maestro.json, opus.json, …
  rhythm/           durations, as exact fractions of a beat
  corpus/           the catalogue, and the PDFs it points at
    catalogue.py      the listing, flattened to sequences
    fetch.py          one PDF, by catalogue id
  run/              reading many at once
    batch.py          the engine, and the totals
    tally.py          counting a piece already read — no PDF, no pymupdf
    held.py           generates HELD-BACK.md
```

Four things here are easy to undo by habit:

**The verdict is computed in TypeScript, never in Python.** The pipeline ships
evidence across the boundary — durations, and a count of unnamed symbols — and
`@snare-drummer/core` decides. A second copy of the rule in Python would have no
tests and would drift.

**Durations are exact rationals.** A sixteenth-note triplet is `[1, 6]` of a
beat. Every confidence check asks "do these fill the bar exactly?", and in
floating point twelve triplets sum to 3.9999999999999996 — every triplet passage
in the catalogue would be flagged.

**A symbol's identity is its outline, not its name or its code.** Both are
destroyed by font subsetting: the code is renumbered per file and the name is
usually stripped. `fonts.py` fingerprints the outline as a normalised occupancy
grid. Naming happens once per engraving family, by eye, off a contact sheet — the
only human judgement in the pipeline. **Never** make the matcher fall back to the
nearest entry.

**`HELD-BACK.md` is generated.** It lists what is not shipped and why. A list
written by hand would be wrong the moment something started working, which is the
one thing this package cannot afford.

## Setup

```bash
python3 -m venv pipeline/.venv
pipeline/.venv/bin/pip install -r pipeline/requirements.txt
```

PDFs land in `work/corpus/` and stay there, ignored by git — they are
transcriptions of copyrighted shows hosted elsewhere, and a finished score does
not need them: each piece records the URL it was read from.
