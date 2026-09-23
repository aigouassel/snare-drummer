import {
  Articulation, Beam, Dot, Formatter, Renderer, Stave, StaveNote, Tuplet, Voice,
} from 'vexflow'
import { type Bar, meterText } from '@snare-drummer/core/bar'
import { type Event, isRest } from '@snare-drummer/core/stroke'
import { type Options, type PlacedBar, DEFAULTS, layout } from './systems'
import { resolve } from './vexDuration'

/**
 * Draw a piece, bar by bar.
 *
 * Everything that decides *where* the music goes lives in systems.ts, which
 * has no VexFlow and no DOM in it and is tested. What is left here is the
 * drawing itself, which needs a real element and an SVG backend and therefore
 * cannot be. Keep new layout decisions on the other side of that line.
 *
 * A snare part is written on one line, not five. Everything is the same drum,
 * so a five-line stave would spend four lines saying nothing — and the marks
 * that *do* carry meaning (a rimshot, a cross-stick) are then legible as
 * departures from that single line.
 */

const LINE = 'b/4'          // the one line a snare part is written on
const STAVE_HEIGHT = 120
const TOP_MARGIN = 28

export type ScoreOptions = Partial<Options> & {
  /** Bar currently under the playhead, outlined as it plays. */
  playingBar?: number
  /** Called when a bar is clicked, so a range can be chosen by pointing. */
  onBarClick?: (n: number) => void
}

const noteOf = (event: Event): { note: StaveNote; tuplet?: { notes: number; inSpaceOf: number } } | null => {
  const vex = resolve(event.duration)
  // A length no engraver writes is not drawn as its nearest neighbour. The
  // bar carrying it is already flagged, and silently rounding would hide the
  // very evidence the flag is about.
  if (!vex) return null

  const note = new StaveNote({
    keys: [LINE],
    duration: isRest(event) ? `${vex.glyph}r` : vex.glyph,
    stemDirection: 1,
  })
  for (let i = 0; i < vex.dots; i++) Dot.buildAndAttach([note], { all: true })

  if (!isRest(event)) {
    // Accents go above the line: on a one-line stave there is no "away from
    // the notehead" direction to fall back on, so the side is chosen once.
    const mark = event.accent === 'accent' ? 'a>' : event.accent === 'marcato' ? 'a^' : null
    if (mark) note.addModifier(new Articulation(mark).setPosition(3), 0)
  }

  return vex.tuplet ? { note, tuplet: vex.tuplet } : { note }
}

const drawBar = (context: ReturnType<Renderer['getContext']>, placed: PlacedBar,
                 y: number, showMeter: boolean, options: ScoreOptions) => {
  const { bar, x, width } = placed
  const stave = new Stave(x, y, width, { numLines: 1 })
  if (showMeter) stave.addTimeSignature(meterText(bar.meter))
  stave.setContext(context).draw()

  const notes: StaveNote[] = []
  const tuplets: Tuplet[] = []
  let pending: { notes: StaveNote[]; ratio: { notes: number; inSpaceOf: number } } | null = null

  for (const event of bar.events) {
    const built = noteOf(event)
    if (!built) continue
    notes.push(built.note)

    // Tuplets must be constructed before the voice is built: `Tuplet` rewrites
    // its notes' tick values in place, while a `Voice` caches its total the
    // moment tickables are added. Grouping them here keeps that order.
    if (built.tuplet) {
      if (pending && pending.ratio.notes === built.tuplet.notes) {
        pending.notes.push(built.note)
      } else {
        if (pending) tuplets.push(makeTuplet(pending))
        pending = { notes: [built.note], ratio: built.tuplet }
      }
    } else if (pending) {
      tuplets.push(makeTuplet(pending))
      pending = null
    }
  }
  if (pending) tuplets.push(makeTuplet(pending))

  if (notes.length === 0) return

  const beams = Beam.generateBeams(notes)
  const voice = new Voice({ numBeats: bar.meter[0], beatValue: bar.meter[1] })
  voice.setStrict(false)
  voice.addTickables(notes)
  new Formatter().joinVoices([voice]).format([voice], Math.max(width - 30, 40))
  voice.draw(context, stave)
  for (const beam of beams) beam.setContext(context).draw()
  for (const tuplet of tuplets) tuplet.setContext(context).draw()

  markBar(context, bar, x, y, width, options)
}

const makeTuplet = (pending: { notes: StaveNote[]; ratio: { notes: number; inSpaceOf: number } }) =>
  new Tuplet(pending.notes, {
    numNotes: pending.ratio.notes,
    notesOccupied: pending.ratio.inSpaceOf,
  })

/**
 * The bar number, and the mark on a bar that is not trusted.
 *
 * Drawn rather than left to the surrounding page because the flag has to sit
 * on the music itself: the whole point of judging bar by bar is that you can
 * see, while playing, which bar the app is unsure about.
 */
const markBar = (context: ReturnType<Renderer['getContext']>, bar: Bar,
                 x: number, y: number, width: number, options: ScoreOptions) => {
  context.save()
  context.setFont('system-ui', 10)
  context.setFillStyle('#8a8a8a')
  context.fillText(String(bar.n), x + 2, y - 6)

  if (!bar.verdict.trusted) {
    context.setStrokeStyle('#c2410c')
    context.setLineWidth(1.5)
    context.beginPath()
    context.rect(x + 1, y - 2, width - 2, 56)
    context.stroke()
  }
  if (options.playingBar === bar.n) {
    context.setStrokeStyle('#2563eb')
    context.setLineWidth(2)
    context.beginPath()
    context.rect(x + 1, y - 2, width - 2, 56)
    context.stroke()
  }
  context.restore()
}

export type Rendered = {
  height: number
  /** Screen rectangle of each bar, so a click can be mapped back to one. */
  boxes: readonly { n: number; x: number; y: number; width: number; height: number }[]
}

export const renderScore = (
  element: HTMLDivElement,
  bars: readonly Bar[],
  options: ScoreOptions = {},
): Rendered => {
  element.innerHTML = ''
  const width = options.width ?? element.clientWidth ?? 900
  const opts: Options = { ...DEFAULTS, ...options, width }

  const systems = layout(bars, opts)
  const height = TOP_MARGIN + systems.length * STAVE_HEIGHT

  const renderer = new Renderer(element, Renderer.Backends.SVG)
  renderer.resize(width, height)
  const context = renderer.getContext()

  const boxes: Rendered['boxes'] = systems.flatMap((system, row) => {
    const y = TOP_MARGIN + row * STAVE_HEIGHT
    let previous: string | null = null
    return system.bars.map((placed) => {
      const meter = meterText(placed.bar.meter)
      const showMeter = row === 0 || meter !== previous
      previous = meter
      drawBar(context, placed, y, showMeter, options)
      return { n: placed.bar.n, x: placed.x, y: y - 8, width: placed.width, height: 70 }
    })
  })

  return { height, boxes }
}
