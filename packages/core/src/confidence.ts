import { equals, isZero, toText } from './fraction'
import { type Concern, type Meter, type Verdict, barBeats, playedBeats } from './bar'
import { type Event } from './stroke'

/**
 * Whether a reconstructed bar can be trusted, and if not, why.
 *
 * This is the project's only defence, and it is worth being explicit about
 * what it replaces. Where a small transcription is checked by eye, a catalogue
 * of nearly nine hundred scores cannot be — so nothing here may depend on
 * somebody having looked. Every signal below is one a machine can take alone.
 *
 * The signals are not equal, and the order they are weighed in reflects that:
 *
 *   * **Arithmetic is the strong signal.** A 4/4 bar whose notes total three
 *     and three-quarter beats is wrong, with no judgement required. It is not
 *     a complete signal — two errors can cancel, and a bar can close while
 *     being wrong — but when it fires it is never a false alarm.
 *
 *   * **An unnamed symbol is a confession.** The extractor found something
 *     drawn on the staff and could not say what it was. That must be counted
 *     and surfaced, never quietly dropped: a parser that silently skips what
 *     it does not understand produces a plausible score, and a plausible wrong
 *     score is the one failure this project cannot afford. The bug that has
 *     bitten this codebase three times already was exactly that shape.
 *
 *   * **An empty bar is not an empty bar.** Printed music does not leave a bar
 *     blank; it writes a whole-bar rest. So nothing read means nothing
 *     understood.
 *
 * Deliberately *not* a signal: how wide the bar is on the page. Engraving does
 * space a bar roughly in proportion to what it contains, so the temptation is
 * real — but density varies legitimately from bar to bar, and an early version
 * of the extractor flagged perfectly good bars as suspect on exactly this
 * reasoning. A signal that fires on correct input is worse than no signal,
 * because it teaches you to ignore the warnings.
 */
export const judge = (input: {
  meter: Meter | null
  events: readonly Event[]
  /** Symbols found inside this bar that the extractor could not name. */
  unnamedSymbols?: number
}): Verdict => {
  const concerns: Concern[] = []

  if (input.events.length === 0) {
    concerns.push({ kind: 'empty' })
  }

  const unnamed = input.unnamedSymbols ?? 0
  if (unnamed > 0) {
    concerns.push({ kind: 'unnamedSymbols', count: unnamed })
  }

  if (input.meter === null) {
    concerns.push({ kind: 'meterUnknown' })
  } else if (input.events.length > 0) {
    const played = playedBeats(input.events)
    const expected = barBeats(input.meter)
    if (!equals(played, expected)) {
      concerns.push({ kind: 'arithmetic', played, expected })
    }
  }

  return concerns.length === 0 ? { trusted: true } : { trusted: false, concerns }
}

/** One line a drummer can read, for the app to print under a flagged bar. */
export const explain = (concern: Concern): string => {
  switch (concern.kind) {
    case 'arithmetic':
      return isZero(concern.played)
        ? `aucune durée lue, ${toText(concern.expected)} temps attendus`
        : `${toText(concern.played)} temps lus, ${toText(concern.expected)} attendus`
    case 'unnamedSymbols':
      return concern.count === 1
        ? 'un symbole non identifié sur la portée'
        : `${concern.count} symboles non identifiés sur la portée`
    case 'empty':
      return 'mesure vide : rien n’a pu être lu'
    case 'meterUnknown':
      return 'aucune métrique connue, donc rien à vérifier'
  }
}
