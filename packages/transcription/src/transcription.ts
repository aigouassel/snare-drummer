import { type Bar, type Meter } from '@snare-drummer/core/bar'
import { judge } from '@snare-drummer/core/confidence'
import { type Circuit, type Piece } from '@snare-drummer/core/piece'
import { type Event } from '@snare-drummer/core/stroke'

import { RAW_PIECES } from './pieces/index'

/**
 * Scores read off their PDFs by the pipeline, as pieces the app can play.
 *
 * The pipeline writes plain JSON and stops short of judging it. The verdict
 * is computed here instead, by `@snare-drummer/core`, for one reason: the
 * rule that decides whether a bar is trustworthy is the same rule whichever
 * score it is applied to, and it has tests. Letting the Python side ship its
 * own opinion would put a second, untested copy of that rule in the tree, and
 * the two would drift.
 *
 * So what crosses the language boundary is evidence — durations, and a count
 * of symbols nobody could name — never a conclusion.
 */
type RawEvent = {
  duration: [number, number]
  rest?: true
  accent?: string
  zone?: string
  roll?: string
  graces?: number
  hand?: string
  dynamic?: string
}

type RawBar = {
  n: number
  meter: [number, number] | null
  events: readonly RawEvent[]
  unnamedSymbols: number
  readFrom?: 'notation' | 'spacing' | 'none'
  at?: { page: number; system: number; x0: number; x1: number }
}

type RawPiece = {
  id: string
  title: string
  workId: string
  corps: string
  circuit: string
  year?: number
  bpm?: number
  source: { url: string; listedAt: string; read: string }
  bars: readonly RawBar[]
}

const FALLBACK_METER: Meter = [4, 4]

const toEvent = (raw: RawEvent): Event =>
  raw.rest
    ? { rest: true, duration: raw.duration }
    : {
        duration: raw.duration,
        ...(raw.accent ? { accent: raw.accent as never } : {}),
        ...(raw.zone ? { zone: raw.zone as never } : {}),
        ...(raw.roll ? { roll: raw.roll as never } : {}),
        ...(raw.graces ? { graces: raw.graces } : {}),
        ...(raw.hand ? { hand: raw.hand as never } : {}),
        ...(raw.dynamic ? { dynamic: raw.dynamic as never } : {}),
      }

const toBar = (raw: RawBar): Bar => {
  const events = raw.events.map(toEvent)
  const meter = raw.meter as Meter | null
  return {
    n: raw.n,
    // A bar with no metre still needs one to be laid out in time; the verdict
    // records that it was never read, so the fallback cannot pass for a fact.
    meter: meter ?? FALLBACK_METER,
    events,
    verdict: judge({
      meter,
      events,
      unnamedSymbols: raw.unnamedSymbols,
      // 'none' means nothing was read at all, which the empty-bar signal
      // already covers; only a measured reading is its own concern.
      ...(raw.readFrom === 'spacing' ? { readFrom: 'spacing' as const } : {}),
    }),
    ...(raw.at ? { at: raw.at } : {}),
  }
}

const toPiece = (raw: RawPiece): Piece => ({
  id: raw.id,
  title: raw.title,
  workId: raw.workId,
  corps: raw.corps,
  circuit: raw.circuit as Circuit,
  ...(raw.year === undefined ? {} : { year: raw.year }),
  ...(raw.bpm === undefined ? {} : { bpm: raw.bpm }),
  bars: raw.bars.map(toBar),
  source: raw.source,
})

/**
 * `as unknown as` and not a plain assertion: TypeScript reads a JSON array as
 * `number[]`, which cannot narrow to the fixed-length tuples a metre and a
 * duration are. The shape is guaranteed by the pipeline that writes the files
 * and asserted by this package's tests, which is where that guarantee belongs
 * -- a structural check at the boundary, rather than a type the compiler has
 * no way to verify against a file on disk.
 */
const RAW: readonly RawPiece[] = RAW_PIECES as readonly RawPiece[]

export const PIECES: readonly Piece[] = RAW.map(toPiece)
  .slice()
  .sort((a, b) => a.id.localeCompare(b.id))

export const pieceById = (id: string): Piece | undefined =>
  PIECES.find((p) => p.id === id)

/** Sequence ids that have been read, so the library can mark them. */
export const TRANSCRIBED: ReadonlySet<string> = new Set(PIECES.map((p) => p.id))

/** Works holding at least one transcribed sequence. */
export const TRANSCRIBED_WORKS: ReadonlySet<string> = new Set(PIECES.map((p) => p.workId))

/** The transcribed sequences of one work, in catalogue order. */
export const piecesOfWork = (workId: string): readonly Piece[] =>
  PIECES.filter((p) => p.workId === workId)
