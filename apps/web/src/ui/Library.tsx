import { useMemo, useState } from 'react'
import {
  type Work, LISTED_COUNT, SEQUENCE_COUNT, WORKS, corpsList, filter, workTitle,
  years,
} from '@snare-drummer/catalogue'
import { type Circuit } from '@snare-drummer/core/piece'
import { TRANSCRIBED, TRANSCRIBED_WORKS } from '@snare-drummer/transcription'

/**
 * The library, listed by show rather than by file.
 *
 * A corps performs one show a season and writes it in passages; the site
 * publishes one PDF per passage. Listing the PDFs flat turned 327 shows into
 * 884 unrelated rows, which is not how any of it is practised — the passages
 * of one season belong together and are worked together.
 *
 * Untranscribed works are listed too. One that cannot be played yet can still
 * be opened as a PDF, and showing it keeps the size of the remaining work
 * visible instead of hidden.
 */
export const Library = ({ selected, onSelect }: {
  selected: string | null
  onSelect: (work: Work) => void
}) => {
  const [text, setText] = useState('')
  const [circuit, setCircuit] = useState<Circuit | ''>('')
  const [corps, setCorps] = useState('')
  const [year, setYear] = useState('')

  const works = useMemo(
    () =>
      filter({
        ...(text ? { text } : {}),
        ...(circuit ? { circuit } : {}),
        ...(corps ? { corps } : {}),
        ...(year ? { year: Number(year) } : {}),
      }),
    [text, circuit, corps, year],
  )

  return (
    <aside className="library">
      <header>
        <h1>snare drummer</h1>
        <div className="count">
          {works.length} / {WORKS.length} morceaux · {SEQUENCE_COUNT} séquences ·{' '}
          {TRANSCRIBED.size} retranscrite{TRANSCRIBED.size > 1 ? 's' : ''}
        </div>
        {/* The library is each corps at its most recent season. Saying so
            keeps the count from looking like the whole site. */}
        <div className="note">
          la saison la plus récente de chaque ensemble, sur {LISTED_COUNT.works}{' '}
          listées
        </div>
      </header>

      <div className="filters">
        <input
          placeholder="chercher un ensemble, une année, une séquence…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <select value={circuit} onChange={(e) => setCircuit(e.target.value as Circuit | '')}>
          <option value="">tous les circuits</option>
          <option value="DCI">DCI</option>
          <option value="WGI">WGI</option>
          <option value="DCA">DCA</option>
          <option value="other">autres</option>
        </select>
        <select value={corps} onChange={(e) => setCorps(e.target.value)}>
          <option value="">tous les ensembles</option>
          {corpsList().map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <select value={year} onChange={(e) => setYear(e.target.value)}>
          <option value="">toutes les années</option>
          {[...years()].reverse().map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      <div className="entries">
        {works.slice(0, 300).map((work) => (
          <button
            key={work.id}
            className="entry"
            aria-current={work.id === selected}
            onClick={() => onSelect(work)}
          >
            <div className="title">
              {workTitle(work)}
              {TRANSCRIBED_WORKS.has(work.id) && <span className="badge">jouable</span>}
            </div>
            <div className="meta">
              {work.circuit} · {work.sequences.length} séquence
              {work.sequences.length > 1 ? 's' : ''}
            </div>
          </button>
        ))}
        {works.length > 300 && (
          <div className="empty" style={{ padding: '12px 16px' }}>
            … et {works.length - 300} autres. Affine la recherche.
          </div>
        )}
        {works.length === 0 && (
          <div className="empty" style={{ padding: '20px 16px' }}>Rien ne correspond.</div>
        )}
      </div>
    </aside>
  )
}
