import { type Fraction, fraction, multiply } from './fraction'

/**
 * A length of time, measured in quarter-note beats — not a glyph.
 *
 * The distinction is load-bearing. A drum part is full of lengths that no
 * single symbol names: a sixteenth-note triplet is 1/6 of a beat, and the
 * seven-stroke figures in this repertoire routinely divide a beat by five.
 * Written as a fraction, all of them add up; written as glyph names, they
 * would need a special case each, and the sum that decides whether a bar is
 * trustworthy could not be taken at all.
 *
 * Choosing a glyph to draw is the renderer's problem, and it is the only
 * place where the question "which note head is that?" is allowed to arise.
 */
export type Duration = Fraction

export const WHOLE: Duration = [4, 1]
export const HALF: Duration = [2, 1]
export const QUARTER: Duration = [1, 1]
export const EIGHTH: Duration = [1, 2]
export const SIXTEENTH: Duration = [1, 4]
export const THIRTYSECOND: Duration = [1, 8]
export const SIXTYFOURTH: Duration = [1, 16]

/** A dotted note: half as long again, and doubly so for a double dot. */
export const dotted = (d: Duration, dots = 1): Duration =>
  multiply(d, fraction(2 ** (dots + 1) - 1, 2 ** dots))

/**
 * `count` notes played in the time of `inThe` of the same kind.
 * A triplet is `tuplet(d, 3, 2)`; the quintuplets in this repertoire are
 * `tuplet(d, 5, 4)`.
 */
export const tuplet = (d: Duration, count: number, inThe: number): Duration =>
  multiply(d, fraction(inThe, count))
