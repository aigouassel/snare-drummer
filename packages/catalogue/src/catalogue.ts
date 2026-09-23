import { type Circuit, type Source } from '@snare-drummer/core/piece'
import data from './catalogue.json' with { type: 'json' }

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
 * Regenerate with `yarn workspace @snare-drummer/catalogue scrape`.
 */

/** One PDF: a named passage of a show. */
export type Sequence = {
  /** Derived from the PDF's filename, which outlives an edited title. */
  id: string
  title: string
  url: string
}

/** One corps in one season, and the sequences its show was written in. */
export type Work = {
  id: string
  corps: string
  circuit: Circuit
  /** Absent where the listing gives no year; such entries are not dated here
   *  rather than being folded into an arbitrary season. */
  year?: number
  sequences: readonly Sequence[]
}

type CatalogueFile = {
  source: string
  read: string
  works: readonly Work[]
}

const file = data as unknown as CatalogueFile

export const WORKS: readonly Work[] = file.works

export const SEQUENCE_COUNT: number = WORKS.reduce((n, w) => n + w.sequences.length, 0)

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
