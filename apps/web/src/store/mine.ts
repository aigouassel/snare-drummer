import { type Draft } from '../editor/draft'

/**
 * The scores typed in here, kept in this browser.
 *
 * localStorage, and nothing cleverer: a draft is a few kilobytes, and what it
 * needs is to survive a reload, not to be shared. Sharing is what the JSON
 * export is for -- the file it writes is the pipeline's own format, so a score
 * good enough to keep can be dropped into `src/pieces/` and shipped with the
 * rest, and one exported here can be imported on another machine.
 *
 * Every access is wrapped: storage can be absent, full or blocked, and the
 * editor has to keep working with an empty list rather than die on a read.
 */
const KEY = 'snare-drummer.mine.v1'

const read = (): Draft[] => {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as Draft[]) : []
  } catch {
    return []
  }
}

const write = (drafts: readonly Draft[]): boolean => {
  try {
    localStorage.setItem(KEY, JSON.stringify(drafts))
    return true
  } catch {
    return false
  }
}

const listeners = new Set<() => void>()
const notify = () => listeners.forEach((l) => l())

export const mine = {
  list: (): Draft[] =>
    read().sort((a, b) => b.savedAt.localeCompare(a.savedAt)),

  get: (id: string): Draft | undefined => read().find((d) => d.id === id),

  /** Saves and stamps the time; returns false when the browser refused. */
  save: (draft: Draft): boolean => {
    const stamped = { ...draft, savedAt: new Date().toISOString() }
    const rest = read().filter((d) => d.id !== draft.id)
    const ok = write([stamped, ...rest])
    notify()
    return ok
  },

  remove: (id: string): void => {
    write(read().filter((d) => d.id !== id))
    notify()
  },

  subscribe: (listener: () => void): (() => void) => {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
}

/** A stable snapshot for useSyncExternalStore: the serialised list. */
let cache: { key: string; value: Draft[] } | null = null
export const snapshot = (): Draft[] => {
  let key = ''
  try {
    key = localStorage.getItem(KEY) ?? ''
  } catch {
    key = ''
  }
  if (cache && cache.key === key) return cache.value
  cache = { key, value: mine.list() }
  return cache.value
}
