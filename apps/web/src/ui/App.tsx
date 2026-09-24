import { useEffect, useState } from 'react'
import { type Work } from '@snare-drummer/catalogue'
import { TRANSCRIBED } from '@snare-drummer/transcription'
import { engine } from '../audio/engine'
import { Library } from './Library'
import { WorkView } from './WorkView'

export const App = () => {
  const [work, setWork] = useState<Work | null>(null)
  const [sequenceId, setSequenceId] = useState<string | null>(null)

  // Changing show stops whatever was playing. Letting one season's audio run
  // under another's score is confusing in exactly the way this app is meant
  // to avoid.
  useEffect(() => {
    engine.stop()
    // Open on a sequence that can actually be played, where the show has one.
    // Only playable passages are listed, so opening a work opens its first
    // one. The fallback is kept for the case where the library and the
    // transcriptions disagree, which would otherwise show a chosen sequence
    // that is not in the list.
    const playable = work?.sequences.find((s) => TRANSCRIBED.has(s.id))
    setSequenceId(playable?.id ?? null)
  }, [work])

  return (
    <div className="app">
      <Library selected={work?.id ?? null} onSelect={setWork} />
      <WorkView work={work} sequenceId={sequenceId} onSelectSequence={setSequenceId} />
    </div>
  )
}
