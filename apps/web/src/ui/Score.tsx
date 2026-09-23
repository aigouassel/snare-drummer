import { useEffect, useRef, useState } from 'react'
import { type Bar } from '@snare-drummer/core/bar'
import { renderScore } from '@snare-drummer/notation/score'

/**
 * The engraved music.
 *
 * Re-drawn when the bars, the width or the playing bar change — and not on
 * every frame. VexFlow lays a system out from scratch each time, which is far
 * too much work to do sixty times a second; the playhead therefore moves a
 * bar at a time rather than a note at a time, which is also what you actually
 * follow when reading.
 */
export const Score = ({ bars, playingBar, onBarClick }: {
  bars: readonly Bar[]
  playingBar?: number | null
  onBarClick?: (n: number) => void
}) => {
  const host = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(900)

  useEffect(() => {
    const element = host.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setWidth(Math.max(420, entry.contentRect.width - 8))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const element = host.current
    if (!element) return
    const { boxes } = renderScore(element, bars, {
      width,
      ...(playingBar == null ? {} : { playingBar }),
    })
    if (!onBarClick) return

    const onClick = (event: MouseEvent) => {
      const rect = element.getBoundingClientRect()
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top
      const hit = boxes.find(
        (b) => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height,
      )
      if (hit) onBarClick(hit.n)
    }
    element.addEventListener('click', onClick)
    return () => element.removeEventListener('click', onClick)
  }, [bars, width, playingBar, onBarClick])

  return <div className="score" ref={host} />
}
