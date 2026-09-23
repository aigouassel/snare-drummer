import { type Bar, barBeats } from '@snare-drummer/core/bar'
import { toNumber } from '@snare-drummer/core/fraction'
import { isRest } from '@snare-drummer/core/stroke'
import { type PlacedStroke, atSeconds, lengthInBeats, place, selectBars } from '@snare-drummer/core/timeline'
import { type Hit, playClick, playHit } from './voices'

/**
 * Playback, against the audio clock rather than the browser's.
 *
 * Two rules hold this together, and both are easy to undo by accident.
 *
 * **The engine is not React state.** React re-renders when the browser feels
 * like it; a drum part at 160bpm has a sixteenth every 94ms, and a note
 * scheduled from a render is a note played late. So the engine keeps its own
 * timer, schedules against `AudioContext.currentTime`, and React subscribes
 * for display only.
 *
 * **Nothing is scheduled far ahead.** A timer that fired exactly on time
 * would still be at the mercy of a busy main thread, so the standard remedy
 * applies: wake often, and hand the audio clock everything falling due in the
 * next fraction of a second. The window is long enough to survive a stutter
 * and short enough that stopping is immediate.
 */

const TICK_MS = 25
const WINDOW_SECONDS = 0.15

export type Selection = { from: number; to: number }

export type PlayOptions = {
  bpm: number
  selection?: Selection
  loop: boolean
  click: boolean
}

export type EngineState = {
  playing: boolean
  /** Bar under the playhead, by its own number. */
  bar: number | null
  /** Beats elapsed within the current pass, for a smooth playhead. */
  beat: number
}

const IDLE: EngineState = { playing: false, bar: null, beat: 0 }

type ScheduledStroke = PlacedStroke & { seconds: number }

export class Engine {
  private context: AudioContext | null = null
  private master: GainNode | null = null
  private timer: number | null = null

  private strokes: readonly ScheduledStroke[] = []
  private bars: readonly Bar[] = []
  private totalBeats = 0
  private options: PlayOptions = { bpm: 100, loop: false, click: true }

  /** When, on the audio clock, beat zero of the current pass happened. */
  private origin = 0
  private nextStroke = 0
  private nextClickBeat = 0

  private state: EngineState = IDLE
  private listeners = new Set<(state: EngineState) => void>()

  subscribe(listener: (state: EngineState) => void): () => void {
    this.listeners.add(listener)
    listener(this.state)
    return () => this.listeners.delete(listener)
  }

  getState(): EngineState {
    return this.state
  }

  private emit(next: Partial<EngineState>) {
    this.state = { ...this.state, ...next }
    for (const listener of this.listeners) listener(this.state)
  }

  /**
   * An AudioContext may only start from a gesture, so it is created on the
   * first play rather than up front — and reused after, because a context per
   * play would leak one per press.
   */
  private ensureContext(): AudioContext {
    if (!this.context) {
      this.context = new AudioContext()
      this.master = this.context.createGain()
      this.master.gain.value = 0.9
      this.master.connect(this.context.destination)
    }
    void this.context.resume()
    return this.context
  }

  play(bars: readonly Bar[], options: PlayOptions) {
    this.stop()
    const context = this.ensureContext()

    const selected = options.selection
      ? selectBars(bars, options.selection.from, options.selection.to)
      : bars
    if (selected.length === 0) return

    this.bars = selected
    this.options = options
    this.totalBeats = toNumber(lengthInBeats(selected))

    // Each stroke's length in seconds is wanted for rolls, which fill their
    // written duration rather than striking once.
    this.strokes = place(selected).map((stroke) => ({
      ...stroke,
      seconds: atSeconds(stroke.stroke.duration, options.bpm),
    }))

    this.origin = context.currentTime + 0.12
    this.nextStroke = 0
    this.nextClickBeat = 0
    this.emit({ playing: true, bar: selected[0]?.n ?? null, beat: 0 })

    this.timer = window.setInterval(() => this.tick(), TICK_MS)
    this.tick()
  }

  stop() {
    if (this.timer !== null) window.clearInterval(this.timer)
    this.timer = null
    this.strokes = []
    this.emit(IDLE)
  }

  setTempo(bpm: number) {
    // Changing tempo mid-flight would need the origin re-derived from the
    // beat already elapsed; restarting the pass is honest and predictable,
    // and this music is practised by choosing a tempo and then playing.
    if (this.state.playing) this.play(this.bars, { ...this.options, bpm })
    else this.options = { ...this.options, bpm }
  }

  private tick() {
    const context = this.context
    const master = this.master
    if (!context || !master) return

    const { bpm, click, loop } = this.options
    const horizon = context.currentTime + WINDOW_SECONDS

    while (this.nextStroke < this.strokes.length) {
      const stroke = this.strokes[this.nextStroke]
      if (!stroke) break
      const at = this.origin + atSeconds(stroke.atBeat, bpm)
      if (at > horizon) break
      if (!isRest(stroke.stroke)) {
        const hit: Hit = {
          at,
          seconds: stroke.seconds,
          ...(stroke.stroke.accent ? { accent: stroke.stroke.accent } : {}),
          ...(stroke.stroke.zone ? { zone: stroke.stroke.zone } : {}),
          ...(stroke.stroke.graces ? { graces: stroke.stroke.graces } : {}),
          ...(stroke.stroke.roll ? { roll: stroke.stroke.roll } : {}),
        }
        playHit(context, master, hit)
      }
      this.nextStroke++
    }

    if (click) {
      while (this.nextClickBeat < this.totalBeats) {
        const at = this.origin + (this.nextClickBeat * 60) / bpm
        if (at > horizon) break
        playClick(context, master, at, this.isDownbeat(this.nextClickBeat))
        this.nextClickBeat++
      }
    }

    const elapsed = (context.currentTime - this.origin) * (bpm / 60)
    if (elapsed >= this.totalBeats) {
      if (loop) {
        this.origin += (this.totalBeats * 60) / bpm
        this.nextStroke = 0
        this.nextClickBeat = 0
      } else if (this.nextStroke >= this.strokes.length) {
        this.stop()
        return
      }
    }

    const beat = Math.max(0, Math.min(elapsed, this.totalBeats))
    this.emit({ beat, bar: this.barAt(beat) })
  }

  /** Whether a beat is the first of a bar, which the click accents. */
  private isDownbeat(beat: number): boolean {
    let edge = 0
    for (const bar of this.bars) {
      if (Math.abs(edge - beat) < 1e-6) return true
      edge += toNumber(barBeats(bar.meter))
    }
    return false
  }

  private barAt(beat: number): number | null {
    let edge = 0
    for (const bar of this.bars) {
      const next = edge + toNumber(barBeats(bar.meter))
      if (beat < next - 1e-9) return bar.n
      edge = next
    }
    return this.bars[this.bars.length - 1]?.n ?? null
  }
}

export const engine = new Engine()
