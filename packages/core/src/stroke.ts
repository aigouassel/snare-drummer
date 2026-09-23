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
}

/** A silence occupying its own length. */
export type Rest = { rest: true; duration: Duration }

export type Event = Stroke | Rest

export const isRest = (event: Event): event is Rest => 'rest' in event

export const isStroke = (event: Event): event is Stroke => !('rest' in event)

/** A flam counts as one stroke, not two: the grace note is part of it. */
export const strokeCount = (events: readonly Event[]): number =>
  events.filter(isStroke).length
