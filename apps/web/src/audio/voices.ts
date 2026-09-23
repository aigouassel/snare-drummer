/**
 * The sounds: one drum, and a click.
 *
 * Synthesised rather than sampled, and the reason is the job the sound has to
 * do. You listen to a transcription to catch it being wrong — a flam that is
 * not a flam, an accent on the wrong note, a roll written as plain eighths.
 * What that needs is for the *differences* to be unmistakable, not for the
 * drum to be convincing. A noise burst through a bandpass gives a clean,
 * repeatable attack whose weight tracks the written dynamic exactly, which a
 * sampled drum with its own room and its own player does not.
 */

/** Relative weight of each written dynamic. */
const WEIGHT: Record<string, number> = {
  ghost: 0.18,
  tap: 0.45,
  accent: 0.9,
  marcato: 1,
}

const DEFAULT_WEIGHT = 0.6

export type Hit = {
  /** When, on the AudioContext clock. */
  at: number
  accent?: string
  zone?: string
  /** Grace notes in front: one is a flam, two a drag. */
  graces?: number
  roll?: 'buzz' | 'double'
  /** How long the note lasts, in seconds — a roll fills it. */
  seconds: number
}

let noiseBuffer: AudioBuffer | null = null

const noise = (ctx: AudioContext): AudioBuffer => {
  if (noiseBuffer && noiseBuffer.sampleRate === ctx.sampleRate) return noiseBuffer
  const length = Math.floor(ctx.sampleRate * 0.4)
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1
  noiseBuffer = buffer
  return buffer
}

/** One stick stroke. */
const strike = (ctx: AudioContext, out: AudioNode, at: number, weight: number,
                zone?: string) => {
  const source = ctx.createBufferSource()
  source.buffer = noise(ctx)

  const band = ctx.createBiquadFilter()
  band.type = 'bandpass'
  // The zone is what a rimshot or a cross-stick actually changes: where the
  // energy sits, not how loud it is.
  band.frequency.value = zone === 'crossStick' ? 900
    : zone === 'rimshot' ? 3200
    : zone === 'rim' ? 4200
    : 1900
  band.Q.value = zone === 'crossStick' ? 6 : 1.1

  const gain = ctx.createGain()
  const peak = Math.min(1, weight)
  const decay = zone === 'crossStick' ? 0.05 : 0.11

  gain.gain.setValueAtTime(0, at)
  gain.gain.linearRampToValueAtTime(peak, at + 0.001)
  gain.gain.exponentialRampToValueAtTime(0.0001, at + decay)

  source.connect(band).connect(gain).connect(out)
  source.start(at)
  source.stop(at + decay + 0.02)
}

export const playHit = (ctx: AudioContext, out: AudioNode, hit: Hit) => {
  const weight = WEIGHT[hit.accent ?? ''] ?? DEFAULT_WEIGHT

  // Grace notes sit *before* the beat, which is what makes a flam sound like
  // a flam rather than two notes: the main stroke stays where it was written.
  const graces = hit.graces ?? 0
  for (let i = graces; i > 0; i--) {
    strike(ctx, out, hit.at - i * 0.028, weight * 0.35, hit.zone)
  }

  if (hit.roll === 'buzz') {
    // A press roll is a texture, not a count: fill the written length with
    // strokes too close together to hear individually.
    const step = 0.022
    for (let t = 0; t < hit.seconds - 0.005; t += step) {
      strike(ctx, out, hit.at + t, weight * (t === 0 ? 1 : 0.4), hit.zone)
    }
    return
  }

  if (hit.roll === 'double') {
    // A measured roll: the diddle is written, so play it as two.
    strike(ctx, out, hit.at, weight, hit.zone)
    strike(ctx, out, hit.at + hit.seconds / 2, weight * 0.75, hit.zone)
    return
  }

  strike(ctx, out, hit.at, weight, hit.zone)
}

/** The metronome. Deliberately unlike the drum, so the two never blur. */
export const playClick = (ctx: AudioContext, out: AudioNode, at: number,
                          downbeat: boolean) => {
  const osc = ctx.createOscillator()
  osc.type = 'square'
  osc.frequency.value = downbeat ? 1600 : 1050

  const gain = ctx.createGain()
  gain.gain.setValueAtTime(0, at)
  gain.gain.linearRampToValueAtTime(downbeat ? 0.28 : 0.16, at + 0.001)
  gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.035)

  osc.connect(gain).connect(out)
  osc.start(at)
  osc.stop(at + 0.05)
}
