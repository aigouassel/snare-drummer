import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { type Meter } from '@snare-drummer/core/bar'
import { fromRaw } from '@snare-drummer/transcription'
import { engine } from '../../audio/engine'
import {
  ACCENTS, type Cell, type Draft, type DraftBar, UNITS, type Unit, cellCount, emptyBar,
  recut, toRaw,
} from '../../editor/draft'
import { mine } from '../../store/mine'
import { go } from '../App'
import { PdfPane } from '../PdfPane'
import { Score } from '../Score'
import { useEngine } from '../useEngine'
import { Grid } from './Grid'

/**
 * Typing a score in, with the page it comes from beside it.
 *
 * The grid is the instrument and the keyboard drives it: the cursor is a cell,
 * the arrows move it, and a key writes into it -- R and L a stroke, space a
 * rest, backspace a blank, the accents by their own signs. Everything typed is
 * shown engraved below the grid at once, by the same renderer the library
 * uses, and played by the same engine; a bar is a click away from being
 * heard. Nothing here is saved on a timer: the draft is saved on every change,
 * because a browser tab closes without asking.
 */
const METERS: readonly Meter[] = [[4, 4], [3, 4], [2, 4], [5, 4], [6, 8], [7, 8], [9, 8], [12, 8]]

export const Editor = ({ id }: { id: string }) => {
  const [draft, setDraft] = useState<Draft | undefined>(() => mine.get(id))
  const [bar, setBar] = useState(0)
  const [cursor, setCursor] = useState<number | null>(0)
  const [bpm, setBpm] = useState(draft?.bpm ?? 90)
  const [saved, setSaved] = useState(true)
  // What the last play call covered, because the engine's beat counts from
  // the start of the pass and only means "beat of this bar" when the pass is
  // this one bar.
  const [range, setRange] = useState<{ from: number; to: number } | null>(null)
  const state = useEngine()
  const gridHost = useRef<HTMLDivElement>(null)

  // Saved on every change. The stamp is what tells the front page which was
  // touched last.
  const update = useCallback((next: Draft) => {
    setDraft(next)
    setSaved(mine.save(next))
  }, [])

  const piece = useMemo(() => (draft ? fromRaw(toRaw(draft)) : null), [draft])

  const current: DraftBar | undefined = draft?.bars[bar]

  const setCurrent = useCallback((patch: (b: DraftBar) => DraftBar) => {
    if (!draft) return
    const bars = draft.bars.map((b, i) => (i === bar ? patch(b) : b))
    update({ ...draft, bars })
  }, [draft, bar, update])

  const setCell = useCallback((index: number, cell: Cell) => {
    setCurrent((b) => ({ ...b, cells: b.cells.map((c, i) => (i === index ? cell : c)) }))
  }, [setCurrent])

  const editCell = useCallback((index: number, patch: (c: Cell) => Cell) => {
    setCurrent((b) => ({ ...b, cells: b.cells.map((c, i) => (i === index ? patch(c) : c)) }))
  }, [setCurrent])

  const addBar = useCallback(() => {
    if (!draft) return
    const last = draft.bars[draft.bars.length - 1] ?? emptyBar()
    update({ ...draft, bars: [...draft.bars, emptyBar(last.meter, last.unit)] })
    setBar(draft.bars.length)
    setCursor(0)
  }, [draft, update])

  const removeBar = useCallback(() => {
    if (!draft || draft.bars.length <= 1) return
    update({ ...draft, bars: draft.bars.filter((_b, i) => i !== bar) })
    setBar(Math.max(0, bar - 1))
  }, [draft, bar, update])

  const play = useCallback((from: number, to: number) => {
    if (!piece) return
    if (state.playing) engine.stop()
    else {
      setRange({ from, to })
      engine.play(piece.bars, { bpm, selection: { from, to }, loop: false, click: true })
    }
  }, [piece, bpm, state.playing])

  // Keys act on the cursor. They are captured on the grid's own host so that
  // typing a title or a tempo never writes a stroke.
  useEffect(() => {
    const host = gridHost.current
    if (!host || !current) return
    const onKey = (e: KeyboardEvent) => {
      if (cursor === null) return
      const n = current.cells.length
      const at = (c: Cell) => current.cells[cursor] ?? c
      const stroke = (patch: Partial<Extract<Cell, { kind: 'stroke' }>>) =>
        editCell(cursor, (c) => ({ ...(c.kind === 'stroke' ? c : { kind: 'stroke' as const }), ...patch }))
      const advance = () => setCursor((cursor + 1) % n)
      switch (e.key) {
        case 'ArrowRight': setCursor((cursor + 1) % n); break
        case 'ArrowLeft': setCursor((cursor - 1 + n) % n); break
        case 'ArrowUp': if (bar > 0) { setBar(bar - 1); setCursor(0) } break
        case 'ArrowDown': if (draft && bar < draft.bars.length - 1) { setBar(bar + 1); setCursor(0) } break
        case 'Home': setCursor(0); break
        case 'End': setCursor(n - 1); break
        case 'r': case 'R': stroke({ hand: 'right' }); advance(); break
        case 'l': case 'L': stroke({ hand: 'left' }); advance(); break
        case 'x': case 'X': stroke({}); advance(); break
        case ' ': setCell(cursor, { kind: 'rest' }); advance(); e.preventDefault(); break
        case 'Backspace': case 'Delete': setCell(cursor, { kind: 'hold' }); break
        case '>': stroke({ accent: at({ kind: 'stroke' }).kind === 'stroke' && (at({ kind: 'stroke' }) as { accent?: string }).accent === 'accent' ? undefined : 'accent' }); break
        case '^': stroke({ accent: 'marcato' }); break
        case '-': stroke({ accent: 'tap' }); break
        case '(': stroke({ accent: 'ghost' }); break
        case 'f': case 'F': editCell(cursor, (c) => c.kind === 'stroke' ? { ...c, graces: ((c.graces ?? 0) + 1) % 4 || undefined } : c); break
        case 'z': case 'Z': editCell(cursor, (c) => c.kind === 'stroke' ? { ...c, roll: c.roll === 'buzz' ? undefined : 'buzz' } : c); break
        case 'd': case 'D': editCell(cursor, (c) => c.kind === 'stroke' ? { ...c, roll: c.roll === 'double' ? undefined : 'double' } : c); break
        case 'Enter': play(bar + 1, bar + 1); e.preventDefault(); break
        case 'Tab': if (!e.shiftKey && bar === (draft?.bars.length ?? 1) - 1) { addBar(); e.preventDefault() } break
        default: return
      }
      e.preventDefault()
    }
    host.addEventListener('keydown', onKey)
    return () => host.removeEventListener('keydown', onKey)
  }, [current, cursor, bar, draft, editCell, setCell, play, addBar])

  useEffect(() => {
    gridHost.current?.focus()
  }, [bar])

  if (!draft || !current) {
    return (
      <main className="editor-missing">
        <div className="empty">Ce brouillon n’existe pas dans ce navigateur.</div>
        <button onClick={() => go('/')}>retour à l’accueil</button>
      </main>
    )
  }

  const playingBar = state.playing ? state.bar : null

  return (
    <div className="editor">
      <section className="edit">
        <header className="edit-head">
          <button className="small" onClick={() => go('/')}>← accueil</button>
          <input
            className="edit-title"
            value={draft.title}
            onChange={(e) => update({ ...draft, title: e.target.value })}
            placeholder="titre"
          />
          <input
            className="edit-corps"
            value={draft.corps}
            onChange={(e) => update({ ...draft, corps: e.target.value })}
            placeholder="ensemble"
          />
          <label className="edit-bpm">
            <input type="number" min={30} max={300} value={bpm}
                   onChange={(e) => { const v = Number(e.target.value) || bpm; setBpm(v); update({ ...draft, bpm: v }) }} />
            bpm
          </label>
          <span className={`saved ${saved ? '' : 'failed'}`}>{saved ? 'enregistré' : 'non enregistré — stockage refusé'}</span>
        </header>

        <label className="field edit-source">
          référence (PDF ou page)
          <input value={draft.sourceUrl} onChange={(e) => update({ ...draft, sourceUrl: e.target.value })} placeholder="https://…" />
        </label>

        <nav className="bars">
          {draft.bars.map((_b, i) => (
            <button key={i} className="sequence" aria-current={i === bar} onClick={() => { setBar(i); setCursor(0) }}>
              {i + 1}
            </button>
          ))}
          <button className="sequence add" onClick={addBar} title="Tab sur la dernière mesure">+ mesure</button>
        </nav>

        <div className="bar-tools">
          <label>
            métrique
            <select
              value={`${current.meter[0]}/${current.meter[1]}`}
              onChange={(e) => {
                const [a, b] = e.target.value.split('/').map(Number)
                const meter = [a, b] as unknown as Meter
                setCurrent((cur) => recut(cur, meter, cellCount(meter, cur.unit) ? cur.unit : [1, 4]))
                setCursor(0)
              }}
            >
              {METERS.map((m) => <option key={m.join('/')} value={m.join('/')}>{m[0]}/{m[1]}</option>)}
            </select>
          </label>
          <label>
            grille
            <select
              value={current.unit.join('/')}
              onChange={(e) => {
                const [a, b] = e.target.value.split('/').map(Number)
                const unit = [a, b] as unknown as Unit
                if (cellCount(current.meter, unit) === null) return
                setCurrent((cur) => recut(cur, cur.meter, unit))
                setCursor(0)
              }}
            >
              {UNITS.map((u) => (
                <option key={u.unit.join('/')} value={u.unit.join('/')} disabled={cellCount(current.meter, u.unit) === null}>
                  {u.label} — {u.hint}
                </option>
              ))}
            </select>
          </label>
          <button onClick={() => play(bar + 1, bar + 1)}>{state.playing ? 'arrêter' : '▶ cette mesure'}</button>
          <button onClick={() => play(1, draft.bars.length)}>{state.playing ? 'arrêter' : '▶ tout'}</button>
          <button className="danger small" onClick={removeBar} disabled={draft.bars.length <= 1}>supprimer la mesure</button>
        </div>

        <div className="grid-host" tabIndex={0} ref={gridHost}>
          <Grid
            bar={current}
            cursor={cursor}
            onCursor={(i) => { setCursor(i); gridHost.current?.focus() }}
            playingBeat={
              playingBar === bar + 1 && range && range.from === range.to
                ? Math.floor(state.beat) + 1
                : null
            }
          />
        </div>

        <div className="palette">
          {cursor !== null && (
            <>
              <button onClick={() => { editCell(cursor, (c) => ({ ...(c.kind === 'stroke' ? c : { kind: 'stroke' }), hand: 'right' })) }}>R</button>
              <button onClick={() => { editCell(cursor, (c) => ({ ...(c.kind === 'stroke' ? c : { kind: 'stroke' }), hand: 'left' })) }}>L</button>
              <button onClick={() => { editCell(cursor, (c) => ({ ...(c.kind === 'stroke' ? c : { kind: 'stroke' }), hand: undefined })) }}>● sans main</button>
              <button onClick={() => setCell(cursor, { kind: 'rest' })}>· silence</button>
              <button onClick={() => setCell(cursor, { kind: 'hold' })}>⌫ vide</button>
              <span className="sep" />
              {ACCENTS.map((a) => (
                <button key={a.label} onClick={() => editCell(cursor, (c) => c.kind === 'stroke' ? { ...c, accent: a.value } : c)}>
                  {a.key || '–'} {a.label}
                </button>
              ))}
              <span className="sep" />
              <button onClick={() => editCell(cursor, (c) => c.kind === 'stroke' ? { ...c, graces: ((c.graces ?? 0) + 1) % 4 || undefined } : c)}>f flam / drag</button>
              <button onClick={() => editCell(cursor, (c) => c.kind === 'stroke' ? { ...c, roll: c.roll === 'buzz' ? undefined : 'buzz' } : c)}>z roulé</button>
              <button onClick={() => editCell(cursor, (c) => c.kind === 'stroke' ? { ...c, roll: c.roll === 'double' ? undefined : 'double' } : c)}>d diddle</button>
            </>
          )}
        </div>
        <p className="keys">
          clavier : ← → case · ↑ ↓ mesure · <b>R</b>/<b>L</b> frappe · <b>X</b> sans main · <b>espace</b> silence · <b>⌫</b> vide
          · <b>&gt;</b> accent · <b>^</b> marcato · <b>-</b> tap · <b>(</b> ghost · <b>F</b> flam→drag→ruff · <b>Z</b> roulé · <b>D</b> diddle
          · <b>Entrée</b> écouter · <b>Tab</b> nouvelle mesure
        </p>

        {piece && (
          <div className="preview">
            <Score bars={piece.bars} playingBar={playingBar} onBarClick={(n) => { setBar(n - 1); setCursor(0) }} />
          </div>
        )}
      </section>

      <PdfPane url={draft.sourceUrl} />
    </div>
  )
}
