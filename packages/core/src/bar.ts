import { type Fraction, fraction, sum } from './fraction'
import { type Duration } from './duration'
import { type Event, isRest } from './stroke'

/**
 * A bar, and everything that can be said about one.
 *
 * The bar is the unit of this whole project, which is a departure worth
 * stating. It would be natural to model a piece as one stream of events and
 * let barlines fall out of the arithmetic — that is how a short rudiment is
 * best described. Here it would be the wrong way round, for two reasons.
 *
 * First, the barline is the *most reliable* thing an engraved PDF contains: a
 * stroked vertical segment with exact coordinates, read off the page with no
 * inference at all, whereas every duration inside it is reconstructed. Trust
 * should follow the evidence, so the structure is built from the part that was
 * read and the contents are placed into it.
 *
 * Second, it is what lets a doubtful bar stay local. A piece is ninety bars of
 * which four are unreadable; with one stream, an error displaces everything
 * after it and the piece is lost. With addressable bars, the four are marked
 * and the other eighty-six remain playable — and playable *by themselves*,
 * which is what practising a passage actually means.
 */

/** Beats per bar over the note value that gets the beat. */
export type Meter = readonly [beats: number, beatValue: 1 | 2 | 4 | 8 | 16]

/** How long one bar of this metre lasts, in quarter-note beats. 7/8 is 3½. */
export const barBeats = (meter: Meter): Fraction => fraction(meter[0] * 4, meter[1])

export const meterText = (meter: Meter): string => `${meter[0]}/${meter[1]}`

/**
 * Why a bar is not trusted.
 *
 * These are reasons, not a score. The app shows them, so each one has to be
 * sayable in a sentence to somebody holding a drumstick.
 */
export type Concern =
  /** The durations inside the bar do not add up to the metre. */
  | { kind: 'arithmetic'; played: Duration; expected: Duration }
  /** Symbols were found on the staff that the extractor could not name. */
  | { kind: 'unnamedSymbols'; count: number }
  /** Nothing was read here at all, which is never what a printed bar means. */
  | { kind: 'empty' }
  /** No time signature was in force, so there was nothing to check against. */
  | { kind: 'meterUnknown' }

/**
 * Playable as read, or shown with its reasons.
 *
 * Deliberately binary. A graded score would have to be turned back into a
 * yes-or-no at the moment of playing anyway, and the grade would only move the
 * decision somewhere less visible. The richness lives in `concerns` instead,
 * which explains the verdict without diluting it.
 */
export type Verdict =
  | { trusted: true }
  | { trusted: false; concerns: readonly Concern[] }

/** Where on the source document a bar was read from. */
export type BarSource = {
  /** 1-based page of the source PDF. */
  page: number
  /** 0-based staff system down that page. */
  system: number
  /** Horizontal extent within the page, in PDF points. */
  x0: number
  x1: number
}

export type Bar = {
  /** 1-based position in the piece, counted from the first bar of music. */
  n: number
  meter: Meter
  events: readonly Event[]
  verdict: Verdict
  at?: BarSource
}

/** The total length of what was read, whatever the metre says it should be. */
export const playedBeats = (events: readonly Event[]): Fraction =>
  sum(events.map((e) => e.duration))

export const isSilent = (bar: Bar): boolean => bar.events.every(isRest)

export const isTrusted = (bar: Bar): boolean => bar.verdict.trusted
