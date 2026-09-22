import { useEffect, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { InboxFilter, Ticket, TicketAction } from '../data/inbox'
import type { AgentRun, AIStatus } from '../agentApi'
import { ConversationList } from './ConversationList'
import { Conversation } from './Conversation'
import type { Drafts } from './Conversation'
import { CustomerDetails } from './CustomerDetails'
import { Drawer } from './Drawer'
import { Icon } from './Icon'

const emptyDraft: Drafts = { reply: '', note: '', mode: 'reply' }
export type InboxView = { selectedId: string; query: string; filter: InboxFilter; mobileConversation: boolean }

export function Inbox({ runs, aiStatus, tickets, onAction, saving, view, onViewChange }: { runs: AgentRun[]; aiStatus: AIStatus | null; tickets: Ticket[]; onAction: (id: string, action: TicketAction) => Promise<void>; saving: boolean; view: InboxView; onViewChange: Dispatch<SetStateAction<InboxView>> }) {
  const { selectedId, query, filter, mobileConversation } = view
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [showDesktopDetails, setShowDesktopDetails] = useState(true)
  const [wide, setWide] = useState(() => window.matchMedia('(min-width: 1500px)').matches)
  const [drafts, setDrafts] = useState<Record<string, Drafts>>({})
  const selected = tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0]

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1500px)')
    const changed = () => { setWide(media.matches); setDrawerOpen(false) }
    media.addEventListener('change', changed)
    return () => media.removeEventListener('change', changed)
  }, [])

  if (!selected) return <main className="load-state"><h1>No conversations yet</h1><p>The database is empty. Run the explicit seed command in README to add the four sample scenarios, then refresh the workspace.</p></main>

  return (
    <main className={`inbox-layout ${mobileConversation ? 'show-conversation' : 'show-list'} ${wide && showDesktopDetails ? 'with-details' : ''}`}>
      <ConversationList tickets={tickets} selectedId={selectedId} query={query} filter={filter} onQuery={(query) => onViewChange((current) => ({ ...current, query }))} onFilter={(filter) => onViewChange((current) => ({ ...current, filter }))} onSelect={(id) => { onViewChange((current) => ({ ...current, selectedId: id, mobileConversation: true })); setDrawerOpen(false); requestAnimationFrame(() => document.querySelector<HTMLElement>('.chat-title h2')?.focus({ preventScroll: true })) }} />
      <Conversation runs={runs.filter((run) => run.conversation_id === selected.id)} aiStatus={aiStatus} key={selected.id} ticket={selected} drafts={drafts[selected.id] ?? emptyDraft} onDrafts={(value) => setDrafts((current) => ({ ...current, [selected.id]: value }))} onAction={(action) => onAction(selected.id, action)} saving={saving} detailsOpen={wide ? showDesktopDetails : drawerOpen} onDetails={() => wide ? setShowDesktopDetails((value) => !value) : setDrawerOpen(true)} onBack={() => { onViewChange({ ...view, mobileConversation: false }); requestAnimationFrame(() => document.getElementById(`ticket-${selected.id}`)?.focus()) }} />
      {wide && showDesktopDetails && <aside className="desktop-details" aria-label="Customer details"><div className="drawer-heading"><h2>Customer details</h2><button className="icon-button" aria-label="Close customer details" onClick={() => setShowDesktopDetails(false)}><Icon name="close" size={18} /></button></div><CustomerDetails ticket={selected} /></aside>}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Customer details"><button className="text-button drawer-back" onClick={() => setDrawerOpen(false)}><Icon name="back" size={16} />Back to conversation</button><CustomerDetails ticket={selected} /></Drawer>
    </main>
  )
}
