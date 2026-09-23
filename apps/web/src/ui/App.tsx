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
    // Landing on an untranscribed passage of a work marked "jouable" reads as
    // a bug rather than as the honest state of the library.
    const playable = work?.sequences.find((s) => TRANSCRIBED.has(s.id))
    setSequenceId(playable?.id ?? work?.sequences[0]?.id ?? null)
  }, [work])

  return (
    <div className="app">
      <Library selected={work?.id ?? null} onSelect={setWork} />
      <WorkView work={work} sequenceId={sequenceId} onSelectSequence={setSequenceId} />
    </div>
  )
}
