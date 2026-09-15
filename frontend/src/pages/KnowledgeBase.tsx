import { useEffect, useState } from 'react'
import { initialDocuments, makeSimulatedDocument } from '../data/workspace'
import { Icon } from '../components/Icon'
import { PageHeading } from '../components/PageHeading'

export function KnowledgeBase() {
  const [documents, setDocuments] = useState(initialDocuments)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('All statuses')
  const [selectedId, setSelectedId] = useState(initialDocuments[0].id)
  const [mobilePreview, setMobilePreview] = useState(false)
  const [notice, setNotice] = useState('')
  const processing = documents.some((document) => document.status === 'Processing')
  useEffect(() => {
    if (!processing) return
    const timer = window.setTimeout(() => {
      setDocuments((current) => current.map((document) => document.status === 'Processing' ? { ...document, status: 'Ready' } : document))
      setNotice('Simulated processing complete. The sample document is ready to preview.')
    }, 1600)
    return () => window.clearTimeout(timer)
  }, [processing])
  const visible = documents.filter((document) => (status === 'All statuses' || document.status === status) && `${document.title} ${document.category} ${document.sections.map((section) => section.excerpt).join(' ')}`.toLowerCase().includes(query.trim().toLowerCase()))
  const selected = documents.find((document) => document.id === selectedId) ?? documents[0]

  function upload() {
    const document = makeSimulatedDocument(documents.length - initialDocuments.length + 1)
    setDocuments((current) => [...current, document])
    setSelectedId(document.id)
    setQuery('')
    setStatus('All statuses')
    setMobilePreview(true)
    setNotice('Simulating a PDF upload using a built-in sample. No file is read or sent.')
  }
  return <main className="content-page knowledge-page">
    <PageHeading title="Knowledge Base" description="The policies and guides behind your sample support conversations." action={<button className="primary-button" onClick={upload} disabled={processing}><Icon name="book" size={17} />{processing ? 'Processing sample…' : 'Simulate upload'}</button>} />
    <p className="page-notice" role="status">{notice || 'Demo library · Uploads use a built-in sample. No files leave your device.'}</p>
    <div className="page-filters"><div className="search-field"><Icon name="search" size={17} /><input aria-label="Search documents" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search documents or policy text" /></div><select aria-label="Document status" value={status} onChange={(event) => setStatus(event.target.value)}><option>All statuses</option><option>Ready</option><option>Processing</option></select><span className="muted">{visible.length} of {documents.length} documents</span></div>
    <div className={`knowledge-columns ${mobilePreview ? 'show-preview' : ''}`}>
      <section className="panel document-list" aria-label="Documents"><div className="panel-heading"><h2>Policy documents</h2><span className="count">{documents.length}</span></div>{visible.map((document) => <button key={document.id} className={`document-row ${document.id === selectedId ? 'is-selected' : ''}`} aria-pressed={document.id === selectedId} onClick={() => { setSelectedId(document.id); setMobilePreview(true) }}><span className="document-icon"><Icon name="book" /></span><span><strong>{document.title}</strong><small>{document.format} · {document.category}</small><span className={`badge ${document.status === 'Ready' ? 'badge--teal' : 'badge--amber'}`}>{document.status}</span></span><Icon name="chevron" size={16} /></button>)}{!visible.length && <div className="page-empty"><h3>No matching documents</h3><p>Try another search or processing status.</p><button className="text-button" onClick={() => { setQuery(''); setStatus('All statuses') }}>Clear filters</button></div>}</section>
      <section className="panel document-preview"><button className="text-button preview-back" onClick={() => setMobilePreview(false)}><Icon name="back" size={16} />Back to documents</button><div className="panel-heading"><h2>Document preview</h2><span className="badge badge--neutral">Sample content</span></div><div className="document-body"><span className="section-label">{selected.category} · {selected.format}</span><h2>{selected.title}</h2><p className="muted">Added {selected.added}</p>{selected.status === 'Processing' ? <div className="processing-message" role="status">Processing the sample document…<p>No extraction or indexing service is running.</p></div> : selected.sections.map((section) => <article key={section.section} className="policy-section"><h3>{section.section}</h3><p>{section.excerpt}</p></article>)}<details className="advanced-section"><summary>Advanced</summary><dl><div><dt>Document ID</dt><dd>{selected.id}</dd></div><div><dt>Sections</dt><dd>{selected.sections.length}</dd></div><div><dt>Storage</dt><dd>In-memory demo fixture</dd></div></dl><p>Search matches local text. No embeddings, vector database, document parser, or AI retrieval service is connected. Simulated uploads reset on refresh.</p></details></div></section>
    </div>
  </main>
}
