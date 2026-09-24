import { describe, expect, it } from 'vitest'
import {
  LISTED_COUNT, LISTED_WORKS, PROVENANCE, SEQUENCE_COUNT, WORKS, corpsList,
  filter, findSequence, sourceOf, workById, workTitle, years,
} from './catalogue'

/**
 * These assert the shape of scraped data, which is the only thing standing
 * between a site redesign and a silently emptied library. A scraper that
 * stops matching does not throw — it returns fewer rows — so the checks that
 * matter are about volume and completeness, not about any one entry.
 */
describe('catalogue', () => {
  it('holds the whole listing, grouped into shows', () => {
    expect(LISTED_COUNT.sequences).toBeGreaterThan(800)
    expect(LISTED_COUNT.works).toBeGreaterThan(300)
    expect(LISTED_COUNT.works).toBeLessThan(LISTED_COUNT.sequences)
    expect(LISTED_WORKS.length).toBe(LISTED_COUNT.works)
  })

  it('gives every work a corps, a circuit and at least one sequence', () => {
    for (const work of LISTED_WORKS) {
      expect(work.id).toMatch(/^[a-z0-9-]+$/)
      expect(work.corps.length).toBeGreaterThan(0)
      expect(['DCI', 'WGI', 'DCA', 'other']).toContain(work.circuit)
      expect(work.sequences.length).toBeGreaterThan(0)
    }
  })

  it('gives every sequence a title and a PDF URL', () => {
    for (const work of LISTED_WORKS) {
      for (const sequence of work.sequences) {
        expect(sequence.title.length).toBeGreaterThan(0)
        expect(sequence.url).toMatch(/^https:\/\/lothype\.com\/.*\.pdf$/)
      }
    }
  })

  it('keeps work ids and sequence ids unique across the catalogue', () => {
    expect(new Set(LISTED_WORKS.map((w) => w.id)).size).toBe(LISTED_WORKS.length)
    const sequences = LISTED_WORKS.flatMap((w) => w.sequences.map((s) => s.id))
    expect(new Set(sequences).size).toBe(sequences.length)
  })

  /**
   * The grouping is the point of this module. A show written in several
   * passages must come back as one work holding several sequences — flat, it
   * was 884 unrelated rows.
   */
  it('groups a season that was written in several passages', () => {
    const many = LISTED_WORKS.filter((w) => w.sequences.length > 1)
    expect(many.length).toBeGreaterThan(100)
    const biggest = LISTED_WORKS.reduce(
      (a, b) => (a.sequences.length >= b.sequences.length ? a : b),
    )
    expect(biggest.sequences.length).toBeGreaterThan(5)
  })

  it('never puts two seasons of one corps in the same work', () => {
    const seen = new Set<string>()
    for (const work of LISTED_WORKS) {
      const key = `${work.corps}|${work.year ?? ''}`
      expect(seen.has(key)).toBe(false)
      seen.add(key)
    }
  })

  it('records where and when it was read', () => {
    expect(PROVENANCE.source).toMatch(/^https:\/\/lothype\.com\//)
    expect(PROVENANCE.read).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('dates the great majority of works', () => {
    const dated = WORKS.filter((w) => w.year !== undefined)
    expect(dated.length / WORKS.length).toBeGreaterThan(0.8)
    for (const y of years()) expect(y).toBeGreaterThan(1960)
  })

  it('finds a work by id, and a sequence with the work holding it', () => {
    const work = WORKS[0]
    expect(work).toBeDefined()
    if (!work) return
    expect(workById(work.id)).toBe(work)

    const sequence = work.sequences[0]
    expect(sequence).toBeDefined()
    if (!sequence) return
    const found = findSequence(sequence.id)
    expect(found?.work).toBe(work)
    expect(found?.sequence).toBe(sequence)
    expect(findSequence('no-such-sequence')).toBeUndefined()

    expect(sourceOf(sequence)).toEqual({
      url: sequence.url,
      listedAt: PROVENANCE.source,
      read: PROVENANCE.read,
    })
  })

  it('names a work by its corps and season', () => {
    expect(workTitle({ id: 'x', corps: 'Blue Devils', circuit: 'DCI', year: 2019, sequences: [] }))
      .toBe('Blue Devils 2019')
    expect(workTitle({ id: 'x', corps: 'Blue Devils', circuit: 'DCI', sequences: [] }))
      .toContain('sans année')
  })

  it('filters by circuit, corps, year, and text matched against sequences too', () => {
    expect(filter({ circuit: 'DCI' }).every((w) => w.circuit === 'DCI')).toBe(true)
    const corps = corpsList()[0]
    expect(corps).toBeDefined()
    if (!corps) return
    expect(filter({ corps }).every((w) => w.corps === corps)).toBe(true)
    expect(filter({}).length).toBe(WORKS.length)
    expect(filter({ text: '   ' }).length).toBe(WORKS.length)
    // A sequence title is searchable even though it is not the work's name.
    expect(filter({ text: 'opener' }).length).toBeGreaterThan(0)
  })

  it('lists more than sixty ensembles', () => {
    expect(corpsList().length).toBeGreaterThan(60)
  })
})

/**
 * The repertoire is a reading of the listing, not a subset of it chosen by
 * hand, so what is asserted is the rule: one season per corps, and that
 * season the latest one the page holds.
 */
describe('the repertoire', () => {
  it('keeps exactly one season of each corps', () => {
    const perCorps = new Map<string, number>()
    for (const work of WORKS) {
      perCorps.set(work.corps, (perCorps.get(work.corps) ?? 0) + 1)
    }
    for (const [corps, count] of perCorps) {
      expect(count, `${corps} appears ${count} times`).toBe(1)
    }
    expect(perCorps.size).toBe(corpsList().length)
  })

  /**
   * The reduction to one season per corps must not quietly lose a corps —
   * that is the difference between narrowing a library and shrinking it.
   *
   * There is one exception, and it is not a shortfall of the reduction: a
   * corps every one of whose listed sequences is a scan has nothing this
   * project can read, in any season. Stated as a list rather than tolerated
   * as a count, so that a second one appearing has to be looked at.
   */
  it('loses no corps from the listing, except those with nothing readable', () => {
    const readable = (work: (typeof LISTED_WORKS)[number]) =>
      work.sequences.some((s) => !s.scanned)
    const expected = new Set(
      LISTED_WORKS.filter(readable).map((w) => w.corps),
    )
    expect(new Set(WORKS.map((w) => w.corps))).toEqual(expected)

    const lost = [...new Set(LISTED_WORKS.map((w) => w.corps))].filter(
      (corps) => !expected.has(corps),
    )
    expect(lost).toEqual(['Anaheim Kingsmen'])
  })

  it('keeps no scanned sequence in the repertoire', () => {
    for (const work of WORKS) {
      for (const sequence of work.sequences) {
        expect(sequence.scanned, `${sequence.id} is a scan`).toBeUndefined()
      }
    }
    // And the listing still holds it, because it does exist.
    const scanned = LISTED_WORKS.flatMap((w) => w.sequences).filter((s) => s.scanned)
    expect(scanned.map((s) => s.id)).toEqual(['1971-drum-break'])
  })

  it('keeps the latest season a corps has, and no earlier one', () => {
    for (const work of WORKS) {
      const seasons = LISTED_WORKS.filter((w) => w.corps === work.corps)
      const dated = seasons.filter((w) => w.year !== undefined)
      if (dated.length === 0) {
        // Nothing to prefer it to: an undated entry stands for its corps.
        expect(work.year).toBeUndefined()
        continue
      }
      // A corps that has dated seasons loses its undated entry, which cannot
      // be shown to be the most recent.
      expect(work.year).toBe(Math.max(...dated.map((w) => w.year as number)))
    }
  })

  it('is a real reduction, and stays a small multiple of its corps', () => {
    expect(WORKS.length).toBeLessThan(LISTED_COUNT.works / 3)
    expect(SEQUENCE_COUNT).toBeLessThan(LISTED_COUNT.sequences / 3)
    expect(SEQUENCE_COUNT).toBeGreaterThan(WORKS.length)
  })

  it('reaches every repertoire sequence through findSequence', () => {
    for (const work of WORKS) {
      for (const sequence of work.sequences) {
        expect(findSequence(sequence.id)?.work.id).toBe(work.id)
      }
    }
  })
})
