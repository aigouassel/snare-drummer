import { type Circuit, type Source } from '@snare-drummer/core/piece'
import data from './catalogue.json' with { type: 'json' }
import { type Hit, searchWorks } from './search'

/**
 * Everything the site lists, grouped the way the music is actually organised.
 *
 * A PDF is not a piece of music. A corps performs one show per season, and
 * that show is what gets worked on; the PDFs under it are its **sequences** —
 * Opener, Drum Feature, Lick, Movement 2 Part 1, 2 and 3. The page states
 * that grouping only in the link text, as the year each title begins with,
 * so the scraper reconstructs it and the app reads it from here.
 *
 * The whole index is kept, transcribed or not. A library showing only what
 * has been read would misrepresent 327 shows as one, and an untranscribed
 * sequence is still useful: it opens its PDF.
 *
 * What the app works from is narrower: **each corps at its most recent
 * season**. A corps rewrites its book every year, so nineteen seasons of Blue
 * Devils are nineteen different shows rather than nineteen versions of one,
 * and what is worth practising is the latest. That reduction is 327 works to
 * 66, and 884 sequences to 129. Everything else stays listed behind it, and
 * `LISTED_WORKS` still holds it all.
 *
 * Which season is current is read from the file rather than worked out here,
 * because the pipeline needs the same answer and two implementations of one
 * rule would drift invisibly -- both would produce a plausible library. The
 * scraper decides what a work is, so it is what says which one is current.
 *
 * Regenerate with `yarn workspace @snare-drummer/catalogue scrape`.
 */

/** One PDF: a named passage of a show. */
export type Sequence = {
  /** Derived from the PDF's filename, which outlives an edited title. */
  id: string
  title: string
  url: string
  /**
   * A photograph of a page rather than an engraved score.
   *
   * Reading one would be optical music recognition, which this project does
   * not do: everything here rests on a notehead having exact coordinates.
   * Such a sequence stays in the listing — it exists — and is kept out of the
   * repertoire, because the repertoire is what somebody could work on.
   */
  scanned?: true
}

/** One corps in one season, and the sequences its show was written in. */
export type Work = {
  id: string
  corps: string
  circuit: Circuit
  /** Absent where the listing gives no year; such entries are not dated here
   *  rather than being folded into an arbitrary season. */
  year?: number
  /** This corps' most recent season: the one the app plays from. */
  current?: true
  sequences: readonly Sequence[]
}

type CatalogueFile = {
  source: string
  read: string
  works: readonly Work[]
}

const file = data as unknown as CatalogueFile

/** Everything the page lists, every season of every corps. */
export const LISTED_WORKS: readonly Work[] = file.works

/**
 * The repertoire: each corps at its most recent season, minus what is not a
 * transcription at all. A scanned page is dropped here rather than in the
 * app, so every count downstream agrees without anyone having to remember.
 */
export const WORKS: readonly Work[] = LISTED_WORKS.filter((w) => w.current).map(
  (w) =>
    w.sequences.some((s) => s.scanned)
      ? { ...w, sequences: w.sequences.filter((s) => !s.scanned) }
      : w,
)

export const SEQUENCE_COUNT: number = WORKS.reduce((n, w) => n + w.sequences.length, 0)

/** How much of the listing is held back, so the app can say so. */
export const LISTED_COUNT = {
  works: LISTED_WORKS.length,
  sequences: LISTED_WORKS.reduce((n, w) => n + w.sequences.length, 0),
} as const

/** The page the catalogue was read from, and when. */
export const PROVENANCE = { source: file.source, read: file.read } as const

export const workById = (id: string): Work | undefined => WORKS.find((w) => w.id === id)

/** The work a sequence belongs to, and the sequence itself. */
export const findSequence = (
  id: string,
): { work: Work; sequence: Sequence } | undefined => {
  for (const work of WORKS) {
    const sequence = work.sequences.find((s) => s.id === id)
    if (sequence) return { work, sequence }
  }
  return undefined
}

/** The `Source` a transcription of this sequence should carry. */
export const sourceOf = (sequence: Sequence): Source => ({
  url: sequence.url,
  listedAt: PROVENANCE.source,
  read: PROVENANCE.read,
})

/** How a work is named in a list: the corps and its season. */
export const workTitle = (work: Work): string =>
  work.year ? `${work.corps} ${work.year}` : `${work.corps} — sans année`

export const corpsList = (): readonly string[] =>
  [...new Set(WORKS.map((w) => w.corps))].sort((a, b) => a.localeCompare(b))

export const years = (): readonly number[] =>
  [...new Set(WORKS.flatMap((w) => (w.year === undefined ? [] : [w.year])))].sort(
    (a, b) => a - b,
  )

export type Filter = {
  circuit?: Circuit
  corps?: string
  year?: number
  /** Matched against the corps and any sequence title, case-insensitively. */
  text?: string
}

export const filter = (f: Filter): readonly Work[] => {
  const needle = f.text?.trim().toLowerCase()
  return WORKS.filter(
    (w) =>
      (f.circuit === undefined || w.circuit === f.circuit) &&
      (f.corps === undefined || w.corps === f.corps) &&
      (f.year === undefined || w.year === f.year) &&
      (needle === undefined ||
        needle === '' ||
        w.corps.toLowerCase().includes(needle) ||
        String(w.year ?? '').includes(needle) ||
        w.sequences.some((s) => s.title.toLowerCase().includes(needle))),
  )
}

export { type Hit, searchWorks } from './search'

/**
 * The repertoire matching what somebody typed, best match first.
 *
 * `filter` above is an exact facet: given a corps, it gives that corps. This
 * is the other question -- given some words, what did they mean -- and the
 * library asks only this one. See `search.ts` for why they are not the same
 * function.
 */
export const search = (query: string): readonly Hit[] => searchWorks(WORKS, query)
