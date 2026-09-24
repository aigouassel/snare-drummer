import { type Fraction, ZERO, add, compare, toNumber } from './fraction'
import { type Bar, barBeats } from './bar'
import { type Dynamic, type Event, type Stroke, isStroke } from './stroke'

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
  /**
   * The dynamic in force here, carried forward from the last one printed.
   *
   * A page marks a dynamic once and means it until it says otherwise, so a
   * stroke's own `dynamic` is absent on almost every note. Resolving that
   * here rather than at playback keeps the rule testable, and keeps it in one
   * place: every consumer that asks how loud a note is gets the same answer.
   */
  dynamic?: Dynamic
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
export const place = (
  bars: readonly Bar[],
  opening?: Dynamic,
): readonly PlacedStroke[] => {
  const out: PlacedStroke[] = []
  let barStart: Fraction = ZERO
  // Playing from bar 40 does not start the passage at whatever the default
  // is: the dynamic printed at bar 12 is still in force, and the caller says
  // so by passing it in. Recomputing it here would need the bars before the
  // selection, which is precisely what a selection does not have.
  let inForce: Dynamic | undefined = opening

  for (const bar of bars) {
    let at: Fraction = barStart
    bar.events.forEach((event: Event, index: number) => {
      if (isStroke(event)) {
        if (event.dynamic) inForce = event.dynamic
        out.push({
          stroke: event, atBeat: at, bar: bar.n, index,
          ...(inForce ? { dynamic: inForce } : {}),
        })
      }
      at = add(at, event.duration)
    })
    barStart = add(barStart, barBeats(bar.meter))
  }
  return out
}

/**
 * The dynamic still in force when a bar begins, from everything before it.
 *
 * Absent where nothing has been printed yet, which is not the same as a
 * default: a score that marks nothing at all is played at one weight, and one
 * that opens pianissimo is not.
 */
export const dynamicBefore = (
  bars: readonly Bar[],
  barNumber: number,
): Dynamic | undefined => {
  let found: Dynamic | undefined
  for (const bar of bars) {
    if (bar.n >= barNumber) break
    for (const event of bar.events) {
      if (isStroke(event) && event.dynamic) found = event.dynamic
    }
  }
  return found
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
