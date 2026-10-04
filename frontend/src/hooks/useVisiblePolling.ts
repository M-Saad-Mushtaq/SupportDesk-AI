import { useEffect } from 'react'

/** One request at a time; no hidden-tab polling or timers after unmount. */
export function useVisiblePolling(task: (signal: AbortSignal) => Promise<void>, enabled: boolean, delay: number) {
  useEffect(() => {
    if (!enabled) return
    let disposed = false
    let busy = false
    let timer: number | undefined
    let controller: AbortController | undefined
    async function tick() {
      if (disposed || document.hidden || busy) return
      busy = true
      controller = new AbortController()
      try { await task(controller.signal) }
      catch { /* Callers own actionable error UI; aborted requests need no alert. */ }
      finally {
        busy = false
        if (!disposed && !document.hidden) timer = window.setTimeout(() => { void tick() }, delay)
      }
    }
    function visibility() {
      window.clearTimeout(timer)
      if (document.hidden) controller?.abort()
      else void tick()
    }
    document.addEventListener('visibilitychange', visibility)
    void tick()
    return () => { disposed = true; window.clearTimeout(timer); controller?.abort(); document.removeEventListener('visibilitychange', visibility) }
  }, [task, enabled, delay])
}
