import { useState } from 'react'
import type { Ticket } from '../data/inbox'
import type { AgentRun, AIStatus } from '../agentApi'
import { providerLabel } from '../agentApi'
import { PageHeading } from '../components/PageHeading'
import { Icon } from '../components/Icon'
import { ConversationHistory } from './ConversationHistory'

export function AgentActivity({ tickets, runs, aiStatus, openTicket }: { tickets: Ticket[]; runs: AgentRun[]; aiStatus: AIStatus | null; openTicket: (id: string) => void }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [selectedId, setSelectedId] = useState('')
  const [mobileTimeline, setMobileTimeline] = useState(false)
  const visible = runs.filter((run) => (filter === 'all' || run.status === filter) && `${run.id} ${run.conversation_id} ${run.provider} ${run.model} ${tickets.find((ticket) => ticket.id === run.conversation_id)?.customer.name}`.toLowerCase().includes(query.toLowerCase().trim()))
  const selected = visible.find((run) => run.id === selectedId) ?? visible[0]
  const ticket = tickets.find((ticket) => ticket.id === selected?.conversation_id)
  const sources = ticket?.messages.find((message) => message.id === selected?.response_message_id)?.sources ?? []
  return <main className="content-page activity-page">
    <PageHeading title="Agent Activity" description="Actual agent turns and observable tool results. Mock runs are labeled; seeded examples are kept separately below." action={<span className="page-period">{providerLabel(aiStatus)}</span>} />
    {aiStatus?.error && <p className="action-error" role="alert">{aiStatus.error}</p>}
    <div className="page-filters"><div className="search-field"><Icon name="search" size={17} /><input type="search" aria-label="Search agent runs" placeholder="Search customer, ticket, provider, or run" value={query} onChange={(event) => setQuery(event.target.value)} /></div><select aria-label="Filter agent runs" value={filter} onChange={(event) => setFilter(event.target.value)}>{['all', 'pending', 'running', 'completed', 'failed', 'cancelled', 'interrupted'].map((value) => <option key={value} value={value}>{value === 'all' ? 'All statuses' : value}</option>)}</select><span className="muted">{visible.length} runs / Latest 200 loaded</span></div>
    {!runs.length && <div className="panel page-empty"><h2>No agent runs yet</h2><p>Open an active conversation in AI handling mode, then send a test customer message. Existing sample replies do not count as real runs.</p></div>}
    {!!runs.length && <div className={`activity-columns ${mobileTimeline ? 'show-timeline' : ''}`}>
      <section className="panel run-list"><div className="panel-heading"><h2>Agent runs</h2></div>{visible.map((run) => <button key={run.id} className={`run-row ${run.id === selected?.id ? 'is-selected' : ''}`} aria-pressed={run.id === selected?.id} onClick={() => { setSelectedId(run.id); setMobileTimeline(true) }}><div><strong>{run.conversation_id}</strong><span>{run.status}</span></div><h3>{tickets.find((ticket) => ticket.id === run.conversation_id)?.customer.name ?? 'Customer'}</h3><p>{run.model}</p><span className="badge badge--neutral">{run.provider === 'mock' ? 'Mock simulation' : run.provider} / {new Date(run.created_at).toLocaleTimeString()}</span></button>)}{!visible.length && <p className="page-empty">No matching runs. Try another search or status.</p>}</section>
      {selected && <section className="panel run-detail"><button className="text-button preview-back" onClick={() => setMobileTimeline(false)}><Icon name="back" size={16} />Back to runs</button><div className="panel-heading"><div><h2>{ticket?.customer.name ?? selected.conversation_id}</h2><p>{selected.status} / Attempt {selected.attempt}</p></div><button className="secondary-button" onClick={() => openTicket(selected.conversation_id)}>Open conversation</button></div><div className="run-body">
        <div className="run-summary"><span className="badge badge--teal">{selected.provider === 'mock' ? 'Mock simulation' : selected.provider}</span><span>{selected.model}</span></div>
        <dl className="run-facts"><div><dt>Duration</dt><dd>{selected.duration_ms === null ? 'Pending' : `${selected.duration_ms.toLocaleString()} ms`}</dd></div><div><dt>Model requests</dt><dd>{selected.request_count}</dd></div><div><dt>Tool calls</dt><dd>{selected.tool_count}</dd></div><div><dt>Tokens (provider reported)</dt><dd>{selected.usage.total_tokens === undefined ? 'Not reported' : selected.usage.total_tokens.toLocaleString()}</dd></div></dl>
        {Object.keys(selected.usage).length > 0 && <p className="muted">Input: {selected.usage.input_tokens ?? 'Not reported'} / Output: {selected.usage.output_tokens ?? 'Not reported'}. Totals cover reported responses in this attempt.</p>}
        {selected.error && <div className="action-error" role="alert"><p>{selected.error}</p>{selected.retry_at && <p>Retry after {new Date(selected.retry_at).toLocaleString()}</p>}<p>Open the conversation to review handling and retry explicitly.</p></div>}
        <ol className="run-timeline"><li><div className="event-heading"><strong>Customer message saved</strong><time>{new Date(selected.created_at).toLocaleTimeString()}</time></div><p className="muted">Run {selected.id}</p></li>{selected.tools.map((tool) => <li key={tool.id}><div className="event-heading"><strong>{tool.name.replaceAll('_', ' ')}</strong><time>{new Date(tool.created_at).toLocaleTimeString()}</time></div><details className="event-payload"><summary>View tool input and result / Attempt {tool.attempt}</summary><span className="section-label">Validated input</span><pre>{JSON.stringify(tool.arguments, null, 2)}</pre><span className="section-label">Observable result</span><pre>{JSON.stringify(tool.result, null, 2)}</pre></details></li>)}<li><strong>{selected.status}</strong><p>{selected.response_message_id ? 'Reply saved locally. No external delivery.' : 'No agent reply saved for this run.'}</p></li></ol>
        <details className="run-sources"><summary>Source references ({sources.length})</summary>{sources.map((source) => <article className="source-card" key={source.source_id ?? source.title}><strong>{source.title}</strong><span>{source.section}</span><p>{source.quote ?? source.excerpt}</p></article>)}{!sources.length && <p>No cited reply for this run.</p>}</details>
        {!!selected.attempts.length && <details className="event-payload"><summary>Earlier attempts ({selected.attempts.length})</summary><pre>{JSON.stringify(selected.attempts, null, 2)}</pre></details>}
      </div></section>}
    </div>}
    <details className="legacy-history"><summary>Conversation history and seeded examples</summary><ConversationHistory tickets={tickets} openTicket={openTicket} /></details>
  </main>
}
