import { describe, expect, it } from 'vitest'
import { type Bar } from './bar'
import { EIGHTH, QUARTER, SIXTEENTH } from './duration'
import { atSeconds, dynamicBefore, lengthInBeats, place, selectBars } from './timeline'

const bar = (n: number, events: Bar['events'], meter: Bar['meter'] = [4, 4]): Bar => ({
  n, meter, events, verdict: { trusted: true },
})

const four = [
  { duration: QUARTER, hand: 'right' as const },
  { duration: QUARTER, hand: 'left' as const },
  { duration: QUARTER, hand: 'right' as const },
  { duration: QUARTER, hand: 'left' as const },
]

describe('place', () => {
  it('lays bars end to end', () => {
    const placed = place([bar(1, four), bar(2, four)])
    expect(placed).toHaveLength(8)
    expect(placed[0]?.atBeat).toEqual([0, 1])
    expect(placed[4]?.atBeat).toEqual([4, 1])
    expect(placed[4]?.bar).toBe(2)
  })

  it('advances past rests without emitting them', () => {
    const placed = place([bar(1, [{ rest: true, duration: QUARTER }, ...four.slice(0, 3)])])
    expect(placed).toHaveLength(3)
    expect(placed[0]?.atBeat).toEqual([1, 1])
    // The index counts rests, so a drawn note can be found again by position.
    expect(placed[0]?.index).toBe(1)
  })

  /**
   * The point of laying bars out by their written length: a bar whose contents
   * were misread is wrong on its own, and the bars after it still start where
   * the page says they start.
   */
  it('keeps a short bar from dragging the rest of the piece off the beat', () => {
    const short = bar(1, [{ duration: EIGHTH }])      // a 4/4 bar holding half a beat
    const placed = place([short, bar(2, four)])
    expect(placed[1]?.atBeat).toEqual([4, 1])
    expect(placed[1]?.bar).toBe(2)
  })

  it('handles a metre that is not a whole number of beats', () => {
    const seven = bar(1, Array.from({ length: 7 }, () => ({ duration: EIGHTH })), [7, 8])
    expect(lengthInBeats([seven])).toEqual([7, 2])
  })
})

describe('selectBars', () => {
  it('takes a range by the bars own numbering, inclusive', () => {
    const bars = [bar(1, four), bar(2, four), bar(3, four), bar(4, four)]
    expect(selectBars(bars, 2, 3).map((b) => b.n)).toEqual([2, 3])
    expect(selectBars(bars, 3, 3).map((b) => b.n)).toEqual([3])
    expect(selectBars(bars, 9, 12)).toEqual([])
  })
})

describe('atSeconds', () => {
  it('converts beats to seconds at a tempo', () => {
    expect(atSeconds([4, 1], 120)).toBe(2)
    expect(atSeconds([1, 4], 60)).toBe(0.25)
  })

  it('is exact on a triplet, which decimal beats are not', () => {
    expect(atSeconds([1, 3], 60)).toBeCloseTo(1 / 3, 12)
  })

  it('slows down as the tempo drops, which is how this music is practised', () => {
    expect(atSeconds([16, 1], 60)).toBe(16)
    expect(atSeconds([16, 1], 160)).toBe(6)
  })
})

describe('SIXTEENTH', () => {
  it('is a quarter of a beat', () => {
    expect(SIXTEENTH).toEqual([1, 4])
  })
})

describe('dynamics in force', () => {
  /**
   * A page marks a dynamic once and means it until it says otherwise, so
   * almost every note carries none of its own. Resolving that here keeps one
   * answer to "how loud is this note" rather than one per consumer.
   */
  it('carries a printed dynamic forward to the notes after it', () => {
    const placed = place([
      bar(1, [
        { duration: QUARTER, dynamic: 'p' as const },
        { duration: QUARTER },
        { duration: QUARTER, dynamic: 'ff' as const },
        { duration: QUARTER },
      ]),
      bar(2, [{ duration: QUARTER }, { duration: QUARTER }, { duration: QUARTER },
              { duration: QUARTER }]),
    ])
    expect(placed.map((s) => s.dynamic)).toEqual([
      'p', 'p', 'ff', 'ff', 'ff', 'ff', 'ff', 'ff',
    ])
  })

  it('leaves it absent until the page prints one', () => {
    const placed = place([
      bar(1, [{ duration: QUARTER }, { duration: QUARTER, dynamic: 'mf' as const },
              { duration: QUARTER }, { duration: QUARTER }]),
    ])
    // Absent is not a quiet default: a score that marks nothing is played at
    // one weight, and one that opens pianissimo is not.
    expect(placed[0]?.dynamic).toBeUndefined()
    expect(placed[1]?.dynamic).toBe('mf')
  })

  it('starts a selection at the dynamic still in force before it', () => {
    const bars = [
      bar(1, [{ duration: QUARTER, dynamic: 'pp' as const }, { duration: QUARTER },
              { duration: QUARTER }, { duration: QUARTER }]),
      bar(2, four),
      bar(3, four),
    ]
    expect(dynamicBefore(bars, 3)).toBe('pp')
    expect(dynamicBefore(bars, 1)).toBeUndefined()
    const placed = place(selectBars(bars, 3, 3), dynamicBefore(bars, 3))
    expect(placed.every((s) => s.dynamic === 'pp')).toBe(true)
  })

  it('takes the last dynamic before the selection, not the first', () => {
    const bars = [
      bar(1, [{ duration: QUARTER, dynamic: 'pp' as const }, { duration: QUARTER },
              { duration: QUARTER }, { duration: QUARTER, dynamic: 'f' as const }]),
      bar(2, four),
    ]
    expect(dynamicBefore(bars, 2)).toBe('f')
  })
})
