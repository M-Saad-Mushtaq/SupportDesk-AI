import { useState } from 'react'
import type { ReactNode } from 'react'
import { Icon } from './Icon'
import { Drawer } from './Drawer'
import { providerLabel } from '../agentApi'
import type { AIStatus } from '../agentApi'
import { BackendHealth } from './BackendHealth'

const pages = [
  { name: 'Overview', icon: 'grid' },
  { name: 'Support Inbox', icon: 'inbox' },
  { name: 'Knowledge Base', icon: 'book' },
  { name: 'Agent Activity', icon: 'activity' },
  { name: 'Settings', icon: 'settings' },
] as const
export type Page = typeof pages[number]['name']

function Brand() {
  return <div className="brand"><img src="/supportdesk-logo.svg" alt="" width="34" height="34" /><span>SupportDesk <strong>AI</strong></span></div>
}

function Navigation({ page, onNavigate, count }: { page: Page; onNavigate: (page: Page) => void; count: number }) {
  return <nav aria-label="Main navigation"><p className="nav-label">Workspace</p>{pages.map((item) => (
    <button key={item.name} className={`nav-item ${page === item.name ? 'is-active' : ''}`} aria-current={page === item.name ? 'page' : undefined} onClick={() => onNavigate(item.name)}>
      <Icon name={item.icon} /><span>{item.name}</span>{item.name === 'Support Inbox' && <span className="nav-count">{count}</span>}
    </button>
  ))}</nav>
}

export function AppShell({ aiStatus, page, onNavigate, count, children, onRefresh, refreshing }: { aiStatus: AIStatus | null; page: Page; onNavigate: (page: Page) => void; count: number; children: ReactNode; onRefresh: () => void; refreshing: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <Navigation page={page} onNavigate={onNavigate} count={count} />
        <div className="sidebar-footer"><div className="demo-agent"><img src="/supportdesk-logo.svg" alt="" width="26" height="26" /><div>AI assistant<span>{providerLabel(aiStatus)}</span></div></div><div className="profile"><span className="avatar avatar--agent">AM</span><div>Alex Morgan<span>Support specialist · Demo</span></div></div></div>
      </aside>
      <div className="workspace">
        <header className="app-header">
          <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMenuOpen(true)}><Icon name="menu" /></button>
          <div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={14} /><strong>{page}</strong></div>
          <span className="demo-label"><span className="dot" />Demo — sample data</span>
          <BackendHealth />
          <button className="icon-button" aria-label="Refresh stored workspace data" title="Refresh stored workspace data" disabled={refreshing} onClick={onRefresh}><Icon name="activity" size={17} /></button>
        </header>
        {children}
      </div>
      <Drawer open={menuOpen} onClose={() => setMenuOpen(false)} title="Navigation" side="left">
        <Brand /><Navigation page={page} onNavigate={(next) => { onNavigate(next); setMenuOpen(false) }} count={count} />
      </Drawer>
    </div>
  )
}
