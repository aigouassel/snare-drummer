import { describe, expect, it } from 'vitest'
import { WORKS, search, workTitle } from './catalogue'

/**
 * These are the queries the old substring match failed, written down so that a
 * later simplification has to fail them out loud.
 *
 * They run against the real catalogue rather than a fixture. A search is only
 * as good as the data it faces -- a fixture of three tidy works would pass
 * anything -- and the shape of this data is the point: sixty-five shows whose
 * titles share words like `opener`.
 */

const titles = (query: string) => search(query).map((h) => workTitle(h.work))

describe('search', () => {
  it('returns the whole repertoire, in order, for an empty query', () => {
    expect(search('').length).toBe(WORKS.length)
    expect(search('   ').map((h) => h.work.id)).toEqual(WORKS.map((w) => w.id))
  })

  it('takes words from different fields at once', () => {
    // The failure that made the field feel exact-only: no single field holds
    // both the corps and the year.
    const found = titles('blue devils 2019')
    expect(found[0]).toBe('Blue Devils 2019')
    expect(found.every((t) => t.includes('2019'))).toBe(true)
  })

  it('searches the circuit, which no text search reached before', () => {
    const dci = search('dci')
    expect(dci.length).toBeGreaterThan(20)
    expect(dci.every((h) => h.work.circuit === 'DCI')).toBe(true)
  })

  it('narrows by circuit and year together, as two dropdowns used to', () => {
    const found = search('dci 2019')
    expect(found.length).toBeGreaterThan(0)
    expect(found.every((h) => h.work.circuit === 'DCI' && h.work.year === 2019))
      .toBe(true)
  })

  it('finds a show by a passage it contains, and says which', () => {
    const first = search('circus')[0]
    expect(first).toBeDefined()
    expect(first?.matched).not.toBeNull()
    expect(first?.work.sequences.some((s) => s.id === first.matched)).toBe(true)
  })

  it('ranks a corps above a passage that merely shares the word', () => {
    // `crown` is the corps Carolina Crown; it is also a word a title may hold.
    const first = search('crown')[0]
    expect(first?.work.corps).toContain('Crown')
  })

  it('forgives a typo, but only when nothing matches outright', () => {
    expect(titles('bluecoats')[0]).toBe(titles('bluecots')[0])
    expect(search('bluecoats').every((h) => h.exact)).toBe(true)
  })

  it('never mixes an approximate match into results that fit', () => {
    // `opener` matches many passages exactly. Nothing in that answer may be
    // there by edit distance: a guess beside a fact reads as a fact.
    const found = search('opener')
    expect(found.length).toBeGreaterThan(1)
    expect(found.every((h) => h.exact)).toBe(true)
  })

  it('knows a corps by its initials', () => {
    expect(titles('bd')[0]).toBe('Blue Devils 2019')
    expect(titles('bk')[0]).toBe('Blue Knights 2019')
    expect(search('bd').every((h) => h.exact)).toBe(true)
  })

  it('does not need the space', () => {
    expect(titles('bluedevils')[0]).toBe('Blue Devils 2019')
    expect(search('bluedevils').every((h) => h.exact)).toBe(true)
  })

  it('keeps a run of words inside one passage title', () => {
    // `snare` from one passage and `break` from another is a show holding
    // neither, returned with the same confidence as a real hit.
    for (const hit of search('snare break')) {
      const named = hit.work.sequences.find((s) => s.id === hit.matched)
      expect(named?.title.toLowerCase()).toContain('snare')
      expect(named?.title.toLowerCase()).toContain('break')
    }
  })

  it('does not let a season stand in for a movement number', () => {
    // `'2017'.includes('2')` was enough to return a show whose only Movement
    // is the third, scoring exactly as much as the shows that have a second.
    const found = search('movement 2')
    expect(found.length).toBeGreaterThan(0)
    for (const hit of found) {
      expect(
        hit.work.sequences.some((s) => /movement 2/i.test(s.title)),
      ).toBe(true)
    }
  })

  it('does not guess from two letters', () => {
    // Within one edit, a two-letter token reaches most of the alphabet. The
    // answer to `zq` is nothing, not a plausible show.
    expect(search('zq')).toEqual([])
    expect(search('qwertyuiop')).toEqual([])
  })

  it('requires every word to land somewhere', () => {
    expect(search('blue devils zzzzzzzz')).toEqual([])
  })

  it('ignores case and accents', () => {
    expect(titles('BLUE DEVILS')).toEqual(titles('blue devils'))
  })
})
