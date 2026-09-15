import { useCallback, useEffect, useRef, useState } from 'react'
import { AppShell } from './components/AppShell'
import type { Page } from './components/AppShell'
import { Inbox } from './components/Inbox'
import type { InboxView } from './components/Inbox'
import { Overview } from './pages/Overview'
import { KnowledgeBase } from './pages/KnowledgeBase'
import { AgentActivity } from './pages/AgentActivity'
import { Settings } from './pages/Settings'
import type { Ticket, TicketAction } from './data/inbox'
import { api } from './api'
import type { OverviewMetrics } from './api'
import './App.css'
import './pages.css'

function App() {
  const [page, setPage] = useState<Page>('Support Inbox')
  const [tickets, setTickets] = useState<Ticket[] | null>(null)
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const writing = useRef(false)
  const loadVersion = useRef(0)
  const [inboxView, setInboxView] = useState<InboxView>({ selectedId: '', query: '', filter: 'All', mobileConversation: false })

  const refresh = useCallback(async () => {
    const version = ++loadVersion.current
    try {
      const [stored, overview] = await Promise.all([api.conversations(), api.overview()])
      if (version !== loadVersion.current) return
      setTickets(stored)
      setMetrics(overview)
      setError('')
    } catch (error) {
      if (version === loadVersion.current) setError(error instanceof Error ? error.message : 'Could not load stored data.')
    } finally {
      if (version === loadVersion.current) setLoading(false)
    }
  }, [])

  const invalidateLoad = useCallback(() => { loadVersion.current++ }, [])
  // The read callback updates state only after awaited API I/O.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void refresh(); return invalidateLoad }, [refresh, invalidateLoad])

  function openTicket(id: string) {
    setInboxView({ selectedId: id, query: '', filter: 'All', mobileConversation: true })
    setPage('Support Inbox')
    requestAnimationFrame(() => document.querySelector<HTMLElement>('.chat-title h2')?.focus({ preventScroll: true }))
  }

  async function handleAction(id: string, action: TicketAction) {
    if (writing.current) throw new Error('Another action is being saved. Please wait, then try again.')
    writing.current = true
    setSaving(true)
    loadVersion.current++
    try {
      const saved = await api.action(id, action)
      setTickets((current) => current?.map((ticket) => ticket.id === id ? saved : ticket) ?? [saved])
      // Replays return the original response; refresh to obtain the latest
      // conversation and Overview rather than leaving a stale replay on screen.
      await refresh()
    } finally {
      writing.current = false
      setSaving(false)
    }
  }

  const storedPage = page === 'Support Inbox' || page === 'Overview' || page === 'Agent Activity'
  return (
    <AppShell page={page} onNavigate={setPage} count={tickets?.length ?? 0} onRefresh={() => { setLoading(true); void refresh() }} refreshing={loading || saving}>
      {error && storedPage && <div className="storage-error" role="alert"><span>{error} {tickets && 'Showing the last loaded data.'}</span><button className="secondary-button" disabled={loading || saving} onClick={() => { setLoading(true); void refresh() }}>Retry loading</button></div>}
      {tickets === null && storedPage && <main className="load-state" role="status"><h1>{loading ? 'Loading your workspace…' : 'Workspace unavailable'}</h1><p>{loading ? 'Reading conversations from the local database.' : 'Check that the backend is running and migrations have been applied, then retry.'}</p></main>}
      {tickets !== null && <>
        <div className="page-container" hidden={page !== 'Support Inbox'}><Inbox tickets={tickets} onAction={handleAction} saving={saving || loading} view={inboxView} onViewChange={setInboxView} /></div>
        <div className="page-container" hidden={page !== 'Overview'}>{metrics && <Overview tickets={tickets} metrics={metrics} openTicket={openTicket} />}</div>
        <div className="page-container" hidden={page !== 'Agent Activity'}><AgentActivity tickets={tickets} openTicket={openTicket} /></div>
      </>}
      <div className="page-container" hidden={page !== 'Knowledge Base'}><KnowledgeBase /></div>
      <div className="page-container" hidden={page !== 'Settings'}><Settings /></div>
    </AppShell>
  )
}

export default App
