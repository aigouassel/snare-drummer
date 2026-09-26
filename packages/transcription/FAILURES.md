# How this package has been wrong

Every fault listed here produced a score. None of them raised an error.

That is the whole reason the file exists. A parser that crashes tells you where
to look; this one, when it is wrong, hands back a plausible piece of music —
right number of bars, sensible rhythms, nothing obviously amiss — and the only
way anyone would know is by playing it against the page. Nobody is going to do
that for 884 scores, which is the constraint `CLAUDE.md` opens with and the one
every decision here answers to.

So the useful thing to record is not the bugs. It is their **shapes**, because
they repeat. The next one will not be any of these; it will be one of these
*kinds*. They are grouped that way below, with the chronology at the end.

Two habits come out of the list, and they earn their keep:

- **Measure the catalogue, not the example.** Most of these were found by a
  proportion moving, never by reading code. Several were invisible on the score
  they were found in.
- **Prefer the page's own statement to an inference from it.** Nearly every
  entry is an inference that was right most of the time.

---

## 1 · Reading the container

The PDF is a format, and a format has corners. These are the cheapest faults to
make and the hardest to notice, because the result is simply *less* — fewer
pages, fewer glyphs, a shorter string — and less looks exactly like a shorter
piece.

**Only ever one page.** The reader took the longest content stream on the
assumption that it was the page. A score whose second page was never read is
indistinguishable from a score half as long.

**A regex that stopped at a nested `>>`.** Dictionaries nest; the pattern did
not. It returned a truncated dictionary, which parses.

**A character class that excluded the dot in `/F1.0`.** Font names may carry
one. The reference resolved to nothing and the run was dropped.

**One-byte reads of two-byte glyph codes.** A composite font addresses glyphs
in two bytes. Read singly, every code is wrong and every glyph is a different
glyph — all of them nameable, none of them right.

**A glyph code taken for a glyph index.** The two are related by the font's own
tables, and only by them.

**`'` treated as a plain `Tj`.** The quote operator moves to the next line
first. Without that, a time signature stacked as two glyphs came out at one
height — and a `12` over an `8` read at the same height is not 12/8.

**A `/Widths` array skipped for being an indirect object.** Every glyph of a run
then advanced by zero and landed on the same x, so the run sorted into an
anagram of itself: "Blue Devils 2009" came out as `lBuedevis2l009`. The fix is
also a lesson in defaults — zero is the *dangerous* default here, and
`NOMINAL_ADVANCE = 500` is wrong by a little for every glyph precisely so that
it is never catastrophically wrong for a line.

---

## 2 · Deciding what a shape *is*

Symbol identity is the outline, because neither the glyph code nor the glyph
name survives font subsetting. Everything in this section is a measurement of
an outline that measured something else as well.

**A fingerprint that counted how many curve segments the author used.** The grid
was built by sampling points along each segment, so a notehead drawn as a dozen
segments and the same notehead converted to four cubic béziers produced
different fingerprints — the page's cells came out a strict *subset* of
Bravura's `noteheadBlack`, the same ellipse sampled more thinly, 25 bits away
against a threshold of 16. Two symptoms, opposite in sign: every notehead on
that page went unnamed, *and* a sparse grid is a small target, so the slash of a
diddle landed inside 16 bits of a triangular notehead thirty-two times. Walking
the contour instead removes the segment count without inventing anything.

**Four matches demanded of a font holding three glyphs.** Three scores carry the
music in two subsets — one with the clef, rests, flags and digits, one with
nothing but three noteheads. The second could not clear `MIN_MATCHES = 4`, so
every notehead on the page was dropped and the scores came out as bars with no
strokes in them. Lowering the threshold was the wrong fix and would have
enrolled `ArialMT` as a music font: a lone slash or ellipse is a shape any text
face carries. What settles it is the company the shapes keep —
`corroborate()` attaches an unjudgeable subset to a family already established
*in the same document*, and only if **all** its shapes agree.

**A family read off a font name that embedding had destroyed.** The name is the
first thing a subsetter throws away.

**Cue size measured as ink width instead of type size.** A cross notehead is
narrower than an oval one at the same size, so measuring ink conflates the shape
of the head with the scale. On one score that put a whole class of full-size
noteheads at 0.79 of the commonest width — just inside the 0.8 threshold — and
deleted ninety-nine real notes from the arithmetic as ornaments. Type size is
the scale alone, and it comes out cleanly bimodal: 0.60 on Opus, 0.70 on
MuseScore, 1.00 for everything real.

---

## 3 · Reading the structure the page states

The barline is the most reliable thing an engraved PDF contains — a stroked
segment with exact coordinates — which is why structure is built from what was
read and contents are placed into it. That reliability is also why a structural
fault is so destructive: everything downstream inherits it.

**A staff line swallowed by the beams above it.** Rules were merged when they
overlapped. A beam drawn three quarters of a point above a staff line overlaps
it completely, and is sixty points long against five hundred. Merging moved the
top line off the even spacing, the five-line test failed, and the whole system
was read as a **one-line percussion staff** — which made every stem on it look
like a barline and cut a twelve-note bar into twelve bars of one note. Rules now
merge only when they run between the same two x, which two edges of one filled
rectangle are by construction and nothing else on a page is.

**A staff line engraved one segment per bar.** A quarter of the scores here draw
the rule of a one-line staff as a run of abutting segments rather than as one
line, and the page looks identical either way. Read unjoined, each segment faced
the one-line test as if it were a whole staff and failed both its guards, so the
head of every staff was discarded — with its metre and its bars. One page
printing about thirty-five bars yielded sixteen. This one had a required
counterpart in `rhythm.py`: without it, `2017-drum-break-finals` read eight times
too fast, silently.

**A percussion clef read as four barlines.** The clef is two thick strokes,
arrives as four edges each about a space tall, and straddles the rule as evenly
as any barline. Read as barlines they made the heights disagree and the whole
staff — metre, bars and all — was thrown away for carrying a clef. They are told
apart by position: four verticals inside seven points cannot be four bars.

---

## 4 · Deciding what a mark *means*

Here the ink is read correctly and the conclusion is wrong. These are the
hardest to find, because nothing is missing.

**A tremolo stroke counted as a beam.** The slash that says "roll this note" is
filled and short, and so is a beam stub. Counted as a beam it halves its note,
and the bar comes up short by exactly that difference — no symbol unnamed,
nothing unread, the bar simply wrong. 6,619 strokes across 47 scores. The
correction has two halves and the second matters as much: a stroke merely
*refused* would let the bar close while losing the roll the page prints, which
is a score reading as plain eighths where the engraver wrote a roll — right in
its arithmetic and wrong on its face.

**A single-digit time-signature reader.** It saw nothing at all in 12/8, and
this repertoire is full of 12/8.

**One glyph serving as both whole rest and half rest.** The engraver tells them
apart by hanging one under the fourth line and sitting the other on the third,
so the answer is in where the *ink* went — not where the glyph was placed, since
both are placed with their origin on the middle line. Comparing the origin to
the middle, which is what this did, cannot separate them at all: whole-bar rests
were read as half rests throughout.

**Accents hung one note late in every bar holding a flam.** The articulation
pass rebuilt its own list of onsets, and counted grace noteheads as notes where
reconstruction had folded them into the note they decorate. It now hangs marks
on the onsets reconstruction actually used.

---

## 5 · Order, extent and grouping

**Glyphs sorted by a rounded y, then by x.** Two glyphs of one word whose
baselines differ by a hundredth of a point sort into the wrong order. A baseline
is established first, by tolerance, and only then is anything ordered along it.

**A phrase that ended at the edge of the page.** A band of bar numbers sharing a
baseline joined into one string and swallowed the tempo mark inside it. A phrase
ends at a typographic gap.

**Two tuplet numbers claiming the same note.** Chosen independently, a bar of
four triplets came out as runs 0–3, 3–6, 5–8 and 9–12: one note had the ratio
applied twice and another never got it. Runs are now disjoint and in order.

**A tuplet number read as a count of noteheads.** A tuplet number counts
**subdivisions**, not heads: "9" means nine units in the time of eight, and if
the group mixes values the number of heads has nothing to do with the figure.
`tuplet_groups` looked for exactly `count` consecutive onsets, which is true
only of a homogeneous group — the common case, which is what made the
assumption look sound. On Finale a "3" over a quarter and an eighth spans two
heads; on MuseScore a "9" spans seven. Those groups carry a **bracket**, which
states the extent outright, and `rhythm.brackets()` now reads it: a level run
with a short tick turned in at an end. The number's count is then used for the
ratio only.

**A beam's short sides taken for a bracket's ticks.** The first bracket reader
found 2,700 brackets on a page of 33 bars and displaced 1,324 beams. A filled
beam is a quadrilateral, and its two short sides are verticals exactly as tall
as the beam is thick, standing at its ends — which is what a tick looks like.
What a beam has and a bracket has not is the *second long edge*, so a run with
a co-extent partner a beam's thickness away is a beam whatever stands at its
ends. Found on the fixed sample, where the playable count halved. The drawn
pages then broke 22 more bars: their beams are *stroked*, with no second edge
to give them away, and a stub of secondary beam shifted triplets by a note. What
every beam has, filled or stroked, is the stems that end on it — a run with a
stem through it is a beam, and a bracket stands clear of the notes.

**A digit placed at its word's x.** MuseScore draws a bracket's two ends as
glyphs of the music font, so a bracketed "3" reaches the text reader as one
word of three glyphs, `\ue190 3 \ue190`. The digit's position was estimated
as the word's x plus half a type size per character — counting only the
characters kept after stripping the marks — which put it at the bracket's left
end instead of in the gap. Read against the bracket, the left half alone then
"contained" the number, and a triplet came out as one note in three. Words now
keep the glyphs they were spelled from, and a digit stands where its glyph
does.

---

## 6 · Faults of the machinery around the reading

Not misreadings, but they produce the same thing: a plausible score that is
wrong, or a claim in a document that is not true any more.

**A stale transcription served indefinitely.** The manifest is built from
whatever `src/pieces/` holds, so a piece that stops qualifying goes on being
played from a file older than the code that wrote it. `training-day` was played
that way for a while. Anything that stops qualifying must have its file
**removed**, which is why every transcription run rewrites the manifest from the
directory.

**A listing that could not be listed.** `pipeline.cli list` is designed and
documented as instant — it reads JSON off the disk — and it failed without
`pymupdf` installed, because the CLI loads every subcommand's module to build
its parser and one of them imported the reading half at the top of the file. The
laziness was written into the logic and cancelled by an import three screens
above it.

**A moved function left behind.** `held.py` went on calling `batch.sequences()`
after it moved to `corpus/catalogue.py`. The commit that moved it verified
`list`, `show` and `fetch` — and not the fourth command, which was broken for
two commits.

**A signal that fired on correct input.** Two of these, and they are worth more
than most of the fixes. An early version flagged bars as suspect for being wide,
reasoning that a double-width bar is a missed barline — but engraving spaces a
bar in proportion to its density, so it flagged correct music. And a space draws
no outline, so counting it as an unidentified symbol made bars suspect for
containing word gaps. **A warning that fires on correct input is worse than no
warning**, because it teaches you to ignore the warnings. Bar width is now
evidence of nothing.

**A correct fix with collateral damage, hidden by its own success.** Separating
tremolo strokes from beams by *slope* also refused beams joining two neighbouring
notes, which are short and slant because the notes do: 19 bars that had been
closing were broken, both notes doubling together and a spurious roll appearing.
The net was +177 bars, so the aggregate said nothing. What actually separates the
two is not shape but what the ink *joins* — a beam runs from one stem to another,
a tremolo stroke crosses the one stem it belongs to. Among short slanted runs the
slope distribution is continuous from 0.20 to 0.42, with no gap to put a
threshold in; the joining test needs none.

---

## What the list is for

Four things recur often enough to be worth stating as rules, and each is
already enforced somewhere in the code.

**Anything unrecognised is counted and surfaced, never absorbed.** `ink.py`
counts operators it cannot handle, `vocabulary.resolve()` returns `None` rather
than the nearest match, an unnamed shape leaves its bar suspect. The edge, which
has been crossed once: it assumes there is something to recognise. Loud about
the unrecognised, silent about the blank.

**A threshold goes in a measured gap, or it is not a threshold.** The
fingerprint allows 16 bits of 256 because true matches measured 0–11 and the
nearest unrelated symbol 30. Cue size splits at 0.8 because the two populations
sit at 0.60 and 1.00 with nothing between. The shipping floor sits at 2% because
the proportions run continuously up from 2.7% and one score sat alone at 0.8%.
Where no gap exists — the slope of a beam — the answer is a different test, not
a rounder number.

**A change is judged on totals, and the totals must be able to move both ways.**
`batch.py --sample 80 --seed 7` is the instrument. A fixed sample is the point:
comparing two runs of *different* samples measures nothing. And a net gain can
hide real damage, so a fix is checked bar by bar against the previous reading,
not only in the aggregate.

**Refuse rather than guess.** A note whose stem cannot be found returns nothing;
a tuplet number that cannot be matched is dropped; a metre is never inferred
from the durations. A bar that fails to close is a bar somebody can find. A bar
that closes wrongly is gone for good.
