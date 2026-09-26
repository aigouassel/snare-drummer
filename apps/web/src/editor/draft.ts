import { type Meter, barBeats } from '@snare-drummer/core/bar'
import { type Fraction, fraction, sum } from '@snare-drummer/core/fraction'
import { type Accent, type Hand, type Roll, type Zone } from '@snare-drummer/core/stroke'
import { type RawPiece } from '@snare-drummer/transcription'

/**
 * A score being typed in, before it is a piece.
 *
 * The editor is a grid, not a staff: each bar is cut into cells of one
 * duration -- sixteenths, triplet eighths -- and a cell either starts a
 * stroke, starts a rest, or continues whatever came before it. That last kind
 * is what makes the grid musical rather than a drum machine's step sequencer:
 * a quarter note is a stroke followed by three empty sixteenth cells, and the
 * durations fall out of the spacing exactly as they do on a page.
 *
 * It also means a bar typed here *always* adds up. The grid is the bar's
 * length by construction, so the arithmetic that flags a bar read off a PDF
 * can never flag one typed in, and the verdict a hand-made bar gets is a real
 * one: trusted because it is right, not because nobody checked.
 */

/** The unit a bar is cut into, in quarter-note beats. */
export type Unit = readonly [number, number]

/**
 * The units on offer, and what each can spell. A twelfth of a beat holds both
 * straight sixteenths (three cells) and triplet sixteenths (one), which is why
 * it is here at all; it cannot hold a thirty-second, which is what the eighth
 * of a beat is for.
 */
export const UNITS: readonly { unit: Unit; label: string; hint: string }[] = [
  { unit: [1, 2], label: 'croches', hint: '2 cases par temps' },
  { unit: [1, 4], label: 'doubles', hint: '4 cases par temps' },
  { unit: [1, 6], label: 'triolets de croches', hint: '6 cases par temps' },
  { unit: [1, 12], label: 'doubles et triolets', hint: '12 cases par temps' },
  { unit: [1, 8], label: 'triples', hint: '8 cases par temps' },
]

export type Cell =
  | { kind: 'stroke'; hand?: Hand; accent?: Accent; graces?: number; roll?: Roll; zone?: Zone }
  | { kind: 'rest' }
  /** Continues the stroke or rest before it. */
  | { kind: 'hold' }

export type DraftBar = {
  meter: Meter
  unit: Unit
  cells: Cell[]
}

export type Draft = {
  id: string
  title: string
  corps: string
  /** A PDF or a page to read from, shown beside the grid when it is one. */
  sourceUrl: string
  bpm?: number
  bars: DraftBar[]
  /** ISO date of the last save. */
  savedAt: string
}

const sameFraction = (a: Fraction, b: Fraction): boolean =>
  a[0] * b[1] === b[0] * a[1]

/** How many cells a bar of this metre holds at this unit, or null if it does not divide. */
export const cellCount = (meter: Meter, unit: Unit): number | null => {
  const beats = barBeats(meter)
  // beats / unit, exactly.
  const num = beats[0] * unit[1]
  const den = beats[1] * unit[0]
  return num % den === 0 ? num / den : null
}

export const emptyBar = (meter: Meter = [4, 4], unit: Unit = [1, 4]): DraftBar => {
  const count = cellCount(meter, unit) ?? cellCount(meter, [1, 4]) ?? 16
  return { meter, unit, cells: Array.from({ length: count }, () => ({ kind: 'hold' })) }
}

export const newDraft = (fields: { title: string; corps: string; sourceUrl: string; id?: string }): Draft => ({
  id: fields.id ?? `mine-${Date.now().toString(36)}`,
  title: fields.title,
  corps: fields.corps,
  sourceUrl: fields.sourceUrl,
  bars: [emptyBar()],
  savedAt: new Date().toISOString(),
})

/**
 * Re-cut a bar at another unit, keeping every event that lands on the new
 * grid and dropping the rest. Nothing is rounded: a triplet has no place on a
 * sixteenth grid, and moving it to the nearest cell would write a rhythm the
 * player never typed.
 */
export const recut = (bar: DraftBar, meter: Meter, unit: Unit): DraftBar => {
  const count = cellCount(meter, unit)
  if (count === null) return bar
  const cells: Cell[] = Array.from({ length: count }, () => ({ kind: 'hold' }))
  bar.cells.forEach((cell, i) => {
    if (cell.kind === 'hold') return
    // Position of this cell in beats, then in new cells.
    const at = fraction(i * bar.unit[0], bar.unit[1])
    const index = fraction(at[0] * unit[1], at[1] * unit[0])
    if (index[0] % index[1] !== 0) return
    const j = index[0] / index[1]
    if (j < count) cells[j] = cell
  })
  return { meter, unit, cells }
}

/**
 * The events a bar's cells spell. A stroke or a rest lasts until the next
 * cell that is not a hold; a bar that opens with holds opens with a rest,
 * because silence is what an empty grid means and a bar has to start somewhere.
 */
export const barEvents = (bar: DraftBar): RawPiece['bars'][number]['events'] => {
  const out: { duration: [number, number]; rest?: true; hand?: string; accent?: string;
               graces?: number; roll?: string; zone?: string }[] = []
  let open: (typeof out)[number] | null = null
  let length = 0
  const close = () => {
    if (open === null) return
    const d = fraction(length * bar.unit[0], bar.unit[1])
    open.duration = [d[0], d[1]]
    out.push(open)
  }
  for (const cell of bar.cells) {
    if (cell.kind === 'hold') {
      if (open === null) { open = { duration: [0, 1], rest: true }; length = 0 }
      length += 1
      continue
    }
    close()
    length = 1
    open = cell.kind === 'rest'
      ? { duration: [0, 1], rest: true }
      : {
          duration: [0, 1],
          ...(cell.hand ? { hand: cell.hand } : {}),
          ...(cell.accent ? { accent: cell.accent } : {}),
          ...(cell.graces ? { graces: cell.graces } : {}),
          ...(cell.roll ? { roll: cell.roll } : {}),
          ...(cell.zone ? { zone: cell.zone } : {}),
        }
  }
  close()
  return out as RawPiece['bars'][number]['events']
}

/** The piece this draft is, in the pipeline's own file format. */
export const toRaw = (draft: Draft): RawPiece => ({
  id: draft.id,
  title: draft.title,
  workId: draft.id,
  corps: draft.corps,
  circuit: 'other',
  ...(draft.bpm ? { bpm: draft.bpm } : {}),
  source: { url: draft.sourceUrl, listedAt: 'app', read: draft.savedAt.slice(0, 10) },
  bars: draft.bars.map((bar, i) => ({
    n: i + 1,
    meter: [bar.meter[0], bar.meter[1]],
    events: barEvents(bar),
    unnamedSymbols: 0,
    readFrom: 'notation' as const,
  })),
})

/** Whether the bar's cells fill its metre -- true by construction, checked anyway. */
export const closes = (bar: DraftBar): boolean => {
  const total = sum(barEvents(bar).map((e) => e.duration as Fraction))
  return sameFraction(total, barBeats(bar.meter))
}

/** One-letter labels for the grid, and the palette's order. */
export const ACCENTS: readonly { value: Accent | undefined; key: string; label: string }[] = [
  { value: undefined, key: '', label: 'normale' },
  { value: 'accent', key: '>', label: 'accent' },
  { value: 'marcato', key: '^', label: 'marcato' },
  { value: 'tap', key: '-', label: 'tap' },
  { value: 'ghost', key: '(', label: 'ghost' },
]

export const cellLabel = (cell: Cell): string => {
  if (cell.kind === 'hold') return ''
  if (cell.kind === 'rest') return '·'
  const hand = cell.hand === 'right' ? 'R' : cell.hand === 'left' ? 'L' : '●'
  const accent = ACCENTS.find((a) => a.value === cell.accent)?.key ?? ''
  const graces = cell.graces ? 'f'.repeat(Math.min(cell.graces, 3)) : ''
  const roll = cell.roll === 'buzz' ? 'z' : cell.roll === 'double' ? '≈' : ''
  return `${graces}${hand}${accent}${roll}`
}
