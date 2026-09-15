import type { OverviewMetrics } from '../api'
import type { Ticket } from '../data/inbox'
import { handlingLabel } from '../data/workspace'
import { Icon } from '../components/Icon'
import { PageHeading } from '../components/PageHeading'

export function Overview({ tickets, metrics, openTicket }: { tickets: Ticket[]; metrics: OverviewMetrics; openTicket: (id: string) => void }) {
  const stats = { ...metrics, handovers: tickets.filter((ticket) => metrics.handover_ids.includes(ticket.id)) }
  const cards = [
    { label: 'Active conversations', value: stats.active, hint: 'Open and in-progress tickets', icon: 'inbox' },
    { label: 'AI handling', value: stats.ai, hint: 'Active tickets assigned to AI', icon: 'activity' },
    { label: 'Needs your attention', value: metrics.awaiting_human, hint: 'Awaiting a human handover', icon: 'hand' },
    { label: 'Resolved', value: stats.resolved, hint: `Of ${tickets.length} stored conversations`, icon: 'check' },
  ] as const
  return <main className="content-page overview-page">
    <PageHeading title="Overview" description="A clear view of your conversations and the customers who need help." action={<span className="page-period">Current database snapshot</span>} />
    <div className="metric-grid">{cards.map((metric) => <section className="panel metric-card" key={metric.label}><div><h2>{metric.label}</h2><Icon name={metric.icon} /></div><strong className="metric-value">{metric.value}</strong><p>{metric.hint}</p></section>)}</div>
    <div className="overview-columns">
      <section className="panel volume-panel"><div className="panel-heading"><div><h2>Conversation volume</h2><p>Historical analytics: not implemented</p></div></div><div className="page-empty"><Icon name="activity" size={32} /><h3>Historical volume is not available</h3><p>The cards above reflect stored conversations. Imported sample scenarios do not provide a reliable history for trend reporting.</p></div></section>
      <section className="panel handover-panel"><div className="panel-heading"><div><h2>Handovers to review</h2><p>These customers are waiting for your help.</p></div><span className="badge badge--amber">{stats.handovers.length}</span></div>
        {stats.handovers.length ? stats.handovers.map((ticket) => <article className="handover-card" key={ticket.id}><div><strong>{ticket.customer.name}</strong><span className="badge badge--amber">{ticket.priority}</span></div><p>{ticket.subject}</p><span className="muted">{ticket.id} · {ticket.order.id}</span><button className="primary-button" onClick={() => openTicket(ticket.id)}>Review conversation<Icon name="chevron" size={15} /></button></article>) : <div className="page-empty"><Icon name="check" size={25} /><h3>No handovers waiting</h3><p>All active conversations have an owner.</p></div>}
      </section>
    </div>
    <section className="panel recent-panel"><div className="panel-heading"><div><h2>Recent conversations</h2><p>Open a conversation to reply or review its details.</p></div><span className="badge badge--neutral">{tickets.length} tickets</span></div>
      <div className="recent-list">{[...tickets].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)).map((ticket) => <button className="recent-row" key={ticket.id} onClick={() => openTicket(ticket.id)}><span className={`avatar avatar--${ticket.customer.initials.toLowerCase()}`}>{ticket.customer.initials}</span><span className="recent-person"><strong>{ticket.customer.name}</strong><span>{ticket.id} · {ticket.order.id}</span></span><span className="recent-subject">{ticket.subject}<small>{handlingLabel(ticket)}</small></span><span className={`badge ${ticket.status === 'Resolved' ? 'badge--teal' : 'badge--neutral'}`}>{ticket.status}</span><time>{ticket.updated}</time><Icon name="chevron" size={16} /></button>)}</div>{tickets.length === 0 && <div className="page-empty"><p>No stored conversations yet. Seed the sample scenarios to explore this demo.</p></div>}
    </section>
  </main>
}
