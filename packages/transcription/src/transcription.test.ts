import { describe, expect, it } from 'vitest'
import { barBeats, playedBeats } from '@snare-drummer/core/bar'
import { equals } from '@snare-drummer/core/fraction'
import { trust } from '@snare-drummer/core/piece'
import { place } from '@snare-drummer/core/timeline'
import { PIECES, TRANSCRIBED, TRANSCRIBED_WORKS, pieceById, piecesOfWork } from './transcription'

/**
 * These do not assert that the transcriptions are *right* — nothing in a test
 * can know that. They assert that the pipeline's output is coherent, and that
 * every claim it makes is one the confidence rule has actually passed on.
 */
describe('transcriptions', () => {
  it('reads at least one piece', () => {
    expect(PIECES.length).toBeGreaterThan(0)
  })

  it('carries the source URL on every piece, which is the whole deal', () => {
    for (const piece of PIECES) {
      expect(piece.source.url).toMatch(/^https:\/\/lothype\.com\/.*\.pdf$/)
      expect(piece.source.listedAt).toMatch(/^https:\/\/lothype\.com\//)
      expect(piece.source.read).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    }
  })

  it('numbers bars from one, without gaps', () => {
    for (const piece of PIECES) {
      expect(piece.bars.map((b) => b.n)).toEqual(
        piece.bars.map((_b, i) => i + 1),
      )
    }
  })

  /**
   * The invariant the whole design rests on: a bar is trusted only if what was
   * read fills the metre exactly. If these two ever disagree, the verdict is
   * decorative and the app is lying about what it can play.
   */
  it('trusts a bar only when its durations fill its metre', () => {
    for (const piece of PIECES) {
      for (const bar of piece.bars) {
        if (bar.verdict.trusted) {
          expect(equals(playedBeats(bar.events), barBeats(bar.meter))).toBe(true)
          expect(bar.events.length).toBeGreaterThan(0)
        }
      }
    }
  })

  it('explains every bar it does not trust', () => {
    for (const piece of PIECES) {
      for (const bar of piece.bars) {
        if (!bar.verdict.trusted) expect(bar.verdict.concerns.length).toBeGreaterThan(0)
      }
    }
  })

  it('keeps a doubtful bar in place rather than dropping it', () => {
    for (const piece of PIECES) {
      const placed = place(piece.bars)
      // Every bar contributes its written length, so the last stroke of the
      // piece sits inside the piece's own length however the reading went.
      expect(placed.length).toBeGreaterThan(0)
      const bars = new Set(placed.map((p) => p.bar))
      for (const bar of piece.bars) {
        if (bar.events.some((e) => !('rest' in e))) expect(bars.has(bar.n)).toBe(true)
      }
    }
  })

  it('records where on the page each bar was read from', () => {
    for (const piece of PIECES) {
      for (const bar of piece.bars) {
        expect(bar.at).toBeDefined()
        if (!bar.at) continue
        expect(bar.at.x1).toBeGreaterThan(bar.at.x0)
        expect(bar.at.system).toBeGreaterThanOrEqual(0)
      }
    }
  })

  /**
   * A PDF is one passage of a show, not a piece of music on its own. Losing
   * the link back to the work would present the passages of one season as
   * unrelated, which is not how any of them are practised.
   */
  it('ties every transcribed sequence back to the work it belongs to', () => {
    for (const piece of PIECES) {
      expect(piece.workId).toMatch(/^[a-z0-9-]+$/)
      expect(TRANSCRIBED_WORKS.has(piece.workId)).toBe(true)
      expect(piecesOfWork(piece.workId)).toContain(piece)
    }
    expect(piecesOfWork('no-such-work')).toEqual([])
  })

  it('looks a piece up by id', () => {
    const first = PIECES[0]
    expect(first).toBeDefined()
    if (!first) return
    expect(pieceById(first.id)).toBe(first)
    expect(TRANSCRIBED.has(first.id)).toBe(true)
    expect(pieceById('nothing-here')).toBeUndefined()
  })

  it('reports how much of each piece is playable as read', () => {
    for (const piece of PIECES) {
      const { trusted, total } = trust(piece)
      expect(total).toBe(piece.bars.length)
      expect(trusted).toBeLessThanOrEqual(total)
      // A piece where nothing at all could be verified is not worth shipping.
      expect(trusted).toBeGreaterThan(0)
    }
  })
})
