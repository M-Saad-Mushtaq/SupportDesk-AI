import { useState } from 'react'
import type { Ticket } from '../data/inbox'
import { getTicketSources, handlingLabel } from '../data/workspace'
import { PageHeading } from '../components/PageHeading'
import { Icon } from '../components/Icon'

export function ConversationHistory({ tickets, openTicket }: { tickets: Ticket[]; openTicket: (id: string) => void }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('All histories')
  const [selectedId, setSelectedId] = useState(tickets[0]?.id ?? '')
  const [mobileTimeline, setMobileTimeline] = useState(false)
  const visible = tickets.filter((ticket) => (filter === 'All histories' || handlingLabel(ticket) === filter) && `${ticket.id} ${ticket.customer.name} ${ticket.order.id} ${ticket.subject}`.toLowerCase().includes(query.trim().toLowerCase()))
  const selected = tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0]
  const sources = selected ? getTicketSources(selected) : []
  if (!selected) return <main className="content-page"><PageHeading title="Conversation history" description="No stored conversation activity yet. Seed the sample scenarios to get started." /></main>
  return <main className="content-page activity-page">
    <PageHeading title="Conversation history" description="Review recorded actions, source references, and stored activity and sample tool results." action={<span className="page-period">{tickets.reduce((sum, ticket) => sum + ticket.activity.length, 0)} recorded events</span>} />
    <div className="page-filters"><div className="search-field"><Icon name="search" size={17} /><input type="search" aria-label="Search activity" placeholder="Search customer, ticket, or order" value={query} onChange={(event) => setQuery(event.target.value)} /></div><select aria-label="Filter runs" value={filter} onChange={(event) => setFilter(event.target.value)}>{['All histories', 'AI handling', 'Human handling', 'Awaiting human attention', 'Inactive · Resolved'].map((item) => <option key={item}>{item}</option>)}</select><span className="muted">{visible.length} of {tickets.length} histories</span></div>
    <div className={`activity-columns ${mobileTimeline ? 'show-timeline' : ''}`}>
      <section className="panel run-list"><div className="panel-heading"><h2>Conversation histories</h2><span className="badge badge--neutral">Includes seeded examples</span></div>{visible.map((ticket) => <button key={ticket.id} className={`run-row ${ticket.id === selectedId ? 'is-selected' : ''}`} aria-pressed={ticket.id === selectedId} onClick={() => { setSelectedId(ticket.id); setMobileTimeline(true) }}><div><strong>{ticket.id}</strong><span>{ticket.activity.length} events</span></div><h3>{ticket.customer.name}</h3><p>{ticket.subject}</p><span className={`badge ${ticket.handling === 'Needs handover' && ticket.status !== 'Resolved' ? 'badge--amber' : 'badge--neutral'}`}>{handlingLabel(ticket)}</span></button>)}{!visible.length && <div className="page-empty"><h3>No matching histories</h3><p>Try another customer or handling state.</p><button className="text-button" onClick={() => { setQuery(''); setFilter('All histories') }}>Clear filters</button></div>}</section>
      <section className="panel run-detail"><button className="text-button preview-back" onClick={() => setMobileTimeline(false)}><Icon name="back" size={16} />Back to histories</button><div className="panel-heading"><div><h2>{selected.customer.name}</h2><p>{selected.id} · {selected.order.id}</p></div><button className="secondary-button" onClick={() => openTicket(selected.id)}>Open conversation<Icon name="chevron" size={15} /></button></div><div className="run-body"><div className="run-summary"><span className="badge badge--teal">{handlingLabel(selected)}</span><span>{selected.status}</span></div><p className="muted">One conversation history per ticket. Events are stored in recorded order; imported tool calls remain sample data.</p>
        <ol className="run-timeline">{selected.activity.map((event) => <li key={event.id}><div className="event-heading"><strong>{event.title}</strong><time>{event.time}</time></div><details className="event-payload"><summary>View {event.input ? 'tool input and result' : 'recorded result'}</summary>{event.input && <><span className="section-label">Sample input</span><pre>{JSON.stringify(event.input, null, 2)}</pre></>}<span className="section-label">Recorded result</span><p>{event.result}</p></details></li>)}</ol>
        <details className="run-sources"><summary><Icon name="book" size={16} />Source references ({sources.length})</summary>{sources.length ? sources.map((source) => <article key={source.section} className="source-card"><strong>{source.title}</strong><span>{source.section} / {source.source_id ? 'Retrieved document' : 'Sample policy'}</span><p>{source.excerpt}</p></article>) : <p className="muted">No policy sources are recorded for this conversation.</p>}</details>
      </div></section>
    </div>
  </main>
}
