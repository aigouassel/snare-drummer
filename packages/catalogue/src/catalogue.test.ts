import { describe, expect, it } from 'vitest'
import { CATALOGUE, PROVENANCE, byId, corpsList, filter, sourceOf, years } from './catalogue'

/**
 * These assert the shape of scraped data, which is the only thing standing
 * between a site redesign and a silently emptied library. A scraper that
 * stops matching does not throw — it returns fewer rows — so the checks that
 * matter are about volume and completeness, not about any one entry.
 */
describe('catalogue', () => {
  it('holds the whole listing', () => {
    expect(CATALOGUE.length).toBeGreaterThan(800)
  })

  it('gives every entry an id, a title, a corps, a circuit and a URL', () => {
    for (const e of CATALOGUE) {
      expect(e.id).toMatch(/^[a-z0-9-]+$/)
      expect(e.title.length).toBeGreaterThan(0)
      expect(e.corps.length).toBeGreaterThan(0)
      expect(['DCI', 'WGI', 'DCA', 'other']).toContain(e.circuit)
      expect(e.url).toMatch(/^https:\/\/lothype\.com\/.*\.pdf$/)
    }
  })

  it('keeps ids unique, so one entry cannot shadow another', () => {
    expect(new Set(CATALOGUE.map((e) => e.id)).size).toBe(CATALOGUE.length)
  })

  it('records where and when it was read', () => {
    expect(PROVENANCE.source).toMatch(/^https:\/\/lothype\.com\//)
    expect(PROVENANCE.read).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('carries a year on the great majority of entries', () => {
    const dated = CATALOGUE.filter((e) => e.year !== undefined)
    expect(dated.length / CATALOGUE.length).toBeGreaterThan(0.9)
    for (const y of years()) expect(y).toBeGreaterThan(1960)
  })

  it('does not repeat the corps at the end of the title', () => {
    for (const e of CATALOGUE) expect(e.title.endsWith(e.corps)).toBe(false)
  })

  it('looks an entry up by id and turns it into a source reference', () => {
    const first = CATALOGUE[0]
    expect(first).toBeDefined()
    if (!first) return
    expect(byId(first.id)).toBe(first)
    expect(sourceOf(first)).toEqual({
      url: first.url,
      listedAt: PROVENANCE.source,
      read: PROVENANCE.read,
    })
    expect(byId('no-such-entry')).toBeUndefined()
  })

  it('filters by circuit, corps, year and free text', () => {
    expect(filter({ circuit: 'DCI' }).every((e) => e.circuit === 'DCI')).toBe(true)
    const corps = corpsList()[0]
    expect(corps).toBeDefined()
    if (!corps) return
    expect(filter({ corps }).every((e) => e.corps === corps)).toBe(true)
    expect(filter({}).length).toBe(CATALOGUE.length)
    expect(filter({ text: '   ' }).length).toBe(CATALOGUE.length)
  })

  it('lists more than sixty ensembles', () => {
    expect(corpsList().length).toBeGreaterThan(60)
  })
})
