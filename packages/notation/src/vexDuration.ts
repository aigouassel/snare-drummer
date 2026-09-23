import { type Fraction, compare, equals, fraction, multiply, toText } from '@snare-drummer/core/fraction'
import { type Duration } from '@snare-drummer/core/duration'

/**
 * A length of time, resolved into the three facts VexFlow needs to draw it.
 *
 * The model stores durations as fractions of a quarter-note beat, which is
 * the only way the confidence arithmetic can work. Notation needs something
 * else entirely: a glyph, a number of dots, and — when the length is not a
 * plain division by two — a tuplet ratio to write over the group.
 *
 * This is the only place in the codebase that knows how one turns into the
 * other, and it is deliberately alone: everywhere else, a sixteenth-note
 * triplet is a sixth of a beat and nothing more.
 */
export type VexDuration = {
  /** VexFlow's own duration code: 'w', 'h', 'q', '8', '16', '32', '64'. */
  glyph: string
  dots: number
  /** Present when the notes are written in the time of fewer of their kind. */
  tuplet?: { notes: number; inSpaceOf: number }
}

/** The plain note values, longest first, as lengths in quarter beats. */
const BASES: readonly (readonly [string, Fraction])[] = [
  ['w', [4, 1]], ['h', [2, 1]], ['q', [1, 1]], ['8', [1, 2]],
  ['16', [1, 4]], ['32', [1, 8]], ['64', [1, 16]],
]

/** What a dot does: one dot is half as long again, two is three quarters. */
const dotFactor = (dots: number): Fraction => fraction(2 ** (dots + 1) - 1, 2 ** dots)

/**
 * Tuplets an engraver actually writes, ordered by how ordinary they are.
 *
 * A duration can always be expressed as *some* ratio, so an unbounded search
 * would "succeed" on any measurement error by inventing a 23:16 tuplet. The
 * list is the constraint that makes failure possible — and failure is what
 * the confidence rule needs in order to mean anything.
 */
const TUPLETS: readonly (readonly [number, number])[] = [
  [3, 2], [5, 4], [6, 4], [7, 4], [7, 8], [9, 8], [5, 2], [11, 8], [13, 8],
]

/**
 * Resolve a duration, or return null when no ordinary notation writes it.
 *
 * Null is a real answer, not a gap. It means the reconstruction produced a
 * length no engraver would print, which is evidence the reading is wrong —
 * and a renderer that quietly rounded it to the nearest drawable note would
 * destroy exactly that evidence.
 */
export const resolve = (duration: Duration): VexDuration | null => {
  if (compare(duration, [0, 1]) <= 0) return null

  // Plain and dotted values first: a length that is one of those is never
  // better described as a tuplet, however well the arithmetic works out.
  for (let dots = 0; dots <= 2; dots++) {
    for (const [glyph, base] of BASES) {
      if (equals(multiply(base, dotFactor(dots)), duration)) {
        return dots === 0 ? { glyph, dots } : { glyph, dots }
      }
    }
  }

  for (const [notes, inSpaceOf] of TUPLETS) {
    for (let dots = 0; dots <= 1; dots++) {
      for (const [glyph, base] of BASES) {
        const written = multiply(multiply(base, dotFactor(dots)),
                                 fraction(inSpaceOf, notes))
        if (equals(written, duration)) {
          return { glyph, dots, tuplet: { notes, inSpaceOf } }
        }
      }
    }
  }

  return null
}

/** For an error message: what could not be drawn, in beats. */
export const describe = (duration: Duration): string => `${toText(duration)} temps`
