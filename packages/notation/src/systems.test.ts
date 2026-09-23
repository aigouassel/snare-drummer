import { describe, expect, it } from 'vitest'
import { type Bar } from '@snare-drummer/core/bar'
import { EIGHTH, QUARTER, SIXTEENTH } from '@snare-drummer/core/duration'
import { DEFAULTS, layout, naturalWidth, systemOf } from './systems'

const bar = (n: number, notes: number, duration = SIXTEENTH, meter: Bar['meter'] = [4, 4]): Bar => ({
  n,
  meter,
  events: Array.from({ length: notes }, () => ({ duration })),
  verdict: { trusted: true },
})

const options = { ...DEFAULTS, width: 900 }

describe('naturalWidth', () => {
  it('grows with the number of notes', () => {
    expect(naturalWidth(bar(1, 16), options)).toBeGreaterThan(
      naturalWidth(bar(1, 4, QUARTER), options),
    )
  })

  it('never goes below the minimum, however empty the bar', () => {
    expect(naturalWidth(bar(1, 0), options)).toBe(options.minBar)
    expect(naturalWidth(bar(1, 1, QUARTER), options)).toBeGreaterThanOrEqual(options.minBar)
  })

  it('accounts for a long bar even when it holds few notes', () => {
    const long = bar(1, 2, QUARTER, [12, 8])
    const short = bar(2, 2, QUARTER, [2, 4])
    expect(naturalWidth(long, options)).toBeGreaterThan(naturalWidth(short, options))
  })
})

describe('layout', () => {
  it('puts nothing on a row it cannot fit', () => {
    const bars = Array.from({ length: 12 }, (_v, i) => bar(i + 1, 16))
    for (const system of layout(bars, options)) {
      expect(system.bars.length).toBeLessThanOrEqual(options.maxPerRow)
    }
  })

  it('keeps every bar, exactly once, in order', () => {
    const bars = Array.from({ length: 11 }, (_v, i) => bar(i + 1, 16))
    const laid = layout(bars, options).flatMap((s) => s.bars.map((p) => p.bar.n))
    expect(laid).toEqual(bars.map((b) => b.n))
  })

  it('stretches a full row to the available width, but not the last one', () => {
    const bars = Array.from({ length: 9 }, (_v, i) => bar(i + 1, 16))
    const systems = layout(bars, options)
    expect(systems.length).toBeGreaterThan(1)
    for (const system of systems.slice(0, -1)) {
      expect(system.width).toBeCloseTo(options.width, 6)
    }
    const last = systems[systems.length - 1]
    expect(last).toBeDefined()
    if (!last) return
    expect(last.width).toBeLessThanOrEqual(options.width + 0.001)
  })

  it('never overlaps two bars on a row', () => {
    const bars = Array.from({ length: 10 }, (_v, i) => bar(i + 1, i % 3 === 0 ? 4 : 16, EIGHTH))
    for (const system of layout(bars, options)) {
      let edge = 0
      for (const placed of system.bars) {
        expect(placed.x).toBeCloseTo(edge, 6)
        edge += placed.width
      }
    }
  })

  it('handles an empty piece', () => {
    expect(layout([], options)).toEqual([])
  })

  it('finds which row a bar landed on', () => {
    const bars = Array.from({ length: 9 }, (_v, i) => bar(i + 1, 16))
    const systems = layout(bars, options)
    expect(systemOf(systems, 1)).toBe(0)
    expect(systemOf(systems, 9)).toBe(systems.length - 1)
    expect(systemOf(systems, 99)).toBe(-1)
  })
})
