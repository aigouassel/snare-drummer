import { useMemo, useState, useSyncExternalStore } from 'react'
import { LISTED_WORKS, type Sequence, type Work, searchWorks, workTitle } from '@snare-drummer/catalogue'
import { TRANSCRIBED } from '@snare-drummer/transcription'
import { newDraft, toRaw } from '../editor/draft'
import { mine, snapshot } from '../store/mine'
import { go } from './App'

/**
 * The front page: play what is transcribed, or transcribe something.
 *
 * Two doors and a list. The list is the scores typed in on this browser,
 * because they are the ones with nowhere else to be found; the repertoire
 * has its own page and its own search.
 *
 * Starting a transcription offers the catalogue first. It lists 884 sequences
 * with their PDFs, and the ones the pipeline could not read are exactly the
 * ones worth typing -- so the search covers the *whole* listing here, not the
 * shipped repertoire, and says which are already playable.
 */
export const Home = () => {
  const drafts = useSyncExternalStore(mine.subscribe, snapshot, snapshot)
  const [starting, setStarting] = useState(false)

  return (
    <main className="home">
      <header className="home-head">
        <h1>snare drummer</h1>
        <p>des partitions de caisse claire, à écouter et à travailler.</p>
      </header>

      <section className="doors">
        <button className="door" onClick={() => go('/library')}>
          <span className="door-title">Consulter les partitions</span>
          <span className="door-sub">{TRANSCRIBED.size} séquences retranscrites, à écouter mesure par mesure</span>
        </button>
        <button className="door" onClick={() => setStarting(true)}>
          <span className="door-title">Retranscrire une partition</span>
          <span className="door-sub">la saisir toi-même, le PDF de référence sous les yeux</span>
        </button>
      </section>

      {starting && <Start onClose={() => setStarting(false)} />}

      <section className="mine">
        <h2>Mes partitions</h2>
        {drafts.length === 0 ? (
          <div className="empty">Rien encore. Elles restent dans ce navigateur ; exporte-les en JSON pour les garder ailleurs.</div>
        ) : (
          <ul className="mine-list">
            {drafts.map((d) => (
              <li key={d.id}>
                <button className="mine-open" onClick={() => go(`/edit/${encodeURIComponent(d.id)}`)}>
                  <span className="title">{d.title || 'sans titre'}</span>
                  <span className="meta">{d.corps || '—'} · {d.bars.length} mesure{d.bars.length > 1 ? 's' : ''} · {d.savedAt.slice(0, 10)}</span>
                </button>
                <button className="small" onClick={() => download(d.id, 'draft')} title="le brouillon, réimportable ici">exporter</button>
                <button className="small" onClick={() => download(d.id, 'piece')} title="au format du catalogue, pour src/pieces/">→ catalogue</button>
                <button className="small danger" onClick={() => { if (confirm(`Supprimer « ${d.title} » ?`)) mine.remove(d.id) }}>supprimer</button>
              </li>
            ))}
          </ul>
        )}
        <ImportButton />
      </section>
    </main>
  )
}

/**
 * Two exports, because two things want the file. The draft keeps the grid and
 * comes back through the import button; the piece is the pipeline's own format
 * and is what goes into `src/pieces/` -- it has no grid, so it cannot come
 * back here, which is why it is not the one the import reads.
 */
const download = (id: string, kind: 'draft' | 'piece') => {
  const draft = mine.get(id)
  if (!draft) return
  const body = kind === 'draft' ? draft : toRaw(draft)
  const blob = new Blob([JSON.stringify(body, null, 1)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = kind === 'draft' ? `${draft.id}.draft.json` : `${draft.id}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

/**
 * Importing takes the editor's own save, not the pipeline's JSON: a piece
 * file has events but no grid, and rebuilding cells from durations is a
 * guess this page has no business making. The draft is saved beside the
 * exported piece by the editor, so a score can travel as a pair.
 */
const ImportButton = () => (
  <label className="import">
    importer un brouillon (.draft.json)
    <input
      type="file"
      accept="application/json"
      onChange={async (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        try {
          const parsed: unknown = JSON.parse(await file.text())
          const first = (parsed as { bars?: unknown[] } | null)?.bars?.[0]
          if (first && typeof first === 'object' && 'cells' in first) {
            mine.save(parsed as never)
          } else {
            alert('Ce fichier n’est pas un brouillon de l’éditeur.')
          }
        } catch {
          alert('Fichier illisible.')
        }
        e.target.value = ''
      }}
    />
  </label>
)

/** Where a new transcription starts: a catalogue sequence, or a blank page. */
const Start = ({ onClose }: { onClose: () => void }) => {
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [corps, setCorps] = useState('')

  const hits = useMemo(() => (text.trim() ? searchWorks(LISTED_WORKS, text).slice(0, 12) : []), [text])

  const begin = (fields: { title: string; corps: string; sourceUrl: string; id?: string }) => {
    const draft = newDraft(fields)
    mine.save(draft)
    go(`/edit/${encodeURIComponent(draft.id)}`)
  }

  return (
    <section className="start">
      <div className="start-head">
        <h2>Nouvelle transcription</h2>
        <button className="small" onClick={onClose}>fermer</button>
      </div>

      <label className="field">
        Depuis le catalogue
        <input
          type="search"
          placeholder="blue devils 2019 · scv · snare break…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus
        />
      </label>
      {hits.length > 0 && (
        <ul className="start-hits">
          {hits.map(({ work }) => (
            <li key={work.id}>
              <span className="title">{workTitle(work)}</span>
              <span className="seqs">
                {work.sequences.map((s: Sequence) => (
                  <button
                    key={s.id}
                    className="sequence"
                    title={TRANSCRIBED.has(s.id) ? 'déjà retranscrite par le pipeline' : 'pas encore retranscrite'}
                    onClick={() => begin({ title: `${workTitle(work)} — ${s.title}`, corps: work.corps, sourceUrl: s.url, id: `mine-${s.id}` })}
                  >
                    {s.title}{TRANSCRIBED.has(s.id) ? ' ✓' : ''}
                  </button>
                ))}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="or">ou de zéro</div>
      <div className="start-blank">
        <label className="field">titre<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Snare break" /></label>
        <label className="field">ensemble<input value={corps} onChange={(e) => setCorps(e.target.value)} placeholder="facultatif" /></label>
        <label className="field">lien PDF<input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://… (facultatif)" /></label>
        <button className="primary" disabled={!title.trim()} onClick={() => begin({ title: title.trim(), corps: corps.trim(), sourceUrl: url.trim() })}>
          commencer
        </button>
      </div>
    </section>
  )
}

// Keeps the Work type in use for the search hits' typing above.
export type { Work }
