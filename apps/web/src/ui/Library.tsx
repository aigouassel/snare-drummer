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
 * Only what can be played is listed. Showing the rest was a deliberate choice
 * once — an unread sequence still opens its PDF, and leaving it visible kept
 * the size of the remaining work in sight — and it is worth saying why that
 * changed rather than letting it look like an oversight. This is a practice
 * app: every row you cannot play is a row you have to learn to skip. The
 * remaining work is now written down where it belongs, in HELD-BACK.md,
 * which the pipeline generates and which cannot go stale.
 *
 * The count still says how many were set aside, because a library that
 * quietly shrank would misrepresent the catalogue.
 */
/** Works holding at least one sequence that can be played. */
const PLAYABLE_WORKS = WORKS.filter((w) => TRANSCRIBED_WORKS.has(w.id)).length

/** Sequences of the repertoire the pipeline could not read. See HELD-BACK.md. */
const HELD_BACK = SEQUENCE_COUNT - TRANSCRIBED.size

/** How many of a work's passages can actually be played. */
const playableCount = (work: Work) =>
  work.sequences.filter((s) => TRANSCRIBED.has(s.id)).length

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
      }).filter((w) => TRANSCRIBED_WORKS.has(w.id)),
    [text, circuit, corps, year],
  )

  return (
    <aside className="library">
      <header>
        <h1>snare drummer</h1>
        <div className="count">
          {works.length} / {PLAYABLE_WORKS} morceaux · {TRANSCRIBED.size}{' '}
          séquences jouables
        </div>
        {/* The library is each corps at its most recent season, and only the
            part of it that can be played. Saying both keeps the count from
            looking like the whole site, and keeps what was set aside from
            disappearing without trace. */}
        <div className="note">
          la saison la plus récente de chaque ensemble, sur {LISTED_COUNT.works}{' '}
          listées · {HELD_BACK} séquences illisibles écartées
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
            <div className="title">{workTitle(work)}</div>
            <div className="meta">
              {work.circuit} · {playableCount(work)} séquence
              {playableCount(work) > 1 ? 's' : ''}
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
