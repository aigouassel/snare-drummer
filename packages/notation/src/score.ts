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

// How far the music reaches either side of the staff line, in pixels, measured
// off a rendered page: accents and beams sit above, stems and flags below. The
// page came out at 20.5 above and 34.5 below, and these leave a staff space of
// margin on each. Measured, not derived -- an earlier pair guessed from the
// stave's own numbers and put the outline above the music it was marking.
const ABOVE_LINE = 30
const BELOW_LINE = 45
// The one line of the five that is drawn, and where it falls relative to the y
// the stave is built at.
const STAFF_LINE = 2
const LINE_OFFSET = 60

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
  // Five lines with four of them hidden, rather than a one-line stave.
  // VexFlow draws a lone line where the *top* line would go, while a note
  // keyed to the middle line stays where the middle line would be — so the
  // music hangs two spaces below its own staff. Hiding lines keeps the grid
  // intact, which is also what the measured offsets below are relative to.
  const stave = new Stave(x, y, width)
  stave.setConfigForLines(
    [0, 1, 2, 3, 4].map((i) => ({ visible: i === STAFF_LINE })),
  )
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
  // Format across the room actually left for notes. A time signature takes
  // real width, and formatting across the stave's full span draws the first
  // notes straight on top of it.
  const room = stave.getX() + width - stave.getNoteStartX() - 12
  new Formatter().joinVoices([voice]).format([voice], Math.max(room, 40))
  voice.draw(context, stave)
  for (const beam of beams) beam.setContext(context).draw()
  for (const tuplet of tuplets) tuplet.setContext(context).draw()

  markBar(context, bar, stave, width, options)
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
                 stave: Stave, width: number, options: ScoreOptions) => {
  const x = stave.getX()
  // Anchored to the line the stave actually draws, with offsets measured off
  // the rendered SVG rather than guessed. An outline taken from the stave's
  // y, or from its bounding box, floats above the notes it is supposed to be
  // marking; both were tried. Asking for line 0 does the same, now that the
  // drawn line is the middle of five rather than the only one.
  const line = stave.getYForLine(STAFF_LINE)
  const top = line - ABOVE_LINE
  const height = ABOVE_LINE + BELOW_LINE

  context.save()
  context.setFont('system-ui', 10)
  context.setFillStyle('#8a8a8a')
  context.fillText(String(bar.n), x + 3, top - 4)

  const outline = (colour: string, lineWidth: number) => {
    context.setStrokeStyle(colour)
    context.setLineWidth(lineWidth)
    context.beginPath()
    context.rect(x + 1, top, width - 2, height)
    context.stroke()
  }
  if (!bar.verdict.trusted) outline('#c2410c', 1.5)
  if (options.playingBar === bar.n) outline('#2563eb', 2)
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

  let previous: string | null = null
  const boxes: Rendered['boxes'] = systems.flatMap((system, row) => {
    const y = TOP_MARGIN + row * STAVE_HEIGHT
    return system.bars.map((placed) => {

      const meter = meterText(placed.bar.meter)
      const showMeter = previous === null || meter !== previous
      previous = meter
      drawBar(context, placed, y, showMeter, options)
      // The clickable box follows the same measurement as the outline, so
      // pointing at a bar and seeing it marked agree.
      const line = y + LINE_OFFSET
      return {
        n: placed.bar.n, x: placed.x, y: line - ABOVE_LINE,
        width: placed.width, height: ABOVE_LINE + BELOW_LINE,
      }
    })
  })

  return { height, boxes }
}
