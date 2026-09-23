import { type Bar, barBeats } from '@snare-drummer/core/bar'
import { toNumber } from '@snare-drummer/core/fraction'

/**
 * Where the music goes: which bars share a row, and how wide each one is.
 *
 * This is deliberately separate from the drawing. `score.ts` needs a real DOM
 * element and an SVG backend, so nothing inside it can be tested here —
 * whereas every decision about *layout* is arithmetic, and arithmetic that
 * gets a bar's width wrong is exactly the kind of mistake that looks fine
 * until the music runs off the edge of the row.
 *
 * A **system** is one row of staves, one stave per bar. Keeping a bar whole
 * within a row is what puts beams and tuplets inside the bar they belong to,
 * and it is also what lets a suspect bar be outlined on its own.
 */

/** Rough width of a bar before packing, in pixels. */
export const naturalWidth = (bar: Bar, options: Options): number => {
  // Two things drive how much room a bar needs: how many notes are in it, and
  // how long it is. Neither alone is enough — a 12/8 bar of twelve eighths and
  // a 4/4 bar of twelve triplets hold the same count in different spans.
  const notes = Math.max(bar.events.length, 1)
  const beats = toNumber(barBeats(bar.meter))
  const byNotes = notes * options.perNote
  const byLength = beats * options.perBeat
  return Math.max(options.minBar, Math.max(byNotes, byLength))
}

export type Options = {
  /** Width available for staves, excluding any page margin. */
  width: number
  /** Pixels a single note needs. */
  perNote: number
  /** Pixels a quarter-note beat needs. */
  perBeat: number
  minBar: number
  /** Never put more than this many bars in a row, however short they are. */
  maxPerRow: number
}

export const DEFAULTS: Omit<Options, 'width'> = {
  perNote: 26,
  perBeat: 34,
  minBar: 140,
  maxPerRow: 4,
}

export type PlacedBar = { bar: Bar; x: number; width: number }
export type System = { bars: readonly PlacedBar[]; width: number }

/**
 * Pack bars into rows, then stretch each row to fill the width.
 *
 * Stretching rather than left-aligning is what makes a page of music look
 * like a page of music. The last row is left unstretched on purpose: a final
 * bar pulled across the full width reads as a mistake rather than a flourish.
 */
export const layout = (bars: readonly Bar[], options: Options): readonly System[] => {
  const systems: System[] = []
  let row: Bar[] = []
  let used = 0

  const flush = (stretch: boolean) => {
    if (row.length === 0) return
    const widths = row.map((b) => naturalWidth(b, options))
    const total = widths.reduce((a, b) => a + b, 0)
    const scale = stretch && total > 0 ? options.width / total : 1
    let x = 0
    const placed = row.map((bar, i) => {
      const width = (widths[i] ?? options.minBar) * scale
      const item = { bar, x, width }
      x += width
      return item
    })
    systems.push({ bars: placed, width: x })
    row = []
    used = 0
  }

  for (const bar of bars) {
    const width = naturalWidth(bar, options)
    const wouldOverflow = used + width > options.width && row.length > 0
    if (wouldOverflow || row.length >= options.maxPerRow) flush(true)
    row.push(bar)
    used += width
  }
  flush(false)

  return systems
}

/** Which row a bar landed on, for scrolling to it. */
export const systemOf = (systems: readonly System[], barNumber: number): number =>
  systems.findIndex((s) => s.bars.some((p) => p.bar.n === barNumber))
