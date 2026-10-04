import { useRef, useState } from 'react'
import type { AgentRun, AIStatus } from '../agentApi'
import { providerLabel } from '../agentApi'
import type { Ticket, TicketAction } from '../data/inbox'

export function AgentRunStatus({ ticket, runs, aiStatus, onAction, saving }: { ticket: Ticket; runs: AgentRun[]; aiStatus: AIStatus | null; onAction: (action: TicketAction) => Promise<void>; saving: boolean }) {
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)
  const latest = runs[0]
  const active = runs.some((run) => run.status === 'pending' || run.status === 'running')
  const blocked = saving || busy || ticket.status === 'Resolved' || active

  async function retry() {
    if (!latest || blocked || inFlight.current) return
    inFlight.current = true
    setBusy(true); setError(''); setNotice('')
    try {
      await onAction({ type: 'retry-agent', runId: latest.id, id: crypto.randomUUID(), time: new Date().toLocaleTimeString() })
      setNotice('Retry accepted. Check the run status below.')
    } catch (error) { setError(error instanceof Error ? error.message : 'Request failed. Retry the same action.') }
    finally { inFlight.current = false; setBusy(false) }
  }

  if (!latest && !aiStatus?.error) return null
  return <details className="agent-status-panel"><summary>Agent run status <span>{latest ? `Latest run: ${latest.status} / ` : ''}{providerLabel(aiStatus)}</span></summary>
    {aiStatus?.error && <p className="action-error" role="alert">{aiStatus.error}</p>}
    {active && <p role="status">Agent turn pending/running. AI-handled conversations accept the next message after this turn finishes. Takeover remains available.</p>}
    {latest && <div className="agent-run-status"><strong>Latest run: {latest.status}</strong><span>{latest.provider} / {latest.model} / Attempt {latest.attempt}</span>{latest.error && <p role="alert">{latest.error}</p>}{latest.retry_at && <p>Retry after {new Date(latest.retry_at).toLocaleString()}</p>}{['failed', 'interrupted'].includes(latest.status) && ticket.handling === 'AI handling' && <button className="text-button" disabled={blocked} onClick={() => { void retry() }}>Retry agent turn</button>}</div>}
    <p role="status">{notice}</p>{error && <p className="action-error" role="alert">{error}</p>}
  </details>
}
