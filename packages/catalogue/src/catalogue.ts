import { type Circuit, type Source } from '@snare-drummer/core/piece'
import data from './catalogue.json' with { type: 'json' }

/**
 * Every score the site lists, transcribed or not.
 *
 * Keeping the whole index — rather than only what has been read — is a
 * deliberate choice about what the app is. A library that showed eight
 * transcribed pieces would misrepresent a catalogue of nearly nine hundred;
 * showing all of them, with the link, makes the untranscribed ones useful
 * today (as a PDF to open) and makes the gap visible rather than hidden.
 *
 * Regenerate with `yarn workspace @snare-drummer/catalogue scrape`.
 */
export type CatalogueEntry = {
  /** Derived from the PDF's filename, which outlives an edited title. */
  id: string
  title: string
  corps: string
  circuit: Circuit
  /** Absent where the listing's title does not start with one. */
  year?: number
  url: string
}

type CatalogueFile = {
  source: string
  read: string
  entries: readonly CatalogueEntry[]
}

const file = data as CatalogueFile

export const CATALOGUE: readonly CatalogueEntry[] = file.entries

/** The page the catalogue was read from, and when. */
export const PROVENANCE = { source: file.source, read: file.read } as const

export const byId = (id: string): CatalogueEntry | undefined =>
  CATALOGUE.find((e) => e.id === id)

/** The `Source` a transcription of this entry should carry. */
export const sourceOf = (entry: CatalogueEntry): Source => ({
  url: entry.url,
  listedAt: PROVENANCE.source,
  read: PROVENANCE.read,
})

export const corpsList = (): readonly string[] =>
  [...new Set(CATALOGUE.map((e) => e.corps))].sort((a, b) => a.localeCompare(b))

export const years = (): readonly number[] =>
  [...new Set(CATALOGUE.flatMap((e) => (e.year === undefined ? [] : [e.year])))].sort(
    (a, b) => a - b,
  )

export type Filter = {
  circuit?: Circuit
  corps?: string
  year?: number
  /** Matched against title and corps, case-insensitively. */
  text?: string
}

export const filter = (f: Filter): readonly CatalogueEntry[] => {
  const needle = f.text?.trim().toLowerCase()
  return CATALOGUE.filter(
    (e) =>
      (f.circuit === undefined || e.circuit === f.circuit) &&
      (f.corps === undefined || e.corps === f.corps) &&
      (f.year === undefined || e.year === f.year) &&
      (needle === undefined ||
        needle === '' ||
        e.title.toLowerCase().includes(needle) ||
        e.corps.toLowerCase().includes(needle)),
  )
}
