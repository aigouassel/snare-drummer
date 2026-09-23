import { useSyncExternalStore } from 'react'
import { type EngineState, engine } from '../audio/engine'

/**
 * React's view of the engine, and nothing more.
 *
 * The engine runs on its own timer against the audio clock; this subscribes
 * for display. Keeping the direction of that arrow one-way is what stops a
 * re-render from ever being in the path of a note being scheduled.
 */
export const useEngine = (): EngineState =>
  useSyncExternalStore(
    (listener) => engine.subscribe(listener),
    () => engine.getState(),
    () => engine.getState(),
  )
