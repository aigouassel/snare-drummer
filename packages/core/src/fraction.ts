/**
 * Exact rational arithmetic, because rhythm is not decimal.
 *
 * A sixteenth-note triplet is a third of a beat. In floating point that is
 * 0.333…, and twelve of them do not add up to four — they add up to
 * 3.9999999999999996. Every check this project relies on is a question of the
 * form "do these durations fill the bar exactly?", so a model that cannot
 * answer it exactly would make the confidence verdict meaningless: bars would
 * be flagged suspect for the crime of containing triplets.
 */

/** A rational number as [numerator, denominator], always in lowest terms. */
export type Fraction = readonly [number, number]

const gcd = (a: number, b: number): number => (b === 0 ? Math.abs(a) : gcd(b, a % b))

export const fraction = (numerator: number, denominator: number): Fraction => {
  if (denominator === 0) throw new Error('fraction with zero denominator')
  const sign = denominator < 0 ? -1 : 1
  const n = numerator * sign
  const d = denominator * sign
  const g = gcd(n, d) || 1
  return [n / g, d / g]
}

export const ZERO: Fraction = [0, 1]
export const ONE: Fraction = [1, 1]

export const add = (a: Fraction, b: Fraction): Fraction =>
  fraction(a[0] * b[1] + b[0] * a[1], a[1] * b[1])

export const subtract = (a: Fraction, b: Fraction): Fraction =>
  fraction(a[0] * b[1] - b[0] * a[1], a[1] * b[1])

export const multiply = (a: Fraction, b: Fraction): Fraction =>
  fraction(a[0] * b[0], a[1] * b[1])

export const sum = (fractions: readonly Fraction[]): Fraction =>
  fractions.reduce<Fraction>(add, ZERO)

/** Negative, zero or positive, like a comparator. */
export const compare = (a: Fraction, b: Fraction): number => a[0] * b[1] - b[0] * a[1]

export const equals = (a: Fraction, b: Fraction): boolean => compare(a, b) === 0

export const isZero = (a: Fraction): boolean => a[0] === 0

/** For anything that has to leave exact arithmetic: audio, pixels, display. */
export const toNumber = (a: Fraction): number => a[0] / a[1]

export const toText = (a: Fraction): string => (a[1] === 1 ? `${a[0]}` : `${a[0]}/${a[1]}`)
