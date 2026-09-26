import { describe, expect, it } from 'vitest'
import { type Event } from './stroke'
import { SIXTEENTH, QUARTER, EIGHTH, tuplet } from './duration'
import { explain, judge } from './confidence'

const strokes = (duration: Event['duration'], count: number): Event[] =>
  Array.from({ length: count }, () => ({ duration }))

describe('judge', () => {
  it('trusts a bar whose durations fill its metre', () => {
    expect(judge({ meter: [4, 4], events: strokes(SIXTEENTH, 16) })).toEqual({ trusted: true })
  })

  it('flags a bar that comes up short, and says by how much', () => {
    const verdict = judge({ meter: [4, 4], events: strokes(SIXTEENTH, 15) })
    expect(verdict.trusted).toBe(false)
    if (verdict.trusted) return
    expect(verdict.concerns).toEqual([
      { kind: 'arithmetic', played: [15, 4], expected: [4, 1] },
    ])
  })

  /**
   * Triplets are the case that made exact arithmetic non-negotiable: in
   * floating point this bar does not fill, and every triplet passage in the
   * catalogue would be flagged.
   */
  it('trusts a bar of triplets', () => {
    const third = tuplet(EIGHTH, 3, 2)
    expect(judge({ meter: [4, 4], events: strokes(third, 12) })).toEqual({ trusted: true })
  })

  it('understands metres other than four-four', () => {
    expect(judge({ meter: [6, 8], events: strokes(EIGHTH, 6) })).toEqual({ trusted: true })
    expect(judge({ meter: [7, 8], events: strokes(EIGHTH, 7) })).toEqual({ trusted: true })
    expect(judge({ meter: [2, 2], events: strokes(QUARTER, 4) })).toEqual({ trusted: true })
  })

  it('flags an unnamed symbol even when the arithmetic closes', () => {
    const verdict = judge({ meter: [4, 4], events: strokes(QUARTER, 4), unnamedSymbols: 2 })
    expect(verdict.trusted).toBe(false)
    if (verdict.trusted) return
    expect(verdict.concerns).toContainEqual({ kind: 'unnamedSymbols', count: 2 })
  })

  it('flags an empty bar, which printed music never is', () => {
    const verdict = judge({ meter: [4, 4], events: [] })
    expect(verdict.trusted).toBe(false)
    if (verdict.trusted) return
    expect(verdict.concerns).toContainEqual({ kind: 'empty' })
    // With nothing read, there is no arithmetic to report on top of it.
    expect(verdict.concerns.some((c) => c.kind === 'arithmetic')).toBe(false)
  })

  it('flags a bar with no metre in force rather than guessing one', () => {
    const verdict = judge({ meter: null, events: strokes(QUARTER, 4) })
    expect(verdict.trusted).toBe(false)
    if (verdict.trusted) return
    expect(verdict.concerns).toEqual([{ kind: 'meterUnknown' }])
  })

  it('reports every concern at once, not just the first', () => {
    const verdict = judge({ meter: [4, 4], events: strokes(SIXTEENTH, 3), unnamedSymbols: 1 })
    expect(verdict.trusted).toBe(false)
    if (verdict.trusted) return
    expect(verdict.concerns.map((c) => c.kind).sort()).toEqual(['arithmetic', 'unnamedSymbols'])
  })

  /**
   * Bar width on the page is deliberately not a signal. An earlier version
   * treated an unusually wide bar as evidence of a missed barline and flagged
   * correct music; engraving widens a bar legitimately when it is denser.
   */
  it('does not care how much room the bar took on the page', () => {
    expect(judge({ meter: [4, 4], events: strokes(SIXTEENTH, 16) })).toEqual({ trusted: true })
    expect(judge({ meter: [4, 4], events: strokes(QUARTER, 4) })).toEqual({ trusted: true })
  })
})

describe('explain', () => {
  it('gives one readable line per concern', () => {
    expect(explain({ kind: 'arithmetic', played: [15, 4], expected: [4, 1] }))
      .toBe('15/4 temps lus, 4 attendus')
    expect(explain({ kind: 'unnamedSymbols', count: 1 })).toContain('un symbole')
    expect(explain({ kind: 'unnamedSymbols', count: 3 })).toContain('3 symboles')
    expect(explain({ kind: 'empty' })).toContain('vide')
    expect(explain({ kind: 'meterUnknown' })).toContain('métrique')
  })
})

describe('durations measured rather than read', () => {
  it('reports a bar whose lengths came from spacing, even when it closes', () => {
    const verdict = judge({
      meter: [4, 4],
      events: strokes(QUARTER, 4),
      readFrom: 'spacing',
    })
    expect(verdict.trusted).toBe(false)
    expect(verdict.trusted === false && verdict.concerns).toContainEqual({
      kind: 'spacingOnly',
    })
  })

  it('trusts the same bar when its lengths were read from the notation', () => {
    expect(
      judge({
        meter: [4, 4],
        events: strokes(QUARTER, 4),
        readFrom: 'notation',
      }).trusted,
    ).toBe(true)
  })
})

describe('two voices on one staff', () => {
  it('refuses a divisi bar even when its two voices happen to close', () => {
    // One does: five quarters in 5/4, a snare part and a bass part read into
    // one stream. The arithmetic has nothing to object to, which is exactly
    // why the reading has to say so itself.
    const verdict = judge({
      meter: [5, 4],
      events: strokes(QUARTER, 5),
      readFrom: 'polyphonic',
    })
    expect(verdict.trusted).toBe(false)
    expect(verdict.trusted === false && verdict.concerns).toContainEqual({
      kind: 'polyphonic',
    })
  })

  it('says so as well as reporting the arithmetic, not instead of it', () => {
    // A divisi usually sums to about twice its metre. Both facts are kept: the
    // arithmetic is the evidence, the divisi is what it means.
    const verdict = judge({
      meter: [4, 4],
      events: strokes(QUARTER, 8),
      readFrom: 'polyphonic',
    })
    expect(verdict.trusted === false && verdict.concerns.map((c) => c.kind))
      .toEqual(expect.arrayContaining(['polyphonic', 'arithmetic']))
  })
})
