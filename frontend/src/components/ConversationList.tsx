import { filterTickets, inboxFilters } from '../data/inbox'
import type { InboxFilter, Ticket } from '../data/inbox'
import { Icon } from './Icon'

export function ConversationList({ tickets, selectedId, query, filter, onQuery, onFilter, onSelect }: {
  tickets: Ticket[]; selectedId: string; query: string; filter: InboxFilter
  onQuery: (value: string) => void; onFilter: (value: InboxFilter) => void; onSelect: (id: string) => void
}) {
  const visible = filterTickets(tickets, query, filter)
  return (
    <section className="conversation-list" aria-labelledby="inbox-heading">
      <div className="list-heading"><div className="heading-line"><h1 id="inbox-heading">Support Inbox</h1><span className="count">{tickets.length}</span></div><p>Your customer conversations</p>
        <div className="search-field"><Icon name="search" size={17} /><input aria-label="Search conversations" type="search" placeholder="Search name, ticket, or order" value={query} onChange={(event) => onQuery(event.target.value)} /></div>
        <label className="filter-field"><span>Show</span><select aria-label="Filter conversations" value={filter} onChange={(event) => onFilter(event.target.value as InboxFilter)}>{inboxFilters.map((item) => <option key={item}>{item}</option>)}</select></label>
      </div>
      <div className="ticket-list">
        {visible.map((ticket) => (
          <button key={ticket.id} id={`ticket-${ticket.id}`} className={`ticket-row ${ticket.id === selectedId ? 'is-selected' : ''}`} aria-pressed={ticket.id === selectedId} onClick={() => onSelect(ticket.id)}>
            <span className="ticket-row-top"><span className={`avatar avatar--${ticket.customer.initials.toLowerCase()}`}>{ticket.customer.initials}</span><span className="ticket-person"><strong>{ticket.customer.name}</strong><span>{ticket.id}</span></span><time>{ticket.updated}</time></span>
            <strong className="ticket-subject">{ticket.subject}</strong>
            <span className="ticket-preview">{ticket.preview}</span>
            <span className="ticket-tags"><span className={`badge ${ticket.status === 'Resolved' ? 'badge--teal' : ticket.handling === 'Needs handover' ? 'badge--amber' : 'badge--neutral'}`}>{ticket.status === 'Resolved' ? 'Resolved' : ticket.handling === 'You are handling' ? 'Assigned to you' : ticket.handling}</span>{(ticket.priority === 'Urgent' || ticket.priority === 'High') && <span className="priority">{ticket.priority}</span>}</span>
          </button>
        ))}
        {visible.length === 0 && <div className="empty-list"><Icon name="search" size={26} /><h2>No conversations found</h2><p>Try another name, order number, or filter.</p><button className="text-button" onClick={() => { onQuery(''); onFilter('All') }}>Clear search and filter</button></div>}
      </div>
      <div className="list-footer" role="status">{visible.length} of {tickets.length} conversations · Sample data</div>
    </section>
  )
}
