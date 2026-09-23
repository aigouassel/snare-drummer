import { type Fraction, ZERO, add, compare, toNumber } from './fraction'
import { type Bar, barBeats } from './bar'
import { type Event, type Stroke, isStroke } from './stroke'

/**
 * Where every stroke falls in time, so playback has something to schedule.
 *
 * Kept as a pure function of the bars and a tempo: nothing here touches an
 * audio clock, a React state or the passage of time. What comes out is a list
 * of "this stroke, at this many seconds", which the app's scheduler consumes
 * and the tests can read directly.
 */

export type PlacedStroke = {
  stroke: Stroke
  /** Beats from the start of the selection. */
  atBeat: Fraction
  /** Which bar it came from, by the bar's own number. */
  bar: number
  /** Where in that bar's events it sits, rests included. */
  index: number
}

/** The bars of a piece between two bar numbers, inclusive. */
export const selectBars = (bars: readonly Bar[], from: number, to: number): readonly Bar[] =>
  bars.filter((b) => b.n >= from && b.n <= to)

/**
 * Lay a run of bars out end to end.
 *
 * A bar contributes its *written* length, not the length of what was read from
 * it. The two differ exactly when a bar is flagged for arithmetic, and using
 * the written length is what keeps a doubtful bar from dragging everything
 * after it off the beat: the mistake stays inside the bar it belongs to.
 */
export const place = (bars: readonly Bar[]): readonly PlacedStroke[] => {
  const out: PlacedStroke[] = []
  let barStart: Fraction = ZERO

  for (const bar of bars) {
    let at: Fraction = barStart
    bar.events.forEach((event: Event, index: number) => {
      if (isStroke(event)) out.push({ stroke: event, atBeat: at, bar: bar.n, index })
      at = add(at, event.duration)
    })
    barStart = add(barStart, barBeats(bar.meter))
  }
  return out
}

/** Total written length of a run of bars, in quarter-note beats. */
export const lengthInBeats = (bars: readonly Bar[]): Fraction =>
  bars.reduce<Fraction>((total, bar) => add(total, barBeats(bar.meter)), ZERO)

/** Seconds from the start, at a tempo in quarter-note beats per minute. */
export const atSeconds = (beat: Fraction, bpm: number): number =>
  (toNumber(beat) * 60) / bpm

/** Beats sort ascending; ties keep the order they were placed in. */
export const byBeat = (a: PlacedStroke, b: PlacedStroke): number =>
  compare(a.atBeat, b.atBeat)
