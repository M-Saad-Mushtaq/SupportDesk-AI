import { useCallback, useEffect, useRef, useState } from 'react'
import { customerApi } from '../customerApi'
import type { CustomerHome, DemoIdentity, PublicConversation } from '../customerApi'
import { useVisiblePolling } from '../hooks/useVisiblePolling'
import { useChatScroll } from '../hooks/useChatScroll'
import '../customer.css'

const failure = (error: unknown) => error instanceof Error ? error.message : 'Could not load the demo. Check the backend and try again.'
function remember(customer: string, conversation?: string) {
  const url = new URL(window.location.href)
  url.searchParams.set('customer', customer)
  if (conversation) url.searchParams.set('conversation', conversation)
  else url.searchParams.delete('conversation')
  window.history.replaceState(null, '', url)
}
function stored(key: string) { try { return sessionStorage.getItem(key) ?? '' } catch { return '' } }
function store(key: string, value: string) { try { if (value) sessionStorage.setItem(key, value); else sessionStorage.removeItem(key) } catch { /* Tab state still works when storage is disabled. */ } }

export function CustomerDemo() {
  const [identities, setIdentities] = useState<DemoIdentity[] | null>(null)
  const [selected, setSelected] = useState(() => new URLSearchParams(window.location.search).get('customer') ?? '')
  const [error, setError] = useState('')
  const load = useCallback(async (signal: AbortSignal) => {
    try { const value = await customerApi.identities(signal); if (!signal.aborted) { setIdentities(value); setError('') } }
    catch (error) { if (!signal.aborted) setError(failure(error)) }
  }, [])
  useVisiblePolling(load, identities === null, 10000)
  return <main className="customer-demo">
    <header className="store-header"><a className="store-brand" href="/demo/customer"><img src="/supportdesk-logo.svg" alt="" width="36" height="36" /><span>SupportDesk <strong>Demo Store</strong></span></a><span className="store-demo-label">Demo store &mdash; fictional customer data</span><a className="store-staff-link" href="/" target="_blank" rel="noreferrer">Open staff Inbox &#8599;</a></header>
    <div className="customer-workspace"><aside className="customer-launcher"><span className="store-eyebrow">TRY BOTH SIDES OF SUPPORT</span><h1>A little help,<br />right here.</h1><p>Ask a question, check an order, or talk to our demo support team.</p><label htmlFor="demo-customer">Choose a fictional customer</label><select id="demo-customer" value={selected} onChange={(event) => { setSelected(event.target.value); remember(event.target.value) }}><option value="">Select a demo customer</option>{identities?.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select><p className="demo-identity-notice">This selector impersonates fictional customers for the demo. It is not a sign-in or real authentication.</p>{identities?.length === 0 && <p>No fictional customers are available. Ask the demo owner to check the existing database.</p>}{identities === null && !error && <p role="status">Loading demo customers...</p>}{error && <div className="customer-error" role="alert">{error}<button onClick={() => { void load(new AbortController().signal) }}>Retry loading</button></div>}<div className="store-local-note"><strong>One workspace, two perspectives</strong><p>Keep the staff Inbox in a second tab to take over, reply, and resume AI. Everything stays in this local support workspace; no messages are delivered externally.</p></div></aside>
      {selected && identities?.some((identity) => identity.id === selected) ? <CustomerWorkspace key={selected} customer={selected} /> : <section className="customer-welcome"><img src="/supportdesk-logo.svg" alt="" width="64" height="64" /><h2>Welcome to your support chat</h2><p>Choose a fictional customer to open their conversation. Your saved history will be here when you return.</p><span>Public messages only</span></section>}
    </div>
  </main>
}

function CustomerWorkspace({ customer }: { customer: string }) {
  const [home, setHome] = useState<CustomerHome | null>(null)
  const [ticket, setTicket] = useState('')
  const [order, setOrder] = useState('')
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)
  const busy = useRef(false)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const load = useCallback(async (signal: AbortSignal) => {
    try {
      const value = await customerApi.home(customer, signal)
      if (signal.aborted) return
      setHome(value); setOrder(value.order_ids[0] ?? ''); setError('')
      const remembered = new URLSearchParams(window.location.search).get('conversation')
      const id = value.conversations.find((item) => item.id === remembered)?.id ?? value.conversations[0]?.id ?? ''
      setTicket(id)
      remember(customer, id)
    } catch (error) { if (!signal.aborted) setError(failure(error)) }
  }, [customer])
  useVisiblePolling(load, home === null, 10000)
  async function start() {
    if (busy.current) return
    busy.current = true; setStarting(true); setError('')
    try {
      const conversation = await customerApi.start(customer, order)
      if (!mounted.current) return
      setHome((current) => current ? { ...current, conversations: [...current.conversations.filter((item) => item.id !== conversation.id), conversation] } : current)
      setTicket(conversation.id); remember(customer, conversation.id)
    } catch (error) { if (mounted.current) setError(failure(error)) }
    finally { busy.current = false; if (mounted.current) setStarting(false) }
  }
  if (!home) return <section className="customer-welcome" role="status"><h2>{error ? 'Chat unavailable' : 'Opening your conversations...'}</h2>{error && <div className="customer-error">{error}<button onClick={() => { void load(new AbortController().signal) }}>Retry loading</button></div>}</section>
  return <section className="customer-chat-area">
    <details className="customer-conversations"><summary>Conversations for {home.customer.name}</summary><div>{!!home.conversations.length && <label>Continue a conversation<select aria-label="Demo conversation" value={ticket} onChange={(event) => { setTicket(event.target.value); remember(customer, event.target.value) }}>{home.conversations.map((item) => <option value={item.id} key={item.id}>{item.id} / {item.subject}</option>)}</select></label>}<label>Stored demo order<select aria-label="Demo order" value={order} onChange={(event) => setOrder(event.target.value)}>{home.order_ids.map((id) => <option key={id}>{id}</option>)}</select></label><button onClick={() => { void start() }} disabled={starting || !order}>{starting ? 'Opening...' : 'Start or continue order conversation'}</button><p>Existing conversations keep their history and handling state. Only staff can reopen a resolved conversation.</p></div></details>
    {error && <p className="customer-error" role="alert">{error}</p>}
    {ticket ? <CustomerChat key={ticket} customer={customer} conversation={ticket} /> : <div className="customer-welcome"><h2>Start a conversation</h2><p>{order ? 'Choose Start or continue above to open support for your stored demo order.' : 'This demo customer has no stored orders. Ask the demo owner to check their records.'}</p></div>}
  </section>
}

function CustomerChat({ customer, conversation }: { customer: string; conversation: string }) {
  const [data, setData] = useState<PublicConversation | null>(null)
  const draftKey = `supportdesk.customer.draft.${customer}.${conversation}`
  const intentKey = `supportdesk.customer.intent.${customer}.${conversation}`
  const [draft, setDraft] = useState(() => stored(draftKey))
  const [loadError, setLoadError] = useState('')
  const [actionError, setActionError] = useState('')
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const writing = useRef(false)
  const version = useRef(0)
  const { thread, onScroll, unread, jump } = useChatScroll(data?.messages.length ?? 0)
  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (writing.current) return
    const attempt = ++version.current
    try { const value = await customerApi.conversation(customer, conversation, signal); if (!signal?.aborted && attempt === version.current) { setData(value); setLoadError('') } }
    catch (error) { if (!signal?.aborted && attempt === version.current) setLoadError(failure(error)) }
  }, [customer, conversation])
  const poll = useCallback((signal: AbortSignal) => refresh(signal), [refresh])
  const active = !!data?.run && ['pending', 'running'].includes(data.run.status)
  useVisiblePolling(poll, true, loadError ? 10000 : active ? 1500 : data?.status === 'resolved' ? 10000 : 3000)
  function updateDraft(value: string) { setDraft(value); store(draftKey, value) }
  async function send(retry = false) {
    if (writing.current || !data || (!retry && !draft.trim())) return
    writing.current = true; version.current++; setSaving(true); setActionError(''); setNotice('')
    const text = draft.trim()
    try {
      let value: PublicConversation
      if (retry && data.run) value = await customerApi.retry(customer, conversation, data.run.id)
      else {
        let intent: { id: string; text: string } | null = null
        try { intent = JSON.parse(stored(intentKey)) as { id: string; text: string } | null } catch { /* No saved uncertain request. */ }
        const id = intent?.text === text ? intent.id : crypto.randomUUID()
        store(intentKey, JSON.stringify({ id, text }))
        value = await customerApi.send(customer, conversation, text, id)
        store(intentKey, ''); updateDraft('')
      }
      setData(value); setLoadError(''); setNotice(retry ? 'Retry accepted. Waiting for the result.' : 'Message saved to this demo conversation.')
    } catch (error) { setActionError(failure(error)) }
    finally { writing.current = false; setSaving(false) }
  }
  if (!data) return <section className="customer-welcome"><h2>{loadError ? 'Could not open this chat' : 'Loading your chat...'}</h2>{loadError && <div className="customer-error" role="alert">{loadError}<button onClick={() => { void refresh() }}>Retry loading</button></div>}</section>
  const resolved = data.status === 'resolved'
  const blocked = resolved || (active && data.handling_mode === 'ai')
  const handling = resolved ? 'Resolved - ask staff to reopen' : data.handling_mode === 'human' ? 'A support specialist is helping you' : data.handling_mode === 'awaiting_human' ? 'Waiting for a support specialist' : active ? 'AI is preparing a reply...' : 'AI assistance / ready for your message'
  return <div className="customer-chat">
    <header className="customer-chat-heading"><img src="/supportdesk-logo.svg" alt="" width="38" height="38" /><div><h2>Store support</h2><p>{data.customer.name} / {data.id}</p></div><a href={`/?conversation=${encodeURIComponent(data.id)}`} target="_blank" rel="noreferrer">Staff view &#8599;</a></header>
    <div className="customer-handling" role="status"><span className="dot" />{handling}</div>
    <details className="demo-scenarios"><summary>Try a demo scenario</summary><div><p>Choose a prompt to put in the composer. Nothing is sent until you press Send.</p><button disabled={saving || !!draft.trim()} onClick={() => updateDraft('What is your returns policy?')}>Policy question</button><button disabled={saving || !!draft.trim()} onClick={() => updateDraft(`What is the stored status of my order ${data.order_id}?`)}>Order-status question</button><button disabled={saving || !!draft.trim()} onClick={() => updateDraft('Please connect me with a person.')}>Request human support</button><small>Policy answers use documents imported by the demo owner. Order information is fictional, not live tracking. Clear your draft to choose another example.</small></div></details>
    {loadError && <div className="customer-error" role="alert">{loadError} Showing saved data from the last successful check.<button onClick={() => { void refresh() }}>Retry loading</button></div>}
    <div className="customer-messages" ref={thread} onScroll={onScroll} tabIndex={0} aria-label="Public conversation history">
      <p className="customer-history-label">Your public conversation / Times shown locally</p>
      {!data.messages.length && <div className="customer-empty"><h3>How can we help?</h3><p>Send your first question or choose a demo scenario above.</p></div>}
      {data.messages.map((message) => <article key={message.id} className={`customer-message customer-message--${message.kind}`} data-message-id={message.id}><div className="customer-message-meta"><strong>{message.kind === 'customer' ? 'You' : message.kind === 'reply' ? 'Support specialist' : 'AI assistant'}</strong>{message.kind === 'ai' && <span>{message.origin === 'mock' ? 'Mock simulation' : message.origin === 'sample' ? 'Seeded example' : 'AI reply'}</span>}<time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div><p>{message.text}</p></article>)}
    </div>
    {unread > 0 && <button className="new-message-button" onClick={jump}>{unread} new message{unread === 1 ? '' : 's'} - jump to latest</button>}
    {data.run?.message && <div className="customer-run-notice" role="status"><p>{data.run.message}</p>{data.run.retry_at && <p>Retry available no earlier than {new Date(data.run.retry_at).toLocaleString()}.</p>}{['failed', 'interrupted'].includes(data.run.status) && <button disabled={saving || !data.run.retry_allowed} onClick={() => { void send(true) }}>Retry AI reply</button>}</div>}
    <form className="customer-composer" onSubmit={(event) => { event.preventDefault(); if (!blocked) void send() }}><label htmlFor="customer-message">Your message</label><div><textarea id="customer-message" rows={2} maxLength={3000} value={draft} onChange={(event) => updateDraft(event.target.value)} disabled={saving || resolved} placeholder={resolved ? 'Ask staff to reopen this conversation.' : 'Write your message...'} /><button type="submit" disabled={saving || blocked || !draft.trim()}>{saving ? 'Saving...' : 'Send message'}</button></div><small>Local portfolio demo. Use fictional information only.</small><p className="customer-send-status" role="status">{notice || (active && data.handling_mode === 'ai' ? 'Wait for this reply before sending another message.' : 'Your saved messages remain after refresh.')}</p>{actionError && <p className="customer-error" role="alert">{actionError} Your draft is kept. Try the same action again.</p>}</form>
  </div>
}
