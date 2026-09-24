import { useEffect, useMemo, useState } from 'react'
import { type Work, workTitle } from '@snare-drummer/catalogue'
import { explain } from '@snare-drummer/core/confidence'
import { trust } from '@snare-drummer/core/piece'
import { TRANSCRIBED, pieceById } from '@snare-drummer/transcription'
import { type Selection, engine } from '../audio/engine'
import { Score } from './Score'
import { Transport } from './Transport'
import { useEngine } from './useEngine'

/**
 * One show: its passages, and the one currently open.
 *
 * The sequences are listed even when only one of them can be played, because
 * the list is what says how the season was written. Choosing between them is
 * the first thing you do; everything below it belongs to the chosen one.
 *
 * The source link is printed whatever state a sequence is in. These are other
 * people's transcriptions of other people's shows, and saying where each came
 * from is the only honest way to hold them — it is also what makes a flagged
 * bar actionable, since checking one means looking at the original.
 */
export const WorkView = ({ work, sequenceId, onSelectSequence }: {
  work: Work | null
  sequenceId: string | null
  onSelectSequence: (id: string) => void
}) => {
  const sequence = work?.sequences.find((s) => s.id === sequenceId) ?? null
  const piece = sequence ? pieceById(sequence.id) : undefined
  const state = useEngine()

  // The score's own tempo where it prints one, and a working tempo where it
  // does not. Not a default dressed up as a reading: `piece.bpm` is absent
  // when the page said nothing, and 90 is then this app's choice, not the
  // arranger's.
  const [bpm, setBpm] = useState(piece?.bpm ?? 90)
  const [loop, setLoop] = useState(true)
  const [click, setClick] = useState(true)
  const [selection, setSelection] = useState<Selection>({ from: 1, to: 1 })

  const last = piece?.bars[piece.bars.length - 1]?.n ?? 1
  useEffect(() => {
    engine.stop()
    setSelection({ from: 1, to: last })
    setBpm(piece?.bpm ?? 90)
  }, [piece?.id, piece?.bpm, last])

  const flagged = useMemo(
    () => (piece ? piece.bars.filter((b) => !b.verdict.trusted) : []),
    [piece],
  )

  if (!work) {
    return <main className="piece"><div className="empty">Choisis un morceau à gauche.</div></main>
  }

  return (
    <main className="piece">
      <h2>{workTitle(work)}</h2>
      <div className="sub">
        {work.circuit} · {work.sequences.length} séquence
        {work.sequences.length > 1 ? 's' : ''}
      </div>

      <nav className="sequences">
        {work.sequences.map((s) => (
          <button
            key={s.id}
            className="sequence"
            aria-current={s.id === sequenceId}
            onClick={() => onSelectSequence(s.id)}
          >
            {s.title}
            {TRANSCRIBED.has(s.id) && <span className="dot" aria-label="retranscrite" />}
          </button>
        ))}
      </nav>

      {sequence && (
        <div className="source">
          source : <a href={sequence.url} target="_blank" rel="noreferrer">{sequence.url}</a>
        </div>
      )}

      {!piece ? (
        <div className="empty">
          Séquence pas encore retranscrite. Le PDF reste consultable par le lien ci-dessus.
        </div>
      ) : (
        <>
          <Transport
            bars={piece.bars}
            bpm={bpm} setBpm={setBpm} {...(piece.bpm ? { printed: piece.bpm } : {})}
            selection={selection} setSelection={setSelection}
            loop={loop} setLoop={setLoop}
            click={click} setClick={setClick}
          />

          <div className="trust">
            <span>{trust(piece).trusted} / {trust(piece).total} mesures vérifiées</span>
            {flagged.length > 0 && (
              <span className="flagged">
                {flagged.length} signalée{flagged.length > 1 ? 's' : ''}
              </span>
            )}
          </div>

          <Score
            bars={piece.bars}
            playingBar={state.playing ? state.bar : null}
            onBarClick={(n) =>
              setSelection((current) =>
                current.from === current.to && current.from === n
                  ? { from: 1, to: last }
                  : { from: n, to: n },
              )
            }
          />

          {flagged.length > 0 && (
            <div className="concerns">
              {flagged.map((bar) => (
                <div className="concern" key={bar.n}>
                  <strong>mesure {bar.n}</strong>
                  {' — '}
                  {bar.verdict.trusted ? null : bar.verdict.concerns.map(explain).join(' ; ')}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  )
}
