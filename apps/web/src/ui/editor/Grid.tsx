import { type Cell, type DraftBar, cellLabel } from '../../editor/draft'

/**
 * One bar as a row of cells.
 *
 * The beat is what the eye needs: cells are grouped per beat with a wider gap
 * between beats, and each beat's first cell says its number. A stroke's cell
 * carries a short label -- hand, accent, flam, roll -- and a held cell stays
 * blank, so a quarter note reads as one mark and three blanks, which is also
 * how it feels to play.
 */
export const Grid = ({ bar, cursor, onCursor, playingBeat }: {
  bar: DraftBar
  cursor: number | null
  onCursor: (index: number) => void
  playingBeat?: number | null
}) => {
  const perBeat = bar.unit[1] / bar.unit[0]
  const beats = Math.ceil(bar.cells.length / perBeat)
  return (
    <div className="grid" role="grid">
      {Array.from({ length: beats }, (_, beat) => (
        <div
          className="beat"
          key={beat}
          data-playing={playingBeat === beat + 1 ? 'true' : undefined}
        >
          {bar.cells.slice(beat * perBeat, (beat + 1) * perBeat).map((cell, k) => {
            const index = beat * perBeat + k
            return (
              <button
                key={index}
                className={`cell ${kindClass(cell)}`}
                aria-current={cursor === index}
                onClick={() => onCursor(index)}
                title={k === 0 ? `temps ${beat + 1}` : undefined}
              >
                <span className="cell-label">{cellLabel(cell)}</span>
                {k === 0 && <span className="cell-beat">{beat + 1}</span>}
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}

const kindClass = (cell: Cell): string => {
  if (cell.kind === 'hold') return 'hold'
  if (cell.kind === 'rest') return 'rest'
  return `stroke${cell.accent ? ` ${cell.accent}` : ''}`
}
