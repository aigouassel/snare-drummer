import { type Work } from './catalogue'

/**
 * Searching the library by typing, rather than by knowing.
 *
 * The library replaced three dropdowns -- circuit, corps, season -- with one
 * field, so this has to do everything they did and then the thing they could
 * not: find a show from a half-remembered name.
 *
 * Three separate things made the old substring match feel like it demanded the
 * exact title, and only the last is about spelling:
 *
 * - The circuit was never searched at all. It was a dropdown's job, so `DCI`
 *   matched nothing typed.
 * - One field had to contain the whole query. `blue devils 2019` found nothing,
 *   because no single field holds both the corps and the year. Queries are
 *   words, and the words come from different fields.
 * - Nothing was ranked. `opener` returned twenty shows in catalogue order, so
 *   the one you meant was wherever it happened to fall.
 *
 * So: the query is split into words, **every** word must match something, and
 * each may match a different field. What comes back is ordered by how well it
 * matched, not by how the catalogue happens to be stored.
 *
 * What is deliberately not done is guessing at abbreviations -- reading `mvt`
 * as `movement`. Dropping vowels is a rule with no edge: applied widely enough
 * to catch what people actually type, it also matches words nobody meant, and
 * the result looks exactly like a real hit.
 */

/** Where a token was found, and how well. Higher is a better match. */
const enum Tier {
  None = 0,
  /** Levenshtein distance within tolerance: a typo, or a misremembered word. */
  Near = 1,
  /** The field contains the token somewhere. */
  Inside = 2,
  /** A word of the field begins with the token, or is its initials. */
  WordStart = 3,
  /** The field itself begins with the token. */
  Start = 4,
}

/** What a field is worth when it matches: a corps is a stronger signal than a
 *  passage title, because `opener` is a word twenty shows share. */
const WEIGHT = { corps: 3, year: 2, circuit: 2, sequence: 2 } as const

/**
 * How far a token may be from a word and still count as that word.
 *
 * Short tokens get none. Two letters within one edit of each other is most of
 * the alphabet -- `bd` would reach `be`, `ad` and `b`, and the search would
 * answer confidently about something nobody asked for. This project holds a
 * signal that fires on correct input to be worse than no signal, and a guess
 * presented as a result is the same fault.
 */
const tolerance = (token: string): number =>
  token.length >= 7 ? 2 : token.length >= 4 ? 1 : 0

/** Case, accents and punctuation folded away, so typing is not transcription. */
const fold = (value: string): string =>
  value
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

/** The words of a folded field: punctuation separates, so `(SCV)` yields `scv`. */
const words = (value: string): readonly string[] =>
  value.split(/[^a-z0-9]+/).filter((w) => w.length > 0)

/**
 * The first letter of each word: `bd` for Blue Devils, `bk` for Blue Knights.
 *
 * Corps are spoken about by their initials, so they get typed that way. This is
 * matched whole rather than as a substring: `b` abbreviates nothing in a list
 * where a dozen names begin with Blue.
 */
const initials = (parts: readonly string[]): string =>
  parts.map((w) => w[0]).join('')

/**
 * Edit distance, abandoned as soon as it cannot come in under `limit`.
 *
 * The bound is what makes this cheap enough to run over every word of every
 * field: most comparisons are between words of very different lengths and stop
 * before the first row is finished.
 */
const distance = (a: string, b: string, limit: number): number => {
  if (Math.abs(a.length - b.length) > limit) return limit + 1

  /* Every index below is in range by construction. The fallback is there
     because the compiler cannot see that, and `limit + 1` is the one value that
     makes an impossible read fail the comparison rather than pass it: a broken
     lookup can only ever lose a match here, never invent one. */
  const at = (row: readonly number[], j: number): number => row[j] ?? limit + 1

  let previous: readonly number[] = [...Array(b.length + 1).keys()]
  for (let i = 1; i <= a.length; i++) {
    const current = [i]
    let best = i
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1
      const value = Math.min(
        at(previous, j) + 1,
        at(current, j - 1) + 1,
        at(previous, j - 1) + cost,
      )
      current.push(value)
      best = Math.min(best, value)
    }
    // Nothing on this row is within tolerance, and a row can only grow.
    if (best > limit) return limit + 1
    previous = current
  }
  return at(previous, b.length)
}

/** How well one token matches one already-folded field. */
const tierOf = (field: string, token: string): Tier => {
  if (field.startsWith(token)) return Tier.Start
  const parts = words(field)
  if (parts.some((w) => w.startsWith(token))) return Tier.WordStart
  if (token.length >= 2 && initials(parts) === token) return Tier.WordStart
  if (field.includes(token)) return Tier.Inside
  // Someone typing `bluedevils` has spelled it correctly and merely not pressed
  // space. That is not an approximation, so it does not sit with the guesses.
  if (parts.length > 1 && parts.join('').includes(token)) return Tier.Inside
  const limit = tolerance(token)
  if (limit > 0 && parts.some((w) => distance(w, token, limit) <= limit)) {
    return Tier.Near
  }
  return Tier.None
}

/**
 * A season, matched only by a token long enough to be one.
 *
 * `'2017'.includes('2')` is true, and that one character let `movement 2`
 * return a show whose only Movement is the third -- `movement` from the title,
 * `2` from the season -- scoring exactly as much as a real hit and sitting
 * indistinguishably beside it. Two digits are a year someone half-typed; one
 * digit is a movement, a part, a bar number.
 */
const yearTier = (year: string, token: string): Tier =>
  token.length >= 2 ? tierOf(year, token) : Tier.None

/** A work's searchable text, folded once per search rather than once per token. */
type Indexed = {
  work: Work
  corps: string
  year: string
  circuit: string
  sequences: readonly { id: string; title: string }[]
}

const index = (work: Work): Indexed => ({
  work,
  corps: fold(work.corps),
  year: String(work.year ?? ''),
  circuit: fold(work.circuit),
  sequences: work.sequences.map((s) => ({ id: s.id, title: fold(s.title) })),
})

/** One token's coverage: how it was found, and what that is worth. */
type Cover = { tier: Tier; weighted: number }

const NOTHING: Cover = { tier: Tier.None, weighted: 0 }

const better = (a: Cover, b: Cover): Cover => (b.weighted > a.weighted ? b : a)

const cover = (tier: Tier, weight: number): Cover =>
  tier === Tier.None ? NOTHING : { tier, weighted: tier * weight }

export type Hit = {
  work: Work
  /** Higher is a better match. Meaningless in isolation; only for ordering. */
  score: number
  /**
   * The passage the query named, if it was found by passage at all.
   *
   * The library lists shows, not PDFs, so a row can be returned by something
   * its own title does not contain: `circus` finds Blue Devils 2019. Naming the
   * passage is what keeps that from looking like a stray result.
   */
  matched: string | null
  /** Whether every word was found outright, rather than by edit distance. */
  exact: boolean
}

/**
 * The works matching `query`, best first.
 *
 * An empty query returns everything in catalogue order: no query is not a
 * failed query, and reordering the library when the field is cleared would be
 * disorienting.
 *
 * Approximate matches are kept apart from real ones. If any work matched every
 * word outright, only those come back -- a typo is worth guessing about when
 * nothing else fits, and never worth mixing into results that do.
 */
export const searchWorks = (
  works: readonly Work[],
  query: string,
): readonly Hit[] => {
  const tokens = words(fold(query))
  if (tokens.length === 0) {
    return works.map((work) => ({ work, score: 0, matched: null, exact: true }))
  }

  const hits: Hit[] = []

  for (const entry of works.map(index)) {
    // What the show itself answers for, whichever passage you had in mind.
    const own = tokens.map((token) =>
      better(
        better(
          cover(tierOf(entry.corps, token), WEIGHT.corps),
          cover(yearTier(entry.year, token), WEIGHT.year),
        ),
        cover(tierOf(entry.circuit, token), WEIGHT.circuit),
      ),
    )

    // A run of words is the title of *one* passage. Letting `snare` come from
    // one passage and `break` from another returns a show holding neither
    // `Snare Break` nor anything like it, and this project would rather answer
    // nothing than answer plausibly.
    let best: Hit | null = null
    const consider = (extra: readonly Cover[], sequence: string | null) => {
      let score = 0
      let exact = true
      for (let i = 0; i < tokens.length; i++) {
        const found = better(own[i] ?? NOTHING, extra[i] ?? NOTHING)
        if (found.tier === Tier.None) return
        if (found.tier === Tier.Near) exact = false
        score += found.weighted
      }
      if (best === null || score > best.score) {
        best = { work: entry.work, score, matched: sequence, exact }
      }
    }

    const none = tokens.map(() => NOTHING)
    consider(none, null)
    for (const sequence of entry.sequences) {
      consider(
        tokens.map((token) =>
          cover(tierOf(sequence.title, token), WEIGHT.sequence),
        ),
        sequence.id,
      )
    }

    if (best !== null) hits.push(best)
  }

  const exactly = hits.filter((h) => h.exact)
  const kept = exactly.length > 0 ? exactly : hits

  return kept.sort(
    (a, b) =>
      b.score - a.score ||
      (b.work.year ?? 0) - (a.work.year ?? 0) ||
      a.work.corps.localeCompare(b.work.corps),
  )
}
