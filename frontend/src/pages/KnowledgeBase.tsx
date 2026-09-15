import { useCallback, useEffect, useRef, useState } from 'react'
import { documentApi, documentStatusLabels } from '../documentApi'
import type { DocumentPreview, DocumentStatus, SearchHit, SearchResults, StoredDocument } from '../documentApi'
import { Icon } from '../components/Icon'
import { PageHeading } from '../components/PageHeading'
import { Drawer } from '../components/Drawer'

export function KnowledgeBase() {
  const [documents, setDocuments] = useState<StoredDocument[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<DocumentStatus | ''>('')
  const [selected, setSelected] = useState<DocumentPreview | null>(null)
  const [mobilePreview, setMobilePreview] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')
  const [previewId, setPreviewId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<StoredDocument | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState<SearchResults | null>(null)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const listVersion = useRef(0)
  const previewVersion = useRef(0)
  const searchVersion = useRef(0)
  const uploadLock = useRef(false)
  const deleteLock = useRef(false)

  const load = useCallback(async () => {
    const version = ++listVersion.current
    try {
      const items = await documentApi.list()
      if (version !== listVersion.current) return
      setDocuments(items)
      setError('')
    } catch (error) {
      if (version === listVersion.current) setError(error instanceof Error ? error.message : 'Could not load documents. Retry loading.')
    } finally { if (version === listVersion.current) setLoading(false) }
  }, [])
  const invalidate = useCallback(() => { listVersion.current++; previewVersion.current++; searchVersion.current++ }, [])
  useEffect(() => {
    // Defer initial I/O; ignore responses after unmount or a newer load.
    const timer = window.setTimeout(() => { void load() }, 0)
    return () => { window.clearTimeout(timer); invalidate() }
  }, [load, invalidate])
  const processing = documents.some((document) => document.status === 'processing' || document.status === 'deleting')
  useEffect(() => {
    if (!processing) return
    const timer = window.setInterval(() => { void load() }, 3000)
    return () => window.clearInterval(timer)
  }, [load, processing])

  async function openDocument(id: string, hit?: SearchHit) {
    const version = ++previewVersion.current
    setPreviewId(id)
    setPreviewLoading(true)
    setPreviewError('')
    setSelected(null)
    setMobilePreview(true)
    try {
      const preview = await documentApi.preview(id)
      if (version !== previewVersion.current) return
      setSelected(preview)
      if (hit) requestAnimationFrame(() => {
        const index = preview.segments.findIndex((segment) => hit.page ? segment.page === hit.page : hit.section ? segment.section === hit.section : segment.text.includes(hit.text))
        document.getElementById(`source-segment-${Math.max(0, index)}`)?.scrollIntoView({ block: 'center' })
      })
    } catch (error) {
      if (version === previewVersion.current) setPreviewError(error instanceof Error ? error.message : 'Preview could not load. Retry.')
    } finally { if (version === previewVersion.current) setPreviewLoading(false) }
  }

  async function upload() {
    if (!file || uploadLock.current) return
    if (file.size > 10 * 1024 * 1024) { setError('The file exceeds 10 MB. Split it and choose a smaller file.'); return }
    uploadLock.current = true
    setUploading(true)
    setNotice('')
    setError('')
    try {
      const result = await documentApi.upload(file)
      setDocuments((current) => [result.document, ...current.filter((item) => item.id !== result.document.id)])
      setNotice(result.duplicate ? `Identical content already exists as ${result.document.filename}. Status: ${documentStatusLabels[result.document.status]}.` : result.document.status === 'ready' ? 'Document stored and ready to search. No AI service was called.' : `Document stored. ${documentStatusLabels[result.document.status]}: ${result.document.error ?? 'Refresh to check progress.'}`)
      setFile(null)
      if (input.current) input.current.value = ''
      setQuery(''); setStatus('')
      setResults(null)
      searchVersion.current++
      setSearching(false)
      void openDocument(result.document.id)
      await load()
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Upload failed. Your file selection is kept; retry.')
    } finally { uploadLock.current = false; setUploading(false) }
  }

  async function search() {
    const version = ++searchVersion.current
    setSearching(true); setSearchError(''); setResults(null)
    try {
      const found = await documentApi.search(searchQuery.trim())
      if (version === searchVersion.current) setResults(found)
    } catch (error) {
      if (version === searchVersion.current) setSearchError(error instanceof Error ? error.message : 'Search failed. Retry the search.')
    } finally { if (version === searchVersion.current) setSearching(false) }
  }

  async function remove() {
    if (!confirmDelete || deleteLock.current) return
    deleteLock.current = true
    setDeleting(true); setDeleteError('')
    try {
      await documentApi.remove(confirmDelete.id)
      setDocuments((current) => current.filter((item) => item.id !== confirmDelete.id))
      if (previewId === confirmDelete.id) { previewVersion.current++; setSelected(null); setPreviewId(''); setPreviewLoading(false); setMobilePreview(false) }
      searchVersion.current++
      setResults(null); setSearching(false)
      setNotice(`Deleted ${confirmDelete.filename}, its stored file, and search passages.`)
      setConfirmDelete(null)
      await load()
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : 'Deletion failed. Retry after checking local storage.')
    } finally { deleteLock.current = false; setDeleting(false) }
  }

  const visible = documents.filter((document) => (!status || document.status === status) && document.filename.toLowerCase().includes(query.trim().toLowerCase()))
  const latest = documents.find((document) => document.id === previewId)
  const previewStale = latest && selected && latest.updated_at !== selected.updated_at
  return <main className="content-page knowledge-page">
    <PageHeading title="Knowledge Base" description="Upload local documents, review extracted text, and find relevant passages." action={<button className="secondary-button" disabled={loading} onClick={() => { setLoading(true); void load() }}>Refresh documents</button>} />
    <div className="panel kb-upload"><label htmlFor="document-file">Choose a document<input ref={input} id="document-file" type="file" accept=".pdf,.txt,.md" disabled={uploading} onChange={(event) => { setFile(event.target.files?.[0] ?? null); setNotice(''); setError('') }} /></label><button className="primary-button" disabled={!file || uploading} onClick={() => { void upload() }}><Icon name="book" size={17} />{uploading ? 'Uploading and extracting...' : 'Upload document'}</button><p className="muted">PDF with selectable text, TXT or Markdown. Maximum 10 MB. Stored on this computer; no external services.</p></div>
    <p className="page-notice" role="status">{notice || 'Local document library. Uploaded documents and search passages remain after restart.'}</p>
    {error && <div className="storage-error" role="alert"><span>{error}</span><button className="secondary-button" disabled={loading} onClick={() => { setLoading(true); void load() }}>Retry loading</button></div>}
    <section className="panel kb-search" aria-label="Document search"><div className="panel-heading"><div><h2>Document search</h2><p>Find matching words in extracted text. Results are source excerpts, not AI answers.</p></div></div><form onSubmit={(event) => { event.preventDefault(); void search() }}><div className="search-field"><Icon name="search" size={17} /><input aria-label="Search passages" type="search" value={searchQuery} maxLength={200} onChange={(event) => { setSearchQuery(event.target.value); searchVersion.current++; setResults(null); setSearching(false); setSearchError('') }} placeholder="Search for delivery, refunds, or a policy phrase" /></div><button type="submit" className="primary-button" disabled={searching}>{searching ? 'Searching...' : 'Search documents'}</button></form>
      {searchError && <p className="kb-error" role="alert">{searchError}</p>}{results && <div className="kb-results"><p role="status">{results.message}</p>{results.results.map((hit) => <article className="policy-section" key={hit.id}><button className="text-button" onClick={() => { void openDocument(hit.document_id, hit) }}>{hit.title} - {hit.location}<Icon name="chevron" size={14} /></button><p>{hit.text}</p></article>)}<details className="advanced-section"><summary>Advanced search details</summary><p>{results.mode === 'fts5' ? 'SQLite FTS5 full-text index. Results use keyword relevance.' : 'Keyword fallback: all words must occur as substrings. Results follow passage order.'} Up to 20 results. The first 16 distinct words are combined with AND. No embeddings or confidence scores.</p></details></div>}
    </section>
    <div className="page-filters"><div className="search-field"><Icon name="search" size={17} /><input aria-label="Filter documents" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter by filename" /></div><select aria-label="Document status" value={status} onChange={(event) => setStatus(event.target.value as DocumentStatus | '')}><option value="">All statuses</option>{Object.entries(documentStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><span className="muted">{visible.length} of {documents.length} documents</span></div>
    <div className={`knowledge-columns ${mobilePreview ? 'show-preview' : ''}`}>
      <section className="panel document-list" aria-label="Documents"><div className="panel-heading"><h2>Documents</h2><span className="count">{documents.length}</span></div>{loading && <p className="page-empty" role="status">Loading stored documents...</p>}{visible.map((document) => <button key={document.id} className={`document-row ${document.id === previewId ? 'is-selected' : ''}`} aria-pressed={document.id === previewId} onClick={() => { void openDocument(document.id) }}><span className="document-icon"><Icon name="book" /></span><span><strong>{document.filename}</strong><small>{document.format} - {(document.size / 1024).toFixed(1)} KB - {document.chunk_count} passages</small><span className={`badge ${document.status === 'ready' ? 'badge--teal' : 'badge--amber'}`}>{documentStatusLabels[document.status]}</span></span><Icon name="chevron" size={16} /></button>)}{!loading && !visible.length && <div className="page-empty"><h3>{documents.length ? 'No matching documents' : error ? 'Documents unavailable' : 'Your document library is empty'}</h3><p>{documents.length ? 'Try another filename or status.' : error ? 'Check the backend and retry loading.' : 'Choose a PDF, TXT, or Markdown file above to get started.'}</p>{documents.length > 0 && <button className="text-button" onClick={() => { setQuery(''); setStatus('') }}>Clear filters</button>}</div>}</section>
      <section className="panel document-preview"><button className="text-button preview-back" onClick={() => setMobilePreview(false)}><Icon name="back" size={16} />Back to documents</button><div className="panel-heading"><h2>Document preview</h2><span className="badge badge--neutral">Extracted text</span></div><div className="document-body">
        {previewLoading && <p role="status">Loading extracted text...</p>}{previewError && <div className="kb-error" role="alert"><p>{previewError}</p><button className="text-button" onClick={() => { void openDocument(previewId) }}>Retry preview</button></div>}
        {!selected && !previewLoading && !previewError && <p className="page-empty">Select a document or a search citation to review its text.</p>}
        {selected && <><span className="section-label">{selected.format} - {documentStatusLabels[latest?.status ?? selected.status]}</span><h2>{selected.title}</h2><p className="muted">Uploaded {new Date(selected.created_at).toLocaleString()}</p>
          {(previewStale || selected.status === 'processing') && <p className="processing-message">{previewStale ? 'Processing status has changed.' : 'Processing locally. Interrupted jobs are marked failed within 90 seconds when refreshed.'} <button className="text-button" onClick={() => { void openDocument(selected.id) }}>Refresh preview</button></p>}
          {(latest?.error ?? selected.error) && <p className="kb-error" role="alert">{latest?.error ?? selected.error}</p>}{selected.warning && <p className="page-notice">{selected.warning}</p>}
          {selected.segments.map((segment, index) => <article id={`source-segment-${index}`} key={index} className="policy-section"><h3>{segment.page ? `Page ${segment.page}` : segment.section ?? 'Document text'}</h3><p>{segment.text}</p></article>)}
          <details className="advanced-section"><summary>Advanced</summary><dl><div><dt>Document ID</dt><dd>{selected.id}</dd></div><div><dt>SHA-256 content hash</dt><dd>{selected.content_hash}</dd></div><div><dt>Passages</dt><dd>{selected.chunk_count}</dd></div><div><dt>Storage and extraction</dt><dd>Private local files and SQLite. PDF pages and Markdown headings are retained.</dd></div></dl><p>Passages target 1,200 characters with about 180 characters of overlap within each page or section. Reading order in complex PDFs may differ from the original. No OCR, vector search, or generated answers.</p></details>
          <button className="secondary-button kb-delete" disabled={(latest?.status ?? selected.status) === 'processing'} onClick={() => { setDeleteError(''); setConfirmDelete(latest ?? selected) }}>Delete document</button>
        </>}
      </div></section>
    </div>
    <Drawer open={!!confirmDelete} onClose={() => { if (!deleting) setConfirmDelete(null) }} title="Delete document"><div className="kb-delete-confirm"><p>Delete <strong>{confirmDelete?.filename}</strong> from this Knowledge Base?</p><p>This removes its stored file, extracted text, and search passages. Your original file on your computer is unaffected.</p>{deleteError && <p className="kb-error" role="alert">{deleteError}</p>}<div><button className="secondary-button" disabled={deleting} onClick={() => setConfirmDelete(null)}>Cancel</button><button className="primary-button" disabled={deleting} onClick={() => { void remove() }}>{deleting ? 'Deleting...' : 'Confirm deletion'}</button></div></div></Drawer>
  </main>
}
