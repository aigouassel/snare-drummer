import { type Duration } from './duration'

/**
 * What a snare drummer actually does to the drum.
 *
 * This is a one-instrument vocabulary, so pitch plays no part: everything that
 * distinguishes one note from the next is *how* it is struck. That makes the
 * model flatter than a pitched one, and richer in articulation — a bar can be
 * sixteen notes on the same spot of the head and still be four different
 * sounds.
 *
 * Every attribute below is optional, and absence means "the source does not
 * say" rather than a default. That distinction is the whole reason the type is
 * shaped this way: a transcription that does not notate sticking must not be
 * indistinguishable from one that notates it as all right-hand, because the
 * app would then teach a sticking nobody wrote.
 */
export type Hand = 'right' | 'left'

/**
 * Every dynamic the page can print, loudest last.
 *
 * Ordered so that playback can place one relative to the others without
 * hard-coding a scale, and so a test can assert the order is total.
 */
export const DYNAMICS = [
  'pppp', 'ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff', 'ffff',
] as const

/** Relative weight, as the page marks it — not a MIDI velocity. */
export type Accent =
  | 'accent'     // >
  | 'marcato'    // ^, the heaviest mark in this repertoire
  | 'ghost'      // a note in parentheses, felt more than heard
  | 'tap'        // explicitly unaccented where the page bothers to say so

/** Where on the drum, when the page asks for something other than the head. */
export type Zone =
  | 'head'
  | 'rimshot'
  | 'rim'         // the hoop alone
  | 'crossStick'
  | 'shell'
  | 'stickShot'

/**
 * A sustained roll, which is a way of playing a length rather than a note.
 *
 * `buzz` is a press roll — an unmeasured sustain. `double` is a measured
 * roll, where the diddles are written out in the rhythm. The distinction
 * survives into playback: one is a texture and the other is a count.
 */
export type Roll = 'buzz' | 'double'

/**
 * A printed dynamic, as a level rather than a loudness.
 *
 * Carried on the note the mark is printed over, and in force from there until
 * the next one. A bar would be the tempting place to put it and the wrong
 * one: a score changes dynamic mid-bar all the time, and a bar-level field
 * would have to choose between misreporting the start of the bar and the end
 * of it.
 *
 * What each level is worth in sound is decided at playback, not here. The
 * page states an order, not a number of decibels, and the gap between mf and
 * f is a matter of interpretation that a transcription has no business
 * fixing.
 */
export type Dynamic =
  | 'pppp' | 'ppp' | 'pp' | 'p' | 'mp' | 'mf' | 'f' | 'ff' | 'fff' | 'ffff'
  /** Accents in their own right: a stroke's weight, not a passage's. */
  | 'sfz' | 'fp' | 'fz'

export type Stroke = {
  duration: Duration
  hand?: Hand
  accent?: Accent
  zone?: Zone
  /**
   * Grace notes hung in front of the stroke: one is a flam, two a drag,
   * three a ruff. Stored as a count rather than a name because the count is
   * what playback needs, and the name is a label the glossary can attach.
   */
  graces?: number
  roll?: Roll
  /**
   * The dynamic printed at this note, in force until the next one is
   * printed. Absent means the page says nothing *here*, not that it says
   * nothing at all.
   */
  dynamic?: Dynamic
}

/** A silence occupying its own length. */
export type Rest = { rest: true; duration: Duration }

export type Event = Stroke | Rest

export const isRest = (event: Event): event is Rest => 'rest' in event

export const isStroke = (event: Event): event is Stroke => !('rest' in event)

/** A flam counts as one stroke, not two: the grace note is part of it. */
export const strokeCount = (events: readonly Event[]): number =>
  events.filter(isStroke).length
