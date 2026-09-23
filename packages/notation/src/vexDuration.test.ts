import { describe, expect, it } from 'vitest'
import { EIGHTH, QUARTER, SIXTEENTH, WHOLE, dotted, tuplet } from '@snare-drummer/core/duration'
import { resolve } from './vexDuration'

describe('resolve', () => {
  it('reads the plain note values', () => {
    expect(resolve(WHOLE)).toEqual({ glyph: 'w', dots: 0 })
    expect(resolve(QUARTER)).toEqual({ glyph: 'q', dots: 0 })
    expect(resolve(SIXTEENTH)).toEqual({ glyph: '16', dots: 0 })
    expect(resolve([1, 16])).toEqual({ glyph: '64', dots: 0 })
  })

  it('reads dotted values as dots, not as tuplets', () => {
    expect(resolve(dotted(QUARTER))).toEqual({ glyph: 'q', dots: 1 })
    expect(resolve(dotted(EIGHTH))).toEqual({ glyph: '8', dots: 1 })
    expect(resolve(dotted(QUARTER, 2))).toEqual({ glyph: 'q', dots: 2 })
  })

  it('reads triplets', () => {
    expect(resolve(tuplet(EIGHTH, 3, 2))).toEqual({
      glyph: '8', dots: 0, tuplet: { notes: 3, inSpaceOf: 2 },
    })
    expect(resolve(tuplet(SIXTEENTH, 3, 2))).toEqual({
      glyph: '16', dots: 0, tuplet: { notes: 3, inSpaceOf: 2 },
    })
  })

  it('reads the quintuplets this repertoire is full of', () => {
    expect(resolve(tuplet(SIXTEENTH, 5, 4))).toEqual({
      glyph: '16', dots: 0, tuplet: { notes: 5, inSpaceOf: 4 },
    })
  })

  /**
   * The point of the bounded tuplet list. Any length can be written as some
   * ratio, so an open-ended search would rescue a measurement error by
   * inventing an absurd tuplet — and destroy the evidence that the bar was
   * misread. Refusing is the useful answer.
   */
  it('refuses a length no engraver writes', () => {
    expect(resolve([1, 23])).toBeNull()
    expect(resolve([5, 37])).toBeNull()
  })

  it('refuses zero and negative lengths', () => {
    expect(resolve([0, 1])).toBeNull()
    expect(resolve([-1, 4])).toBeNull()
  })

  it('prefers a plain value over a tuplet that would also fit', () => {
    // 1/2 is an eighth, never "a quarter in the time of two".
    expect(resolve([1, 2])?.tuplet).toBeUndefined()
  })
})
