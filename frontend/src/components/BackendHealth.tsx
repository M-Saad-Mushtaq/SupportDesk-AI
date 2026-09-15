import { useEffect, useState } from 'react'

export function BackendHealth() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let disposed = false
    const timer = window.setTimeout(() => controller.abort(), 5000)
    async function check() {
      try {
        const response = await fetch('/api/health', { signal: controller.signal, cache: 'no-store' })
        if (!response.ok) throw new Error('Health check failed')
        const data: unknown = await response.json()
        if (typeof data !== 'object' || data === null || !('status' in data) || data.status !== 'ok') throw new Error('Unexpected health response')
        if (!disposed) setStatus('ok')
      } catch {
        if (!disposed) setStatus('error')
      } finally { window.clearTimeout(timer) }
    }
    void check()
    return () => { disposed = true; controller.abort(); window.clearTimeout(timer) }
  }, [attempt])
  return (
    <div className={`backend-health backend-health--${status}`}>
      <span role="status"><span className="dot" />{status === 'loading' ? 'Checking backend…' : status === 'ok' ? 'Backend connected' : 'Backend unavailable'}</span>
      <button aria-label="Recheck backend connection" title="Recheck backend connection" disabled={status === 'loading'} onClick={() => { setStatus('loading'); setAttempt((value) => value + 1) }}>↻</button>
    </div>
  )
}
