import { useMemo, useState } from 'react'
import {
  type Work, LISTED_COUNT, SEQUENCE_COUNT, WORKS, findSequence, searchWorks,
  workTitle,
} from '@snare-drummer/catalogue'
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
/** Works holding at least one sequence that can be played.
 *
 *  The search runs over these rather than over the whole repertoire and being
 *  narrowed afterwards. It decides one thing globally -- that an approximate
 *  match is withheld while an exact one exists -- and deciding it over shows
 *  the library does not list would withhold the best answer it has on account
 *  of a row nobody can see. */
const PLAYABLE = WORKS.filter((w) => TRANSCRIBED_WORKS.has(w.id))

/** Sequences of the repertoire the pipeline could not read. See HELD-BACK.md. */
const HELD_BACK = SEQUENCE_COUNT - TRANSCRIBED.size

/** The passage a search matched, named, or nothing if the show's own name did.
 *
 *  A held-back passage is not named: it matched, but it cannot be opened, and
 *  pointing at it would promise something the library does not offer. */
const matchedTitle = (id: string | null): string | null => {
  if (id === null || !TRANSCRIBED.has(id)) return null
  return findSequence(id)?.sequence.title ?? null
}

/** How many of a work's passages can actually be played. */
const playableCount = (work: Work) =>
  work.sequences.filter((s) => TRANSCRIBED.has(s.id)).length

export const Library = ({ selected, onSelect }: {
  selected: string | null
  onSelect: (work: Work) => void
}) => {
  const [text, setText] = useState('')

  const hits = useMemo(() => searchWorks(PLAYABLE, text), [text])

  /* A search that had to fall back on edit distance says so. The alternative
     is presenting a guess with the same face as a fact, which is the failure
     this whole project is built to avoid. */
  const approximate = text.trim() !== '' && hits[0]?.exact === false

  return (
    <aside className="library">
      <header>
        <h1>snare drummer</h1>
        <div className="count">
          {hits.length} / {PLAYABLE.length} morceaux · {TRANSCRIBED.size}{' '}
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

      {/* One field, and no dropdowns. Each of the three said one thing about a
          show, and all three things are in the text of the entry: the search
          now reads the circuit too, which it never did while that was a
          dropdown's job. The words may come from different fields -- `bd 2019`,
          `dci snare break` -- and the placeholder says so, because a field that
          accepts more than it looks like it does gets used for less. */}
      <div className="filters">
        <input
          type="search"
          autoComplete="off"
          spellCheck={false}
          aria-label="chercher dans la bibliothèque"
          placeholder="blue devils 2019 · dci · snare break · bd…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {approximate && (
          <div className="note">
            rien ne correspond exactement — voici le plus proche
          </div>
        )}
      </div>

      <div className="entries">
        {hits.map(({ work, matched }) => (
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
              {/* Why this row came back, when it was a passage that matched and
                  not the show's own name. Without it, searching `circus` returns
                  `Blue Devils 2019` and the row looks like a stray. */}
              {matchedTitle(matched) && <> · {matchedTitle(matched)}</>}
            </div>
          </button>
        ))}
        {hits.length === 0 && (
          <div className="empty" style={{ padding: '20px 16px' }}>Rien ne correspond.</div>
        )}
      </div>
    </aside>
  )
}
