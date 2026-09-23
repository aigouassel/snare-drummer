import { type Bar, isTrusted } from './bar'

/**
 * Where a transcription came from, and how to get back to it.
 *
 * Every piece carries this, and the app prints it. That is not a courtesy:
 * these are other people's transcriptions of other people's shows, and the
 * only honest way to hold them is to say where each one came from. It is also
 * what makes the downloaded PDF disposable — the source is a link away, so
 * nothing needs to be kept to stay checkable.
 */
export type Source = {
  /** The PDF this was read from. */
  url: string
  /** The catalogue page that listed it. */
  listedAt: string
  /** When it was read, ISO date. Engraving sites re-upload and re-file. */
  read: string
}

/** Which circuit the score belongs to, as the catalogue files it. */
export type Circuit = 'DCI' | 'WGI' | 'DCA' | 'other'

/**
 * A transcribed sequence: one PDF of one show, read into playable bars.
 *
 * The name is about what it is, not how much of it there is. A corps writes
 * a season's show in passages — Opener, Drum Feature, Movement 2 Part 1 — and
 * each is published as its own PDF. So a piece is a *sequence* of a work, and
 * `workId` is what puts it back beside the others it was written with. That
 * matters for practice: the passages of one show are worked together, and a
 * model that lost the link would present them as unrelated.
 *
 * The corps, circuit and year are repeated here rather than looked up. It is
 * denormalised on purpose — it keeps this package independent of the
 * catalogue, and a transcription that cannot say what it is a transcription
 * *of* is worth less than the duplication costs.
 */
export type Piece = {
  /** The sequence's id, from the catalogue. */
  id: string
  /** The sequence's own name: "Opener", "Movement 2 Part 1". */
  title: string
  /** The work this sequence belongs to: one corps, one season. */
  workId: string
  /** The corps or ensemble, as the catalogue names it. */
  corps: string
  circuit: Circuit
  /** Absent where the catalogue gives no year. */
  year?: number
  /**
   * The tempo the score prints, where it prints one.
   *
   * Absent is meaningful. A show was played at a tempo somebody chose, and
   * inventing one misrepresents it; a piece with no marking is played at
   * whatever tempo you are working at today, which is the app's default
   * anyway.
   */
  bpm?: number
  bars: readonly Bar[]
  source: Source
}

/** How much of a piece can be played as read. */
export const trust = (piece: Piece): { trusted: number; total: number } => ({
  trusted: piece.bars.filter(isTrusted).length,
  total: piece.bars.length,
})

/**
 * The bars a practice session would actually play.
 *
 * A flagged bar is not dropped — that would silently shorten the music and
 * put everything after it on the wrong beat. It stays in place and stays
 * audible; the app marks it, and the player decides.
 */
export const isFullyTrusted = (piece: Piece): boolean =>
  piece.bars.length > 0 && piece.bars.every(isTrusted)
