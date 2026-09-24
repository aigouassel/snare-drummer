import { type Bar } from '@snare-drummer/core/bar'
import { type Selection, engine } from '../audio/engine'
import { useEngine } from './useEngine'

/**
 * Tempo, the click, and which bars to play.
 *
 * The bar range is the control this project exists for. You do not practise a
 * show from the top; you take four bars and sit on them, slowly. So the range
 * is a first-class control rather than a hidden feature, and clicking a bar
 * in the score sets it.
 */
export const Transport = ({ bars, bpm, setBpm, printed, selection, setSelection,
                           loop, setLoop, click, setClick }: {
  bars: readonly Bar[]
  bpm: number
  setBpm: (bpm: number) => void
  /** The tempo the score prints, where it prints one. */
  printed?: number
  selection: Selection
  setSelection: (selection: Selection) => void
  loop: boolean
  setLoop: (loop: boolean) => void
  click: boolean
  setClick: (click: boolean) => void
}) => {
  const state = useEngine()
  const last = bars[bars.length - 1]?.n ?? 1

  const clamp = (n: number) => Math.min(Math.max(1, n), last)

  return (
    <div className="transport">
      <button
        className="primary"
        onClick={() =>
          state.playing ? engine.stop() : engine.play(bars, { bpm, selection, loop, click })
        }
      >
        {state.playing ? 'Arrêter' : 'Écouter'}
      </button>

      <label>
        Tempo
        <input
          type="range" min={30} max={300} value={bpm}
          onChange={(e) => setBpm(Number(e.target.value))}
        />
        <input
          type="number" min={30} max={300} value={bpm}
          onChange={(e) => setBpm(Number(e.target.value) || bpm)}
        />
        bpm
      </label>

      {/* The printed tempo is offered, never imposed past the first look: a
          show tempo is not a practice tempo, and the whole point of this app
          is working a passage slowly and winding it up. */}
      {printed !== undefined && printed !== bpm && (
        <button className="printed" onClick={() => setBpm(printed)}>
          partition : {printed}
        </button>
      )}

      <label>
        Mesures
        <input
          type="number" min={1} max={last} value={selection.from}
          onChange={(e) => {
            const from = clamp(Number(e.target.value))
            setSelection({ from, to: Math.max(from, selection.to) })
          }}
        />
        à
        <input
          type="number" min={1} max={last} value={selection.to}
          onChange={(e) => {
            const to = clamp(Number(e.target.value))
            setSelection({ from: Math.min(selection.from, to), to })
          }}
        />
        <button onClick={() => setSelection({ from: 1, to: last })}>tout</button>
      </label>

      <label>
        <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} />
        boucle
      </label>
      <label>
        <input type="checkbox" checked={click} onChange={(e) => setClick(e.target.checked)} />
        métronome
      </label>
    </div>
  )
}
