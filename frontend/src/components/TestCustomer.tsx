import { useState } from 'react'
import type { AgentRun, AIStatus } from '../agentApi'
import { providerLabel } from '../agentApi'
import type { Ticket, TicketAction } from '../data/inbox'

export function TestCustomer({ ticket, runs, aiStatus, onAction, saving }: { ticket: Ticket; runs: AgentRun[]; aiStatus: AIStatus | null; onAction: (action: TicketAction) => Promise<void>; saving: boolean }) {
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const latest = runs[0]
  const active = runs.some((run) => run.status === 'pending' || run.status === 'running')
  const blocked = saving || busy || ticket.status === 'Resolved' || (active && ticket.handling === 'AI handling')
  const context = () => ({ id: crypto.randomUUID(), time: new Date().toLocaleTimeString() })
  async function perform(action: TicketAction) {
    setBusy(true); setError(''); setNotice('')
    try {
      await onAction(action)
      if (action.type === 'test-customer') setDraft('')
      setNotice(action.type === 'test-customer' ? 'Test message saved locally. Check the run status below.' : 'Retry accepted. Check the run status below.')
    } catch (error) { setError(error instanceof Error ? error.message : 'Request failed. Your input is kept; retry the same action.') }
    finally { setBusy(false) }
  }
  return <details className="test-customer-panel"><summary>Send test customer message <span>{latest ? `Latest run: ${latest.status} / ` : ''}{providerLabel(aiStatus)}</span></summary>
    <p className="muted">Local test only. {ticket.handling === 'AI handling' ? 'Uses the configured provider. Gemini sends public conversation context and relevant tool excerpts to Google.' : 'AI is paused. This message will be stored without generating a reply.'}</p>
    {aiStatus?.error && <p className="action-error">{aiStatus.error}</p>}
    <form onSubmit={(event) => { event.preventDefault(); if (!blocked && draft.trim()) void perform({ type: 'test-customer', text: draft.trim(), ...context() }) }}>
      <label htmlFor="test-customer-text">Customer message</label><textarea id="test-customer-text" rows={2} maxLength={3000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about a policy, your order, or human support" />
      <button className="secondary-button" disabled={blocked || !draft.trim()}>{busy ? 'Saving...' : 'Send test message'}</button>
    </form>
    {ticket.status === 'Resolved' && <p>Reopen the ticket to send a test message.</p>}
    {active && <p role="status">Agent turn pending/running. AI-handled conversations accept the next message after this turn finishes. Takeover remains available.</p>}
    {latest && <div className="agent-run-status"><strong>Latest run: {latest.status}</strong><span>{latest.provider} / {latest.model} / Attempt {latest.attempt}</span>{latest.error && <p role="alert">{latest.error}</p>}{latest.retry_at && <p>Retry after {new Date(latest.retry_at).toLocaleString()}</p>}{['failed', 'interrupted'].includes(latest.status) && ticket.handling === 'AI handling' && <button className="text-button" disabled={blocked} onClick={() => { void perform({ type: 'retry-agent', runId: latest.id, ...context() }) }}>Retry agent turn</button>}</div>}
    <p role="status">{notice}</p>{error && <p className="action-error" role="alert">{error}</p>}
  </details>
}
