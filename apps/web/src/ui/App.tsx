import { useEffect, useState } from 'react'
import { type Work } from '@snare-drummer/catalogue'
import { TRANSCRIBED } from '@snare-drummer/transcription'
import { engine } from '../audio/engine'
import { Editor } from './editor/Editor'
import { Home } from './Home'
import { Library } from './Library'
import { WorkView } from './WorkView'

/**
 * Three places, and the address bar says which.
 *
 * Hash routes rather than a router: there are three destinations and no
 * server, so the fragment is the whole URL that matters, and a dependency
 * would be bought to do what `hashchange` already does. What the hash buys is
 * that a score being edited survives a reload and can be bookmarked.
 *
 *   #/            the front page: play, or transcribe
 *   #/library     the transcribed repertoire, as before
 *   #/edit/<id>   one score being typed in
 */
type Route =
  | { page: 'home' }
  | { page: 'library' }
  | { page: 'edit'; id: string }

const parse = (hash: string): Route => {
  const path = hash.replace(/^#\/?/, '')
  if (path.startsWith('edit/')) return { page: 'edit', id: decodeURIComponent(path.slice(5)) }
  if (path === 'library') return { page: 'library' }
  return { page: 'home' }
}

export const go = (to: string) => {
  window.location.hash = to
}

const useRoute = (): Route => {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash))
  useEffect(() => {
    const onChange = () => setRoute(parse(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

const LibraryPage = () => {
  const [work, setWork] = useState<Work | null>(null)
  const [sequenceId, setSequenceId] = useState<string | null>(null)

  // Changing show stops whatever was playing. Letting one season's audio run
  // under another's score is confusing in exactly the way this app is meant
  // to avoid.
  useEffect(() => {
    engine.stop()
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

export const App = () => {
  const route = useRoute()

  // Leaving a page stops its audio; a score playing under another page is
  // the same confusion as one season under another.
  useEffect(() => {
    engine.stop()
  }, [route.page])

  switch (route.page) {
    case 'library':
      return <LibraryPage />
    case 'edit':
      return <Editor id={route.id} />
    default:
      return <Home />
  }
}
