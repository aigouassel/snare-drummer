import { describe, expect, it } from 'vitest'
import {
  PROVENANCE, SEQUENCE_COUNT, WORKS, corpsList, filter, findSequence, sourceOf,
  workById, workTitle, years,
} from './catalogue'

/**
 * These assert the shape of scraped data, which is the only thing standing
 * between a site redesign and a silently emptied library. A scraper that
 * stops matching does not throw — it returns fewer rows — so the checks that
 * matter are about volume and completeness, not about any one entry.
 */
describe('catalogue', () => {
  it('holds the whole listing, grouped into shows', () => {
    expect(SEQUENCE_COUNT).toBeGreaterThan(800)
    expect(WORKS.length).toBeGreaterThan(300)
    expect(WORKS.length).toBeLessThan(SEQUENCE_COUNT)
  })

  it('gives every work a corps, a circuit and at least one sequence', () => {
    for (const work of WORKS) {
      expect(work.id).toMatch(/^[a-z0-9-]+$/)
      expect(work.corps.length).toBeGreaterThan(0)
      expect(['DCI', 'WGI', 'DCA', 'other']).toContain(work.circuit)
      expect(work.sequences.length).toBeGreaterThan(0)
    }
  })

  it('gives every sequence a title and a PDF URL', () => {
    for (const work of WORKS) {
      for (const sequence of work.sequences) {
        expect(sequence.title.length).toBeGreaterThan(0)
        expect(sequence.url).toMatch(/^https:\/\/lothype\.com\/.*\.pdf$/)
      }
    }
  })

  it('keeps work ids and sequence ids unique across the catalogue', () => {
    expect(new Set(WORKS.map((w) => w.id)).size).toBe(WORKS.length)
    const sequences = WORKS.flatMap((w) => w.sequences.map((s) => s.id))
    expect(new Set(sequences).size).toBe(sequences.length)
  })

  /**
   * The grouping is the point of this module. A show written in several
   * passages must come back as one work holding several sequences — flat, it
   * was 884 unrelated rows.
   */
  it('groups a season that was written in several passages', () => {
    const many = WORKS.filter((w) => w.sequences.length > 1)
    expect(many.length).toBeGreaterThan(100)
    const biggest = WORKS.reduce((a, b) => (a.sequences.length >= b.sequences.length ? a : b))
    expect(biggest.sequences.length).toBeGreaterThan(5)
  })

  it('never puts two seasons of one corps in the same work', () => {
    const seen = new Set<string>()
    for (const work of WORKS) {
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
