import { useEffect, useRef, useState } from 'react'
import type { Message, Ticket, TicketAction } from '../data/inbox'
import { ticketStatuses } from '../data/inbox'
import type { TicketStatus } from '../data/inbox'
import type { AgentRun, AIStatus } from '../agentApi'
import { AgentRunStatus } from './AgentRunStatus'
import { useChatScroll } from '../hooks/useChatScroll'
import { Icon } from './Icon'

export type Drafts = { reply: string; note: string; mode: 'reply' | 'note' }

function MessageBubble({ message, ticket }: { message: Message; ticket: Ticket }) {
  const isCustomer = message.kind === 'customer'
  const author = isCustomer ? ticket.customer.name : message.kind === 'ai' ? 'SupportDesk Assistant' : 'Alex Morgan'
  return <article className={`message message--${message.kind}`}>
    <span className={`avatar ${isCustomer ? `avatar--${ticket.customer.initials.toLowerCase()}` : 'avatar--agent'}`}>
      {message.kind === 'ai' ? <img src="/supportdesk-logo.svg" alt="" width="30" height="30" /> : isCustomer ? ticket.customer.initials : 'AM'}
    </span>
    <div className="message-content"><div className="message-meta"><strong>{author}</strong>{message.kind === 'ai' && <span className="message-label">{message.origin === 'gemini' ? 'Gemini' : message.origin === 'mock' ? 'Mock simulation' : 'AI sample'}</span>}{message.kind === 'note' && <span className="message-label"><Icon name="lock" size={12} />Internal note</span>}{message.kind === 'reply' && <span className="message-label">Demo reply</span>}<time>{message.time}</time></div>
      <div className="message-bubble">{message.text}</div>
      {!!message.sources?.length && <details className="sources"><summary><Icon name="book" size={15} />View sources ({message.sources.length})</summary><div>{message.sources.map((source) => <div className="source-card" key={source.source_id ?? source.title}><strong>{source.title}</strong><span>{source.section} / {source.source_id ? 'Retrieved document' : 'Sample policy'}</span><p>{source.quote ?? source.excerpt}</p></div>)}</div></details>}
    </div>
  </article>
}

export function Conversation({ runs, aiStatus, ticket, drafts, onDrafts, onAction, saving, onBack, onDetails, detailsOpen }: {
  runs: AgentRun[]; aiStatus: AIStatus | null; ticket: Ticket; drafts: Drafts; onDrafts: (drafts: Drafts) => void
  onAction: (action: TicketAction) => Promise<void>; saving: boolean; onBack: () => void; onDetails: () => void; detailsOpen: boolean
}) {
  const { thread, unread, jump, onScroll } = useChatScroll(ticket.messages.length)
  const heading = useRef<HTMLHeadingElement>(null)
  const [feedback, setFeedback] = useState('')
  const [actionError, setActionError] = useState('')
  const [failed, setFailed] = useState<{ action: TicketAction; success: string; clearMode?: 'reply' | 'note' } | null>(null)
  const inFlight = useRef(false)

  async function perform(action: TicketAction, success: string, clearMode?: 'reply' | 'note') {
    if (saving || inFlight.current) return
    inFlight.current = true
    setFeedback('')
    setActionError('')
    try {
      await onAction(action)
      if (clearMode && action.type === 'message' && drafts[clearMode].trim() === action.text) onDrafts({ ...drafts, [clearMode]: '' })
      setFeedback(success)
      setFailed(null)
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Save failed. Please retry.')
      setFailed({ action, success, clearMode })
    } finally { inFlight.current = false }
  }
  const isNote = drafts.mode === 'note'
  const canReply = ticket.status !== 'Resolved' && ticket.handling === 'You are handling'
  const disabled = !isNote && !canReply

  useEffect(() => { heading.current?.focus({ preventScroll: true }) }, [ticket.id])

  function context() {
    return { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) }
  }
  function submit() {
    const text = drafts[drafts.mode].trim()
    if (!text || disabled) return
    void perform({ type: 'message', kind: drafts.mode, text, ...context() }, isNote ? 'Internal note saved to SQLite.' : 'Demo reply saved to SQLite. Nothing was sent externally.', drafts.mode)
  }

  return (
    <section className="conversation" aria-label={`Conversation with ${ticket.customer.name}`}>
      <header className="chat-header">
        <div className="chat-title-row"><button className="icon-button back-to-list" onClick={onBack} aria-label="Back to inbox"><Icon name="back" /></button><div className="chat-title"><h2 ref={heading} tabIndex={-1}>{ticket.customer.name}</h2><p>{ticket.subject}</p></div><button className="secondary-button details-button" onClick={onDetails} aria-expanded={detailsOpen}><Icon name="user" size={16} /><span>Details</span></button></div>
        <div className="chat-toolbar"><span className="ticket-channel">{ticket.id}<span>·</span>{ticket.channel}</span><label className="ticket-status"><span className="sr-only">Ticket status</span><span className={`dot dot--${ticket.status.toLowerCase().replace(' ', '-')}`} /><select aria-label="Ticket status" value={ticket.status} disabled={saving} onChange={(event) => { void perform({ type: 'status', status: event.target.value as TicketStatus, ...context() }, `Status changed to ${event.target.value}.`) }}>{ticketStatuses.map((status) => <option key={status}>{status}</option>)}</select></label></div>
      </header>
      <div className={`handling-bar ${ticket.handling === 'Needs handover' && ticket.status !== 'Resolved' ? 'handling-bar--waiting' : ''}`}>
        <span><span className="dot" />{ticket.status === 'Resolved' ? 'Conversation resolved · Inactive' : ticket.handling === 'Needs handover' ? 'AI paused · Your help is needed' : ticket.handling === 'You are handling' ? 'You are handling · AI paused' : runs.some((run) => run.status === 'pending' || run.status === 'running') ? 'AI handling / Agent turn running' : 'AI handling / Waiting for customer'}</span>
        {ticket.handling !== 'You are handling' && ticket.status !== 'Resolved' && <button className="takeover-button" disabled={saving} onClick={() => { void perform({ type: 'takeover', ...context() }, 'Takeover saved. AI replies are paused.') }}><Icon name="hand" size={15} />Take over from AI</button>}
        {ticket.handling === 'You are handling' && ticket.status !== 'Resolved' && <button className="takeover-button resume-button" disabled={saving} onClick={() => { void perform({ type: 'resume', ...context() }, 'AI handling saved. Waiting for the next customer message; no reply generated.') }}><Icon name="activity" size={15} />Resume AI</button>}
      </div>
      <div className="message-thread" ref={thread} onScroll={onScroll} tabIndex={0} aria-label="Message history">
        <div className="thread-date"><span>Stored demo conversation · Times shown locally</span></div>
        {ticket.messages.map((message) => <MessageBubble key={message.id} message={message} ticket={ticket} />)}
        <details className="activity-panel"><summary><Icon name="activity" size={16} />View activity<span>{ticket.activity.length} events</span></summary><div className="activity-content"><p className="muted">Recorded actions from SQLite. Original sample events remain examples. New agent turns appear in Agent Activity.</p>{ticket.activity.map((event) => <details className="activity-event" key={event.id}><summary>{event.title}<time>{event.time}</time></summary>{event.input && <div><span className="section-label">Sample input</span><pre>{JSON.stringify(event.input, null, 2)}</pre></div>}<span className="section-label">Recorded result</span><p>{event.result}</p></details>)}</div></details>
        <AgentRunStatus ticket={ticket} runs={runs} aiStatus={aiStatus} onAction={onAction} saving={saving} />
      </div>
      {unread > 0 && <button className="new-message-button" onClick={jump}>{unread} new message{unread === 1 ? '' : 's'} - jump to latest</button>}
      <form className={`composer ${isNote ? 'composer--note' : ''}`} onSubmit={(event) => { event.preventDefault(); submit() }}>
        <fieldset disabled={saving}><div className="composer-modes" role="group" aria-label="Message type"><button type="button" aria-pressed={!isNote} onClick={() => { onDrafts({ ...drafts, mode: 'reply' }); setFeedback('') }}>Public reply</button><button type="button" aria-pressed={isNote} onClick={() => { onDrafts({ ...drafts, mode: 'note' }); setFeedback('') }}><Icon name="lock" size={14} />Internal note</button></div>
        <label className="sr-only" htmlFor="reply-text">{isNote ? 'Internal note' : 'Public reply'}</label>
        <textarea id="reply-text" rows={2} maxLength={5000} value={drafts[drafts.mode]} disabled={disabled} onChange={(event) => onDrafts({ ...drafts, [drafts.mode]: event.target.value })} placeholder={disabled ? ticket.status === 'Resolved' ? 'Reopen this ticket to write a reply.' : 'Take over from AI to write a reply.' : isNote ? 'Add context for your team…' : `Reply to ${ticket.customer.name.split(' ')[0]}…`} aria-describedby={isNote ? 'composer-help' : undefined} />
        <div className="composer-footer">{isNote && <span id="composer-help">Team note · Local demo only</span>}<button type="submit" className="primary-button" disabled={disabled || !drafts[drafts.mode].trim()}>{isNote ? 'Add note' : 'Send demo reply'}<Icon name={isNote ? 'lock' : 'send'} size={16} /></button></div>
        <p className="action-feedback" role="status">{saving ? 'Saving to SQLite...' : feedback || 'Saved messages persist. Unsent drafts stay in this tab.'}</p></fieldset>{actionError && <div className="action-error" role="alert"><p>{actionError}</p>{failed && <button type="button" className="text-button" disabled={saving} onClick={() => { void perform(failed.action, failed.success, failed.clearMode) }}>Retry action</button>}</div>}
      </form>
    </section>
  )
}
